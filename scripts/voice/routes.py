"""Routes HTTP de la tuile **voice** — STT + TTS + speak + DSP audio.

Phases B1+B2 du voice tuile (refactor jarvis.py étapes 13-14, 2026-05-23).
Étape 13 = STT routes (api_stt, api_stt_status).
Étape 14 = TTS + speak family (api_speak*, api_tts*, api_tts_local_*).

Endpoints exposés :
- POST /api/stt                  — transcription Whisper local
- GET  /api/stt/status           — statut STT
- POST /api/speak                — déclenche TTS background
- POST /api/speak/stop           — arrêt immédiat TTS
- GET  /api/speak/status         — état queue + stream
- GET  /api/speak/queue          — récupère et vide la queue TTS
- GET  /api/tts-log              — log TTS rotatif (N dernières lignes)
- GET  /api/tts/status           — statut par moteur TTS (edge/kokoro/piper/sapi)
- POST /api/tts                  — synthèse audio (edge cloud + fallback locaux)
- GET  /api/tts/local/voices     — moteurs locaux + voix disponibles
- POST /api/tts/local/download   — download voix Piper depuis HuggingFace
"""
import json
import os
import queue as _queue_mod
import tempfile
import time

from flask import Response, request

from . import audio_dsp, bp, stt, tts_dedup, tts_engines

# Dépendances injectées par __init__.init() — pour les routes TTS/speak.
_log               = None
_tts_logger        = None
_speak_fn          = None              # speak() de jarvis.py (deferred TTS)
_speak_queue       = None              # queue.Queue partagée
_speak_deferred    = None              # queue.Queue partagée
_chat_stream_active = None             # threading.Event
_tts_log_path      = None              # Path
_get_dsp_params    = None              # callable → dict mutable
_get_voice         = None              # callable → str (voix edge-tts active)
_get_internet_up   = None              # callable → bool (edge-tts joignable)
_clean_for_tts     = None              # callable
_tts_log_preview   = 0
_tts_dedup_s       = 0


def init_routes(*,
                log,
                tts_logger=None,
                speak_fn=None,
                speak_queue=None,
                speak_deferred=None,
                chat_stream_active=None,
                tts_log_path=None,
                get_dsp_params=None,
                get_voice=None,
                get_internet_up=None,
                clean_for_tts=None,
                tts_log_preview=200,
                tts_dedup_s=60) -> None:
    """Injecte les dépendances (log obligatoire, le reste optionnel pour phase B1)."""
    global _log, _tts_logger, _speak_fn, _speak_queue, _speak_deferred
    global _chat_stream_active, _tts_log_path, _get_dsp_params, _get_voice
    global _get_internet_up, _clean_for_tts, _tts_log_preview, _tts_dedup_s
    _log               = log
    _tts_logger        = tts_logger
    _speak_fn          = speak_fn
    _speak_queue       = speak_queue
    _speak_deferred    = speak_deferred
    _chat_stream_active = chat_stream_active
    _tts_log_path      = tts_log_path
    _get_dsp_params    = get_dsp_params
    _get_voice         = get_voice
    _get_internet_up   = get_internet_up
    _clean_for_tts     = clean_for_tts
    _tts_log_preview   = tts_log_preview
    _tts_dedup_s       = tts_dedup_s


def _apply_dsp(audio_bytes, df_override=None):
    """Wrapper local — applique le DSP avec DSP_PARAMS accédé via accesseur."""
    return audio_dsp.apply_dsp_to_mp3(audio_bytes, _get_dsp_params(), df_override)


# ─────────────────────────────────────────────────────────────────────────
# STT — Transcription Whisper (Phase B1)
# ─────────────────────────────────────────────────────────────────────────


@bp.route("/api/stt", methods=["POST"])
def api_stt():
    """Transcription audio → texte via Whisper local (hors-ligne)."""
    if request.content_length and request.content_length > stt.get_max_bytes():
        return Response(json.dumps({"error": "Fichier trop volumineux (max 25 MB)"}), status=413, mimetype="application/json")
    if stt.is_available() is False:
        return Response(json.dumps({"error": "faster-whisper non installé. Lancez: pip install faster-whisper"}),
                        status=503, mimetype="application/json")
    f = request.files.get("audio")
    if not f:
        return Response(json.dumps({"error": "Aucun fichier audio"}), status=400, mimetype="application/json")
    lang = request.form.get("lang", "fr")
    raw_ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "webm"
    suffix = "." + (raw_ext if raw_ext in stt.get_allowed_ext() else "webm")
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        os.close(tmp_fd)
        f.save(tmp_path)
        text, language = stt.transcribe(tmp_path, lang=lang)
        return Response(json.dumps({"text": text, "language": language}, ensure_ascii=False),
                        mimetype="application/json")
    except RuntimeError as e:
        return Response(json.dumps({"error": str(e)}), status=503, mimetype="application/json")
    except Exception as e:
        _log.error(f"[STT] Erreur: {e}")
        return Response(json.dumps({"error": "Erreur interne serveur"}), status=500, mimetype="application/json")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # fichier temporaire déjà supprimé ou accès refusé — non bloquant


@bp.route("/api/stt/status")
def api_stt_status():
    """État du module STT."""
    return Response(json.dumps({
        "available": stt.is_available(),
        "loaded": stt.is_loaded(),
        "model": stt.get_model_size() if stt.is_available() else None
    }), mimetype="application/json")


# ─────────────────────────────────────────────────────────────────────────
# Speak / TTS log / TTS status (Phase B2)
# ─────────────────────────────────────────────────────────────────────────


@bp.route("/api/speak", methods=["POST"])
def api_speak():
    data = request.json or {}
    text = data.get("text", "")
    if text:
        source = data.get("source", request.headers.get("Referer", "unknown"))
        preview = text[:_tts_log_preview].replace("\n", " ")
        suffix = "..." if len(text) > _tts_log_preview else ""
        _tts_logger.info("source=%-20s | %s%s", source, preview, suffix)
        _speak_fn(text, blocking=False)
    return Response("{}", mimetype="application/json")


@bp.route("/api/speak/stop", methods=["POST"])
def api_speak_stop():
    """Arrête immédiatement la lecture TTS en cours (WinMM) et vide les queues."""
    try:
        import ctypes
        winmm = ctypes.WinDLL("winmm")
        winmm.mciSendStringW("stop all", None, 0, None)
        winmm.mciSendStringW("close all", None, 0, None)
    except Exception as e:
        _log.info(f"[TTS-stop] {e}")
    drained = 0
    for q in (_speak_queue, _speak_deferred):
        try:
            while True:
                q.get_nowait()
                drained += 1
        except _queue_mod.Empty:
            pass
    return Response(json.dumps({"ok": True, "drained": drained}), mimetype="application/json")


@bp.route("/api/speak/status", methods=["GET"])
def api_speak_status():
    """État complet TTS : queue principale, deferred et stream SSE actif."""
    queued   = _speak_queue.qsize()
    deferred = _speak_deferred.qsize()
    streaming = _chat_stream_active.is_set()
    return Response(json.dumps({
        "speaking":      queued > 0 or deferred > 0 or streaming,
        "queued":        queued,
        "deferred":      deferred,
        "stream_active": streaming,
    }), mimetype="application/json")


@bp.route("/api/speak/queue", methods=["GET"])
def api_speak_queue():
    """Retourne et vide la queue TTS Python — le browser joue chaque item via queueSpeech."""
    items = []
    try:
        while True:
            items.append(_speak_queue.get_nowait())
    except _queue_mod.Empty:
        pass
    return Response(json.dumps({"items": items}), mimetype="application/json")


@bp.route("/api/tts-log", methods=["GET"])
def api_tts_log():
    """Retourne les N dernières lignes du log TTS rotatif."""
    try:
        n = min(int(request.args.get("n", 50)), 500)
    except (ValueError, TypeError):
        n = 50
    lines = []
    if _tts_log_path.exists():
        try:
            with open(_tts_log_path, encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            pass
    tail = [ln.rstrip("\n") for ln in lines[-n:]]
    return Response(json.dumps({"lines": tail, "total": len(lines), "file": str(_tts_log_path)}, ensure_ascii=False), mimetype="application/json")


@bp.route("/api/tts/status", methods=["GET"])
def api_tts_status():
    """État opérationnel de chaque moteur TTS."""
    _kok = tts_engines.is_kokoro_available()
    _pip = tts_engines.is_piper_available()
    _sap = tts_engines.is_sapi_available()
    return Response(json.dumps({
        "edge":   {"ok": bool(_get_internet_up()), "label": "EN SERVICE" if _get_internet_up() else "ARRÊTÉ"},
        "kokoro": {"ok": _kok is True, "label": "EN SERVICE" if _kok is True else ("CHARGEMENT" if _kok is None else "ARRÊTÉ")},
        "piper":  {"ok": bool(_pip), "label": "EN SERVICE" if _pip else "ARRÊTÉ"},
        "sapi":   {"ok": bool(_sap), "label": "EN SERVICE" if _sap else "ARRÊTÉ"},
    }, ensure_ascii=False), mimetype="application/json")


def _tts_wav_response(wav, mime):
    return Response(wav, mimetype=mime,
                    headers={"Content-Length": str(len(wav)), "Cache-Control": "no-cache"})


def _tts_local_response(engine, text, local_voice):
    """Tente un moteur TTS local. Retourne Response ou None si moteur indisponible."""
    try:
        if engine == "kokoro" and tts_engines.is_kokoro_available() is not False:
            _spd = float(_get_dsp_params().get("tts_kokoro_speed", 1.0))
            try:
                wav, mime = _apply_dsp(tts_engines.kokoro_synth(text, local_voice, _spd))
                return _tts_wav_response(wav, mime)
            except Exception as ke:
                _log.warning(f"[Kokoro] Echec synthese ({type(ke).__name__}: {ke}) — fallback edge-tts")
                return None
        if engine == "piper" and tts_engines.is_piper_available():
            wav, mime = _apply_dsp(tts_engines.piper_synth(text, local_voice or None))
            return _tts_wav_response(wav, mime)
        if engine == "sapi" and tts_engines.is_sapi_available():
            wav, mime = _apply_dsp(tts_engines.sapi5_synth(text, local_voice or None))
            return _tts_wav_response(wav, mime)
    except Exception as e:
        _log.error(f"[JARVIS] Erreur interne: {e}")
        return Response(json.dumps({"error": "Erreur interne serveur"}), status=500, mimetype="application/json")
    return None


def _tts_edge_fallback(text, local_voice):
    """Chaîne de fallback après échec edge-tts : Kokoro → Piper → SAPI5 → erreur 503."""
    if tts_engines.is_kokoro_available() is not False:
        try:
            _spd = float(_get_dsp_params().get("tts_kokoro_speed", 1.0))
            wav, mime = _apply_dsp(tts_engines.kokoro_synth(text, local_voice, _spd))
            _tts_logger.warning("[FALLBACK] Kokoro utilisé à la place de edge-tts (internet KO)")
            return _tts_wav_response(wav, mime)
        except Exception as ke:
            _log.info(f"[JARVIS] Kokoro fallback échoué: {ke}")
    if tts_engines.is_piper_available():
        try:
            wav, mime = _apply_dsp(tts_engines.piper_synth(text, local_voice or None))
            _tts_logger.warning("[FALLBACK] Piper utilisé à la place de edge-tts")
            return _tts_wav_response(wav, mime)
        except Exception as pe:
            _log.info(f"[JARVIS] Piper fallback échoué: {pe}")
    if tts_engines.is_sapi_available():
        try:
            wav, mime = _apply_dsp(tts_engines.sapi5_synth(text, None))
            _tts_logger.warning("[FALLBACK] SAPI5 (Microsoft) utilisé à la place de edge-tts")
            return _tts_wav_response(wav, mime)
        except Exception as se:
            _log.info(f"[JARVIS] SAPI5 fallback échoué: {se}")
    return Response(
        json.dumps({"error": "TTS indisponible — edge-tts hors ligne, aucun moteur local actif"}),
        status=503, mimetype="application/json"
    )


@bp.route("/api/tts", methods=["POST"])
def api_tts():
    _perf_t0 = time.monotonic()
    data = request.json or {}
    text = _clean_for_tts(data.get("text", ""))
    if not text:
        return Response("{}", mimetype="application/json", status=400)
    source = data.get("source", request.headers.get("Referer", "unknown"))
    now = time.monotonic()
    if tts_dedup.check_and_register(text, now):
        _log.debug(f"[TTS] Dedup global skip (/api/tts, même texte < {_tts_dedup_s}s) : {text[:80]}")
        return Response('{"dedup":true}', mimetype="application/json", status=200)
    preview = text[:_tts_log_preview].replace("\n", " ")
    _tts_logger.info("source=%-20s | %s%s", source, preview, "..." if len(text) > _tts_log_preview else "")
    engine      = _get_dsp_params().get("tts_engine", "edge")
    local_voice = _get_dsp_params().get("tts_local_voice", "")

    local_resp = _tts_local_response(engine, text, local_voice)
    if local_resp is not None:
        _log.info(f"[TTS-PERF] /api/tts engine={engine} (local) total={time.monotonic() - _perf_t0:.2f}s chars={len(text)}")
        return local_resp

    try:
        _t_edge = time.monotonic()
        tmp_path = tts_engines.edge_generate_mp3(text, _get_voice())
        _perf_edge = time.monotonic() - _t_edge
        with open(tmp_path, "rb") as f:
            audio_data = f.read()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        _t_dsp = time.monotonic()
        audio_data, mime = _apply_dsp(audio_data)
        _perf_dsp = time.monotonic() - _t_dsp
        _log.info(f"[TTS-PERF] /api/tts engine=edge edge_gen={_perf_edge:.2f}s dsp={_perf_dsp:.2f}s total={time.monotonic() - _perf_t0:.2f}s chars={len(text)}")
        return _tts_wav_response(audio_data, mime)
    except Exception as edge_err:
        _log.warning(f"[JARVIS] edge-tts indisponible ({type(edge_err).__name__}: {edge_err}) — bascule TTS local")
        _tts_logger.warning(f"[FALLBACK] edge-tts échec ({type(edge_err).__name__}) — tentative moteur local")
        _fallback_resp = _tts_edge_fallback(text, local_voice)
        _log.info(f"[TTS-PERF] /api/tts engine=edge→fallback-local total={time.monotonic() - _perf_t0:.2f}s chars={len(text)}")
        return _fallback_resp


@bp.route("/api/tts/local/voices")
def api_tts_local_voices():
    """Liste les moteurs TTS locaux et voix disponibles."""
    _kok = tts_engines.is_kokoro_available()
    _pip = tts_engines.is_piper_available()
    _sap = tts_engines.is_sapi_available()
    dsp = _get_dsp_params()
    result = {
        "kokoro": {"available": _kok, "voices": [
            {"id": "ff_siwis", "name": "Siwis (FR féminine) — très haute qualité"},
        ] if _kok else []},
        "piper": {"available": _pip, "models": tts_engines.list_piper_models() if _pip else []},
        "sapi":  {"available": _sap, "voices": tts_engines.list_sapi_voices()},
        "current_engine": dsp.get("tts_engine", "kokoro"),
        "current_voice":  dsp.get("tts_local_voice", "ff_siwis"),
    }
    return Response(json.dumps(result, ensure_ascii=False), mimetype="application/json")


@bp.route("/api/tts/local/download", methods=["POST"])
def api_tts_local_download():
    """Télécharge un modèle Piper depuis HuggingFace (internet requis une seule fois)."""
    data = request.json or {}
    voice_name = data.get("voice", "fr_FR-upmc-medium")
    try:
        import shutil as _shutil

        from huggingface_hub import hf_hub_download
        _HF_MAP = {
            "fr_FR-upmc-medium":   "fr/fr_FR/upmc/medium",
            "fr_FR-siwis-medium":  "fr/fr_FR/siwis/medium",
            "fr_FR-mls-medium":    "fr/fr_FR/mls/medium",
            "fr_FR-mls_1840-low":  "fr/fr_FR/mls_1840/low",
        }
        hf_subdir = _HF_MAP.get(voice_name)
        if not hf_subdir:
            return Response(json.dumps({"error": f"Voix inconnue: {voice_name}. Choisir parmi: {list(_HF_MAP.keys())}"}),
                            status=400, mimetype="application/json")
        downloaded = []
        for fname in [f"{voice_name}.onnx", f"{voice_name}.onnx.json"]:
            path = hf_hub_download(repo_id="rhasspy/piper-voices",
                                   filename=f"{hf_subdir}/{fname}")
            dest = tts_engines.VOICES_DIR / fname
            if str(path) != str(dest):
                _shutil.copy2(path, dest)
            downloaded.append(str(dest))
        return Response(json.dumps({"ok": True, "model": voice_name, "files": downloaded}), mimetype="application/json")
    except Exception as e:
        _log.error(f"[JARVIS] Erreur interne: {e}")
        return Response(json.dumps({"error": "Erreur interne serveur"}), status=500, mimetype="application/json")
