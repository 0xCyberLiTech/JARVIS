"""Tuile **memory** — mémoire conversationnelle (historique + résumés long terme).

Architecture par tuiles (refactor jarvis.py étape 4, 2026-05-23) — 2ème tuile
après `system/`. Autoportante : zéro import vers `jarvis.py`. Toutes les
dépendances passent par `init()`.

Public surface :
- `bp`     : Flask Blueprint à enregistrer dans l'ossature.
- `init()` : injection unique des dépendances + rate limits.

Sous-modules :
- `store`  : persistance + résumé Ollama (load/save/summarize/append).
- `routes` : 6 endpoints `/api/memory*` qui exposent le store côté HTTP.
"""
from flask import Blueprint

bp = Blueprint("memory", __name__)

from . import routes, store  # noqa: E402,F401

# Rate limits par view function (appliqués dans init() après injection du limiter).
_ROUTE_LIMITS = {
    "api_memory_get":                "60 per minute",
    "api_memory_save":               "30 per minute",
    "api_memory_clear":              "10 per minute",
    "api_memory_summary_get":        "60 per minute",
    "api_memory_summary_clear":      "5 per minute",
    "api_memory_summarize_session":  "10 per minute",
}


def init(*, limiter, ollama_url, ollama_circuit, log,
         get_memory_file, get_summary_file, get_model, get_mode,
         memory_limit, summary_keep, summary_min_msgs,
         general_model, code_model, get_corrections_file=None) -> None:
    """Injecte toutes les dépendances de la tuile et applique les rate limits."""
    # 1) Brique store (DI initialisée à l'étape 2 du refactor jarvis.py)
    store.init(
        get_memory_file  = get_memory_file,
        get_summary_file = get_summary_file,
        get_model        = get_model,
        get_mode         = get_mode,
        memory_limit     = memory_limit,
        summary_keep     = summary_keep,
        summary_min_msgs = summary_min_msgs,
        general_model    = general_model,
        code_model       = code_model,
        ollama_url       = ollama_url,
        ollama_circuit   = ollama_circuit,
        log              = log,
    )
    # 2) Routes (accesseurs fichier + log + seuil min msgs)
    routes.init_routes(
        get_memory_file       = get_memory_file,
        get_summary_file      = get_summary_file,
        summary_min_msgs      = summary_min_msgs,
        log                   = log,
        get_corrections_file  = get_corrections_file,
    )
    # 3) Rate limits par route
    for fn_name, limit_str in _ROUTE_LIMITS.items():
        fn = getattr(routes, fn_name, None)
        if fn is not None:
            limiter.limit(limit_str)(fn)
