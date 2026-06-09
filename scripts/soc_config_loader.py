"""Loader source unique soc_config.json.

Partagé par blueprints/soc.py, ssh_terminal.py, bypass/code.py.
Source de vérité unique des adresses et clés SSH de l'infrastructure.
soc_config.json surcharge les DEFAULTS à chaud — modifier le JSON suffit,
aucun redémarrage nécessaire si le module recharge via load().
"""
import json
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
CONFIG_PATH = _SCRIPTS_DIR / "soc_config.json"

DEFAULTS: dict = {
    "nginx_host":       "192.168.1.50",
    "nginx_ssh_port":   "2272",
    "nginx_ssh_user":   "root",
    "nginx_ssh_key":    str(Path.home() / ".ssh" / "id_nginx"),
    "monitoring_url":   "http://192.168.1.50:8080/monitoring.json",
    "proxmox_host":     "192.168.1.20",
    "proxmox_ssh_port": "2272",
    "proxmox_ssh_user": "root",
    "proxmox_ssh_key":  str(Path.home() / ".ssh" / "id_proxmox"),
    "clt_host":         "192.168.1.12",
    "clt_ssh_port":     "2272",
    "clt_ssh_user":     "root",
    "clt_ssh_key":      str(Path.home() / ".ssh" / "id_clt"),
    "pa85_host":        "192.168.1.13",
    "pa85_ssh_port":    "2272",
    "pa85_ssh_user":    "root",
    "pa85_ssh_key":     str(Path.home() / ".ssh" / "id_pa85"),
    "dev1_host":        "192.168.1.21",
    "dev1_ssh_port":    "2272",
    "dev1_ssh_user":    "root",
    "dev1_ssh_key":     str(Path.home() / ".ssh" / "id_dev"),
}


def load() -> dict:
    """Charge soc_config.json avec fallback sur DEFAULTS.

    Retourne une copie du dict — les appelants ne partagent pas de référence.
    Les clés absentes de DEFAULTS sont ignorées (validation implicite).
    """
    cfg = dict(DEFAULTS)
    try:
        if CONFIG_PATH.exists():
            overrides = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            cfg.update({k: v for k, v in overrides.items() if k in cfg})
    except Exception:
        pass
    return cfg
