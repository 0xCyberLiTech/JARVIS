"""Security whitelists & write-op validation — code défensif pur.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 6b.

Contient les listes immuables qui contrôlent ce que JARVIS peut faire en SSH
sur les VMs distantes. Toute modification ici doit être documentée et
validée — c'est la couche sécurité ultime contre les commandes destructives.

Couvre :
- BLOCKED_SSH_PATTERNS : 29 patterns SSH interdits (rm, mkfs, dd, shutdown, qm destroy, etc.)
- ALLOWED_RESTART_SVCS : services autorisés via `systemctl restart` (SSH, 4 hôtes)
- ALLOWED_SOC_RESTART_SVCS : services restartables via la route HTTP SOC (srv-nginx)
- ALLOWED_APT_PKGS : paquets autorisés via `apt install/upgrade`
- check_write_op() : validation stricte des ops write
- parse_upgradable_packages() : parsing sortie `apt list --upgradable`
- audit_writeop() : append JSON ligne à logs/audit_writeops.jsonl (best-effort,
  ne bloque jamais l'exécution si IO échoue) — ajouté 2026-05-17.
- INTERNAL_IPS + PROTECTED_EXTERNAL_IPS + INTERNAL_CIDRS + is_protected_ip() :
  source unique JARVIS pour filtrer les IPs internes (LAN srv + LAN ASUS + loopback)
  ET les IPs externes whitelistées (DNS publics + WAN Freebox de Marc) — ajouté
  2026-05-25 (validation Marc, cf. mémoire soc_design_harmonisation). Toute modif
  ici impose un grep des consommateurs (blueprints/soc.py, chat/soc_context.py).

Couplage : zéro pour validation pure, write fichier I/O pour audit_writeop().
"""
import ipaddress
import json
import re
from datetime import UTC, datetime
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
    # apt install/upgrade bloqués — passent par whitelist ALLOWED_APT_PKGS
    # (ajout 2026-05-17 : avant, ces patterns absents → check_write_op jamais
    # appelée → apt install <evilpkg> s'exécutait sans vérification.)
    "apt install", "apt upgrade", "apt-get install", "apt-get upgrade",
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

# Services restartables via SSH write-op (`systemctl restart`) sur les 4 hôtes.
# Vérifié SSH 2026-05-22 : aucun hôte ne tourne php-fpm — srv-nginx n'a pas PHP,
# clt/pa85 utilisent mod_php (libapache2-mod-php8.4) → restart PHP = restart apache2.
# Les anciennes entrées php7.4-fpm / php8.2-fpm étaient mortes : retirées.
ALLOWED_RESTART_SVCS = {
    "nginx", "fail2ban", "crowdsec", _SVC_BOUNCER,
    "suricata", "apache2",
}

# Services restartables via la route HTTP /api/soc/restart-service (soc.py) ET par
# l'auto-engine SOC (_check_services). Portée : srv-nginx uniquement.
# Vérifié SSH 2026-05-22 : srv-nginx fait tourner nginx + CrowdSec + fail2ban +
# Suricata, sans aucun PHP. `suricata` ajouté 2026-05-22 : l'auto-engine est censé
# le redémarrer s'il tombe (déclencheur #10) mais son absence de cette whitelist
# bloquait l'action. Anciennes entrées php*-fpm mortes retirées.
ALLOWED_SOC_RESTART_SVCS = {
    "nginx", "crowdsec", "fail2ban", "suricata",
}

ALLOWED_APT_PKGS = {
    "nginx", "fail2ban", "crowdsec", _SVC_BOUNCER,
    "suricata", "suricata-update", "libssl3", "openssl",
    "python3", "python3-pip", "certbot", "python3-certbot-nginx",
}


# ── Regex partagees (source unique check_write_op + is_known_write_op) ────────
_RE_SYSTEMCTL_RESTART = re.compile(r'^systemctl\s+restart\s+(\S+)$', re.I)
_RE_APT_WRITE = re.compile(
    r'^(?:DEBIAN_FRONTEND=\S+\s+)?apt(?:-get)?\s+(?:install|upgrade)\s+(?:-[yq\s]+)?(\S+)$',
    re.I,
)


# ── Validation ────────────────────────────────────────────────

def is_known_write_op(cmd: str) -> bool:
    """Retourne True si la commande est une write op de forme reconnue.

    Sert de gardien dans `_tool_commande_ssh_run` (jarvis.py) : si un pattern
    BLOCKED_SSH_PATTERNS matche MAIS que la commande n'est PAS une write op
    reconnue (ex: 'rm -rf /'), elle doit etre refusee par defaut (et non
    autorisee parce que check_write_op renvoie None).

    Ajoute 2026-05-17 — corrige une faille critique de defense-en-profondeur
    ou rm/mkfs/dd/shutdown etc. matchaient BLOCKED mais s'executaient car
    check_write_op retournait None (pas son role).
    """
    c = cmd.strip()
    return bool(_RE_SYSTEMCTL_RESTART.match(c) or _RE_APT_WRITE.match(c))


def check_write_op(cmd: str) -> str | None:
    """Autorise ops write sur whitelist stricte. Retourne message d'erreur ou None si OK.

    Cas gérés :
    - `systemctl restart <svc>` → autorisé si svc ∈ ALLOWED_RESTART_SVCS
    - `apt[-get] install/upgrade <pkg>` → autorisé si pkg ∈ ALLOWED_APT_PKGS

    ⚠ Retourne `None` aussi pour les commandes HORS scope (ex: 'rm -rf /').
    Le caller doit utiliser `is_known_write_op()` AVANT pour distinguer
    'write op autorisee' de 'commande pas reconnue' — sinon faille critique
    de defense-en-profondeur.
    """
    c = cmd.strip()
    # systemctl restart <svc>
    m = _RE_SYSTEMCTL_RESTART.match(c)
    if m:
        svc = m.group(1).lower()
        if svc in ALLOWED_RESTART_SVCS:
            return None  # autorisé
        return f"Refusé : systemctl restart '{svc}' non whitelisté — services autorisés : {', '.join(sorted(ALLOWED_RESTART_SVCS))}"
    # apt/apt-get install/upgrade <pkg>
    m2 = _RE_APT_WRITE.match(c)
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
        host: hote SSH cible (nginx/proxmox/clt/pa85/...)
        cmd: commande SSH (tronquee a 500 chars dans le log pour limiter taille)
        allowed: True si check_write_op a autorise · False si refusee
        output: sortie commande (uniquement sa longueur est loggee, pas le contenu)
        log_path: override path pour tests
        ts: override timestamp pour tests (sinon UTC maintenant)
    """
    path = log_path or AUDIT_WRITEOP_PATH
    record = {
        "ts": ts or datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
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


# ── Whitelist IPs protégées (source unique JARVIS — validation Marc 2026-05-25) ─
# Doit rester aligné avec `SOC/soc_infra.yaml` (hosts.* + protected_external_ips)
# + architecture réseau documentée dans `CLAUDE.md` racine.
#
# Pourquoi cette source ICI dans security_whitelists ? Marc a tranché 2026-05-25
# (cf. soc_design_harmonisation) : option (c) hardcode dans le fichier qui sert
# déjà de source unique pour les whitelists JARVIS — cohérence avec ALLOWED_*.
# Le yaml SOC reste source maître documentaire ; toute évolution = MAJ ici + grep
# des consommateurs (chat/soc_context.py, blueprints/soc.py).
#
# Évolution = modifier les dicts ci-dessous + commentaire daté + run grep :
#   grep -rn "INTERNAL_IPS\|PROTECTED_EXTERNAL_IPS\|is_protected_ip" scripts/

# A — Infrastructure interne (LAN serveur + LAN ASUS + loopback)
INTERNAL_IPS = {
    "127.0.0.1":     "loopback",
    "192.168.1.12":  "clt",
    "192.168.1.13":  "pa85",
    "192.168.1.20":  "proxmox",
    "192.168.1.21":  "srv-dev-1",
    "192.168.1.50":  "srv-nginx",
    "192.168.1.110": "routeur-asus-wan",
    "192.168.1.254": "freebox-lan",
    "192.168.50.1":  "routeur-asus-rog-be19000-ai",
    "192.168.50.90": "windows-jarvis",
}

# B — Externes protégées (DNS publics + IP publique Freebox de Marc)
PROTECTED_EXTERNAL_IPS = {
    "1.1.1.1":       "cloudflare-dns-1",
    "1.0.0.1":       "cloudflare-dns-2",
    "8.8.8.8":       "google-dns-1",
    "8.8.4.4":       "google-dns-2",
    "212.27.40.240": "free-dns-1",
    "212.27.40.241": "free-dns-2",
    "82.65.147.2":   "freebox-wan-public",
}

# C — Catch-all CIDRs (RFC1918 + loopback étendu)
# Toute IP ajoutée demain sur LAN srv ou LAN ASUS est automatiquement protégée.
INTERNAL_CIDRS = [
    ipaddress.ip_network("192.168.1.0/24"),
    ipaddress.ip_network("192.168.50.0/24"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
]


def is_protected_ip(ip: str) -> bool:
    """True si l'IP est protégée (interne LAN OU externe whitelistée).

    À utiliser pour :
    - exclure l'IP du contexte SOC envoyé à phi4 (analyses)
    - refuser tout ban automatique sur cette IP
    - exclure des listes top_ips affichées dans les rapports JARVIS

    Couvre 3 niveaux de défense :
    1. Match exact dans INTERNAL_IPS (10 hôtes infra)
    2. Match exact dans PROTECTED_EXTERNAL_IPS (7 DNS+WAN publique)
    3. Match CIDR (RFC1918 catch-all + loopback)

    Empty/None/invalide → True (refus par défaut = sécurité).
    """
    if not ip:
        return True
    if ip in INTERNAL_IPS or ip in PROTECTED_EXTERNAL_IPS:
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        # IP malformée → considère comme protégée pour ne rien casser en aval
        return True
    return any(addr in net for net in INTERNAL_CIDRS)


def protected_ip_label(ip: str) -> str:
    """Retourne le rôle si l'IP est protégée (ex: "srv-nginx"), vide sinon.

    Utile pour afficher le label de rôle dans les rapports JARVIS au lieu
    d'une IP brute (transparence : "192.168.1.50 srv-nginx" vs "192.168.1.50").
    """
    if not ip:
        return ""
    return INTERNAL_IPS.get(ip) or PROTECTED_EXTERNAL_IPS.get(ip) or ""
