"""Tuile **proxmox** — client API Proxmox VE (auth ticket + token).

Architecture par tuiles (refactor jarvis.py étape 9, 2026-05-23) — 7ème tuile.
**Pas de routes HTTP propres** — consommé par le routing chat (injection PVE
dans le system prompt) et par `bypass.proxmox` (commandes VM).

Sous-modules :
- `api` : client REST PVE + cache d'état 30 s + helper d'injection prompt.

Lecture seule par défaut : la tuile NE FAIT JAMAIS d'écriture sur Proxmox.
Les actions VM (start/stop/reboot) passent par `bypass.proxmox` qui utilise
SSH + `qm`, pas l'API REST.
"""
from . import api  # noqa: F401
