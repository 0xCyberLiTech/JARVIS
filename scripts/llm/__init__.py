"""Tuile **llm** — gestion VRAM Ollama + stream chat + filtre think.

Architecture par tuiles (refactor jarvis.py étape 35, 2026-05-23) — 23ème tuile.
**Pas de routes HTTP** — uniquement le cœur runtime LLM consommé par
`chat/orchestrator` et `api_mode` :

Sous-modules :
- `vram`   : `ensure_vram(next_model)` + `ollama_swap(unload, load)` — gère le
             swap synchrone des modèles dans la VRAM (unload sync + preload
             async) pour éviter le split VRAM/RAM lors du routing inter-modes
- `stream` : `stream_llm(messages, ...)` + `_think_filter_step` — generator
             SSE qui appelle Ollama `/api/chat` en streaming, filtre les blocs
             `<think>...</think>` des modèles de raisonnement (phi4-reasoning,
             deepseek-r1, qwen3) avant émission au client

Chaque sous-module gère son DI via `init(...)` au câblage côté jarvis.py.
"""
from . import stream, vram  # noqa: F401
