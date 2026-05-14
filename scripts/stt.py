"""STT module — Whisper local (faster-whisper) avec initial_prompt SOC.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 split monolithe.
Couvre : chargement lazy du modèle CUDA (large-v3-turbo · int8) + transcription
audio avec vocabulaire SOC injecté pour améliorer la reconnaissance jargon homelab.
"""
import logging
import threading

_log = logging.getLogger("jarvis.stt")

# ── Constantes ────────────────────────────────────────────────
_WHISPER_MODEL_SIZE = "large-v3-turbo"
_STT_INITIAL_PROMPT = (
    "CrowdSec, fail2ban, Suricata, Proxmox, nginx, Apache, JARVIS, SSH, VRAM, GPU, RTX, "
    "Ollama, phi4, qwen, deepseek, gemma, IPv4, firewall, systemctl, journalctl, apt, "
    "nftables, iptables, monitoring, dashboard, SOC, cybersécurité, homelab"
)
_STT_MAX_BYTES   = 25_000_000  # 25 MB — fichiers audio compressés
_STT_ALLOWED_EXT = {"webm", "wav", "mp3", "ogg", "flac", "m4a", "mp4", "opus"}

# ── State ─────────────────────────────────────────────────────
_WHISPER_AVAILABLE = None   # None = pas encore testé, True/False = résultat
_WhisperModel      = None   # importé à la première utilisation
_whisper_model     = None
_WHISPER_LOAD_LOCK = threading.Lock()


def _get_whisper():
    """Charge lazy le modèle Whisper (thread-safe via double-check + lock)."""
    global _whisper_model, _WhisperModel, _WHISPER_AVAILABLE
    if _whisper_model is not None:
        return _whisper_model
    with _WHISPER_LOAD_LOCK:
        if _whisper_model is not None:
            return _whisper_model
        if _WHISPER_AVAILABLE is None:
            try:
                from faster_whisper import WhisperModel as _WM
                _WhisperModel = _WM
                _WHISPER_AVAILABLE = True
            except ImportError:
                _WHISPER_AVAILABLE = False
        if not _WHISPER_AVAILABLE:
            return None
        _log.info(f"[STT] Chargement modèle Whisper '{_WHISPER_MODEL_SIZE}'…")
        try:
            import ctranslate2 as _ct2
            _stt_device = "cuda" if _ct2.get_cuda_device_count() > 0 else "cpu"
        except Exception:
            _stt_device = "cpu"
        _stt_compute = "int8"  # large-v3-turbo ~1 GB VRAM — coexiste avec phi4:14b sur RTX 5080 16 GB
        _whisper_model = _WhisperModel(_WHISPER_MODEL_SIZE, device=_stt_device, compute_type=_stt_compute)
        _log.info(f"[STT] Modèle prêt — device={_stt_device} compute={_stt_compute}")
    return _whisper_model


# ── API publique ──────────────────────────────────────────────

def is_available() -> bool | None:
    """Retourne True/False si testé, None si pas encore testé."""
    return _WHISPER_AVAILABLE


def is_loaded() -> bool:
    """True si le modèle Whisper est chargé en mémoire."""
    return _whisper_model is not None


def get_model_size() -> str:
    return _WHISPER_MODEL_SIZE


def get_max_bytes() -> int:
    return _STT_MAX_BYTES


def get_allowed_ext() -> set[str]:
    return _STT_ALLOWED_EXT


def transcribe(audio_path: str, lang: str = "fr") -> tuple[str, str]:
    """Transcrit un fichier audio. Retourne (text, language_detected).

    Raises RuntimeError si Whisper indispo (faster-whisper non installé).
    """
    model = _get_whisper()
    if model is None:
        raise RuntimeError("faster-whisper non installé. Lancez: pip install faster-whisper")
    segments, info = model.transcribe(
        audio_path, language=lang, beam_size=2,
        vad_filter=True, initial_prompt=_STT_INITIAL_PROMPT,
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text, info.language
