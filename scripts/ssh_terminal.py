"""SSH Terminal — détection + ouverture WebSocket PTY interactif (zéro LLM).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 11.

Couvre :
- Mapping des 5 hôtes SSH terminal (dev1/ngix/clt/pa85/router) — IP/port/user/key/label
- Regex de détection ("ouvre terminal srv-dev-1", "connecte-moi à ngix", etc.)
- Générateur SSE qui émet `open_ssh_terminal` pour déclencher le PTY xterm.js côté navigateur

Le WebSocket handler PTY (`_ws_ssh_handler`) reste dans jarvis.py car couplé Flask-Sock + paramiko.

Dépendance : `bypass_code` (pour réutiliser CODE_DEV_IP/PORT/KEY de srv-dev-1).
"""
import json
import re
from pathlib import Path

import bypass_code

# ── Mapping SSH terminal (5 hôtes) ────────────────────────────
TERMINAL_MAP = {
    "dev1":   {"ip": bypass_code.CODE_DEV_IP,   "port": bypass_code.CODE_DEV_PORT, "user": "root",      "key": bypass_code.CODE_DEV_KEY,                "label": "srv-dev-1"},
    "ngix":   {"ip": "192.168.1.50",            "port": 2272,                       "user": "root",      "key": str(Path.home() / ".ssh" / "id_nginx"),  "label": "srv-ngix"},
    "clt":    {"ip": "192.168.1.12",            "port": 2272,                       "user": "root",      "key": str(Path.home() / ".ssh" / "id_clt"),    "label": "clt"},
    "pa85":   {"ip": "192.168.1.13",            "port": 2272,                       "user": "root",      "key": str(Path.home() / ".ssh" / "id_pa85"),   "label": "pa85"},
    "router": {"ip": "192.168.50.1",            "port": 2272,                       "user": "admin-clt", "key": str(Path.home() / ".ssh" / "id_router"), "label": "be98"},
}


# ── Regex de détection (5 hôtes) ──────────────────────────────
TERMINAL_RE = {
    "dev1": re.compile(
        r'\b(connect[e|é][-\s]?moi|ouvre?|lance?|accède?|terminal|ssh)\b.{0,30}\b(srv[-\s]?dev[-\s]?1|dev[-\s]?1|vm[-\s]?dev)\b'
        r'|\b(srv[-\s]?dev[-\s]?1|dev[-\s]?1|vm[-\s]?dev)\b.{0,30}\b(connect|ouvre?|terminal|ssh)\b',
        re.I,
    ),
    "ngix": re.compile(
        r'\b(connect[e|é][-\s]?moi|ouvre?|lance?|accède?|terminal|ssh)\b.{0,30}\b(srv[-\s]?ngix|ngix|nginx)\b'
        r'|\b(srv[-\s]?ngix|ngix|nginx)\b.{0,30}\b(connect[e|é][-\s]?moi|ouvre?|terminal|ssh)\b',
        re.I,
    ),
    "clt": re.compile(
        r'\b(connect[e|é][-\s]?moi|ouvre?|lance?|accède?|terminal|ssh)\b.{0,30}\b(srv[-\s]?clt|clt)\b'
        r'|\b(srv[-\s]?clt|clt)\b.{0,30}\b(connect[e|é][-\s]?moi|ouvre?|terminal|ssh)\b',
        re.I,
    ),
    "pa85": re.compile(
        r'\b(connect[e|é][-\s]?moi|ouvre?|lance?|accède?|terminal|ssh)\b.{0,30}\b(pa85|srv[-\s]?pa85)\b'
        r'|\b(pa85|srv[-\s]?pa85)\b.{0,30}\b(connect[e|é][-\s]?moi|ouvre?|terminal|ssh)\b',
        re.I,
    ),
    "router": re.compile(
        r'\b(connect[e|é][-\s]?moi|ouvre?|lance?|accède?|terminal|ssh)\b.{0,30}\b(be98|routeur?|router)\b'
        r'|\b(be98|routeur?|router)\b.{0,30}\b(connect[e|é][-\s]?moi|ouvre?|terminal|ssh)\b',
        re.I,
    ),
}


# ── Helper ────────────────────────────────────────────────────

def _sse_tok(t: str, done: bool = False) -> str:
    """Helper SSE token (dupliqué de jarvis.py pour autonomie du module)."""
    return f"data: {json.dumps({'type':'token','token':t,'done':done})}\n\n"


# ── Générateur SSE ────────────────────────────────────────────

def terminal_sse(host_key: str, label: str, user: str = "root"):
    """Bypass LLM — émet `open_ssh_terminal` pour ouvrir le PTY interactif côté JS.

    Le navigateur reçoit l'event SSE et déclenche `devTerminalOpen()` côté `jarvis_main.js`
    qui ouvre le WebSocket `/ws/ssh/<host_key>` géré par `_ws_ssh_handler` dans jarvis.py.
    """
    yield f"data: {json.dumps({'type': 'open_ssh_terminal', 'host': host_key, 'label': label, 'user': user})}\n\n"
    yield _sse_tok(f"Terminal {label} ouvert.", done=True)
