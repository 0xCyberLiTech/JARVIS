"""Ban automatique sur alertes Suricata — sévérité 1 (critique), port scans
(sév.3) et surge C2 (sév.2).

Extrait de blueprints/soc.py le 2026-05-22 (refactor incrémental, étape 2).
Les 3 fonctions sont tissées au noyau ban/whitelist de soc.py : leurs 6
dépendances sont injectées par `init()` (pattern DI). Consommé par
`_soc_suricata_check` (soc.py), qui appelle les `_sur_ban_*` via des alias.
"""

# Dépendances injectées par init() — fonctions du cœur ban/whitelist de soc.py.
_is_whitelisted     = None
_ip_skip            = None
_ip_try_mark_banned = None
_save_auto_banned   = None
_ban_ip_ssh         = None
_soc_log            = None


def init(is_whitelisted, ip_skip, ip_try_mark_banned,
         save_auto_banned, ban_ip_ssh, soc_log) -> None:
    """Injecte les 6 fonctions du cœur ban/whitelist de soc.py."""
    global _is_whitelisted, _ip_skip, _ip_try_mark_banned
    global _save_auto_banned, _ban_ip_ssh, _soc_log
    _is_whitelisted     = is_whitelisted
    _ip_skip            = ip_skip
    _ip_try_mark_banned = ip_try_mark_banned
    _save_auto_banned   = save_auto_banned
    _ban_ip_ssh         = ban_ip_ssh
    _soc_log            = soc_log


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
