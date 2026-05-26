"""Outils SSH exposés au LLM via tool-calling — exec sur srv-nginx/proxmox/clt/pa85.

Tuile `ssh` — pas de routes HTTP. Les fonctions sont consommées par le
dispatcher `execute_tool()` de l'ossature quand le LLM appelle un outil
SSH (typiquement en mode SOC pour diagnostic infra).

Sécurité — logique 3 couches (corrigée 2026-05-17, fix faille defense en
profondeur) :
1. Aucun pattern BLOCKED matche → exec direct (lecture/diagnostic standard).
2. Pattern BLOCKED matche ET commande est une write op reconnue
   (`is_known_write_op`) ET whitelistée (`check_write_op` None) → exec + audit.
3. Pattern BLOCKED matche ET commande PAS une write op reconnue
   (ex: rm/mkfs/dd/shutdown/qm destroy) → **REFUS par défaut + audit**.
4. Pattern BLOCKED matche ET write op reconnue MAIS refusée
   (ex: systemctl restart docker, apt install evilpkg) → REFUS + audit.

Audit log : write ops (autorisées OU refusées) tracées dans
`logs/audit_writeops.jsonl` via `security.audit_writeop()`.

Dépendances injectées par `init()` :
- `ssh_nginx` / `ssh_proxmox` / `ssh_clt` / `ssh_pa85` : fonctions SSH.
- `security` : module `security_whitelists` (BLOCKED_SSH_PATTERNS,
  is_known_write_op, check_write_op, audit_writeop).
"""

# Dépendances injectées par init() — depuis l'ossature.
_ssh_nginx:    object = None
_ssh_proxmox: object = None
_ssh_clt:     object = None
_ssh_pa85:    object = None
_security:    object = None


def init(*, ssh_nginx, ssh_proxmox, ssh_clt, ssh_pa85, security) -> None:
    """Injecte les 4 fonctions SSH + le module security_whitelists."""
    global _ssh_nginx, _ssh_proxmox, _ssh_clt, _ssh_pa85, _security
    _ssh_nginx    = ssh_nginx
    _ssh_proxmox = ssh_proxmox
    _ssh_clt     = ssh_clt
    _ssh_pa85    = ssh_pa85
    _security    = security


def _ssh_timeout(cmd: str, default: int = 15) -> int:
    """Timeout adaptatif — apt/dpkg peuvent durer plusieurs minutes."""
    if any(k in cmd.lower() for k in ("apt", "dpkg", "apt-get")):
        return 180
    return default


def _tool_commande_ssh_run(ssh_fn, label, args):
    """Exécute une commande SSH après validation sécurité — mutualisé pour tous les hôtes."""
    cmd = args.get("commande", "").strip()
    if not cmd:
        return "Erreur : commande vide"
    cmd_lower = cmd.lower()
    is_writeop = False
    for pattern in _security.BLOCKED_SSH_PATTERNS:
        if pattern.lower() in cmd_lower:
            is_writeop = True
            # Gardien : si pattern destructif matche MAIS commande pas reconnue
            # comme write op whitelistable (rm/mkfs/dd/shutdown/...) → REFUS strict.
            # Ne JAMAIS se fier au seul check_write_op qui retourne None pour ces cas.
            if not _security.is_known_write_op(cmd):
                msg = f"commande destructive non whitelistée (pattern: {pattern})"
                _security.audit_writeop(label, cmd, allowed=False, output=msg)
                return f"Erreur : commande refusée par sécurité ({pattern}) — {msg}"
            err = _security.check_write_op(cmd)
            if err is not None:
                _security.audit_writeop(label, cmd, allowed=False, output=err)
                return f"Erreur : commande refusée par sécurité ({pattern}) — {err}"
            break
    ok, output = ssh_fn(cmd, timeout=_ssh_timeout(cmd))
    if is_writeop:
        _security.audit_writeop(label, cmd, allowed=True, output=output or "")
    if not ok and not output:
        return f"Erreur SSH {label} : pas de réponse"
    return output[:4000] if output else "(aucune sortie)"


def _tool_commande_ssh_nginx(args):    return _tool_commande_ssh_run(_ssh_nginx,    "nginx",    args)
def _tool_commande_ssh_proxmox(args): return _tool_commande_ssh_run(_ssh_proxmox, "proxmox", args)
def _tool_commande_ssh_clt(args):     return _tool_commande_ssh_run(_ssh_clt,     "clt",     args)
def _tool_commande_ssh_pa85(args):    return _tool_commande_ssh_run(_ssh_pa85,    "pa85",    args)
