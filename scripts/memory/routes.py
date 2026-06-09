"""Routes HTTP de la tuile **memory** — historique conv. + résumés long terme.

Endpoints exposés :
- GET    /api/memory               — historique complet
- POST   /api/memory                — append + persistance
- DELETE /api/memory                — purge fichier
- GET    /api/memory-summary        — bloc des résumés bruts
- DELETE /api/memory-summary        — purge résumés
- POST   /api/memory/summarize-session — déclenche un résumé immédiat (stop_jarvis.bat)
"""
import json

from flask import Response, request

from . import bp, store

# Accesseurs injectés par __init__.init() (lambdas → suivent les
# monkeypatch de test sur MEMORY_FILE / SUMMARY_FILE).
_get_memory_file:    object = None
_get_summary_file:   object = None
_summary_min_msgs:   int = 5
_log:                object = None


def init_routes(*, get_memory_file, get_summary_file, summary_min_msgs, log) -> None:
    """Injecte les accesseurs fichier + constantes consommées par les routes."""
    global _get_memory_file, _get_summary_file, _summary_min_msgs, _log
    _get_memory_file  = get_memory_file
    _get_summary_file = get_summary_file
    _summary_min_msgs = summary_min_msgs
    _log              = log


@bp.route("/api/memory", methods=["GET"])
def api_memory_get():
    return Response(json.dumps(store.load_memory(), ensure_ascii=False), mimetype="application/json")


@bp.route("/api/memory", methods=["POST"])
def api_memory_save():
    history = (request.json or {}).get("history", [])
    store.save_memory(history)
    return Response('{"ok":true}', mimetype="application/json")


@bp.route("/api/memory", methods=["DELETE"])
def api_memory_clear():
    try:
        f = _get_memory_file()
        if f.exists():
            f.unlink()
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING clear_memory: {e}")
    return Response('{"ok":true}', mimetype="application/json")


@bp.route("/api/memory-summary", methods=["GET"])
def api_memory_summary_get():
    try:
        f = _get_summary_file()
        data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"summaries": []}
    except Exception:
        data = {"summaries": []}
    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/json")


@bp.route("/api/memory-summary", methods=["DELETE"])
def api_memory_summary_clear():
    try:
        f = _get_summary_file()
        if f.exists():
            f.unlink()
    except Exception as e:
        _log.warning(f"[SUMMARY] Erreur suppression: {e}")
    return Response('{"ok":true}', mimetype="application/json")


@bp.route("/api/memory/stats", methods=["GET"])
def api_memory_stats():
    """Stats légères — count échanges, taille fichier, count résumés. Zéro chargement LLM."""
    try:
        f = _get_memory_file()
        if f.exists():
            size_kb  = round(f.stat().st_size / 1024, 1)
            msgs     = json.loads(f.read_text(encoding="utf-8-sig"))
            count    = len(msgs) if isinstance(msgs, list) else 0
        else:
            size_kb, count = 0.0, 0
    except Exception:
        size_kb, count = 0.0, 0
    try:
        sf = _get_summary_file()
        data = json.loads(sf.read_text(encoding="utf-8")) if sf.exists() else {}
        summary_count = len(data.get("summaries", []))
    except Exception:
        summary_count = 0
    return Response(
        json.dumps({"count": count, "size_kb": size_kb, "summary_count": summary_count},
                   ensure_ascii=False),
        mimetype="application/json")


@bp.route("/api/memory/summarize-session", methods=["POST"])
def api_memory_summarize_session():
    """Résume la session courante et l'appende à jarvis_memory_summary.json.
    Appelé par stop_jarvis.bat avant taskkill — garantit la mémoire longue."""
    messages = store.load_memory()
    if len(messages) < _summary_min_msgs:
        return Response(
            json.dumps({"ok": False, "reason": "not_enough_messages", "count": len(messages)}),
            mimetype="application/json")
    summary = store._summarize_messages(messages)
    if not summary:
        # Fallback : extrait brut des derniers échanges si Ollama ne répond pas
        lines = []
        for m in messages[-10:]:
            role = "Marc" if m["role"] == "user" else "JARVIS"
            lines.append(f"• {role}: {m['content'][:200]}")
        summary = "[Résumé brut — LLM indisponible]\n" + "\n".join(lines)
        _log.warning("[SUMMARY] LLM timeout — fallback extrait brut sauvegardé")
    store._append_memory_summary(summary)
    _log.info(f"[SUMMARY] Résumé session — {len(messages)} messages → {len(summary)} chars")
    return Response(json.dumps({"ok": True, "messages": len(messages), "chars": len(summary)}),
                    mimetype="application/json")
