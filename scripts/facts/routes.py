"""Routes /api/facts — GET (list) + POST (save).

Extrait de jarvis.py étape 32 (2026-05-23). Stockage simple JSON sur disque,
pas de cache (volume négligeable, lecture/écriture instantanée).
"""
import datetime
import json
from pathlib import Path

from flask import Response, request

from . import bp

# DI placeholders
_limiter = None
_facts_file: Path | None = None


def init(*, limiter, facts_file: Path) -> None:
    """Injecte limiter + chemin du fichier jarvis_facts.json."""
    global _limiter, _facts_file
    _limiter = limiter
    _facts_file = facts_file
    _limiter.limit("60 per minute")(api_facts_get)
    _limiter.limit("30 per minute")(api_facts_save)


@bp.route("/api/facts", methods=["GET"])
def api_facts_get():
    try:
        data = json.loads(_facts_file.read_text(encoding="utf-8")) if _facts_file.exists() else {"facts": []}
    except Exception:
        data = {"facts": []}
    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/json")


@bp.route("/api/facts", methods=["POST"])
def api_facts_save():
    payload = request.json if isinstance(request.json, dict) else {}
    facts = payload.get("facts", [])
    if not isinstance(facts, list):
        return Response('{"error":"facts must be a list"}', status=400, mimetype="application/json")
    data = {"updated_at": datetime.date.today().isoformat(), "facts": facts}
    try:
        _facts_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")
    return Response('{"ok":true}', mimetype="application/json")
