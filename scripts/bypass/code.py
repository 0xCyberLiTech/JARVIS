"""Bypass code — détection + SCP/exec sur srv-dev-1 (zéro LLM).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 10.

Permet à JARVIS de détecter "exécute test.py sur dev" et d'envoyer le fichier
local sur srv-dev-1 via SCP puis l'exécuter (python3 ou bash).

⚠ RÈGLE ABSOLUE : uniquement srv-dev-1 (192.168.1.21). Aucun autre hôte cible.

Dependency injection : `ssh_dev1_fn` est passé en argument à `code_scp_exec_sse`
(fonction `_ssh_dev1` de jarvis.py couplée paramiko + clé SSH système).
"""
import json
import logging
import re
import subprocess
from pathlib import Path

_log = logging.getLogger("jarvis.bypass_code")

# ── Config srv-dev-1 ──────────────────────────────────────────
CODE_DEV_VM     = "srv-dev-1"
CODE_DEV_IP     = "192.168.1.21"
CODE_DEV_PORT   = 2272
CODE_DEV_KEY    = str(Path.home() / ".ssh" / "id_dev")
CODE_REMOTE_DIR = "/tmp/jarvis-code"

# Timeouts
SCP_TIMEOUT_S       = 20
EXEC_TIMEOUT_S      = 60
MKDIR_TIMEOUT_S     = 8


# ── Regex publiques ───────────────────────────────────────────

CODE_EXEC_RE = re.compile(
    r'\b(ex[eé]cute[rz]?[sz]?|lance[rz]?[sz]?|run|joue[rz]?|test(?:er?)?[sz]?)\b.{0,80}'
    r'\b(sur\s+(?:srv-)?dev(?:-?1)?|vm\s+dev|sur\s+la\s+vm)\b',
    re.I | re.S,
)
CODE_SEND_RE = re.compile(
    r'\b(envoie[rz]?[sz]?|pousse[rz]?[sz]?|copie[rz]?[sz]?|scp|transf[eè]re?[rz]?[sz]?)\b.{0,80}'
    r'\b(sur\s+(?:srv-)?dev(?:-?1)?|vm\s+dev|sur\s+la\s+vm)\b',
    re.I | re.S,
)
CODE_FILE_RE = re.compile(
    r'\b([\w][\w\-]*\.(?:py|sh|js|ts|rb|go|rs|php|sql|pl))\b',
)

# Chemins de recherche locale (priorité scripts/ → JARVIS/ → Documents/Downloads/Desktop).
# Le module vit dans scripts/bypass/ → 2 .parent pour atteindre scripts/.
LOCAL_SEARCH_DIRS = [
    Path(__file__).parent.parent,            # JARVIS/scripts/
    Path(__file__).parent.parent.parent,     # JARVIS/
    Path.home() / "Documents",
    Path.home() / "Downloads",
    Path.home() / "Desktop",
]


# ── Helpers ───────────────────────────────────────────────────

def _sse_tok(t: str, done: bool = False) -> str:
    """Helper SSE token (dupliqué de jarvis.py pour autonomie du module)."""
    return f"data: {json.dumps({'type':'token','token':t,'done':done})}\n\n"


def find_local_code_file(filename: str):
    """Cherche un fichier code en local — JARVIS/scripts/ en priorité.
    Retourne Path ou None si introuvable."""
    for d in LOCAL_SEARCH_DIRS:
        p = d / filename
        if p.exists() and p.is_file():
            return p
    return None


# ── Détecteur ─────────────────────────────────────────────────

def detect_code_command(text: str):
    """Retourne ('exec'|'send', filename) si commande code sur srv-dev-1 détectée, sinon None."""
    file_m = CODE_FILE_RE.search(text)
    if not file_m:
        return None
    filename = file_m.group(1)
    if CODE_EXEC_RE.search(text):
        return "exec", filename
    if CODE_SEND_RE.search(text):
        return "send", filename
    return None


# ── Générateur SSE ────────────────────────────────────────────

def code_scp_exec_sse(filename: str, exec_it: bool, ssh_dev1_fn):
    """Envoie un fichier sur srv-dev-1 via SCP et optionnellement l'exécute.

    `ssh_dev1_fn` : fonction `_ssh_dev1(cmd, timeout=N) -> (ok, output)` de jarvis.py.

    ⚠ RÈGLE ABSOLUE : uniquement CODE_DEV_IP (CODE_DEV_VM) — zéro autre hôte.
    """
    local_path = find_local_code_file(filename)
    if not local_path:
        yield _sse_tok(
            f"✗ Fichier introuvable en local : `{filename}`\n"
            f"Chemins cherchés : `scripts/` · `JARVIS/` · `Documents/` · `Downloads/` · `Desktop/`",
            done=True,
        )
        return

    yield _sse_tok(f"**SCP** `{local_path.name}` → `{CODE_DEV_VM}:{CODE_REMOTE_DIR}/`\n")

    # Créer le répertoire distant
    ssh_dev1_fn(f"mkdir -p {CODE_REMOTE_DIR}", timeout=MKDIR_TIMEOUT_S)

    scp_cmd = [
        "scp",
        "-i", CODE_DEV_KEY,
        "-P", str(CODE_DEV_PORT),
        "-o", "StrictHostKeyChecking=no",
        "-o", "IdentitiesOnly=yes",
        "-o", "BatchMode=yes",
        str(local_path),
        f"root@{CODE_DEV_IP}:{CODE_REMOTE_DIR}/{filename}",
    ]
    try:
        r = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=SCP_TIMEOUT_S)
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "").strip()
            yield _sse_tok(f"✗ SCP échoué :\n```\n{err}\n```", done=True)
            return
    except Exception as exc:
        yield _sse_tok(f"✗ Erreur SCP : {exc}", done=True)
        return

    yield _sse_tok(f"✓ `{filename}` envoyé sur {CODE_DEV_VM}.\n")

    if not exec_it:
        yield _sse_tok(
            f"\nFichier disponible : `{CODE_REMOTE_DIR}/{filename}`\n"
            f"Dis `exécute {filename} sur dev` pour le lancer.",
            done=True,
        )
        return

    # Exécution
    interp = "python3" if filename.endswith(".py") else "bash"
    yield _sse_tok(f"**Exécution** : `{interp} {CODE_REMOTE_DIR}/{filename}`\n\n")
    ok, out = ssh_dev1_fn(
        f"{interp} {CODE_REMOTE_DIR}/{filename} 2>&1",
        timeout=EXEC_TIMEOUT_S,
    )
    if not ok:
        yield _sse_tok("✗ Erreur d'exécution SSH.", done=True)
        return
    out = (out or "").strip()
    if out:
        yield _sse_tok(f"```\n{out}\n```\n")
    else:
        yield _sse_tok("(pas de sortie)\n")
    yield _sse_tok("", done=True)
