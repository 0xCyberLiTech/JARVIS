"""Tuile **vision** — analyse d'image multimodale via gemma4 (LLaVA-style).

Architecture par tuiles (refactor jarvis.py étape 16, 2026-05-23) — 10ème
tuile. Autoportante : zéro import vers `jarvis.py`.

Public surface :
- `bp`     : Flask Blueprint à enregistrer dans l'ossature.
- `init()` : injection unique des dépendances + rate limits.

Sous-modules :
- `llava`  : ex-vision.py. Stream pipeline (RAG-injected) + stream direct.
- `routes` : endpoint `/api/vision`.

Ré-exports backward-compat (consommateurs externes `from vision import X`) :
"""
from flask import Blueprint

from . import llava

# Ré-exports pour les tests/consommateurs qui faisaient `from vision import X`
DEFAULT_PIPELINE_SYSTEM = llava.DEFAULT_PIPELINE_SYSTEM
DEFAULT_TEMPERATURE     = llava.DEFAULT_TEMPERATURE
MODEL                   = llava.MODEL
stream_pipeline         = llava.stream_pipeline
stream_direct           = llava.stream_direct
_log                    = llava._log

bp = Blueprint("vision", __name__)

from . import routes  # noqa: E402,F401


def init(*, limiter, ollama_url, vision_timeout_s, sse_headers, rag_inject_fn) -> None:
    """Injecte les dépendances de la route /api/vision + applique le rate limit."""
    routes.init_routes(
        ollama_url       = ollama_url,
        vision_timeout_s = vision_timeout_s,
        sse_headers      = sse_headers,
        rag_inject_fn    = rag_inject_fn,
    )
    limiter.limit("5 per minute")(routes.api_vision)
