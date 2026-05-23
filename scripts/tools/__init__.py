"""Tuile **tools** — outils LLM exécutés localement par le dispatcher chat.

Architecture par tuiles (refactor jarvis.py étape 33, 2026-05-23) — 21ème tuile.
**Pas de routes HTTP** — uniquement des fonctions appelées par le tool dispatch
chat (`_TOOL_DISPATCH` côté jarvis.py) quand le LLM émet un tool_call.

Sous-modules :
- `local` : 3 outils exécutés en local Windows
  - `executer_code(args)`           — exécute du Python via subprocess + whitelist
  - `soc_status()`                   — invoke monitoring.json + formate contexte SOC
  - `executer_script_windows(args)`  — exécute PowerShell whitelist stricte

DI via `init(...)` au câblage côté jarvis.py — chaque sous-module gère ses deps.
"""
from . import local  # noqa: F401
