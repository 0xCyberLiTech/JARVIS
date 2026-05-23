"""Routes HTTP de la tuile **voice** — STT (Whisper) pour l'instant.

Phase B1 du voice tuile (refactor jarvis.py étape 13, 2026-05-23) : on
extrait les routes STT en premier (le plus net, 2 endpoints, zéro state
mutable cross-route). Les routes TTS/speak/voice_lab seront extraites dans
les étapes 14-16.

Endpoints exposés :
- POST /api/stt        — transcription audio → texte (Whisper local hors-ligne)
- GET  /api/stt/status — disponibilité + modèle chargé
"""
import json
import os
import tempfile

from flask import Response, request

from . import bp, stt

# Dépendance injectée par __init__.init()
_log = None


def init_routes(*, log) -> None:
    """Injecte le logger (les routes STT n'ont pas d'autre dépendance externe)."""
    global _log
    _log = log


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
