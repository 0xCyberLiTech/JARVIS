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
  dérivées de soc_infra.yaml (jarvis_trusted_ips, généré) pour filtrer les IPs internes
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

# IP de confiance — GÉNÉRÉES depuis SOC/scripts/soc_infra.yaml (source unique) par
# SOC/scripts/sync_jarvis_whitelist.py -> jarvis_trusted_ips.py (committé = JARVIS autonome/DR).
from jarvis_trusted_ips import INTERNAL_CIDRS as _TRUSTED_CIDRS_STR
from jarvis_trusted_ips import INTERNAL_IPS, PROTECTED_EXTERNAL_IPS

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
# Maitrise volumetrie : rotation taille-bornee EN PYTHON (jamais de logrotate systeme
# avec copytruncate sur ce JSONL d'etat — anti-pattern connu qui corrompt l'append).
# Aligne sur le pattern RotatingFileHandler de jarvis.log/tts.log. Write-ops rares
# (~qq/semaine, ~120 o/ligne) → la rotation ne se declenchera quasi jamais, mais le
# volume total est borne a max_bytes * (1 + backups) = ~12 Mo dans le pire cas.
AUDIT_WRITEOP_MAX_BYTES = 2_000_000   # 2 MB avant rotation
AUDIT_WRITEOP_BACKUPS = 5             # audit_writeops.jsonl.1 .. .5 conserves


def _rotate_audit_log(path: Path, max_bytes: int, backups: int) -> None:
    """Rotation best-effort facon RotatingFileHandler : .N→.N+1 puis base→.1.

    Conserve l'historique forensic (jamais de troncature en place), borne le volume.
    Toute erreur d'I/O est avalee — la rotation ne doit jamais bloquer un audit.
    """
    try:
        if not (path.exists() and path.stat().st_size >= max_bytes):
            return
        oldest = path.parent / f"{path.name}.{backups}"
        if oldest.exists():
            oldest.unlink()
        for i in range(backups - 1, 0, -1):
            src = path.parent / f"{path.name}.{i}"
            if src.exists():
                src.rename(path.parent / f"{path.name}.{i + 1}")
        path.rename(path.parent / f"{path.name}.1")
    except OSError:
        pass


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
        _rotate_audit_log(path, AUDIT_WRITEOP_MAX_BYTES, AUDIT_WRITEOP_BACKUPS)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── Whitelist IPs protégées — SOURCE UNIQUE : SOC/scripts/soc_infra.yaml ────────
# Unification 2026-06-02 (incident laposte : whitelist dupliquée 4+ endroits -> relais
# mail banni 8j). Les IP de confiance ne sont PLUS hardcodées ici : INTERNAL_IPS et
# PROTECTED_EXTERNAL_IPS sont importées de `jarvis_trusted_ips` (généré depuis soc_infra.yaml
# par sync_jarvis_whitelist.py, committé -> JARVIS autonome/DR). INTERNAL_CIDRS = ces CIDR
# (strings) convertis en objets ip_network. Dérive d'UNE source -> zéro divergence
# (garde-fou DEV/TOOLS/refactor-precheck/audit-whitelist-sources.py).
#
# Évolution = éditer soc_infra.yaml -> python sync_jarvis_whitelist.py -> committer.
# NE PAS éditer jarvis_trusted_ips.py à la main.
INTERNAL_CIDRS = [ipaddress.ip_network(_c) for _c in _TRUSTED_CIDRS_STR]


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
