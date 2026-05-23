"""Tuile **chat** — pipeline LLM (orchestration, streaming, tools, mémoire).

Architecture par tuiles (refactor jarvis.py étape 10 phase A, 2026-05-23) —
8ème tuile. Cette phase regroupe les 9 sous-modules déjà extraits à plat
dans un dossier dédié. La phase B (étape 11) extraira la route `/api/chat`
et les helpers `_chat_*` encore dans `jarvis.py`.

Sous-modules (regroupés ici, pas modifiés sur le fond) :
- `capture`         : capture du SSE generator pour persistance historique
- `generate`        : wrapper Ollama `/api/generate` (réponse one-shot)
- `messages`        : build du payload messages (modes, ctx, vocal, overrides)
- `pending_bypass`  : résolution des bypass différés (ex: confirmation user)
- `routing`         : résolution modèle actif selon mode + override
- `soc_inject`      : injection bloc compact SOC dans system prompt (mode SOC)
- `stream`          : streaming SSE Ollama → client navigateur
- `system_prompt`   : assemblage du system prompt final (profil + facts + RAG)
- `tool_calls`      : dispatch des appels d'outils LLM (file/ssh/code/…)

Pas de fonction `init()` à ce niveau : chaque sous-module gère ses propres
dépendances via signatures de fonctions (DI per-call, pas global state).
"""
from . import (  # noqa: F401
    capture,
    generate,
    messages,
    orchestrator,
    pending_bypass,
    routing,
    soc_inject,
    stream,
    system_prompt,
    tool_calls,
)
