"""Tuile **facts** — gestion des faits utilisateur injectés dans le prompt.

Architecture par tuiles (refactor jarvis.py étape 32, 2026-05-23) — 20ème tuile.
Stocke les faits personnels que l'utilisateur veut systématiquement injecter
dans le system prompt (préférences, contexte projet, etc.) dans
`jarvis_facts.json` à la racine `scripts/`.

Endpoints exposés (Blueprint `facts`) :
- GET  /api/facts  — liste des faits + date de dernière mise à jour
- POST /api/facts  — remplace l'ensemble des faits (validation : doit être une liste)

DI via `init(limiter, facts_file)` : limiter Flask + chemin du fichier JSON.
La fonction `_load_facts()` exposée par le module est appelée par le helper
`_facts_inject()` de jarvis.py qui injecte les faits dans le system prompt.
"""
from flask import Blueprint

bp = Blueprint("facts", __name__)

from . import inject, routes  # noqa: E402, F401
