"""jarvis_trusted_ips — GÉNÉRÉ par SOC/scripts/sync_jarvis_whitelist.py. NE PAS ÉDITER.

Source unique : SOC/scripts/soc_infra.yaml. Pour ajouter/retirer une IP de confiance,
éditer soc_infra.yaml puis régénérer (python sync_jarvis_whitelist.py) + committer.
Consommé par security_whitelists.py (INTERNAL_IPS, PROTECTED_EXTERNAL_IPS, INTERNAL_CIDRS).
"""

INTERNAL_IPS = {
    "127.0.0.1": "loopback",
    "192.168.1.12": "clt",
    "192.168.1.13": "pa85",
    "192.168.1.20": "proxmox",
    "192.168.1.21": "srv-dev-1",
    "192.168.1.50": "srv-nginx",
    "192.168.1.110": "routeur-asus",
    "192.168.1.254": "freebox-lan",
    "192.168.50.1": "routeur-asus-rog-be19000-ai",
    "192.168.50.90": "windows-jarvis",
}

PROTECTED_EXTERNAL_IPS = {
    "1.0.0.1": "cloudflare-dns-2",
    "1.1.1.1": "cloudflare-dns-1",
    "8.8.4.4": "google-dns-2",
    "8.8.8.8": "google-dns-1",
    "82.65.147.2": "freebox-wan-public",
    "160.92.124.65": "laposte-smtp-smarthost",
    "212.27.40.240": "free-dns-1",
    "212.27.40.241": "free-dns-2",
}

INTERNAL_CIDRS = [
    "10.0.0.0/8",
    "127.0.0.0/8",
    "172.16.0.0/12",
    "192.168.1.0/24",
    "192.168.50.0/24",
]
