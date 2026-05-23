"""Tuile **runtime** — helpers d'exécution partagés (GPU, stats, speak).

Architecture par tuiles (refactor jarvis.py étape 31, 2026-05-23) — 19ème tuile.
**Pas de routes HTTP** — uniquement des helpers consommés par plusieurs autres
tuiles (system, health, voice, chat, bootstrap), historiquement définis dans
jarvis.py et passés en DI.

Sous-modules :
- `gpu_stats` : `get_stats()` + `_gpu_cuda_procs` + `_gpu_extended_stats`
                (état local : `_net_prev`, `_disk_prev`, `_STATS_LOCK`)
- `speak`     : `speak()` (état local : `_speak_queue`, `_speak_deferred`,
                `_chat_stream_active`, dedup intra-source 3 s)

Chaque sous-module gère son DI via `init(...)` au câblage côté jarvis.py.
"""
from . import gpu_stats, speak  # noqa: F401
