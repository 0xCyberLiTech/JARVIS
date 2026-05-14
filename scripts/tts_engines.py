"""TTS engines module — drivers pure des 4 moteurs de synthèse vocale.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 split monolithe (module 3).

Couvre les 4 engines TTS (drivers purs, sans coupling au reste du serveur Flask) :
- edge-tts (cloud Microsoft · async · fr-CA-AntoineNeural défaut)
- Kokoro neural (CUDA · 82M params · 24 kHz mono WAV · lazy load)
- Piper (ONNX · CPU · LRU cache 3 modèles)
- SAPI5 via PowerShell SpeechSynthesizer (Windows fallback)

Les routes Flask, queues `_speak_queue/_speak_deferred`, dedup global, dispatch fallback
chain restent dans jarvis.py car couplés à `apply_dsp_to_mp3()`, `DSP_PARAMS`,
`_chat_stream_active`, `_tts_logger` (logger rotatif dédié).
"""
import asyncio
import io
import logging
import os
import subprocess
import tempfile
import threading
import time
import wave
from collections import OrderedDict
from pathlib import Path

import edge_tts

_log = logging.getLogger("jarvis.tts_engines")

# ── Constantes ────────────────────────────────────────────────
EDGE_DEFAULT_VOICE     = "fr-CA-AntoineNeural"
_EDGE_DNS_RETRY_S      = 1.0
_SAPI5_TIMEOUT_S       = 30
VOICES_DIR             = Path(__file__).parent / "voices"
VOICES_DIR.mkdir(exist_ok=True)
_PIPER_MAX_MODELS      = 3
_KOKORO_VALID_PREFIXES = ("ff_", "fm_", "af_", "am_", "bf_", "bm_")
_KOKORO_DEFAULT_VOICE  = "ff_siwis"

# ── Détection disponibilité top-level ─────────────────────────
try:
    import pyttsx3 as _pyttsx3
    _PYTTSX3_AVAILABLE = True
except ImportError:
    _PYTTSX3_AVAILABLE = False

try:
    from piper import PiperVoice as _PiperVoice
    _PIPER_AVAILABLE = True
except ImportError:
    _PIPER_AVAILABLE = False


# ── Kokoro (lazy load · torch lourd) ──────────────────────────
_KOKORO_AVAILABLE = None  # None = pas encore testé
_KPipeline        = None
_sf               = None
_np_kokoro        = None
_kokoro_pipeline  = None
_kokoro_lock      = threading.Lock()

# ── Piper (LRU cache) ─────────────────────────────────────────
_piper_models = OrderedDict()


# ── Helpers Kokoro ────────────────────────────────────────────

def _normalize_kokoro_voice(voice: str) -> str:
    """Retourne `voice` si le préfixe est valide, sinon le défaut ff_siwis."""
    if voice and len(voice) >= 3 and voice[:3] in _KOKORO_VALID_PREFIXES:
        return voice
    return _KOKORO_DEFAULT_VOICE


def _get_kokoro(lang: str = "f"):
    """Charge lazy le pipeline Kokoro CUDA. Retourne None si indisponible."""
    global _kokoro_pipeline, _KPipeline, _sf, _np_kokoro, _KOKORO_AVAILABLE
    if _KOKORO_AVAILABLE is None:
        try:
            import numpy as _np_mod
            import soundfile as _sf_mod
            from kokoro import KPipeline as _KP
            _KPipeline = _KP
            _sf = _sf_mod
            _np_kokoro = _np_mod
            _KOKORO_AVAILABLE = True
        except Exception as _ke:
            _log.debug(f"[Kokoro] indisponible — {type(_ke).__name__}: {_ke}")
            _KOKORO_AVAILABLE = False
    if not _KOKORO_AVAILABLE:
        return None
    if _kokoro_pipeline is None:
        try:
            _log.info("[TTS-Kokoro] Chargement modèle 82M (CUDA)…")
            _kokoro_pipeline = _KPipeline(lang_code=lang, device="cuda")
            _log.info("[TTS-Kokoro] Prêt.")
        except Exception as _load_err:
            _log.warning(f"[Kokoro] Chargement pipeline échoué ({type(_load_err).__name__}: {_load_err})")
            return None
    return _kokoro_pipeline


# ── Helpers Piper ─────────────────────────────────────────────

def list_piper_models() -> list[str]:
    """Liste les modèles Piper (.onnx) présents dans voices/."""
    return [f.stem for f in VOICES_DIR.glob("*.onnx") if (VOICES_DIR / (f.stem + ".onnx.json")).exists()]


def _get_piper_model(name: str):
    """Charge (lazy) un modèle Piper — LRU cache max _PIPER_MAX_MODELS."""
    global _piper_models
    if name in _piper_models:
        _piper_models.move_to_end(name)
        return _piper_models[name]
    onnx_path = VOICES_DIR / f"{name}.onnx"
    if not onnx_path.exists():
        raise FileNotFoundError(f"Modèle Piper introuvable: {onnx_path}")
    _log.info(f"[TTS-Piper] Chargement {name}…")
    _piper_models[name] = _PiperVoice.load(str(onnx_path))
    _log.info(f"[TTS-Piper] {name} prêt.")
    if len(_piper_models) > _PIPER_MAX_MODELS:
        evicted, _ = _piper_models.popitem(last=False)
        _log.info(f"[TTS-Piper] Déchargement LRU: {evicted}")
    return _piper_models[name]


# ── API publique : disponibilité ──────────────────────────────

def is_kokoro_available() -> bool | None:
    """True/False si testé, None si pas encore testé."""
    return _KOKORO_AVAILABLE


def is_piper_available() -> bool:
    return _PIPER_AVAILABLE


def is_sapi_available() -> bool:
    return _PYTTSX3_AVAILABLE


def list_sapi_voices() -> list[dict]:
    """Liste les voix SAPI5 installées Windows."""
    if not _PYTTSX3_AVAILABLE:
        return []
    try:
        e = _pyttsx3.init()
        voices = [{"id": v.id, "name": v.name} for v in e.getProperty("voices")]
        e.stop()
        return voices
    except Exception:
        return []


# ── API publique : synthèse ───────────────────────────────────

def kokoro_synth(text: str, voice: str = "ff_siwis", speed: float = 1.0) -> bytes:
    """Synthèse Kokoro haute qualité → bytes WAV 24 kHz mono.
    Raises RuntimeError si Kokoro indispo ou pipeline failed."""
    global _kokoro_pipeline
    voice = _normalize_kokoro_voice(voice)
    with _kokoro_lock:
        pipeline = _get_kokoro("f")
        if pipeline is None:
            raise RuntimeError("Kokoro non disponible")
        spd = max(0.5, min(2.0, float(speed)))
        chunks = []
        try:
            for _gs, _ps, audio in pipeline(text, voice=voice, speed=spd):
                chunks.append(audio)
        except Exception as _pipe_err:
            _log.warning(f"[Kokoro] Pipeline erreur ({type(_pipe_err).__name__}: {_pipe_err}) — reset pipeline")
            _kokoro_pipeline = None  # force rechargement propre au prochain appel
            raise
        if not chunks:
            raise RuntimeError("Kokoro n'a produit aucun audio")
        audio_data = _np_kokoro.concatenate(chunks)
        buf = io.BytesIO()
        _sf.write(buf, audio_data, 24000, format="WAV", subtype="PCM_16")
        return buf.getvalue()


def piper_synth(text: str, model_name: str | None = None) -> bytes:
    """Synthèse Piper (neural local) → bytes WAV mono.
    Raises RuntimeError si aucun modèle Piper installé."""
    models = list_piper_models()
    if not models:
        raise RuntimeError("Aucun modèle Piper dans voices/. Téléchargez un modèle via /api/tts/local/download")
    if model_name and (VOICES_DIR / f"{model_name}.onnx").exists():
        name = model_name
    else:
        name = models[0]  # fallback : premier modèle disponible
    voice = _get_piper_model(name)
    chunks = list(voice.synthesize(text))
    if not chunks:
        raise RuntimeError("Piper n'a produit aucun audio")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(chunks[0].sample_channels)
        wf.setsampwidth(chunks[0].sample_width)
        wf.setframerate(chunks[0].sample_rate)
        for ch in chunks:
            wf.writeframes(ch.audio_int16_bytes)
    return buf.getvalue()


def sapi5_synth(text: str, voice_id: str | None = None) -> bytes:
    """Synthèse SAPI5 via PowerShell SpeechSynthesizer → bytes WAV.
    Utilise SelectVoice(name) pour supporter les voix Desktop/Neural Windows 11."""
    import base64
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".wav")
    os.close(tmp_fd)
    # Résoudre ID registre → nom de voix (pour SelectVoice)
    voice_name = None
    if voice_id and _PYTTSX3_AVAILABLE:
        try:
            e = _pyttsx3.init()
            match = next((v for v in e.getProperty("voices") if v.id == voice_id), None)
            if match:
                voice_name = match.name
            e.stop()
        except Exception:
            pass  # voix SAPI non trouvée par ID
    if not voice_name and _PYTTSX3_AVAILABLE:
        try:
            e = _pyttsx3.init()
            match = next((v for v in e.getProperty("voices") if "fr" in (v.id + v.name).lower()), None)
            if match:
                voice_name = match.name
            e.stop()
        except Exception:
            pass  # aucune voix FR disponible dans pyttsx3
    # Encoder le texte en base64 UTF-16-LE (évite tout problème d'échappement PS)
    text_b64 = base64.b64encode(text.encode("utf-16-le")).decode("ascii")
    wav_path = tmp_path.replace("\\", "\\\\")
    voice_sel = f'$s.SelectVoice("{voice_name}")' if voice_name else ''
    ps = (
        f'$bytes=[Convert]::FromBase64String("{text_b64}");'
        f'$t=[System.Text.Encoding]::Unicode.GetString($bytes);'
        f'Add-Type -AssemblyName System.Speech;'
        f'$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;'
        f'{voice_sel};'
        f'$s.Rate=1;'
        f'$s.SetOutputToWaveFile("{wav_path}");'
        f'$s.Speak($t);'
        f'$s.SetOutputToNull();'
        f'$s.Dispose()'
    )
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=_SAPI5_TIMEOUT_S,
        )
        fsize = os.path.getsize(tmp_path)
        if r.returncode != 0 or fsize < 100:
            raise RuntimeError(f"PS SAPI rc={r.returncode} size={fsize}: {r.stderr[:200]}")
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass  # fichier temp peut déjà être supprimé


async def _edge_tts_async(text: str, voice: str = EDGE_DEFAULT_VOICE) -> str:
    """Coroutine edge-tts : écrit le MP3 dans un fichier tmp et retourne son chemin."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    c = edge_tts.Communicate(text, voice)
    c.audio_format = "audio-48khz-96kbitrate-mono-mp3"
    await c.save(tmp)
    return tmp


def edge_generate_mp3(text: str, voice: str = EDGE_DEFAULT_VOICE) -> str:
    """Génère un MP3 via edge-tts avec 3 tentatives. Retourne le chemin tmp.
    Raises Exception (last) après 3 échecs."""
    last_exc = None
    for attempt in range(3):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_edge_tts_async(text, voice))
            loop.close()
            return result
        except Exception as e:
            last_exc = e
            loop.close()
            if attempt < 2:
                # DNS transitoire : attendre 1s avant retry (évite bascule SAPI5 pour erreur passagère)
                delay = _EDGE_DNS_RETRY_S if ("getaddrinfo" in str(e) or "ClientConnectorDNS" in type(e).__name__) else 0.3 * (attempt + 1)
                time.sleep(delay)
    raise last_exc
