"""Tuile **ssh** — outils SSH exposés au LLM via tool-calling.

Architecture par tuiles (refactor jarvis.py étape 7, 2026-05-23) — 5ème tuile
après `system/`, `memory/`, `rag/`, `files/`. Autoportante : zéro import vers
`jarvis.py`. **Pas de routes HTTP** — fonctions consommées par le dispatcher
`execute_tool()` (LLM tool-calling).

Public surface :
- `init()` : injection des 4 fonctions SSH (nginx/proxmox/clt/pa85) + module
  `security_whitelists` (validation des write ops).
- Fonctions ré-exportées : `_tool_commande_ssh_nginx/proxmox/clt/pa85`,
  `_tool_commande_ssh_run` (mutualisé), `_ssh_timeout` (helper adaptatif).
"""
from . import tools

init                       = tools.init
_ssh_timeout               = tools._ssh_timeout
_tool_commande_ssh_run     = tools._tool_commande_ssh_run
_tool_commande_ssh_nginx    = tools._tool_commande_ssh_nginx
_tool_commande_ssh_proxmox = tools._tool_commande_ssh_proxmox
_tool_commande_ssh_clt     = tools._tool_commande_ssh_clt
_tool_commande_ssh_pa85    = tools._tool_commande_ssh_pa85
