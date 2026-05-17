# =======================================================================
#  blueprints/soc.py — JARVIS SOC Blueprint
#  Routes : /api/soc/* — journal, ban/unban, restart, monitoring, autoban
#  Dépendances injectées via init_soc(speak_fn, limiter_obj)
# =======================================================================

import base64
import datetime
import ipaddress
import json
import logging
import re
import shlex
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

from flask import Blueprint, Response, request

soc_bp = Blueprint("soc", __name__)

# ── Dépendances injectées (speak + limiter depuis jarvis.py) ──────────
_speak   = None
_limiter = None
_log     = logging.getLogger("JARVIS.SOC")

# Limites par route — appliquées en une seule passe dans init_soc()
_ROUTE_LIMITS = {
    "api_soc_ban_ip":            "10 per minute",
    "api_soc_unban_ip":          "10 per minute",
    "api_soc_restart_service":   "5 per minute",
    "api_soc_force_autoban":     "6 per minute",
    "api_soc_heartbeat":         "120 per minute",
    "api_soc_monitor":           "30 per minute",
    "api_soc_recently_banned":   "60 per minute",
    "api_soc_threat_score":      "30 per minute",
    "api_soc_whitelist_get":     "60 per minute",
    "api_soc_whitelist_add":     "20 per minute",
    "api_soc_whitelist_del":     "20 per minute",
    "api_soc_actions":           "60 per minute",
    "api_soc_actions_clear":     "10 per minute",
    "api_soc_test":              "30 per minute",
    "api_soc_ip_deep":           "20 per minute",
    "api_soc_ip_history":        "20 per minute",
}

# Dossier parent = scripts/ (ce fichier est dans scripts/blueprints/)
_SCRIPTS_DIR = Path(__file__).parent.parent


def init_soc(speak_fn, limiter_obj):
    """Injecte speak() et limiter, applique les rate limits, lance le thread."""
    global _speak, _limiter
    _speak   = speak_fn
    _limiter = limiter_obj
    # Applique les rate limits sur chaque view function
    import sys
    module = sys.modules[__name__]
    for fn_name, limit_str in _ROUTE_LIMITS.items():
        fn = getattr(module, fn_name, None)
        if fn is not None:
            limiter_obj.limit(limit_str)(fn)
    # Lance le thread de surveillance SOC
    _soc_thread = threading.Thread(target=_soc_monitor_loop, daemon=True, name="soc-monitor")
    _soc_thread.start()


# ════════════════════════════════════════════════════════════════
# JOURNAL DES ACTIONS PROACTIVES (persisté, rotation 30 jours)
# ════════════════════════════════════════════════════════════════

_SOC_ACTIONS      = []
_SOC_ACT_DAYS     = 30    # durée conservation en jours
_SOC_ACT_MAX      = 1000  # garde-fou absolu (protection mémoire)
_SOC_LOCK         = threading.Lock()
_SOC_ACTIONS_FILE = _SCRIPTS_DIR / "jarvis_soc_actions.json"


def _soc_actions_load():
    """Charge le journal depuis le fichier JSON au démarrage."""
    global _SOC_ACTIONS
    try:
        if _SOC_ACTIONS_FILE.exists():
            with open(_SOC_ACTIONS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                _SOC_ACTIONS = data[-_SOC_ACT_MAX:]
    except Exception as e:
        _log.debug(f"[soc_actions_load] {e}")


def _soc_actions_save():
    """Persiste le journal sur disque (appelé à chaque nouvelle entrée)."""
    try:
        with open(_SOC_ACTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(_SOC_ACTIONS, f, ensure_ascii=False, indent=None)
    except Exception as e:
        _log.debug(f"[soc_actions_save] {e}")


_soc_actions_load()

# ── Surveillance SOC background ───────────────────────────────
_SOC_HB_LAST       = 0.0    # timestamp dernier heartbeat SOC dashboard
_SOC_HB_TTL        = 120.0  # si pas de HB depuis 120s → dashboard fermé (throttle onglet arrière-plan)
_SOC_MON_COOLDOWNS      = {}     # clé → timestamp dernière alerte (anti-spam)
_SOC_MON_COOLDOWNS_PATH = _SCRIPTS_DIR / "jarvis_soc_cooldowns.json"
_SOC_MON_INTERVAL       = 60     # poll toutes les 60s
_SOC_MON_ENABLED        = True   # peut être désactivé via /api/soc/monitor
_soc_stop_evt           = threading.Event()  # set() pour arrêt propre du thread (J13)
_SOC_AUTO_BANNED      = {}  # ip → timestamp dernier ban auto (cooldown 15min/IP)
_SOC_AUTO_BANNED_PATH = _SCRIPTS_DIR / "jarvis_soc_autobanned.json"

# ── Constantes SOC (ban, seuils, cooldowns) ───────────────────
_SOC_COOLDOWN_IP      = 15 * 60   # cooldown ban par IP (15 min)
_SOC_REQ_HOUR_SEUIL   = 500       # seuil req/h → alerte trafic

# ── Configuration ban auto SOC — source unique stages KC v3.97.195 ────
# Kill Chain 7 maillons (SOC v3.97.195) :
#   PROBE → RECON → SCAN → EXPLOIT → WAF → BRUTE → NEUTRALISÉ
#
# DÉFENSES (jamais bannies — règle absolue) : PROBE (UFW), WAF (ModSec), NEUTRALISÉ (CrowdSec+f2b)
# OFFENSIVES (candidats ban auto, priorité décroissante 0=plus prioritaire) :
#
#   stage      (min_hits, source_label,   duration, priority)
_SOC_BAN_CONFIG = {
    "EXPLOIT": (1,        "exploit-cve",  "24h",    0),   # ban immédiat
    "BRUTE":   (10,       "nginx-logs",   "24h",    1),
    "SCAN":    (20,       "nginx-logs",   "24h",    2),   # seuil élevé : évite bruit internet normal
    "RECON":   (None,     None,           None,     3),   # tracé KC, pas de ban auto direct
}
# Profils transverses (hors stage KC pur)
_SOC_BAN_HONEYPOT = (1, "honeypot",     "24h")   # IP touche uniquement honeypot
_SOC_BAN_SURICATA = (1, "suricata-ids", "48h")   # alerte IDS = ban prolongé

# Alias backwards-compat — dérivés depuis _SOC_BAN_CONFIG (source unique)
_SOC_BAN_MIN_COUNT    = _SOC_BAN_CONFIG["BRUTE"][0]
_SOC_BAN_MIN_EXPLOIT  = _SOC_BAN_CONFIG["EXPLOIT"][0]
_SOC_BAN_MIN_HONEYPOT = _SOC_BAN_HONEYPOT[0]
_SOC_BAN_MIN_SCAN     = _SOC_BAN_CONFIG["SCAN"][0]
# ── Seuils Suricata sév.2 (baseline ~1400/j — recalibrés 2026-03-31) ──
_SUR_SEV2_SURGE       = 3000      # surge C2 — alerte CRITIQUE
_SUR_SEV2_HIGH        = 1500      # activité élevée — alerte WARN
_SUR_SEV2_BAN         = 8000      # ban auto top IPs — C2 confirmé (aligné JS 01-utils.js)
# ── Limites de troncature / historique ────────────────────────
_SSH_ERR_TRUNCATE     = 120       # troncature message erreur SSH
_F2B_HISTORY_LIMIT    = 10        # entrées historique fail2ban dans ip-deep
_AUTOBAN_MIN_HITS     = 5         # hits KC minimum pour candidat ban auto


def _load_auto_banned():
    """Charge le cooldown ban depuis le disque — filtre les entrées expirées (>15min)."""
    global _SOC_AUTO_BANNED
    try:
        if _SOC_AUTO_BANNED_PATH.exists():
            raw = json.loads(_SOC_AUTO_BANNED_PATH.read_text(encoding="utf-8"))
            now = time.time()
            _SOC_AUTO_BANNED = {ip: ts for ip, ts in raw.items() if now - ts < _SOC_COOLDOWN_IP}
    except Exception as e:
        _log.warning(f"[load_auto_banned] {e}")


def _save_auto_banned():
    """Persiste le cooldown ban sur le disque (thread-safe via _SOC_BAN_LOCK).
    Snapshot du dict sous lock pour éviter 'dictionary changed size during iteration'."""
    try:
        with _SOC_BAN_LOCK:
            snapshot = dict(_SOC_AUTO_BANNED)
        _SOC_AUTO_BANNED_PATH.write_text(
            json.dumps(snapshot, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        _log.warning(f"[save_auto_banned] {e}")


def _load_cooldowns():
    """Charge les cooldowns d'alertes depuis le disque — filtre les entrées > 2h."""
    global _SOC_MON_COOLDOWNS
    try:
        if _SOC_MON_COOLDOWNS_PATH.exists():
            raw = json.loads(_SOC_MON_COOLDOWNS_PATH.read_text(encoding="utf-8"))
            now = time.time()
            _SOC_MON_COOLDOWNS = {k: ts for k, ts in raw.items() if now - ts < 7200}
    except Exception as e:
        _log.debug(f"[load_cooldowns] {e}")


def _save_cooldowns():
    """Persiste les cooldowns d'alertes sur le disque — purge les entrées > 48h."""
    global _SOC_MON_COOLDOWNS
    try:
        cutoff = time.time() - 48 * 3600
        _SOC_MON_COOLDOWNS = {k: ts for k, ts in _SOC_MON_COOLDOWNS.items() if ts > cutoff}
        _SOC_MON_COOLDOWNS_PATH.write_text(
            json.dumps(_SOC_MON_COOLDOWNS, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:
        _log.debug(f"[save_cooldowns] {e}")


_load_auto_banned()
_load_cooldowns()

# ════════════════════════════════════════════════════════════════
# CONFIG CENTRALISÉE — chargée depuis soc_config.json (optionnel)
# Fallback sur valeurs par défaut si le fichier est absent.
# Permet de changer IP/port srv-ngix, clé SSH, URL monitoring
# sans modifier le code.
# ════════════════════════════════════════════════════════════════
_SOC_CONFIG_PATH = _SCRIPTS_DIR / "soc_config.json"
_SOC_CONFIG_DEFAULTS = {
    "ngix_host":         "192.168.1.50",
    "ngix_ssh_port":     "2272",
    "ngix_ssh_user":     "root",
    "ngix_ssh_key":      str(Path.home() / ".ssh/id_nginx"),
    "monitoring_url":    "http://192.168.1.50:8080/monitoring.json",
    "proxmox_host":      "192.168.1.20",
    "proxmox_ssh_port":  "2272",
    "proxmox_ssh_user":  "root",
    "proxmox_ssh_key":   str(Path.home() / ".ssh/id_proxmox"),
    "clt_host":          "192.168.1.12",
    "clt_ssh_port":      "2272",
    "clt_ssh_user":      "root",
    "clt_ssh_key":       str(Path.home() / ".ssh/id_clt"),
    "pa85_host":         "192.168.1.13",
    "pa85_ssh_port":     "2272",
    "pa85_ssh_user":     "root",
    "pa85_ssh_key":      str(Path.home() / ".ssh/id_pa85"),
}


def _load_soc_config() -> dict:
    """Charge soc_config.json et fusionne avec les défauts."""
    cfg = dict(_SOC_CONFIG_DEFAULTS)
    try:
        if _SOC_CONFIG_PATH.exists():
            overrides = json.loads(_SOC_CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.update({k: v for k, v in overrides.items() if k in cfg})
            _log.info(f"[SOC-CONFIG] Chargé depuis {_SOC_CONFIG_PATH}")
    except Exception as e:
        _log.warning(f"[SOC-CONFIG] Erreur lecture soc_config.json : {e} — défauts utilisés")
    return cfg


_SOC_CFG = _load_soc_config()

def _ssh_base(user, host, port, key):
    """Retourne le tableau de base d'une commande SSH."""
    return ["ssh", "-i", key, "-p", str(port), "-o", "IdentitiesOnly=yes",
            "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10",
            f"{user}@{host}"]

# ── Config SSH — tous les hôtes ───────────────────────────────
_SSH_NGIX    = _ssh_base(_SOC_CFG["ngix_ssh_user"],    _SOC_CFG["ngix_host"],    _SOC_CFG["ngix_ssh_port"],    _SOC_CFG["ngix_ssh_key"])
_SSH_PROXMOX = _ssh_base(_SOC_CFG["proxmox_ssh_user"], _SOC_CFG["proxmox_host"], _SOC_CFG["proxmox_ssh_port"], _SOC_CFG["proxmox_ssh_key"])
_SSH_CLT     = _ssh_base(_SOC_CFG["clt_ssh_user"],     _SOC_CFG["clt_host"],     _SOC_CFG["clt_ssh_port"],     _SOC_CFG["clt_ssh_key"])
_SSH_PA85    = _ssh_base(_SOC_CFG["pa85_ssh_user"],     _SOC_CFG["pa85_host"],    _SOC_CFG["pa85_ssh_port"],    _SOC_CFG["pa85_ssh_key"])
_SSH_DEV1    = _ssh_base("root", "192.168.1.21", 2272, str(Path.home() / ".ssh" / "id_dev"))

# Lock pour sérialiser les connexions SSH — évite les timeouts par connexions parallèles
_SSH_LOCK  = threading.Lock()
_SOC_BAN_LOCK = threading.Lock()  # atomicité check+set sur _SOC_AUTO_BANNED

# ── Services autorisés au restart ─────────────────────────────
_ALLOWED_SERVICES = {"nginx", "crowdsec", "fail2ban", "php8.2-fpm", "php8.3-fpm"}

# ── IPs LAN — jamais bannies ──────────────────────────────────
# Plage RFC1918 complète — alignée sur le regex JS : /^(192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.|127\.)/
_LAN_PREFIXES = (
    "192.168.", "10.", "127.",
    "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
)

# ── Whitelist dynamique — IPs/préfixes supplémentaires ────────
_SOC_WHITELIST: list = []           # entrées chargées depuis le JSON
_SOC_WHITELIST_PATH = _SCRIPTS_DIR / "jarvis_soc_whitelist.json"
_SOC_WHITELIST_LOCK = threading.Lock()  # protège les accès concurrents (Flask + monitor thread)


def _load_whitelist():
    global _SOC_WHITELIST
    try:
        if _SOC_WHITELIST_PATH.exists():
            data = json.loads(_SOC_WHITELIST_PATH.read_text(encoding="utf-8"))
            with _SOC_WHITELIST_LOCK:
                _SOC_WHITELIST = data
    except Exception as e:
        _log.warning(f"[load_whitelist] {e}")


def _save_whitelist():
    try:
        with _SOC_WHITELIST_LOCK:
            snapshot = list(_SOC_WHITELIST)
        _SOC_WHITELIST_PATH.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        _log.warning(f"[save_whitelist] {e}")


def _is_whitelisted(ip: str) -> bool:
    """Retourne True si l'IP est LAN ou dans la whitelist — jamais alertée ni bannie.
    Thread-safe : snapshot de la liste sous lock avant itération."""
    if any(ip.startswith(p) for p in _LAN_PREFIXES):
        return True
    with _SOC_WHITELIST_LOCK:
        entries = list(_SOC_WHITELIST)
    for entry in entries:
        if ip == entry or ip.startswith(entry):
            return True
    return False


def _ip_skip(ip: str) -> bool:
    """Retourne True si l'IP est vide ou whitelistée — skip de ban."""
    return not ip or _is_whitelisted(ip)


_load_whitelist()


# ════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════

def _soc_log(action_type, detail, success, result=""):
    """Enregistre une action proactive (thread-safe, persisté sur disque)."""
    with _SOC_LOCK:
        _SOC_ACTIONS.append({
            "ts":      time.strftime("%Y-%m-%d %H:%M:%S"),
            "type":    action_type,
            "detail":  detail,
            "success": success,
            "result":  result[:300],
        })
        cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - _SOC_ACT_DAYS * 86400))
        while _SOC_ACTIONS and _SOC_ACTIONS[0]["ts"][:10] < cutoff:
            _SOC_ACTIONS.pop(0)
        if len(_SOC_ACTIONS) > _SOC_ACT_MAX:
            _SOC_ACTIONS.pop(0)
        _soc_actions_save()


# Cache monitoring.json — TTL 30s
_monitoring_cache: dict = {"raw": None, "ts": 0.0}
_MONITORING_TTL = 30
_MONITORING_URL  = _SOC_CFG["monitoring_url"]

# Cache defense_24h.json — TTL 30s · URL dérivée du monitoring_url (même host)
_defense_cache: dict = {"raw": None, "ts": 0.0}
_DEFENSE_TTL = 30
_DEFENSE_URL = _MONITORING_URL.rsplit("/", 1)[0] + "/defense_24h.json"


def _fetch_monitoring(timeout=12, force=False):
    """Récupère monitoring.json depuis srv-ngix via HTTP (plus léger que SSH).
    Cache TTL 30s pour la boucle de fond. force=True bypasse le cache (appels utilisateur).
    Timeout global partagé HTTP+SSH = max 15s (évite 32s worst-case)."""
    now = time.time()
    if not force and _monitoring_cache["raw"] is not None and (now - _monitoring_cache["ts"]) < _MONITORING_TTL:
        return True, _monitoring_cache["raw"]
    _t_start = time.monotonic()
    http_timeout = min(timeout, 8)  # HTTP max 8s
    try:
        import requests as _req
        r = _req.get(_MONITORING_URL, timeout=http_timeout)
        r.raise_for_status()
        raw = r.text
        _monitoring_cache["raw"] = raw
        _monitoring_cache["ts"] = now
        return True, raw
    except Exception as e:
        _log.warning(f"[fetch_monitoring] HTTP échoué ({e}) — fallback SSH")
        elapsed = time.monotonic() - _t_start
        ssh_timeout = max(3, min(10, 15 - int(elapsed)))  # reste du budget 15s
        ok, raw = _ssh_ngix("cat /var/www/monitoring/monitoring.json", timeout=ssh_timeout)
        if ok and raw:
            _monitoring_cache["raw"] = raw
            _monitoring_cache["ts"] = now
        return ok, raw


def _fetch_defense(timeout=8, force=False):
    """Récupère defense_24h.json depuis srv-ngix via HTTP. Cache TTL 30s.
    Pas de fallback SSH — si HTTP échoue on retourne None (la page web est la
    source de vérité, JARVIS s'adapte si elle est temporairement indispo)."""
    now = time.time()
    if not force and _defense_cache["raw"] is not None and (now - _defense_cache["ts"]) < _DEFENSE_TTL:
        return True, _defense_cache["raw"]
    try:
        import requests as _req
        r = _req.get(_DEFENSE_URL, timeout=timeout)
        r.raise_for_status()
        raw = r.text
        _defense_cache["raw"] = raw
        _defense_cache["ts"] = now
        return True, raw
    except Exception as e:
        _log.warning(f"[fetch_defense] HTTP échoué : {e}")
        return False, None


def _ssh_host(ssh_arr, remote_cmd, timeout=20, retries=1):
    """Exécute une commande SSH sur n'importe quel hôte. Retourne (ok, output).
    Sérialisé via _SSH_LOCK — zéro connexion parallèle (évite les timeouts).
    Backoff exponentiel sur retry : 2s, 4s…"""
    last_err = ""
    with _SSH_LOCK:
        for attempt in range(retries + 1):
            try:
                r = subprocess.run(
                    ssh_arr + [remote_cmd],
                    capture_output=True, text=True, timeout=timeout,
                    encoding="utf-8", errors="replace"
                )
                if r.returncode == 0:
                    return True, (r.stdout + r.stderr).strip()
                last_err = (r.stdout + r.stderr).strip()
            except subprocess.TimeoutExpired:
                last_err = "Timeout SSH"
            except Exception as e:
                last_err = str(e)
            if attempt < retries:
                time.sleep(2 ** (attempt + 1))
    return False, last_err


def _ssh_ngix(remote_cmd, timeout=20, retries=1):
    """Exécute une commande sur srv-ngix via SSH."""
    return _ssh_host(_SSH_NGIX, remote_cmd, timeout, retries)


def _ssh_proxmox(remote_cmd, timeout=20, retries=1):
    """Exécute une commande sur Proxmox VE via SSH."""
    return _ssh_host(_SSH_PROXMOX, remote_cmd, timeout, retries)


def _ssh_clt(remote_cmd, timeout=20, retries=1):
    """Exécute une commande sur clt (VM 106 — Apache) via SSH."""
    return _ssh_host(_SSH_CLT, remote_cmd, timeout, retries)


def _ssh_pa85(remote_cmd, timeout=20, retries=1):
    """Exécute une commande sur pa85 (VM 107 — Apache) via SSH."""
    return _ssh_host(_SSH_PA85, remote_cmd, timeout, retries)


def _ssh_dev1(remote_cmd, timeout=20, retries=1):
    """Exécute une commande sur srv-dev-1 (VM 101 — dev JARVIS) via SSH."""
    return _ssh_host(_SSH_DEV1, remote_cmd, timeout, retries)


_DUR_TTS_MAP = {
    "24h":   "vingt-quatre heures",
    "48h":   "quarante-huit heures",
    "72h":   "soixante-douze heures",
    "168h":  "cent soixante-huit heures",
    "8760h": "un an",
}
def _dur_to_tts(duration: str) -> str:
    """Convertit une durée brute ('24h','48h'…) en texte TTS prononceable."""
    if duration in _DUR_TTS_MAP:
        return _DUR_TTS_MAP[duration]
    import re as _re
    m = _re.match(r'^(\d+)h$', duration, _re.IGNORECASE)
    return f"{m.group(1)} heures" if m else duration

def _ip_to_tts(ip: str) -> str:
    """Convertit une IP en texte TTS prononceable ('1.2.3.4' → '1 point 2 point 3 point 4')."""
    return ip.replace(".", " point ")


def _ban_ip_ssh(ip: str, reason: str, duration: str = "24h") -> tuple:
    """Exécute `cscli decisions add` sur srv-ngix. Retourne (ok, output).
    Si la commande échoue (IP déjà bannie en doublon), vérifie via `cscli decisions list`
    et retourne (True, 'already-banned') — évite les faux échecs en race condition."""
    cmd = (f"cscli decisions add --ip {shlex.quote(ip)} "
           f"--reason {shlex.quote(reason)} "
           f"--duration {shlex.quote(duration)} --type ban")
    ok, out = _ssh_ngix(cmd)
    if ok:
        return True, out
    # Vérification post-échec : l'IP est peut-être déjà bannie (doublon gap-check/JS)
    check_cmd = f"cscli decisions list --ip {shlex.quote(ip)} -o json 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); print('banned' if d else 'none')\" 2>/dev/null || echo none"
    _, check_out = _ssh_ngix(check_cmd)
    if check_out.strip() == "banned":
        _log.info(f"[SOC] _ban_ip_ssh {ip} — déjà banni (doublon race) — traité comme succès")
        return True, "already-banned"
    return False, out


def _ip_try_mark_banned(ip: str) -> bool:
    """Check+set atomique sous _SOC_BAN_LOCK : marque l'IP comme bannied si hors cooldown.
    Retourne True si le ban peut procéder (marqué), False si cooldown encore actif."""
    now = time.time()
    with _SOC_BAN_LOCK:
        if now - _SOC_AUTO_BANNED.get(ip, 0) < _SOC_COOLDOWN_IP:
            return False
        _SOC_AUTO_BANNED[ip] = now
    return True


def _sync_autoban_log(data: dict) -> None:
    """Synchronise les bans récents de monitoring_gen.py dans _SOC_AUTO_BANNED.
    Évite que JARVIS re-banne une IP que monitoring_gen.py vient de bannir (< 15 min).
    Corrige la fenêtre de chevauchement due au délai max 5 min entre deux cycles."""
    entries = data.get("autoban_log", [])
    if not entries:
        return
    now = time.time()
    synced = 0
    with _SOC_BAN_LOCK:
        for entry in entries:
            ip = entry.get("ip", "")
            ts_str = entry.get("ts", "")
            if not ip or not ts_str:
                continue
            try:
                # Format ISO : "2026-04-11T23:35:14Z"
                dt = datetime.datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%SZ")
                ban_ts = dt.replace(tzinfo=datetime.UTC).timestamp()
            except (ValueError, AttributeError):
                continue
            age = now - ban_ts
            if age < _SOC_COOLDOWN_IP:  # < 15 min → dans la fenêtre de cooldown
                existing = _SOC_AUTO_BANNED.get(ip, 0)
                if ban_ts > existing:   # ne pas écraser un ban JARVIS plus récent
                    _SOC_AUTO_BANNED[ip] = ban_ts
                    synced += 1
    if synced:
        _log.debug(f"[JARVIS-SOC-SYNC] {synced} IP(s) importées depuis autoban_log (anti-doublon)")


def _soc_dashboard_open():
    return (time.time() - _SOC_HB_LAST) < _SOC_HB_TTL


def _soc_cooldown_ok(key, minutes=10):
    """Retourne True si l'alerte n'a pas été émise depuis `minutes` minutes.
    Persiste l'état sur disque pour survivre aux redémarrages de JARVIS."""
    last = _SOC_MON_COOLDOWNS.get(key, 0)
    if time.time() - last > minutes * 60:
        _SOC_MON_COOLDOWNS[key] = time.time()
        _save_cooldowns()
        return True
    return False


# ════════════════════════════════════════════════════════════════
# ROUTES SOC
# ════════════════════════════════════════════════════════════════

@soc_bp.route("/api/soc/whitelist", methods=["GET"])
def api_soc_whitelist_get():
    """Retourne la whitelist dynamique (IPs/préfixes)."""
    with _SOC_WHITELIST_LOCK:
        snapshot = list(_SOC_WHITELIST)
    return Response(json.dumps({"whitelist": snapshot}), mimetype="application/json")


@soc_bp.route("/api/soc/whitelist", methods=["POST"])
def api_soc_whitelist_add():
    """Ajoute une IP ou un préfixe à la whitelist."""
    err = _check_csrf()
    if err: return err
    entry = (request.json or {}).get("ip", "").strip()
    if not entry:
        return Response(json.dumps({"error": "Champ ip requis"}), status=400, mimetype="application/json")
    with _SOC_WHITELIST_LOCK:
        if entry in _SOC_WHITELIST:
            return Response(json.dumps({"ok": True, "info": "déjà présent"}), mimetype="application/json")
        _SOC_WHITELIST.append(entry)
        snapshot = list(_SOC_WHITELIST)
    _save_whitelist()
    _log.info(f"[SOC-WHITELIST] +{entry}")
    return Response(json.dumps({"ok": True, "whitelist": snapshot}), mimetype="application/json")


@soc_bp.route("/api/soc/whitelist", methods=["DELETE"])
def api_soc_whitelist_del():
    """Retire une IP ou un préfixe de la whitelist."""
    err = _check_csrf()
    if err: return err
    entry = (request.json or {}).get("ip", "").strip()
    with _SOC_WHITELIST_LOCK:
        if entry not in _SOC_WHITELIST:
            return Response(json.dumps({"error": "Entrée non trouvée"}), status=404, mimetype="application/json")
        _SOC_WHITELIST.remove(entry)
        snapshot = list(_SOC_WHITELIST)
    _save_whitelist()
    _log.info(f"[SOC-WHITELIST] -{entry}")
    return Response(json.dumps({"ok": True, "whitelist": snapshot}), mimetype="application/json")


def _check_csrf():
    """Vérifie que la requête provient bien du JS SOC (anti-CSRF LAN).
    Retourne un Response d'erreur si invalide, None sinon."""
    if request.headers.get("X-Requested-With") != "XMLHttpRequest":
        return Response(
            json.dumps({"error": "Requête non autorisée (CSRF)"}),
            status=403, mimetype="application/json"
        )
    return None


@soc_bp.route("/api/soc/ban-ip", methods=["POST"])
def api_soc_ban_ip():
    """Ban une IP via CrowdSec sur srv-ngix."""
    err = _check_csrf()
    if err: return err
    data     = request.json or {}
    ip       = data.get("ip", "").strip()
    reason   = re.sub(r"[^a-zA-Z0-9 \-._]", "", data.get("reason", "SOC auto-ban"))[:80]
    duration = data.get("duration", "24h")
    try:
        ipaddress.IPv4Address(ip)
    except ValueError:
        return Response(json.dumps({"error": "IP invalide"}), status=400, mimetype="application/json")
    if _is_whitelisted(ip):
        _log.warning(f"[SOC] Tentative de ban bloquée — IP LAN/whitelist : {ip} (reason={reason!r})")
        _soc_log("ban_ip_blocked", f"{ip} — IP LAN/protégée — ban refusé (reason={reason!r})", False, "LAN/whitelist")
        return Response(json.dumps({"error": "IP protégée (LAN/whitelist) — ban refusé"}), status=403, mimetype="application/json")
    _dur_max = {'s': 86400, 'm': 1440, 'h': 8760, 'd': 365}
    if not re.match(r'^\d{1,6}[smhd]$', duration) or int(duration[:-1]) > _dur_max.get(duration[-1], 0):
        duration = "24h"
    ok, out = _ban_ip_ssh(ip, reason, duration)
    _soc_log("ban_ip", f"{ip} — {reason} ({duration})", ok, out)
    return Response(json.dumps({"ok": ok, "ip": ip, "result": out}, ensure_ascii=False), mimetype="application/json")


@soc_bp.route("/api/soc/unban-ip", methods=["POST"])
def api_soc_unban_ip():
    """Lève le ban d'une IP via CrowdSec."""
    err = _check_csrf()
    if err: return err
    ip = (request.json or {}).get("ip", "").strip()
    try:
        ipaddress.IPv4Address(ip)
    except ValueError:
        return Response(json.dumps({"error": "IP invalide"}), status=400, mimetype="application/json")
    cmd = f"cscli decisions delete --ip {shlex.quote(ip)}"
    ok, out = _ssh_ngix(cmd)
    _soc_log("unban_ip", ip, ok, out)
    return Response(json.dumps({"ok": ok, "ip": ip, "result": out}, ensure_ascii=False), mimetype="application/json")


@soc_bp.route("/api/soc/restart-service", methods=["POST"])
def api_soc_restart_service():
    """Redémarre un service autorisé sur srv-ngix."""
    err = _check_csrf()
    if err: return err
    svc = (request.json or {}).get("service", "").strip().lower()
    if svc not in _ALLOWED_SERVICES:
        return Response(json.dumps({"error": f"Service non autorisé. Autorisés: {sorted(_ALLOWED_SERVICES)}"}),
                        status=403, mimetype="application/json")
    cmd = f"systemctl restart {shlex.quote(svc)}"
    ok, out = _ssh_ngix(cmd, timeout=20)
    _soc_log("restart_service", svc, ok, out)
    return Response(json.dumps({"ok": ok, "service": svc, "result": out}, ensure_ascii=False), mimetype="application/json")


@soc_bp.route("/api/soc/actions", methods=["GET"])
def api_soc_actions():
    """Journal des actions proactives SOC."""
    with _SOC_LOCK:
        total   = len(_SOC_ACTIONS)
        success = sum(1 for a in _SOC_ACTIONS if a["success"])
        by_type = {"ban_ip": 0, "unban_ip": 0, "restart_service": 0}
        for a in _SOC_ACTIONS:
            t = a.get("type", "")
            if t in by_type:
                by_type[t] += 1
        snapshot = _SOC_ACTIONS[-50:][::-1]
        ts_list  = [a["ts"] for a in _SOC_ACTIONS]
    return Response(json.dumps({
        "total":   total,
        "success": success,
        "failed":  total - success,
        "by_type": by_type,
        "actions": snapshot,
        "ts_list": ts_list,
    }, ensure_ascii=False), mimetype="application/json")


@soc_bp.route("/api/soc/actions/clear", methods=["POST"])
def api_soc_actions_clear():
    """Vide le journal des actions proactives."""
    with _SOC_LOCK:
        _SOC_ACTIONS.clear()
        _soc_actions_save()
    return Response('{"ok":true}', mimetype="application/json")


@soc_bp.route("/api/soc/test", methods=["GET"])
def api_soc_test():
    """Diagnostic complet mode proactif : API + SSH + TTS."""
    results = {}
    results["jarvis_api"] = {"ok": True, "msg": "JARVIS API opérationnelle"}
    ok_ssh, out_ssh = _ssh_ngix("echo JARVIS_SOC_TEST_OK", timeout=8)
    results["ssh_ngix"] = {
        "ok": ok_ssh,
        "msg": ("SSH srv-ngix opérationnel" if ok_ssh else "SSH srv-ngix KO — " + out_ssh[:_SSH_ERR_TRUNCATE])
    }
    try:
        _speak("Test JARVIS. Mode proactif nominal. SSH opérationnel. Surveillance active.")
        results["tts"] = {"ok": True, "msg": "TTS déclenché"}
    except Exception as e:
        results["tts"] = {"ok": False, "msg": str(e)}
    results["overall"] = results["jarvis_api"]["ok"] and results["ssh_ngix"]["ok"] and results["tts"]["ok"]
    return Response(json.dumps(results, ensure_ascii=False), mimetype="application/json")


@soc_bp.route("/api/soc/force-autoban", methods=["POST"])
def api_soc_force_autoban():
    """Force un cycle auto-ban immédiat (indépendant du dashboard ouvert/fermé)."""
    err = _check_csrf()
    if err: return err
    ok_fetch, raw = _fetch_monitoring(timeout=15, force=True)
    if not ok_fetch or not raw:
        return Response(json.dumps({"ok": False, "error": "monitoring.json inaccessible"}),
                        status=503, mimetype="application/json")
    try:
        d = json.loads(raw)
    except Exception as e:
        return Response(json.dumps({"ok": False, "error": str(e)}),
                        status=500, mimetype="application/json")
    kc         = d.get("kill_chain", {})
    active_ips = kc.get("active_ips", [])
    cs_detail  = d.get("crowdsec", {}).get("decisions_detail", {})
    geo_map    = {g["ip"]: g for g in d.get("traffic", {}).get("recent_geoips", []) if g.get("ip")}
    rph        = d.get("traffic", {}).get("requests_per_hour", {})
    h_key      = time.strftime("%H")
    cur_rph    = max((v for k, v in rph.items() if k == h_key or k[-2:] == h_key), default=0)

    diag_candidates = []
    for ip_obj in active_ips:
        ip = ip_obj.get("ip", "")
        if not ip:
            continue
        geo = geo_map.get(ip, {})
        skip = ("LAN" if _is_whitelisted(ip)
                else "stage" if ip_obj.get("stage") not in {"EXPLOIT", "BRUTE"}
                else "cs_banni" if geo.get("cs_banned") or cs_detail.get(ip)
                else "cooldown" if time.time() - _SOC_AUTO_BANNED.get(ip, 0) < _SOC_COOLDOWN_IP
                else None)
        diag_candidates.append({"ip": ip, "stage": ip_obj.get("stage"), "count": ip_obj.get("count"), "skip": skip})

    before = len(_SOC_ACTIONS)
    _soc_autoban(d)
    _soc_reqhour_check(d)
    after       = len(_SOC_ACTIONS)
    new_actions = after - before
    return Response(json.dumps({
        "ok":          True,
        "new_actions": new_actions,
        "active_ips":  len(active_ips),
        "req_per_hour": cur_rph,
        "candidates":  diag_candidates,
    }, ensure_ascii=False), mimetype="application/json")


@soc_bp.route("/api/soc/threat-score", methods=["GET"])
def api_soc_threat_score():
    """Expose le score de menace pré-calculé par monitoring_gen.py (source de vérité unique).
    Lit threat_score/threat_level depuis monitoring.json — DT-08."""
    ok_fetch, raw = _fetch_monitoring(timeout=15, force=True)
    if not ok_fetch or not raw:
        return Response(json.dumps({"ok": False, "error": "monitoring.json inaccessible"}),
                        status=503, mimetype="application/json")
    try:
        d = json.loads(raw)
    except Exception as e:
        return Response(json.dumps({"ok": False, "error": str(e)}),
                        status=500, mimetype="application/json")
    ts = _threat_score_from_json(d, set())
    return Response(json.dumps({"ok": True, **ts}, ensure_ascii=False), mimetype="application/json")


@soc_bp.route("/api/soc/defense", methods=["GET"])
def api_soc_defense():
    """Expose defense_24h.json (résumé compact 24h des actions défensives —
    bans, WAF, GeoBlock, IDS, fail2ban, UFW). Source : defense_aggregator.py
    sur srv-ngix (cron 60s). Sortie 13× plus compacte que monitoring.json."""
    ok, raw = _fetch_defense(timeout=6)
    if not ok or not raw:
        return Response(json.dumps({"ok": False, "error": "defense_24h.json inaccessible"}),
                        status=503, mimetype="application/json")
    try:
        d = json.loads(raw)
    except Exception as e:
        return Response(json.dumps({"ok": False, "error": str(e)}),
                        status=500, mimetype="application/json")
    return Response(json.dumps({"ok": True, **d}, ensure_ascii=False),
                    mimetype="application/json")


@soc_bp.route("/api/soc/ioc", methods=["GET"])
def api_soc_ioc():
    """Expose le bloc `ioc` de monitoring.json (Indicateurs de Compromission
    POST-COMPROMISSION). Source : ioc_collect.py sur srv-ngix (cron 60s).
    Lecture seule — pure extraction d'une sous-clé pré-calculée.

    Sprint 18d 2026-05-16 : alimente le MCP tool jarvis_ioc_status."""
    ok, raw = _fetch_monitoring(timeout=8)
    if not ok or not raw:
        return Response(json.dumps({"ok": False, "error": "monitoring.json inaccessible"}),
                        status=503, mimetype="application/json")
    try:
        d = json.loads(raw)
    except Exception as e:
        return Response(json.dumps({"ok": False, "error": str(e)}),
                        status=500, mimetype="application/json")
    ioc = d.get("ioc") or {}
    if not ioc:
        return Response(json.dumps({"ok": False, "error": "bloc 'ioc' absent (déploiement SOC partiel ?)"}),
                        status=503, mimetype="application/json")
    return Response(json.dumps({"ok": True, "ioc": ioc}, ensure_ascii=False),
                    mimetype="application/json")


@soc_bp.route("/api/soc/recently-banned", methods=["GET"])
def api_soc_recently_banned():
    """Retourne les IPs bannies par Python dans les 15 dernières minutes.
    Utilisé par le JS pour pré-marquer _autoBanned et éviter le double TTS."""
    now = time.time()
    cutoff = now - _SOC_COOLDOWN_IP
    with _SOC_BAN_LOCK:
        recent = {ip: ts for ip, ts in _SOC_AUTO_BANNED.items() if ts >= cutoff}
    return Response(json.dumps(recent, ensure_ascii=False), mimetype="application/json")


@soc_bp.route("/api/soc/heartbeat", methods=["POST"])
def api_soc_heartbeat():
    global _SOC_HB_LAST
    _SOC_HB_LAST = time.time()
    return Response('{"ok":true}', mimetype="application/json")


def get_soc_status() -> dict:
    """Résumé état SOC — utilisé par /api/status pour la defense chain."""
    with _SOC_LOCK:
        bans_24h  = sum(1 for a in _SOC_ACTIONS if a.get("type") == "ban_ip" and a.get("success"))
        alerts_24h = len(_SOC_ACTIONS)
        engine_on  = _SOC_MON_ENABLED
    return {
        "soc_engine_active": engine_on,
        "bans_24h":          bans_24h,
        "alerts_24h":        alerts_24h,
    }


@soc_bp.route("/api/soc/monitor", methods=["GET", "POST"])
def api_soc_monitor():
    global _SOC_MON_ENABLED
    if request.method == "POST":
        _SOC_MON_ENABLED = bool((request.json or {}).get("enabled", True))
    return Response(json.dumps({"enabled": _SOC_MON_ENABLED, "dashboard_open": _soc_dashboard_open()}),
                    mimetype="application/json")


# ════════════════════════════════════════════════════════════════
# INVESTIGATION IP APPROFONDIE — /api/soc/ip-deep
# Agrège GeoIP · CrowdSec · Fail2ban · autoban · nginx · rsyslog
# central · WHOIS — fenêtre temporelle 7 jours
# ════════════════════════════════════════════════════════════════

def _b64py(script: str) -> str:
    """Encode un script Python en base64 et retourne la commande SSH distante."""
    return f"echo {base64.b64encode(script.encode()).decode()} | base64 -d | python3"


def _ssh_json_exec(script: str, timeout: int = 10) -> dict:
    """Exécute un script Python via SSH b64, retourne le JSON parsé ou {}."""
    ok, out = _ssh_ngix(_b64py(script), timeout=timeout)
    try:
        return json.loads(out.strip()) if ok and out.strip().startswith('{') else {}
    except Exception:
        return {}


def _deep_geoip(ip: str) -> dict:
    """GeoIP via GeoLite2-City.mmdb."""
    script = (
        "import geoip2.database,json,sys\n"
        "try:\n"
        f"    r=geoip2.database.Reader('/usr/share/GeoIP/GeoLite2-City.mmdb').city('{ip}')\n"
        "    print(json.dumps({'country':r.country.name,'iso':r.country.iso_code or '','city':r.city.name or '','lat':float(r.location.latitude or 0),'lon':float(r.location.longitude or 0)}))\n"
        "except Exception:\n"
        "    print('{}')\n"
    )
    return _ssh_json_exec(script, timeout=10)


def _deep_crowdsec(ip: str) -> dict:
    """CrowdSec — décisions actives + alertes 30j."""
    ok, out = _ssh_ngix(f"cscli decisions list --ip {ip} -o json 2>/dev/null || echo '[]'", timeout=10)
    try:
        cs_raw = json.loads(out) if ok else []
        if not isinstance(cs_raw, list):
            cs_raw = []
    except Exception:
        cs_raw = []
    # cscli decisions list -o json retourne des alertes imbriquées :
    # [{..., "decisions": [{scenario, duration, origin, type, value}]}]
    cs_decisions = []
    for alert in cs_raw:
        for d in (alert.get("decisions") or []):
            cs_decisions.append(d)
    ok, out = _ssh_ngix(
        f"cscli alerts list --ip {ip} --since 720h -o json 2>/dev/null || echo '[]'", timeout=12
    )
    try:
        cs_alerts = json.loads(out) if ok else []
        if not isinstance(cs_alerts, list):
            cs_alerts = []
    except Exception:
        cs_alerts = []
    return {
        "banned":        len(cs_decisions) > 0,
        "count":         len(cs_decisions),
        "decisions":     [
            {
                "id":       d.get("id"),
                "scenario": d.get("scenario", "") or d.get("reason", "") or "ban",
                "duration": d.get("duration", ""),
                "origin":   d.get("origin", ""),
                "type":     d.get("type", "ban"),
            }
            for d in cs_decisions[:5]
        ],
        "alerts_30d":    len(cs_alerts),
        "alerts_detail": [
            {"ts": a.get("created_at", ""), "scenario": a.get("scenario", ""), "count": a.get("events_count", 0)}
            for a in cs_alerts[-10:]
        ],
    }


def _deep_fail2ban(ip: str) -> dict:
    """Fail2ban — bans actifs + historique (sqlite)."""
    script = (
        "import sqlite3,json,time\n"
        "try:\n"
        "    db=sqlite3.connect('/var/lib/fail2ban/fail2ban.sqlite3')\n"
        "    c=db.cursor()\n"
        f"    c.execute('SELECT name,timeofban,bantime,bancount FROM bans WHERE ip=?', ('{ip}',))\n"
        "    rows=c.fetchall()\n"
        "    now=int(time.time())\n"
        "    active=[r[0] for r in rows if r[1]+r[2]>now]\n"
        "    history=[{'jail':r[0],'ts':r[1],'bantime':r[2],'count':r[3]} for r in rows]\n"
        "    print(json.dumps({'active':active,'history':history,'total_records':len(rows)}))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'active':[],'history':[],'total_records':0,'err':str(e)}))\n"
    )
    f2b = _ssh_json_exec(script, timeout=10)
    return {
        "banned":        len(f2b.get("active", [])) > 0,
        "jails":         f2b.get("active", []),
        "total_records": f2b.get("total_records", 0),
        "history":       f2b.get("history", [])[:_F2B_HISTORY_LIMIT],
    }


def _deep_autoban(ip: str) -> dict:
    """autoban-log.json — récidive JARVIS/monitoring_gen."""
    script = (
        "import json\n"
        "try:\n"
        "    d=json.load(open('/var/www/monitoring/autoban-log.json'))\n"
        f"    hits=[e for e in d if e.get('ip')=='{ip}']\n"
        "    print(json.dumps({'count':len(hits),'history':hits}))\n"
        "except Exception:\n"
        "    print('{\"count\":0,\"history\":[]}')\n"
    )
    return _ssh_json_exec(script, timeout=10) or {"count": 0, "history": []}


def _deep_nginx_hits(ip: str) -> int:
    """nginx — hits (log courant + archives gz)."""
    cmd = (
        f"a=$(grep -c ' {ip} ' /var/log/nginx/access.log 2>/dev/null || echo 0);"
        f"b=$(zcat /var/log/nginx/access.log.*.gz 2>/dev/null | grep -c ' {ip} ' 2>/dev/null || echo 0);"
        "echo $((a+b))"
    )
    ok, out = _ssh_ngix(cmd, timeout=15)
    try:
        return int(out.strip()) if ok and out.strip().isdigit() else 0
    except Exception:
        return 0


def _deep_nginx_last(ip: str) -> list:
    """nginx — dernières requêtes (aperçu 5 lignes)."""
    ok, out = _ssh_ngix(
        f"grep ' {ip} ' /var/log/nginx/access.log 2>/dev/null | tail -5", timeout=10
    )
    return [ln.strip() for ln in out.split('\n') if ln.strip()] if ok else []


def _deep_rsyslog(ip: str) -> dict:
    """rsyslog central — grep croisé 30j toutes sources."""
    cmd = (
        f"grep -r '{ip}' /var/log/central/ --include='*.log' -c 2>/dev/null"
        " | grep -v ':0$' | sort -t: -k2 -rn | head -15"
    )
    ok, out = _ssh_ngix(cmd, timeout=25)
    counts = {}
    total  = 0
    if ok:
        for line in out.split('\n'):
            line = line.strip()
            if ':' in line:
                fname, cnt = line.rsplit(':', 1)
                if cnt.isdigit():
                    short = '/'.join(fname.strip().split('/')[-2:])
                    counts[short] = int(cnt)
                    total += int(cnt)
    return {"total": total, "sources": counts}


@soc_bp.route("/api/soc/ip-history", methods=["POST"])
def api_soc_ip_history():
    """CrowdSec + fail2ban historique uniquement — endpoint léger pour MCP jarvis_soc_ask.
    Évite les 30s de /api/soc/ip-deep (whois + nginx + rsyslog)."""
    ip = (request.json or {}).get("ip", "").strip()
    try:
        ipaddress.IPv4Address(ip)
    except ValueError:
        return Response(json.dumps({"error": "IP invalide"}), status=400, mimetype="application/json")
    return Response(json.dumps({
        "ip":       ip,
        "crowdsec": _deep_crowdsec(ip),
        "fail2ban": _deep_fail2ban(ip),
    }, ensure_ascii=False), mimetype="application/json")


@soc_bp.route("/api/soc/ip-deep", methods=["POST"])
def api_soc_ip_deep():
    """Investigation approfondie d'une IP — GeoIP, CrowdSec, Fail2ban,
    historique bans 7j, logs nginx + rsyslog croisés, WHOIS/ASN.
    Route lecture seule — CORS LAN suffit, pas de _check_csrf."""
    ip = (request.json or {}).get("ip", "").strip()
    try:
        ipaddress.IPv4Address(ip)
    except ValueError:
        return Response(json.dumps({"error": "IP invalide"}), status=400, mimetype="application/json")

    result = {
        "ip":         ip,
        "ts":         datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "is_lan":     _is_whitelisted(ip),
        "geoip":      _deep_geoip(ip),
        "crowdsec":   _deep_crowdsec(ip),
        "fail2ban":   _deep_fail2ban(ip),
        "autoban":    _deep_autoban(ip),
        "nginx_hits": _deep_nginx_hits(ip),
        "nginx_last": _deep_nginx_last(ip),
        "rsyslog":    _deep_rsyslog(ip),
    }

    # ── WHOIS/ASN ─────────────────────────────────────────────────
    ok, out = _ssh_ngix(
        f"whois {ip} 2>/dev/null"
        r" | grep -iE '^(org-name|netname|descr|country|orgname|owner|route|cidr|org-type):'"
        " | head -12",
        timeout=12,
    )
    result["whois"] = [ln.strip() for ln in out.split('\n') if ln.strip()] if ok else []

    _log.info(f"[ip-deep] {ip} — geo:{bool(result['geoip'])} cs:{result['crowdsec']['banned']} f2b:{result['fail2ban']['banned']}")
    return Response(json.dumps(result, ensure_ascii=False), mimetype="application/json")


# ════════════════════════════════════════════════════════════════
# AUTO-BAN ET SURVEILLANCE BACKGROUND
# ════════════════════════════════════════════════════════════════

# Priorité ban dérivée de _SOC_BAN_CONFIG (source unique — section haut du module)
_STAGE_PRIORITY = {k: v[3] for k, v in _SOC_BAN_CONFIG.items()}


def _autoban_classify(ip_obj):
    """Détermine (threshold, src_lbl, duration) selon le profil de l'IP."""
    sources     = ip_obj.get("sources", [])
    is_nh       = sources and all(s == "NH" for s in sources)
    stage       = ip_obj.get("stage")
    if ip_obj.get("sur_alert", False):
        return 1, "suricata-ids", "48h"
    if is_nh:
        return _SOC_BAN_MIN_HONEYPOT, "honeypot", "24h"
    if stage == "EXPLOIT":
        return _SOC_BAN_MIN_EXPLOIT, "exploit-cve", "24h"
    if stage == "SCAN":
        return _SOC_BAN_MIN_SCAN, "nginx-logs", "24h"
    return _SOC_BAN_MIN_COUNT, "nginx-logs", "24h"  # BRUTE


def _soc_autoban(data):
    """Equivalent Python de checkAutoBan() JS — bannit les IPs EXPLOIT/BRUTE non bannies.
    Appelé uniquement quand le dashboard est FERMÉ (le JS gère sinon)."""
    global _SOC_AUTO_BANNED
    kc         = data.get("kill_chain", {})
    active_ips = kc.get("active_ips", [])
    geo_map    = {g["ip"]: g for g in (data.get("traffic", {}).get("recent_geoips", [])) if g.get("ip")}
    cs_detail_set = set(data.get("crowdsec", {}).get("decisions_detail", {}).keys())
    ban_stages = {"EXPLOIT", "BRUTE", "SCAN"}

    for ip_obj in active_ips:
        ip = ip_obj.get("ip", "")
        if _ip_skip(ip): continue
        if ip_obj.get("stage") not in ban_stages:
            continue
        if geo_map.get(ip, {}).get("cs_banned") or ip in cs_detail_set:
            continue
        threshold, src_lbl, duration = _autoban_classify(ip_obj)
        if (ip_obj.get("count") or 0) < threshold:
            continue
        if not _ip_try_mark_banned(ip):
            continue
        _save_auto_banned()
        stage   = ip_obj.get("stage", "?")
        country = ip_obj.get("country", "-")
        reason  = f"jarvis-autoban-{stage.lower()}-{src_lbl}"
        ok, out = _ban_ip_ssh(ip, reason, duration)
        _soc_log("ban_ip", f"{ip} [{country}] {stage} — {src_lbl} — {ip_obj.get('count',0)} hits ({duration})", ok, out)
        if ok and not _soc_dashboard_open():
            _country_tts = (f" Origine : {country}." if country and country not in ('-', '?', '') else '')
            _dur_tts = _dur_to_tts(duration)
            _speak(f"Ban automatique. IP {_ip_to_tts(ip)}.{_country_tts} Source : {src_lbl.replace('-', ' ')}. Durée : {_dur_tts}. Unban automatique — aucune action requise.")


def _soc_exploit_gap_check(data):
    """Ban EXPLOIT IPs avec cs_decision=None — s'exécute TOUJOURS, même dashboard ouvert.
    Comble le gap du gate _soc_dashboard_open() : le JS peut rater des IPs si l'onglet
    n'est pas actif ou en cas de délai. Ban silencieux si dashboard ouvert (JS gère TTS).
    Retourne le set des IPs effectivement bannies dans ce cycle — utilisé par le thread
    monitor pour exclure ces IPs du calcul exploit_unblocked et éviter le double TTS."""
    global _SOC_AUTO_BANNED
    kc         = data.get("kill_chain", {})
    active_ips = kc.get("active_ips", [])
    cs_detail  = data.get("crowdsec", {}).get("decisions_detail", {})
    just_banned: set = set()

    for ip_obj in active_ips:
        ip = ip_obj.get("ip", "")
        if _ip_skip(ip): continue
        if ip_obj.get("stage") != "EXPLOIT":
            continue
        if ip_obj.get("cs_decision") or cs_detail.get(ip):
            continue
        if (ip_obj.get("count") or 0) < _SOC_BAN_MIN_EXPLOIT:
            continue
        if not _ip_try_mark_banned(ip):
            continue
        _save_auto_banned()
        country = ip_obj.get("country", "-")
        reason  = "jarvis-autoban-exploit-gap"
        ok, out = _ban_ip_ssh(ip, reason, "48h")
        _soc_log("ban_ip",
                 f"{ip} [{country}] EXPLOIT cs_decision=None — gap-check "
                 f"({ip_obj.get('count', 0)} hits, 48h)", ok, out)
        if ok:
            just_banned.add(ip)
            if not _soc_dashboard_open():
                _country_tts = (f" Origine : {country}." if country and country not in ('-', '?', '') else '')
                _speak(f"Ban automatique. IP {_ip_to_tts(ip)}.{_country_tts} Stage exploit, décision CrowdSec manquante comblée. Durée : {_dur_to_tts('48h')}. Unban automatique.")
    return just_banned


def _reqhour_candidates(active_ips, geo_map, cs_detail, now, min_hits):
    """Filtre les IPs actives éligibles au ban (non whitelist, non déjà bannies, hits >= seuil)."""
    return [
        ip_obj for ip_obj in active_ips
        if (ip_obj.get("ip") and
            not _is_whitelisted(ip_obj["ip"]) and
            not geo_map.get(ip_obj["ip"], {}).get("cs_banned") and
            not cs_detail.get(ip_obj["ip"]) and
            now - _SOC_AUTO_BANNED.get(ip_obj["ip"], 0) >= _SOC_COOLDOWN_IP and
            (ip_obj.get("count") or 0) >= min_hits)
    ]


def _reqhour_inject_suricata(candidates, sur, cs_detail, now):
    """Ajoute les IPs Suricata critiques aux candidats si pas déjà présentes."""
    if not sur.get("available"):
        return
    existing = {c.get("ip") for c in candidates}
    for alert in (sur.get("recent_critical") or []):
        ip = alert.get("src_ip", "")
        if (not ip or _is_whitelisted(ip)
                or cs_detail.get(ip)
                or now - _SOC_AUTO_BANNED.get(ip, 0) < _SOC_COOLDOWN_IP
                or ip in existing):
            continue
        candidates.append({"ip": ip, "stage": "EXPLOIT", "country": "-",
                            "count": 1, "sur_alert": True})
        existing.add(ip)


def _soc_reqhour_check(data):
    """Equivalent Python de checkReqPerHour() JS — alerte + ban auto si pic >500 req/h.
    Appelé uniquement quand le dashboard est FERMÉ."""
    global _SOC_AUTO_BANNED
    now    = time.time()
    rph    = data.get("traffic", {}).get("requests_per_hour", {})
    h_key  = time.strftime("%H")
    cur_val = 0
    for k, v in rph.items():
        if k == h_key or k[-2:] == h_key:
            cur_val = max(cur_val, v or 0)
    if cur_val < _SOC_REQ_HOUR_SEUIL:
        return
    if not _soc_cooldown_ok("reqhour_spike", minutes=20):
        return

    kc         = data.get("kill_chain", {})
    active_ips = kc.get("active_ips", [])
    geo_map    = {g["ip"]: g for g in (data.get("traffic", {}).get("recent_geoips", [])) if g.get("ip")}
    cs_detail  = data.get("crowdsec", {}).get("decisions_detail", {})
    min_hits   = _AUTOBAN_MIN_HITS

    candidates = _reqhour_candidates(active_ips, geo_map, cs_detail, now, min_hits)
    _reqhour_inject_suricata(candidates, data.get("suricata", {}), cs_detail, now)
    candidates.sort(key=lambda x: (_STAGE_PRIORITY.get(x.get("stage", "RECON"), 9), -(x.get("count") or 0)))
    banned_count = 0
    for ip_obj in candidates[:3]:
        ip      = ip_obj["ip"]
        stage   = ip_obj.get("stage", "?")
        country = ip_obj.get("country", "-")
        if not _ip_try_mark_banned(ip):
            continue
        _save_auto_banned()
        reason  = f"jarvis-autoban-pic-trafic-{cur_val}rph-{stage.lower()}"
        ok, out = _ban_ip_ssh(ip, reason, "24h")
        _soc_log("ban_ip", f"{ip} [{country}] {stage} — pic {cur_val} req/h (auto-dashboard-off)", ok, out)
        if ok:
            banned_count += 1
    if banned_count > 0:
        _speak(f"Alerte SOC. Pic de trafic : {cur_val} requêtes cette heure. {banned_count} IP{'s' if banned_count > 1 else ''} bannie{'s' if banned_count > 1 else ''} pour vingt-quatre heures. Unban automatique. CrowdSec actif.")
    else:
        _speak(f"Alerte SOC. Pic de trafic : {cur_val} requêtes cette heure. Toutes les IPs actives sont déjà bannies. Aucune action requise.")


def _sur_ban_sev1(sur: dict, cs_detail: dict) -> list:
    """Ban auto sév.1 CRITIQUE — retourne liste IPs bannies."""
    new_bans = []
    seen_ips: set = set()
    for alert in (sur.get("recent_critical") or []):
        ip  = alert.get("src_ip", "")
        sig = alert.get("signature", "Suricata sév.1")[:80]
        if not ip or ip == "?" or _is_whitelisted(ip) or ip in seen_ips:
            continue
        seen_ips.add(ip)
        if cs_detail.get(ip) or not _ip_try_mark_banned(ip):
            continue
        _save_auto_banned()
        ok, out = _ban_ip_ssh(ip, "jarvis-suricata-sev1-critique", "48h")
        _soc_log("ban_ip", f"{ip} — Suricata sév.1 : {sig} (auto)", ok, out)
        if ok:
            new_bans.append(ip)
    return new_bans


def _sur_ban_scans(sur: dict, cs_detail: dict) -> list:
    """Ban auto sév.3 port scan — retourne liste IPs bannies."""
    scan_bans = []
    for scan in (sur.get("recent_scans") or []):
        ip  = scan.get("src_ip", "")
        cnt = scan.get("count", 0)
        if _ip_skip(ip): continue
        if cs_detail.get(ip) or not _ip_try_mark_banned(ip):
            continue
        _save_auto_banned()
        ok_s, out_s = _ban_ip_ssh(ip, f"jarvis-suricata-portscan-{cnt}hits", "24h")
        _soc_log("ban_ip", f"{ip} — Suricata port scan : {cnt} hits (auto)", ok_s, out_s)
        if ok_s:
            scan_bans.append(ip)
    return scan_bans


def _sur_ban_sev2_surge(sev2: int, sur: dict, cs_detail: dict) -> list:
    """Ban auto sév.2 surge C2 — retourne liste IPs bannies."""
    sev2_banned = []
    top_ips = [e.get("ip", "") for e in (sur.get("top_ips") or [])][:3]
    for ip in top_ips:
        if _ip_skip(ip): continue
        if cs_detail.get(ip) or not _ip_try_mark_banned(ip):
            continue
        _save_auto_banned()
        ok_s2, out_s2 = _ban_ip_ssh(ip, "jarvis-suricata-sev2-surge", "24h")
        _soc_log("ban_ip", f"{ip} — Suricata sév.2 surge : {sev2} alertes 24h (auto)", ok_s2, out_s2)
        if ok_s2:
            sev2_banned.append(ip)
    return sev2_banned


def _soc_suricata_check(data):
    """Surveille les alertes Suricata sév.1 (CRITIQUE) — ban auto des IPs sources.
    Appelé uniquement quand le dashboard est FERMÉ."""
    sur = data.get("suricata", {})
    if not sur.get("available") or sur.get("sev1_critical", 0) < 1:
        return

    cs_detail = data.get("crowdsec", {}).get("decisions_detail", {})
    sev1 = sur.get("sev1_critical", 0)

    # ── sév.1 CRITIQUE ──
    new_bans = _sur_ban_sev1(sur, cs_detail)
    if new_bans:
        ips_tts  = ", ".join(_ip_to_tts(b) for b in new_bans[:2])
        more_tts = f" et {len(new_bans)-2} autres" if len(new_bans) > 2 else ""
        _speak(f"Alerte Suricata CRITIQUE. {len(new_bans)} IP bannie{'s' if len(new_bans)>1 else ''} pour {_dur_to_tts('48h')} : {ips_tts}{more_tts}. Unban automatique. Surveillance IDS active.")
    elif sev1 > 0 and _soc_cooldown_ok("suricata_sev1_noban", minutes=60):
        _speak(f"Suricata : {sev1} alerte{'s' if sev1>1 else ''} critique{'s' if sev1>1 else ''} détectée{'s' if sev1>1 else ''}. IPs déjà sous contrôle.")

    # ── sév.2 HIGH alerte ──
    sev2 = sur.get("sev2_high", 0)
    if sev2 > _SUR_SEV2_SURGE and _soc_cooldown_ok("suricata_sev2_high", minutes=60):
        _soc_log("suricata_alert", f"sév.2 HIGH : {sev2} alertes 24h — surge C2", True)
        _speak(f"Suricata : surge détecté. {sev2} alertes réseau HIGH sur 24 heures. Command and Control possible.")
    elif sev2 > _SUR_SEV2_HIGH and _soc_cooldown_ok("suricata_sev2_high", minutes=60):
        _soc_log("suricata_alert", f"sév.2 HIGH : {sev2} alertes 24h — élevé", True)
        _speak(f"Suricata : activité réseau élevée. {sev2} alertes sévérité 2 en 24 heures.")

    # ── sév.3 port scan ──
    scan_bans = _sur_ban_scans(sur, cs_detail)
    if scan_bans:
        ips_tts  = ", ".join(_ip_to_tts(b) for b in scan_bans[:2])
        more_tts = f" et {len(scan_bans)-2} autres" if len(scan_bans) > 2 else ""
        _speak(f"Suricata scan réseau détecté. {len(scan_bans)} IP bannie{'s' if len(scan_bans)>1 else ''} pour vingt-quatre heures : {ips_tts}{more_tts}. Unban automatique.")

    # ── sév.2 surge ban ──
    if sev2 > _SUR_SEV2_BAN and _soc_cooldown_ok("suricata_sev2_ban", minutes=60):
        sev2_banned = _sur_ban_sev2_surge(sev2, sur, cs_detail)
        if sev2_banned:
            ips_tts = ", ".join(_ip_to_tts(b) for b in sev2_banned[:2])
            _speak(f"Surge réseau Suricata. {len(sev2_banned)} IP bannie{'s' if len(sev2_banned)>1 else ''} pour vingt-quatre heures : {ips_tts}. Trafic suspect niveau HIGH.")


def _soc_ollama_query(prompt: str, max_tokens: int = 400) -> str:
    """Appel Ollama non-streaming depuis le thread background.
    Utilise gemma4:latest — léger, rapide (~5s), suffisant pour 3 phrases d'analyse.
    Bloqué pendant CODE REASONING — évite collision VRAM avec qwen3:8b."""
    try:
        from jarvis import _CODE_REASONING_MODE, _jarvis_mode
        if _jarvis_mode == _CODE_REASONING_MODE:
            _log.info("[SOC-LLM] Bypass — CODE REASONING actif (protection VRAM)")
            return ""
        from jarvis import MODEL as _SOC_MODEL
        from jarvis import (
            OLLAMA_URL as _SOC_OLLAMA_URL,  # source unique : évite duplication du hostname
        )
        payload = json.dumps({
            "model":  _SOC_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "keep_alive": 0,
            "options": {"temperature": 0.3, "num_predict": max_tokens, "num_ctx": 4096},
        }).encode()

        req_http = urllib.request.Request(
            f"{_SOC_OLLAMA_URL}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_http, timeout=90) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "").strip()
    except Exception as e:
        _log.warning(f"[SOC-LLM] Ollama indisponible : {e}")
        return ""


# _gap_prompt_c2 retiré 2026-05-17 — migration ASUS BE98 → Freebox directe.
# (Plus de C2 outbound côté routeur — Suricata ET-TROJAN/CNC remplace.)


def _gap_prompt_recon(gap_ips, cs, xh):
    multi_ctx = [
        f"  - {ip} : vues sur {hosts}"
        for ip, hosts in list(xh.get("multi_apache", {}).items())[:5]
        if ip in gap_ips
    ]
    ip_block = "\n".join(multi_ctx) or "  (aucun détail disponible)"
    return (
        "Tu es l'IA défensive JARVIS. Une analyse rsyslog multi-hôtes vient de détecter "
        f"{len(gap_ips)} IP(s) de reconnaissance multi-cibles NON bloquée(s) par CrowdSec ni fail2ban.\n\n"
        f"IPs et hôtes ciblés :\n{ip_block}\n\n"
        f"Score CrowdSec actif : {cs.get('active_decisions',0)} décisions\n\n"
        "En 3 phrases maximum : (1) pourquoi cette reconnaissance a contourné les défenses, "
        "(2) le pattern d'attaque probable (scan lent, evasion rate-limit), "
        "(3) une recommandation pour améliorer la couverture fail2ban/CrowdSec. "
        "Sois concis, technique, sans préambule."
    )


def _soc_rsyslog_gap_analyze(gap_ips: list, gap_type: str, xh: dict, data: dict) -> None:
    """Thread : analyse LLM du gap défensif détecté.
    Appelé APRÈS le ban immédiat — enrichit le journal et le TTS vocal.
    gap_type=='recon' uniquement depuis 2026-05-17 (C2 routeur retiré, migration ASUS → Freebox)."""
    try:
        cs = data.get("crowdsec", {})
        prompt = _gap_prompt_recon(gap_ips, cs, xh)
        analysis = _soc_ollama_query(prompt, max_tokens=350)
        if not analysis:
            return

        # Résumé TTS : première phrase de l'analyse (jusqu'au premier point)
        first_sent = re.split(r'(?<=[.!?])\s', analysis)[0][:200]
        _speak(f"Analyse JARVIS sur le gap reconnaissance multi-cible : {first_sent}")

        # Journal SOC complet
        _soc_log(
            "rsyslog_analysis",
            f"Gap {gap_type} — {len(gap_ips)} IP(s) : {', '.join(gap_ips[:3])}{'...' if len(gap_ips)>3 else ''} — {analysis[:400]}",
            True,
        )
    except Exception as e:
        _log.error(f"[SOC-LLM-GAP] Erreur analyse : {e}")


def _rsyslog_ban_loop(ips: list, reason: str, duration: str, log_label: str, cs_detail: dict) -> list:
    """Boucle ban rsyslog générique — retourne les IPs effectivement bannies."""
    banned = []
    for ip in ips:
        if _ip_skip(ip): continue
        if cs_detail.get(ip): continue
        if not _ip_try_mark_banned(ip): continue
        _save_auto_banned()
        ok, out = _ban_ip_ssh(ip, reason, duration)
        _soc_log("ban_ip", f"{ip} — {log_label} (auto)", ok, out)
        if ok:
            banned.append(ip)
    return banned


def _soc_rsyslog_check(data: dict) -> None:
    """Surveille les corrélations rsyslog cross-hôtes — ban auto C2 outbound et multi-recon.
    Appelé uniquement quand le dashboard est FERMÉ (même garde que _soc_suricata_check).
    Complémente Suricata/fail2ban sur les flux inter-hôtes que ces outils ne voient pas."""
    global _SOC_AUTO_BANNED
    xh = data.get("xhosts", {})
    if not xh:
        return

    cs_detail = data.get("crowdsec", {}).get("decisions_detail", {})

    # Bloc C2 outbound (router_seen) retiré 2026-05-17 — migration ASUS BE98 → Freebox directe.
    # Détection C2 désormais portée par Suricata ET-TROJAN/CNC/MALWARE signatures.

    # ── Multi-recon : IPs vues sur plusieurs Apache en même temps ──
    recon_ips = list(xh.get("multi_apache", {}).keys())
    recon_banned = []
    if recon_ips and _soc_cooldown_ok("rsyslog_recon", minutes=30):
        recon_banned = _rsyslog_ban_loop(
            recon_ips, "jarvis-rsyslog-recon-multicible", "24h",
            "rsyslog recon multi-cible Apache", cs_detail
        )

        if recon_banned:
            ips_tts = ", ".join(_ip_to_tts(b) for b in recon_banned[:2])
            more_tts = f" et {len(recon_banned)-2} autres" if len(recon_banned) > 2 else ""
            _speak(f"Gap défensif rsyslog. {len(recon_banned)} IP recon multi-cible bannie{'s' if len(recon_banned)>1 else ''} pour vingt-quatre heures : {ips_tts}{more_tts}. Analyse en cours.")
            threading.Thread(
                target=_soc_rsyslog_gap_analyze,
                args=(recon_banned, "recon", xh, data),
                daemon=True, name="soc-gap-recon-analysis"
            ).start()


def _threat_score_from_json(d: dict, gap_banned: set) -> dict:
    """Lit le score de menace pré-calculé par monitoring_gen.py depuis monitoring.json.
    gap_banned : IPs bannies ce cycle → soustraites d'exploit_unblocked pour éviter double TTS."""
    exploit_unblocked = max(
        0, d.get("threat_exploit_unblocked", 0) - len(gap_banned))
    return {
        "score":             d.get("threat_score", 0),
        "threat":            d.get("threat_level"),
        "exploit_unblocked": exploit_unblocked,
        "sur_sev1":          d.get("threat_sur_sev1", 0),
        "cs_bans":           d.get("threat_cs_bans", 0),
        "f2b_sat_bans":      d.get("threat_f2b_sat_bans", 0),
        "err_rate":          d.get("threat_err_rate", 0),
        "c2_count":          d.get("threat_c2_count", 0),
        "multi_count":       d.get("threat_multi_count", 0),
    }


def _check_threat_level(ts: dict) -> list:
    """Génère les parties TTS liées au niveau de menace. Retourne une liste de phrases."""
    parts = []
    threat = ts["threat"]
    if not threat or threat == "FAIBLE":
        return parts
    if not _soc_cooldown_ok(f"threat_{threat}", minutes=30):
        return parts
    detail = []
    if ts["exploit_unblocked"] > 0:
        n = ts["exploit_unblocked"]
        detail.append(f"{n} IP EXPLOIT non bloquée{'s' if n>1 else ''}")
    if ts["sur_sev1"] > 0:
        n = ts["sur_sev1"]
        detail.append(f"Suricata {n} alerte{'s' if n>1 else ''} critique{'s' if n>1 else ''}")
    if ts.get("c2_count", 0) > 0:
        n = ts["c2_count"]
        detail.append(f"{n} IP C2 sortant détectée{'s' if n>1 else ''} au routeur")
    if ts.get("multi_count", 0) > 0:
        detail.append(f"Recon multi-cible {ts['multi_count']} hôtes")
    if ts["cs_bans"] > 0:
        detail.append(f"{ts['cs_bans']} IPs bannies CrowdSec")
    suffix = (", ".join(detail) + ".") if detail else f"{ts['cs_bans']} décisions actives."
    parts.append(f"Niveau {threat}. Score {ts['score']} sur 100. {suffix}")
    return parts


def _check_services(svc: dict) -> list:
    """Détecte les services DOWN, tente un restart auto, retourne les parties TTS."""
    parts = []
    for name, val in svc.items():
        if isinstance(val, bool):
            up = val
        elif isinstance(val, dict):
            st = str(val.get("status", "")).lower()
            up = st in ("up", "ok", "running", "true", "1") or val.get("http_code", 0) in range(200, 400)
        else:
            up = str(val).lower() in ("up", "true", "1", "running", "ok")
        if not up and _soc_cooldown_ok(f"svc_{name}", minutes=15):
            if name in _ALLOWED_SERVICES:
                ok_rst, out_rst = _ssh_ngix(f"systemctl restart {shlex.quote(name)}", timeout=30)
                _soc_log("restart_service", f"{name} — DOWN détecté, restart auto (dashboard fermé)", ok_rst, out_rst)
                if ok_rst:
                    parts.append(f"Service {name} était hors ligne. Redémarrage automatique effectué.")
                else:
                    parts.append(f"Service {name} hors ligne — redémarrage échoué. Intervention requise.")
            else:
                parts.append(f"Service {name} est hors ligne sur srv-ngix.")
    return parts


def _check_errors(traf: dict) -> list:
    """Alerte si taux d'erreurs 5xx > 10 %. Retourne les parties TTS."""
    parts = []
    err_rate = traf.get("error_rate", 0)
    if err_rate > 10 and _soc_cooldown_ok("err_5xx", minutes=10):
        parts.append(f"Taux d'erreurs serveur élevé : {err_rate} pourcent.")
    return parts


def _check_net_spikes(d: dict) -> None:
    """Alerte vocale si un pic bande passante récent (<6 min) est détecté."""
    net_spikes = d.get("net_spikes", [])
    if not net_spikes:
        return
    last_spike = net_spikes[-1]
    age = time.time() - last_spike.get("ts", 0)
    if age < 360 and _soc_cooldown_ok("net_spike", minutes=30):
        tx = last_spike.get("tx_mbps", 0)
        rx = last_spike.get("rx_mbps", 0)
        _soc_log("net_spike", f"Pic bande passante — TX:{tx} Mbps / RX:{rx} Mbps", True, "")
        _speak(f"Alerte réseau. Pic de bande passante réseau détecté. "
               f"Téléchargement {tx} mégabits par seconde, upload {rx} mégabits par seconde. "
               f"Source non identifiée — vérification recommandée.")


_FR_MONTHS = ["", "janvier", "février", "mars", "avril", "mai", "juin",
              "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def _soc_subnet_campaign_check(d: dict) -> None:
    """Alerte vocale si un /24 coordonné atteint ≥5 IPs distinctes sur 14 jours."""
    camps = d.get('slow_campaigns', [])
    for c in camps:
        if c.get('count', 0) < 5:
            continue
        sn  = c.get('subnet', '')
        key = 'campaign_' + sn.replace('/', '_').replace('.', '_')
        if not _soc_cooldown_ok(key, minutes=6 * 60):
            continue
        n      = c['count']
        ctry   = c.get('countries', [])
        suffix = f" Origines : {', '.join(ctry[:3])}." if ctry else ''
        _speak(f"Campagne coordonnée détectée sur le sous-réseau {sn}. "
               f"{n} adresses IP distinctes observées sur 14 jours.{suffix}")
        _log.info(f"[JARVIS-SOC-CAMPAIGN] Alerte vocale — {sn} {n} IPs")


def _check_daily_report(d: dict, ts: dict) -> None:
    """Rapport vocal SOC quotidien — déclenché une seule fois entre 08h00 et 08h09."""
    now = datetime.datetime.now()
    if not (now.hour == 8 and now.minute < 10):
        return
    today = now.strftime("%Y-%m-%d")
    if not _soc_cooldown_ok(f"daily_report_{today}", minutes=23 * 60):
        return
    level  = ts.get("threat", "FAIBLE") or "FAIBLE"
    score  = ts.get("score", 0)
    cs_bans = ts.get("cs_bans", 0)
    traf   = d.get("traffic", {}) if isinstance(d.get("traffic"), dict) else {}
    req_h  = traf.get("req_last_hour", 0)
    fb     = d.get("fail2ban", {})
    fb_total = fb.get("total_banned", 0) if isinstance(fb, dict) else 0
    svc    = d.get("services", {}) if isinstance(d.get("services"), dict) else {}
    svc_down = []
    for sname, val in svc.items():
        if isinstance(val, bool):
            up = val
        elif isinstance(val, dict):
            st = str(val.get("status", "")).lower()
            up = st in ("up", "ok", "running", "true", "1") or val.get("http_code", 0) in range(200, 400)
        else:
            up = str(val).lower() in ("up", "true", "1", "running", "ok")
        if not up:
            svc_down.append(sname)
    date_fr = f"{now.day} {_FR_MONTHS[now.month]} {now.year}"
    msg = (f"Bonjour. Rapport SOC du {date_fr}. "
           f"Niveau de menace actuel : {level}. Score {score} sur 100. "
           f"{cs_bans} décisions CrowdSec actives, {fb_total} IPs bloquées par fail2ban. "
           f"Trafic de la dernière heure : {req_h} requêtes. ")
    if svc_down:
        n = len(svc_down)
        msg += f"Attention : {n} service{'s' if n > 1 else ''} hors ligne : {', '.join(svc_down)}."
    else:
        msg += "Tous les services surveillés sont opérationnels."
    _speak(msg)
    _log.info(f"[JARVIS-SOC-DAILY] Rapport 8h envoyé — {level} score={score}")


def _soc_monitor_loop():
    """Thread background — vérifie le SOC toutes les 60s et alerte vocalement.
    Délègue chaque responsabilité à une sous-fonction dédiée.
    S'arrête proprement si _soc_stop_evt est set() (shutdown JARVIS)."""
    _soc_stop_evt.wait(timeout=30)  # attente initiale au démarrage
    while not _soc_stop_evt.is_set():
        _soc_stop_evt.wait(timeout=_SOC_MON_INTERVAL)
        if _soc_stop_evt.is_set():
            break
        if not _SOC_MON_ENABLED:
            continue
        try:
            from jarvis import _jarvis_mode
            if _jarvis_mode != "soc":
                continue  # SOC actif uniquement en mode SOC
        except Exception:
            pass  # import jarvis non encore prêt au démarrage — on continue
        try:
            ok, raw = _fetch_monitoring()
            if not ok or not raw:
                continue
            d = json.loads(raw)

            # ── Sync bans monitoring_gen.py → cooldown JARVIS (anti-doublon) ──
            try:
                _sync_autoban_log(d)
            except Exception as _sa:
                _log.debug(f"[JARVIS-SOC-SYNC] {_sa}")

            # ── EXPLOIT gap : ban immédiat même si dashboard est ouvert ──
            try:
                gap_banned = _soc_exploit_gap_check(d)
            except Exception as _eg:
                _log.error(f"[JARVIS-SOC-GAP] {_eg}")
                gap_banned = set()

            if _soc_dashboard_open():
                continue  # JS gère les alertes vocales (sauf exploit gap ci-dessus)

            ts = _threat_score_from_json(d, gap_banned)
            alert_parts = (
                _check_threat_level(ts)
                + _check_services(d.get("services", {}))
                + _check_errors(d.get("traffic", {}))
            )
            if alert_parts:
                _speak("Alerte SOC. " + " ".join(alert_parts))

            _soc_autoban(d)
            _soc_reqhour_check(d)
            _soc_suricata_check(d)
            _soc_rsyslog_check(d)
            _check_net_spikes(d)
            _soc_subnet_campaign_check(d)
            _check_daily_report(d, ts)

        except Exception as e:
            _log.error(f"[JARVIS-SOC-MON] Erreur : {e}")
