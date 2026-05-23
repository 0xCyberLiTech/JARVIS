"""Tuile **mode** — sélection du mode JARVIS (soc/general/code/code_reasoning).

Architecture par tuiles (refactor jarvis.py étape 37, 2026-05-23) — 24ème tuile.
**Une seule route** : `/api/mode` GET+POST. Très petite tuile par construction
(le mode est juste un dispatcher haut niveau qui sélectionne le LLM actif via
`ensure_vram`), mais elle mérite sa propre tuile car c'est le point de contact
unique entre l'UI et le routing modèle.

Endpoint exposé (Blueprint `mode`) :
- GET  /api/mode  — retourne {mode, model} courants
- POST /api/mode  — change le mode (valide soc|general|code|code_reasoning) +
                    swap VRAM via ensure_vram pour préload le nouveau modèle

DI via `init(...)` : limiter + log + getter/setter _jarvis_mode +
constantes des 4 modèles + ensure_vram (callable depuis llm/vram.ensure_vram).
"""
from flask import Blueprint

bp = Blueprint("mode", __name__)

from . import routes  # noqa: E402, F401
