"""Proxmox API direct — fetch état VE via REST avec cache 30s.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 12.

Couvre :
- Authentification Proxmox VE (token API ou ticket+CSRF)
- Fetch état hyperviseur : node status / VMs QEMU / conteneurs LXC / storage
- Cache module-level avec TTL 30s
- Formatage texte pour injection LLM (system prompt enrichi)
- Détection mots-clés `_CHAT_PVE_KW` pour déclencher l'injection conditionnelle

Le mapping VM → ssh_fn (`_VM_START_SSH_MAP`) reste dans `jarvis.py` (couplé _ssh_*).
Configuration : `jarvis_pve.json` (host, port, node, token_id+token_secret OU user+password).
"""
import json
import logging
import time
from pathlib import Path

import requests

_log = logging.getLogger("jarvis.proxmox_api")

# ── Constantes ────────────────────────────────────────────────
# Module dans scripts/proxmox/ → .parent.parent pour atteindre scripts/.
PVE_CONFIG_PATH = Path(__file__).parent.parent / "jarvis_pve.json"
PVE_CACHE_TTL = 30  # secondes

# Mots-clés déclenchant l'injection PVE dans le system prompt
CHAT_PVE_KW = [
    "proxmox", "pve", "hyperviseur",
    "machine virtuelle", "machines virtuelles",
    "état des vms", "état vm", "liste des vms", "liste vms",
    "vm 106", "vm 107", "vm 108", "vm 109",
    "nœud proxmox", "node proxmox",
    "lxc", "conteneur proxmox", "conteneurs proxmox",
    "stockage proxmox", "sauvegarde proxmox",
    "mémoire ram proxmox", "cpu proxmox", "charge proxmox",
]

# ── State (module-level cache) ────────────────────────────────
_cache: dict = {"ts": 0.0, "data": None}


# ── Helpers internes ──────────────────────────────────────────

def _auth_session(cfg: dict, base: str, host: str):
    """Crée une session HTTP authentifiée pour l'API Proxmox (token ou ticket)."""
    try:
        import urllib3 as _u3
        _u3.disable_warnings(_u3.exceptions.InsecureRequestWarning)
    except Exception:
        pass  # urllib3 optionnel — avertissements SSL toujours visibles
    session = requests.Session()
    session.verify = False
    token_id = cfg.get("token_id", "")
    token_secret = cfg.get("token_secret", "")
    if token_id and token_secret:
        session.headers.update({"Authorization": f"PVEAPIToken={token_id}={token_secret}"})
        return session
    password = cfg.get("password", "")
    if not password:
        _log.warning("[PVE] jarvis_pve.json : ni token ni password — injection désactivée")
        return None
    try:
        r = session.post(
            f"{base}/access/ticket",
            data={"username": cfg.get("user", "root@pam"), "password": password},
            timeout=5,
        )
        r.raise_for_status()
        td = r.json()["data"]
        session.headers.update({"CSRFPreventionToken": td["CSRFPreventionToken"]})
        session.cookies.set("PVEAuthCookie", td["ticket"], domain=host)
    except Exception as e:
        _log.warning(f"[PVE] Auth ticket échouée : {e}")
        return None
    return session


# ── API publique ──────────────────────────────────────────────

def fetch_state() -> dict | None:
    """Récupère l'état Proxmox VE via REST API — cache 30 s.

    Retourne dict `{node, vms, lxc, storage}` ou None si config/auth indisponibles.
    """
    global _cache
    if time.time() - _cache["ts"] < PVE_CACHE_TTL and _cache["data"]:
        return _cache["data"]
    if not PVE_CONFIG_PATH.exists():
        return None
    try:
        cfg = json.loads(PVE_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    host = cfg.get("host", "192.168.1.20")
    port = cfg.get("port", 8006)
    base = f"https://{host}:{port}/api2/json"
    node = cfg.get("node", "proxmox")
    session = _auth_session(cfg, base, host)
    if session is None:
        return None
    state: dict = {}
    try:
        r = session.get(f"{base}/nodes/{node}/status", timeout=5)
        state["node"] = r.json().get("data", {})
    except Exception:
        pass  # données partielles — continue
    try:
        r = session.get(f"{base}/nodes/{node}/qemu", timeout=5)
        state["vms"] = r.json().get("data", [])
    except Exception:
        pass
    try:
        r = session.get(f"{base}/nodes/{node}/lxc", timeout=5)
        state["lxc"] = r.json().get("data", [])
    except Exception:
        pass
    try:
        r = session.get(f"{base}/nodes/{node}/storage", timeout=5)
        state["storage"] = r.json().get("data", [])
    except Exception:
        pass
    if state:
        _cache = {"ts": time.time(), "data": state}
        _log.info(f"[PVE] État rafraîchi — {len(state.get('vms', []))} VMs, {len(state.get('lxc', []))} LXC")
    return state or None


def context_summary(state: dict) -> str:
    """Formate l'état Proxmox en texte lisible pour le LLM."""
    lines = ["=== État Proxmox VE (données en temps réel) ==="]
    node = state.get("node", {})
    if node:
        cpu_pct = round(node.get("cpu", 0) * 100, 1)
        mem = node.get("memory", {})
        mem_used = round(mem.get("used", 0) / 1024 ** 3, 1)
        mem_total = round(mem.get("total", 0) / 1024 ** 3, 1)
        uptime_h = node.get("uptime", 0) // 3600
        lines.append(f"Nœud: CPU {cpu_pct}% | RAM {mem_used}/{mem_total} Go | uptime {uptime_h}h")
    vms = state.get("vms", [])
    if vms:
        lines.append(f"VMs QEMU ({len(vms)}):")
        for vm in sorted(vms, key=lambda x: x.get("vmid", 0)):
            vmid = vm.get("vmid", "?")
            name = vm.get("name", f"vm{vmid}")
            status = vm.get("status", "?")
            cpu = round(vm.get("cpu", 0) * 100, 1)
            maxmem = vm.get("maxmem", 0)
            mem_pct = round(vm.get("mem", 0) / maxmem * 100, 1) if maxmem else 0
            uptime_h = vm.get("uptime", 0) // 3600
            icon = "▶" if status == "running" else "■"
            line = f"  {icon} VM{vmid} {name}: {status}, CPU {cpu}%, RAM {mem_pct}%"
            if status == "running" and uptime_h:
                line += f", uptime {uptime_h}h"
            lines.append(line)
    lxc = state.get("lxc", [])
    if lxc:
        lines.append(f"Conteneurs LXC ({len(lxc)}):")
        for c in sorted(lxc, key=lambda x: x.get("vmid", 0)):
            vmid = c.get("vmid", "?")
            name = c.get("name", f"ct{vmid}")
            status = c.get("status", "?")
            icon = "▶" if status == "running" else "■"
            lines.append(f"  {icon} CT{vmid} {name}: {status}")
    storage = state.get("storage", [])
    if storage:
        lines.append("Stockage:")
        for s in storage:
            if not s.get("active"):
                continue
            store = s.get("storage", "?")
            total = s.get("total", 0)
            used = s.get("used", 0)
            if total > 0:
                pct = round(used / total * 100, 1)
                total_g = round(total / 1024 ** 3, 0)
                used_g = round(used / 1024 ** 3, 1)
                lines.append(f"  {store}: {used_g}/{total_g:.0f} Go ({pct}%)")
    return "\n".join(lines)


def chat_inject(system: str, last_user: str) -> str:
    """Enrichit le prompt système avec l'état Proxmox si la question l'exige.

    Détecte les mots-clés `CHAT_PVE_KW` dans la question utilisateur. Si match,
    fetch l'état (via cache) et l'injecte en français dans le system prompt.
    Sinon retourne `system` inchangé.
    """
    if not any(kw in last_user.lower() for kw in CHAT_PVE_KW):
        return system
    state = fetch_state()
    if not state:
        return system
    system += (
        "\n\nVoici l'état actuel de l'hyperviseur Proxmox VE récupéré en temps réel via l'API :\n"
        + context_summary(state)
        + "\n\nUtilise ces données pour répondre précisément à la question."
    )
    return system
