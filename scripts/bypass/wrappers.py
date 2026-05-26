"""Wrappers de bypass — délégation vers sous-modules avec DI couplée jarvis.

Extrait de jarvis.py étape 27 (2026-05-23) — 11 wrappers + 3 constantes
couplées aux fonctions SSH locales. Ces wrappers existent parce que les
modules bypass purs (proxmox/code/backup) ne connaissent ni les fonctions
SSH (`_ssh_nginx`, ...), ni `_pve_fetch_state`, ni le `_pending_infra_cmd`
global. Les wrappers servent de glue : ils injectent les deps puis délèguent.

Architecture :
- `init(...)`           : DI complet (5 SSH fns + 3 modules bypass + 4 callables/dicts)
- 3 détecteurs Proxmox  : `detect_service_restart`, `detect_vm_command`,
                          `detect_reboot_command`, `detect_update_command`
- 2 wrappers code       : `detect_code_command`, `code_scp_exec_sse`
- 4 wrappers backup     : `detect_backup_command`, `backup_sse`,
                          `jarvis_backup_log_sse`, `jarvis_backup_sse`
- 1 SSE apt upgrade     : `apt_upgrade_bypass_sse` (logique réelle, pas wrapper)

Constantes calculées dans `init()` car couplées aux fns SSH :
- `_VM_START_SSH_MAP`   : {vmid: (host_label, ssh_fn)} pour post-start verify
- `_UPDATE_REBOOT_HOSTS`: liste tuples (aliases, label, ssh_fn, is_proxmox)
- `_SVC_RESTART_RE`     : regex construite via `proxmox.make_svc_restart_re(bouncer)`
"""
import json
import re

# ── Module-level DI placeholders (rempli par init()) ──────────────────────────
_ssh_nginx = None
_ssh_proxmox = None
_ssh_clt = None
_ssh_pa85 = None
_ssh_dev1 = None
_bypass_pve = None
_bypass_code = None
_bypass_bk = None
_pve_fetch_state = None
_sse_tok = None
_log = None
_pending_infra_cmd: dict = {}
_allowed_scripts: dict = {}
_ssh_apt_timeout_s = 180
_svc_bouncer = "crowdsec-firewall-bouncer"

# ── Tables/regex calculées dans init() ────────────────────────────────────────
VM_START_SSH_MAP: dict[int, tuple] = {}
UPDATE_REBOOT_HOSTS: list = []
SVC_RESTART_RE = None


def init(
    *,
    ssh_nginx,
    ssh_proxmox,
    ssh_clt,
    ssh_pa85,
    ssh_dev1,
    bypass_pve,
    bypass_code,
    bypass_bk,
    pve_fetch_state,
    sse_tok,
    log,
    pending_infra_cmd: dict,
    allowed_scripts: dict,
    ssh_apt_timeout_s: int = 180,
    svc_bouncer: str = "crowdsec-firewall-bouncer",
) -> None:
    """Injecte les deps couplées à jarvis.py et calcule les tables/regex."""
    global _ssh_nginx, _ssh_proxmox, _ssh_clt, _ssh_pa85, _ssh_dev1
    global _bypass_pve, _bypass_code, _bypass_bk
    global _pve_fetch_state, _sse_tok, _log
    global _pending_infra_cmd, _allowed_scripts, _ssh_apt_timeout_s, _svc_bouncer
    global VM_START_SSH_MAP, UPDATE_REBOOT_HOSTS, SVC_RESTART_RE

    _ssh_nginx = ssh_nginx
    _ssh_proxmox = ssh_proxmox
    _ssh_clt = ssh_clt
    _ssh_pa85 = ssh_pa85
    _ssh_dev1 = ssh_dev1
    _bypass_pve = bypass_pve
    _bypass_code = bypass_code
    _bypass_bk = bypass_bk
    _pve_fetch_state = pve_fetch_state
    _sse_tok = sse_tok
    _log = log
    _pending_infra_cmd = pending_infra_cmd
    _allowed_scripts = allowed_scripts
    _ssh_apt_timeout_s = ssh_apt_timeout_s
    _svc_bouncer = svc_bouncer

    VM_START_SSH_MAP = {
        101: ("srv-dev-1", _ssh_dev1),
        106: ("srv-clt",   _ssh_clt),
        107: ("srv-pa85",  _ssh_pa85),
        108: ("srv-nginx",  _ssh_nginx),
    }
    UPDATE_REBOOT_HOSTS = [
        (["srv-nginx", "srv-ngix"],          "srv-nginx",  _ssh_nginx,    False),
        (["srv-clt",  "clt"],                "srv-clt",   _ssh_clt,     False),
        (["srv-pa85", "pa85"],               "srv-pa85",  _ssh_pa85,    False),
        (["srv-dev-1", "srv-dev", "dev-1"],  "srv-dev-1", _ssh_dev1,    False),
        (["proxmox",  "pve", "hyperviseur"], "proxmox",   _ssh_proxmox, True),
    ]
    SVC_RESTART_RE = _bypass_pve.make_svc_restart_re(_svc_bouncer)


# ── Détecteurs Proxmox ────────────────────────────────────────────────────────

def detect_service_restart(text):
    """Retourne (host_label, ssh_func, svc_name) si restart service détecté."""
    m = SVC_RESTART_RE.search(text)
    if not m:
        return None
    svc_raw = m.group(2).lower()
    if svc_raw == "nginx":
        return ("srv-nginx", _ssh_nginx, "nginx")
    if svc_raw == "crowdsec":
        return ("srv-nginx", _ssh_nginx, "crowdsec")
    if svc_raw == _svc_bouncer:
        return ("srv-nginx", _ssh_nginx, _svc_bouncer)
    if svc_raw == "suricata":
        return ("srv-nginx", _ssh_nginx, "suricata")
    if svc_raw == "fail2ban":
        return ("srv-nginx", _ssh_nginx, "fail2ban")
    svc_name = "php" if svc_raw == "php" else "apache2"
    if re.search(r'\bclt\b', text, re.I):
        return ("clt", _ssh_clt, svc_name)
    if re.search(r'\bpa85\b', text, re.I):
        return ("pa85", _ssh_pa85, svc_name)
    return ("ambiguous", None, svc_name)


def detect_vm_command(text):
    """Wrapper — injecte vms_api depuis pve_fetch_state() puis délègue."""
    state = _pve_fetch_state()
    vms_api = state.get("vms", []) if state else []
    return _bypass_pve.detect_vm_command(text, vms_api)


def detect_reboot_command(text: str):
    """Wrapper — injecte UPDATE_REBOOT_HOSTS puis délègue."""
    return _bypass_pve.detect_reboot_command(text, UPDATE_REBOOT_HOSTS)


def detect_update_command(text: str):
    """Wrapper — injecte UPDATE_REBOOT_HOSTS puis délègue."""
    return _bypass_pve.detect_update_command(text, UPDATE_REBOOT_HOSTS)


# ── Wrappers code ─────────────────────────────────────────────────────────────

def detect_code_command(text: str):
    """Wrapper — délègue à bypass_code."""
    return _bypass_code.detect_code_command(text)


def code_scp_exec_sse(filename: str, exec_it: bool):
    """Wrapper — injecte ssh_dev1 puis délègue à bypass_code."""
    yield from _bypass_code.code_scp_exec_sse(filename, exec_it, _ssh_dev1)


# ── Wrappers backup ───────────────────────────────────────────────────────────

def detect_backup_command(text: str):
    """Wrapper — délègue à bypass_bk."""
    return _bypass_bk.detect_backup_command(text)


def backup_sse(script_key: str):
    """Wrapper — résout script_path depuis allowed_scripts puis délègue."""
    script_path = _allowed_scripts.get(script_key, "")
    yield from _bypass_bk.backup_sse(script_path, script_key)


def jarvis_backup_log_sse():
    """Wrapper — délègue (lit Desktop\\jarvis-backup.log)."""
    yield from _bypass_bk.jarvis_backup_log_sse()


def jarvis_backup_sse():
    """Wrapper — résout script_path puis délègue."""
    script_path = _allowed_scripts.get("backup-jarvis", "")
    yield from _bypass_bk.jarvis_backup_sse(script_path)


# ── Apt upgrade SSE (logique réelle, pas wrapper) ─────────────────────────────

def apt_upgrade_bypass_sse(pending: dict):
    """Exécute l'apt upgrade en attente via SSH direct — zéro LLM."""
    host    = pending["host"]
    ssh_fn  = pending["ssh_fn"]
    pkgs    = pending["packages"]
    _pending_infra_cmd.clear()
    pkg_str = " ".join(pkgs)
    cmd     = f"DEBIAN_FRONTEND=noninteractive apt-get upgrade -y {pkg_str}"
    yield _sse_tok(f"Mise à jour de {len(pkgs)} paquet(s) sur **{host}** :\n")
    for p in pkgs:
        yield _sse_tok(f"  → {p}\n")
    yield _sse_tok("\n")
    _log.info(f"[BYPASS_APT] {host} → {cmd}")
    ok, output = ssh_fn(cmd, timeout=_ssh_apt_timeout_s)
    if ok:
        updated = sum(1 for ln in output.splitlines() if "Paramétrage de" in ln or "Setting up" in ln)
        yield _sse_tok(f"✓ {updated} paquet(s) mis à jour sur **{host}**.")
        tts_msg = f"Mise à jour Apache réussie sur {host}, {updated} paquets installés."
    else:
        yield _sse_tok(f"✗ Erreur sur **{host}** :\n{output[:400]}")
        tts_msg = f"Erreur lors de la mise à jour sur {host}."
    yield _sse_tok("", done=True)
    yield "data: " + json.dumps({"type": "speak", "text": tts_msg}) + "\n\n"
