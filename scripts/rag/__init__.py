"""Tuile **rag** — Retrieval Augmented Generation local.

Architecture par tuiles (refactor jarvis.py étape 5, 2026-05-23) — 3ème tuile
après `system/` et `memory/`. Autoportante : zéro import vers `jarvis.py`.

Public surface :
- `bp`     : Flask Blueprint à enregistrer dans l'ossature.
- `init()` : injection unique des dépendances + rate limits.

Sous-modules :
- `engine` : moteur RAG (chunk, embed, BM25, recherche hybride, index/inject).
- `routes` : 5 endpoints `/api/rag/*` qui exposent l'engine côté HTTP.
"""
from flask import Blueprint

bp = Blueprint("rag", __name__)

from . import engine, routes  # noqa: E402,F401

_ROUTE_LIMITS = {
    "api_rag_status":     "60 per minute",
    "api_rag_add_note":   "10 per minute",
    "api_rag_index_file": "5 per minute",
    "api_rag_clear":      "5 per minute",
    "api_rag_refresh":    "3 per minute",
}


def init(*, limiter, log, ollama_circuit, ollama_url, embed_model, embed_timeout_s,
         chunk_size, chunk_over, top_n, threshold,
         rag_dir, rag_meta_file, rag_emb_file,
         live_mod, ssh_ngix, ssh_log_timeout_s,
         get_refresh_paths) -> None:
    """Injecte toutes les dépendances de la tuile et applique les rate limits."""
    engine.init(
        ollama_circuit    = ollama_circuit,
        ollama_url        = ollama_url,
        embed_model       = embed_model,
        embed_timeout_s   = embed_timeout_s,
        chunk_size        = chunk_size,
        chunk_over        = chunk_over,
        top_n             = top_n,
        threshold         = threshold,
        rag_dir           = rag_dir,
        rag_meta_file     = rag_meta_file,
        rag_emb_file      = rag_emb_file,
        live_mod          = live_mod,
        ssh_ngix          = ssh_ngix,
        ssh_log_timeout_s = ssh_log_timeout_s,
        log               = log,
    )
    routes.init_routes(get_refresh_paths=get_refresh_paths, log=log)
    for fn_name, limit_str in _ROUTE_LIMITS.items():
        fn = getattr(routes, fn_name, None)
        if fn is not None:
            limiter.limit(limit_str)(fn)
