"""Security whitelists & write-op validation — code défensif pur.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 6b.

Contient les listes immuables qui contrôlent ce que JARVIS peut faire en SSH
sur les VMs distantes. Toute modification ici doit être documentée et
validée — c'est la couche sécurité ultime contre les commandes destructives.

Couvre :
- BLOCKED_SSH_PATTERNS : 29 patterns SSH interdits (rm, mkfs, dd, shutdown, qm destroy, etc.)
- ALLOWED_RESTART_SVCS : services autorisés via `systemctl restart`
- ALLOWED_APT_PKGS : paquets autorisés via `apt install/upgrade`
- check_write_op() : validation stricte des ops write
- parse_upgradable_packages() : parsing sortie `apt list --upgradable`
- audit_writeop() : append JSON ligne à logs/audit_writeops.jsonl (best-effort,
  ne bloque jamais l'exécution si IO échoue) — ajouté 2026-05-17.

Couplage : zéro pour validation pure, write fichier I/O pour audit_writeop().
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# ── Patterns SSH bloqués ──────────────────────────────────────
# Toute commande contenant un de ces patterns est REFUSÉE par défaut.
# Les exceptions passent par check_write_op() (whitelist).
BLOCKED_SSH_PATTERNS = [
    # Destructif
    "rm ", "rmdir", "mkfs", "dd if=", "shutdown", "reboot",
    # Service stop
    "systemctl stop", "systemctl disable",
    # Network
    "iptables -F",
    # systemctl restart bloqué — passe par whitelist ALLOWED_RESTART_SVCS
    "systemctl restart",
    # Redirections shell
    "> /", "| sh", "| bash", "curl.*sh |", "wget.*sh |",
    # Proxmox destructif
    "qm destroy", "qm suspend", "qm migrate",
    "qm set", "qm create", "qm clone", "qm unlock",
    "pct stop", "pct start", "pct destroy", "pvectl",
    # Édition shell
    "tee ", "sed -i", "chmod ", "chown ", "echo >>", "echo >",
    "truncate", "mv ", "cp ", "> /etc", "> /var", "> /opt",
    # Fichiers système critiques — lecture autorisée mais modification bloquée
    "/etc/hosts", "/etc/passwd", "/etc/shadow", "/etc/sudoers",
    "/etc/sudoers.d", "/etc/ssh/sshd_config", "/etc/ssh/ssh_config",
    "/etc/fstab", "/etc/resolv.conf", "/etc/crontab",
    "/etc/iptables", "/etc/nftables", "/etc/pam.d",
    # Éditeurs interactifs — bloqueraient le process SSH
    "nano ", "vi ", "vim ", "emacs ", "pico ", "joe ",
    # Redirections vers fichiers système via cat
    "cat >", "cat >>",
    # Exécution de code inline
    "python -c", "python3 -c", "perl -e", "ruby -e",
]

# ── Whitelists write ops ──────────────────────────────────────
_SVC_BOUNCER = "crowdsec-firewall-bouncer"

ALLOWED_RESTART_SVCS = {
    "nginx", "fail2ban", "crowdsec", _SVC_BOUNCER,
    "suricata", "apache2", "php7.4-fpm", "php8.2-fpm",
}

ALLOWED_APT_PKGS = {
    "nginx", "fail2ban", "crowdsec", _SVC_BOUNCER,
    "suricata", "suricata-update", "libssl3", "openssl",
    "python3", "python3-pip", "certbot", "python3-certbot-nginx",
}


# ── Validation ────────────────────────────────────────────────

def check_write_op(cmd: str) -> str | None:
    """Autorise ops write sur whitelist stricte. Retourne message d'erreur ou None si OK.

    Cas gérés :
    - `systemctl restart <svc>` → autorisé si svc ∈ ALLOWED_RESTART_SVCS
    - `apt[-get] install/upgrade <pkg>` → autorisé si pkg ∈ ALLOWED_APT_PKGS
    """
    c = cmd.strip()
    # systemctl restart <svc>
    m = re.match(r'^systemctl\s+restart\s+(\S+)$', c, re.I)
    if m:
        svc = m.group(1).lower()
        if svc in ALLOWED_RESTART_SVCS:
            return None  # autorisé
        return f"Refusé : systemctl restart '{svc}' non whitelisté — services autorisés : {', '.join(sorted(ALLOWED_RESTART_SVCS))}"
    # apt/apt-get install/upgrade <pkg>
    m2 = re.match(r'^(?:DEBIAN_FRONTEND=\S+\s+)?apt(?:-get)?\s+(?:install|upgrade)\s+(?:-[yq\s]+)?(\S+)$', c, re.I)
    if m2:
        pkg = m2.group(1).lower()
        if pkg in ALLOWED_APT_PKGS:
            return None  # autorisé
        return f"Refusé : apt install/upgrade '{pkg}' non whitelisté — paquets autorisés : {', '.join(sorted(ALLOWED_APT_PKGS))}"
    return None


def parse_upgradable_packages(text: str) -> list:
    """Extrait les noms de paquets depuis la sortie de 'apt list --upgradable'."""
    pkgs = []
    for line in text.splitlines():
        m = re.match(r'^([a-z][a-z0-9.+\-]+)/', line)
        if m:
            pkgs.append(m.group(1))
    return pkgs


# ── Audit log write ops SSH ───────────────────────────────────
# Ajouté 2026-05-17 : tracabilite forensic des ops write (allowed=true) ET
# refusees (allowed=false). Permet une revue post-mortem ciblee en cas
# d'action douteuse de l'auto-engine SOC ou hallucination LLM.

AUDIT_WRITEOP_PATH = Path(__file__).resolve().parent.parent / "logs" / "audit_writeops.jsonl"


def audit_writeop(host: str, cmd: str, allowed: bool, output: str = "",
                  *, log_path: Path | None = None, ts: str | None = None) -> None:
    """Append une ligne JSON a l'audit log des write ops SSH.

    Best-effort : un echec d'I/O n'interrompt JAMAIS l'execution de la commande.

    Args:
        host: hote SSH cible (ngix/proxmox/clt/pa85/...)
        cmd: commande SSH (tronquee a 500 chars dans le log pour limiter taille)
        allowed: True si check_write_op a autorise · False si refusee
        output: sortie commande (uniquement sa longueur est loggee, pas le contenu)
        log_path: override path pour tests
        ts: override timestamp pour tests (sinon UTC maintenant)
    """
    path = log_path or AUDIT_WRITEOP_PATH
    record = {
        "ts": ts or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "host": host,
        "cmd": cmd[:500],
        "allowed": bool(allowed),
        "out_len": len(output) if output else 0,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass
