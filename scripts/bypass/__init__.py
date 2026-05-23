"""Tuile **bypass** — 5 modules de bypass routing (LLM contourné).

Architecture par tuiles (refactor jarvis.py étape 8, 2026-05-23) — 6ème tuile.
**Pas de routes HTTP** — les fonctions sont consommées par le dispatcher de
routing (chat) qui détecte si un message utilisateur correspond à un pattern
court-circuit (commande VM, restart, backup, fichier, code, datetime) et
appelle directement le bon module au lieu de passer par le LLM.

Pourquoi des bypass :
- Latence : un « démarre la VM 108 » exécuté en 200 ms vs 8 s via LLM
- Déterminisme : zéro hallucination sur les paramètres VM/SSH
- Sécurité : la commande passe par le bypass dédié, pas via raw tool-call LLM

Sous-modules :
- `backup`     : sauvegardes (proxmox-backup-auto, jarvis-backup, …)
- `code`       : SCP code sur srv-dev-1 + exécution
- `filesystem` : édition fichier guidée (FEDIT/FADD)
- `proxmox`    : VM start/stop, reboot/update hôte, restart service
- `simple`     : datetime SSE, autres bypass triviaux

Pas de fonction `init()` à ce niveau : chaque sous-module gère ses propres
dépendances via ses signatures (ex: `proxmox.detect_vm_command(text, vms_api)`).
"""
from . import backup, code, filesystem, proxmox, simple  # noqa: F401
