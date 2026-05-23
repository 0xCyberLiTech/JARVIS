"""Routes HTTP de la tuile **rag** — index documentaire local.

Endpoints exposés :
- GET    /api/rag/status      — chunks indexés + sources + modèle d'embedding
- POST   /api/rag/note        — append d'une note libre dans l'index
- POST   /api/rag/index-file  — indexation d'un fichier disque
- DELETE /api/rag/clear       — purge totale (meta + embeddings)
- POST   /api/rag/refresh     — re-indexe les MEMORY.md du workspace
"""
import datetime
import json
from pathlib import Path

from flask import Response, request

from . import bp, engine

_get_refresh_paths: object = None
_log:               object = None


def init_routes(*, get_refresh_paths, log) -> None:
    """Injecte la liste des MEMORY.md à re-indexer + le logger."""
    global _get_refresh_paths, _log
    _get_refresh_paths = get_refresh_paths
    _log               = log


@bp.route("/api/rag/status", methods=["GET"])
def api_rag_status():
    meta, _ = engine._rag_load()
    sources  = list({m.get("source", "?") for m in meta})
    return Response(
        json.dumps({"chunks": len(meta), "sources": sources,
                    "embed_model": engine._embed_model}, ensure_ascii=False),
        mimetype="application/json")


@bp.route("/api/rag/note", methods=["POST"])
def api_rag_add_note():
    data    = request.json or {}
    content = data.get("content", "").strip()
    if not content:
        return Response('{"error":"content required"}', status=400, mimetype="application/json")
    source = data.get("source", f"note/{datetime.date.today().isoformat()}")
    added  = engine._rag_index_text(content, source)
    return Response(json.dumps({"ok": True, "chunks_added": added}), mimetype="application/json")


@bp.route("/api/rag/index-file", methods=["POST"])
def api_rag_index_file():
    data = request.json or {}
    path = data.get("path", "")
    if not path:
        return Response('{"error":"path required"}', status=400, mimetype="application/json")
    try:
        p = Path(path)
        if not p.exists() or not p.is_file():
            return Response('{"error":"file not found"}', status=404, mimetype="application/json")
        text  = p.read_text(encoding="utf-8", errors="ignore")
        added = engine._rag_index_text(text, p.name)
        return Response(json.dumps({"ok": True, "chunks_added": added, "file": p.name}), mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")


@bp.route("/api/rag/clear", methods=["DELETE"])
def api_rag_clear():
    try:
        if engine._rag_meta_file.exists(): engine._rag_meta_file.unlink()
        if engine._rag_emb_file.exists():  engine._rag_emb_file.unlink()
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")
    return Response('{"ok":true}', mimetype="application/json")


@bp.route("/api/rag/refresh", methods=["POST"])
def api_rag_refresh():
    """Re-indexe les MEMORY.md du workspace. MD5 déduplique — safe à appeler plusieurs fois."""
    total, refreshed = 0, []
    for path_str in _get_refresh_paths():
        p = Path(path_str)
        if p.exists():
            try:
                n = engine._rag_index_text(p.read_text(encoding="utf-8", errors="ignore"), p.name)
                total += n
                if n > 0:
                    refreshed.append(f"{p.name}(+{n})")
            except Exception as e:
                _log.warning(f"[RAG] refresh {p.name}: {e}")
    return Response(json.dumps({"ok": True, "chunks_added": total, "refreshed": refreshed}),
                    mimetype="application/json")
