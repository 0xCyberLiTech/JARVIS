"""Bypass Proxmox — détection commandes VM / reboot / update (zéro LLM).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 8.

Permet à JARVIS de détecter "redémarre srv-ngix", "stop VM 108", "mise à jour pa85"
sans appeler le LLM. Les générateurs SSE (`_vm_command_sse`, `_reboot_machine_sse`,
`_update_machine_sse`, `_service_restart_sse`) restent dans `jarvis.py` car
couplés à paramiko/SSH/Proxmox API.

Dependency injection :
- `detect_vm_command()` : reçoit `vms_api` (résultat de `_pve_fetch_state()`)
- `detect_reboot_command()` / `detect_update_command()` : reçoivent `host_map`
  (liste de tuples `(aliases, label, ssh_fn, is_proxmox)`)

Sécurité : les blacklists VM (opnsense=100) sont dans ce module — modification
nécessite revue.
"""
import re

# ── Constantes ────────────────────────────────────────────────

# VMs à NE JAMAIS auto-arrêter (firewall réseau · etc.)
PVE_STOP_BLACKLIST = {100}  # opnsense

# Alias utilisateur → nom Proxmox exact
VM_ALIASES: dict[str, str] = {
    "srv-nginx": "srv-ngix",
}

# Services à vérifier après reboot par hôte (utilisé par _post_start_verify_sse)
REBOOT_SVC_CHECKS: dict[str, list[str]] = {
    "srv-ngix":  ["nginx", "crowdsec", "fail2ban"],
    "srv-clt":   ["apache2"],
    "srv-pa85":  ["apache2"],
    "proxmox":   ["pve-cluster", "pveproxy", "pvedaemon"],
    "srv-dev-1": ["ssh"],
}


# ── Regex publiques ───────────────────────────────────────────

# Mise à jour machine (apt update + upgrade)
UPDATE_ACTION_RE = re.compile(
    r'\b(met[sz]?\s+[àa]\s+jour|mise\s+[àa]\s+jour|update|upgrader?|maj)\b',
    re.I,
)

# Reboot immédiat / différé (utilisé par bypass reboot après upgrade)
REBOOT_NOW_RE = re.compile(
    r'\b(reboot(\s+maintenant)?|red[eé]marre(\s+maintenant)?)\b',
    re.I,
)
REBOOT_DEFER_RE = re.compile(
    r'\b(report[ez]?[rz]?|plus\s+tard|defer|pas\s+maintenant)\b',
    re.I,
)

# Verbes d'action VM (le nom VM est résolu dynamiquement via vms_api)
VM_STOP_ACTION_RE = re.compile(
    r'\b(arr[eêé]te[rz]?[sz]?|stop|[eé]teins?|shutdown|coupe[rz]?[sz]?)\b',
    re.I,
)
VM_START_ACTION_RE = re.compile(
    r'\b(d[eé]marre[rz]?[sz]?|start|allume[rz]?[sz]?|lance[rz]?[sz]?)\b',
    re.I,
)

# Pattern "toutes les VMs" → mode dynamique complet
VM_ALL_STOP_RE = re.compile(
    r'\b(arr[eêé]te[rz]?[sz]?|stop|[eé]teins?|shutdown|coupe[rz]?[sz]?)\b.{0,60}'
    r'\b(vms?|machines?\s+virtuelles?|serveurs?|toutes?)\b',
    re.I,
)
VM_ALL_START_RE = re.compile(
    r'\b(d[eé]marre[rz]?[sz]?|start|allume[rz]?[sz]?|lance[rz]?[sz]?|red[eé]marre[rz]?[sz]?|reboot)\b.{0,60}'
    r'\b(vms?|machines?\s+virtuelles?|serveurs?|toutes?)\b',
    re.I,
)

# Mots qui INVALIDENT une détection VM (faux positifs : sauvegarde, restart service, etc.)
VM_EXCLUDE_RE = re.compile(
    r'\b(sauvegarde[rz]?\b|backup\b|disk[- ]?report\b|rapport\b|'
    r'restart\b|systemctl\b|red[eé]marre[rz]?[sz]?\b|reboot\b|'
    r'relance[rz]?[sz]?\b|apache[2]?\b|crowdsec\b|fail2ban\b|php\b)',
    re.I,
)

# Reboot machine (pas service, pas VM via qm)
REBOOT_MACHINE_RE = re.compile(r'\b(reboot|red[eé]marre[rz]?[sz]?)\b', re.I)


def make_svc_restart_re(svc_bouncer: str) -> re.Pattern:
    """Construit la regex restart service avec le nom du bouncer en arg.
    Le bouncer (`crowdsec-firewall-bouncer`) est défini dans jarvis.py."""
    return re.compile(
        r'\b(red[eé]marr(?:e[rz]?[sz]?|age[sz]?)|relance[rz]?[sz]?|restart)\b.{0,60}'
        r'\b(nginx|apache[2]?|crowdsec|fail2ban|php|suricata|' + re.escape(svc_bouncer) + r')\b',
        re.I,
    )


# ── Détecteurs ────────────────────────────────────────────────

def detect_vm_command(text: str, vms_api: list, alias_map: dict | None = None, blacklist: set | None = None):
    """Retourne ('stop'|'start', [(vmid, vmname), ...] | 'dynamic') si commande VM détectée.
    Lookup 100% dynamique via API Proxmox (`vms_api` passé en arg) — aucune liste hardcodée.

    `vms_api` : résultat de `_pve_fetch_state()['vms']` côté jarvis.py.
    `alias_map` : dict alias → real (défaut VM_ALIASES).
    `blacklist` : set de VMIDs à ignorer (défaut PVE_STOP_BLACKLIST).
    """
    if alias_map is None:
        alias_map = VM_ALIASES
    if blacklist is None:
        blacklist = PVE_STOP_BLACKLIST

    if VM_EXCLUDE_RE.search(text):
        return None
    text_l = text.lower()
    is_stop = bool(VM_STOP_ACTION_RE.search(text))
    is_start = bool(VM_START_ACTION_RE.search(text))
    if not is_stop and not is_start:
        return None
    action = "stop" if is_stop else "start"
    has_all = bool(VM_ALL_STOP_RE.search(text) if is_stop else VM_ALL_START_RE.search(text))

    # Résolution des alias dans le texte utilisateur
    text_l_resolved = text_l
    for alias, real in alias_map.items():
        text_l_resolved = text_l_resolved.replace(alias, real)

    seen: set = set()
    vm_list: list = []
    for vm in vms_api:
        vmid = vm.get("vmid")
        name = (vm.get("name") or "").lower()
        if vmid in blacklist:
            continue
        if name and re.search(r'\b' + re.escape(name) + r'\b', text_l_resolved) and vmid not in seen:
            seen.add(vmid)
            vm_list.append((vmid, vm.get("name", f"vm{vmid}")))
        elif re.search(r'\b' + str(vmid) + r'\b', text_l_resolved) and vmid not in seen:
            seen.add(vmid)
            vm_list.append((vmid, vm.get("name", f"vm{vmid}")))
    if vm_list:
        return action, vm_list
    if has_all:
        return action, "dynamic"
    return None


def detect_reboot_command(text: str, host_map: list):
    """Retourne (host_label, ssh_fn, is_proxmox) si reboot direct d'une machine, sinon None.

    `host_map` : liste de tuples `(aliases, label, ssh_fn, is_proxmox)` — passé par jarvis.py.
    """
    if not REBOOT_MACHINE_RE.search(text):
        return None
    text_l = text.lower()
    for aliases, label, fn, is_pve in host_map:
        for alias in aliases:
            if re.search(r'\b' + re.escape(alias) + r'\b', text_l):
                return label, fn, is_pve
    return None


def detect_update_command(text: str, host_map: list):
    """Retourne (host_label, ssh_fn, is_proxmox) si commande mise à jour détectée, sinon None.

    `host_map` : liste de tuples `(aliases, label, ssh_fn, is_proxmox)` — passé par jarvis.py.
    """
    if not UPDATE_ACTION_RE.search(text):
        return None
    text_l = text.lower()
    for aliases, label, fn, is_pve in host_map:
        for alias in aliases:
            if re.search(r'\b' + re.escape(alias) + r'\b', text_l):
                return label, fn, is_pve
    return None
