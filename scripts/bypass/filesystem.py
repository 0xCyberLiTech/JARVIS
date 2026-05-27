"""Bypass filesystem — détection + lecture fichiers SSH sur VM (zéro LLM).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 7.

Permet à JARVIS de répondre à "lis /etc/nginx/nginx.conf sur srv-nginx" sans
appeler le LLM : juste détection regex + cat/ls SSH + rendu UI holographique.

Couplage : `vm_ssh_map` est passé en argument (dependency injection) — les
fonctions SSH `_ssh_nginx`, `_ssh_clt`, etc. restent dans `jarvis.py` car
couplées à paramiko + clés SSH système.

Sécurité : protégé par `security_whitelists.BLOCKED_SSH_PATTERNS` au niveau du
helper SSH appelé via ssh_fn — les fichiers /etc/shadow, /etc/sudoers, etc.
sont automatiquement refusés en lecture.
"""
import json
import logging
import re

_log = logging.getLogger("jarvis.bypass_fs")

# ── Regex publiques ──────────────────────────────────────────

# Chemins absolus connus (fishing pour faux positifs limité aux racines système)
FPATH_RE = re.compile(
    r'(/(?:etc|var|opt|home|usr|tmp|srv|root|run|mnt|data)[a-zA-Z0-9._/\-]*)|'
    r'\b(etc/\S+|var/\S+|opt/\S+|home/\S+)',
    re.I,
)

# Noms de fichiers connus (sans chemin → résolu vers /etc/<name>)
FNAME_RE = re.compile(
    r'\b(hosts?|resolv\.conf|sshd?_config|nginx\.conf|apache2?\.conf|'
    r'fstab|crontab|sudoers|passwd|shadow|group|environment|'
    r'[\w\-]+\.(?:conf|cfg|log|txt|sh|py|ini|yaml|yml|env|json|htaccess|htpasswd))\b',
    re.I,
)

# Verbe "lecture" (cat, lis, affiche, ls, etc.)
FREAD_RE = re.compile(
    r'\b(cat\b|lis\b|lit\b|lire\b|affiche[rz]?\b|montre[rz]?\b|voir\b|'
    r'vois\b|contenu\b|ouvre\b|display\b|show\b|print\b|'
    r'rends?[-\s]?(?:toi\s+)?vers?\b|va[sz]?\s+(?:sur|dans|vers|[àa])\b|'
    r'navigu(?:e[rz]?\b|er\b)|cd\b|ls\b|liste[rz]?\b|list\b|explore[rz]?\b)',
    re.I,
)

# Verbe "édition"
FEDIT_RE = re.compile(
    r'\b([eé]dite?[rz]?\b|modifie?[rz]?\b|'
    r'[eé]cris?\b|[eé]crire\b|mise?\s+[àa]\s+jour\b)',
    re.I,
)

# Verbe "ajout"
FADD_RE = re.compile(
    r'\b(ajoute[rz]?\b|ins[eè]re?[rz]?\b|append\b|rajoute[rz]?\b)',
    re.I,
)

# Intention correction/reproposition — déclenche le mode "lis + corrige en un shot"
FCORR_RE = re.compile(
    r'\b(corrige?[rz]?\b|repropose?[rz]?\b|propose?[rz]?\b|proposer\b|'
    r'améliore?[rz]?\b|am[eé]liorer\b|r[eé][eé]cris?\b|r[eé]écrire\b|refai[st]?\b|'
    r'fix\b|correct\b|version\s+corrigée?\b|version\s+complète?\b|'
    r'entier\b|enti[eè]re?\b|complet\b|complète?\b|tout\s+le\s+fichier\b|'
    r'le\s+fichier\s+corrig[eé]\b|nouveau\s+fichier\b)',
    re.I,
)

# VM cible explicite ("sur srv-nginx")
SUR_VM_RE = re.compile(
    r'\bsur\s+(clt|srv-clt|pa85|srv-pa85|nginx|nginx|srv-nginx|proxmox|dev|dev-1|srv-dev|srv-dev-1)\b',
    re.I,
)


# ── Détecteurs ────────────────────────────────────────────────

def _resolve_path(text: str) -> str | None:
    """Extrait le chemin fichier — chemin absolu, ou nom de fichier connu → /etc/<name>."""
    path_matches = FPATH_RE.findall(text)
    file_path = next((g for pair in path_matches for g in pair if g), None)
    if not file_path:
        nm = FNAME_RE.search(text)
        if nm:
            name = nm.group(1).lower()
            file_path = '/etc/hosts' if 'hosts' in name else f'/etc/{name}'
        else:
            return None
    elif not file_path.startswith('/'):
        file_path = '/' + file_path
    return file_path


def _resolve_vm(text: str, vm_ssh_map: dict):
    """Trouve la VM cible — priorité 'sur <vm>' explicite, puis nom dans le texte."""
    tl = text.lower()
    m_sur = SUR_VM_RE.search(tl)
    if m_sur:
        name = m_sur.group(1).lower()
        if name in vm_ssh_map:
            return vm_ssh_map[name]  # (vm_name, ssh_fn)
    for name, vm_tuple in vm_ssh_map.items():
        if re.search(r'\b' + re.escape(name) + r'\b', tl):
            return vm_tuple
    return None


def detect_file_command(text: str, vm_ssh_map: dict):
    """Détecte une commande mono-fichier.
    Retourne (action, vm_name, ssh_fn, file_path) ou None.

    `vm_ssh_map` : dict alias → (vm_name, ssh_fn) — passé par jarvis.py.
    """
    if FADD_RE.search(text):
        action = "add"
    elif FEDIT_RE.search(text):
        action = "edit"
    elif FREAD_RE.search(text):
        action = "read"
    else:
        return None
    file_path = _resolve_path(text)
    if not file_path:
        return None
    vm_tuple = _resolve_vm(text, vm_ssh_map)
    if not vm_tuple:
        return None
    vm_name, ssh_fn = vm_tuple
    return action, vm_name, ssh_fn, file_path


def detect_multi_file_command(text: str, vm_ssh_map: dict):
    """Détecte une commande multi-fichiers (2+ chemins).
    Retourne ('read', vm_name, ssh_fn, [paths]) ou None.
    Multi-fichiers = lecture seule pour correction (pas d'édition)."""
    if FADD_RE.search(text) or FEDIT_RE.search(text) or FREAD_RE.search(text) or FCORR_RE.search(text):
        action = "read"
    else:
        return None
    path_matches = FPATH_RE.findall(text)
    file_paths = list(dict.fromkeys(g for pair in path_matches for g in pair if g))
    if len(file_paths) < 2:
        return None
    file_paths = [('/' + p if not p.startswith('/') else p) for p in file_paths]
    vm_tuple = _resolve_vm(text, vm_ssh_map)
    if not vm_tuple:
        return None
    vm_name, ssh_fn = vm_tuple
    return action, vm_name, ssh_fn, file_paths


# ── Générateur SSE ────────────────────────────────────────────

def _sse_tok(t: str, done: bool = False) -> str:
    """Helper SSE token (dupliqué de jarvis.py pour autonomie du module)."""
    return f"data: {json.dumps({'type':'token','token':t,'done':done})}\n\n"


def file_command_sse(action: str, vm_name: str, ssh_fn, file_path: str):
    """Lit/affiche un fichier sur une VM — bypass LLM — SSH direct.

    Émet un event ssh_file pour rendu holographique côté JS.

    Yields : SSE events (`data: {json}\\n\\n`).
    """
    # Répertoire si chemin se termine par / OU si basename n'a pas d'extension
    basename = file_path.rstrip('/').rsplit('/', 1)[-1]
    is_dir = file_path.endswith('/') or ('.' not in basename and basename != '')
    cmd = f"ls -la {file_path}" if is_dir else f"cat {file_path}"
    ok, content = ssh_fn(cmd)
    if not ok or not content:
        label = "lister" if is_dir else "lire"
        yield _sse_tok(f"Erreur : impossible de {label} `{file_path}` sur {vm_name}.", done=True)
        return
    yield f"data: {json.dumps({'type':'ssh_file','vm':vm_name,'path':file_path,'content':content.rstrip(),'action':action})}\n\n"
    yield _sse_tok("", done=True)
    yield f"data: {json.dumps({'type':'speak','text':f'Contenu de {file_path} affiché.'})}\n\n"
