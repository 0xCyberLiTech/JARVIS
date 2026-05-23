"""Tuile **terminal** — WebSocket PTY SSH (terminaux interactifs xterm.js).

Architecture par tuiles (refactor jarvis.py étape 30, 2026-05-23) — 18ème tuile.
Routes WebSocket Flask-Sock pour les terminaux SSH PTY interactifs (chaque
connexion ouvre un canal `invoke_shell()` paramiko + bidirectionnel WS).

Sous-modules :
- `ssh_ws` : 3 helpers (`_ssh_reader`, `_ssh_connect`, `_ssh_handler`) +
             enregistrement des routes WS `/ws/ssh/<host>` et `/ws/dev` via
             `init(sock, ssh_terminal_map)`

Pourquoi une tuile dédiée : ces handlers ne tournent que dans un thread
worker dédié par connexion (paramiko + queue + select), pas de DI lourde
contrairement aux tuiles HTTP. La séparation isole le couplage paramiko +
Flask-Sock du reste de l'app.
"""
from . import ssh_ws  # noqa: F401
