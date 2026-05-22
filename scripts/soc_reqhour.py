"""Détection des pics de trafic (req/h) + ban automatique — cluster SOC.

Extrait de blueprints/soc.py le 2026-05-22 (refactor incrémental, étape 4).

Équivalent Python de `checkReqPerHour()` côté JS : quand le dashboard SOC est
fermé, `_soc_monitor_loop` appelle `_soc_reqhour_check` pour repérer un pic
> `_req_hour_seuil` requêtes/heure et bannir automatiquement les 3 IPs les plus
offensives de la Kill Chain (+ IPs Suricata critiques).

- `_reqhour_candidates`     : filtre les IPs actives éligibles au ban.
- `_reqhour_inject_suricata`: ajoute les IPs Suricata critiques aux candidats.
- `_soc_reqhour_check`      : orchestrateur — seuil, cooldown, tri, ban, TTS.

Dépendances injectées par `init()` — fonctions et constantes de soc.py. Ce
cluster est plus couplé au cœur ban que les étapes 1-3 : `_speak` et le dict
`_SOC_AUTO_BANNED` sont réassignés *après* le chargement du module, donc
soc.py les injecte via des lambdas résolues à l'appel (`speak`, `auto_banned_ts`).
soc.py conserve des alias légers → la route force-autoban et `_soc_monitor_loop`
restent inchangés.
"""

import time

# Dépendances injectées par init() — depuis soc.py.
_is_whitelisted     = None
_auto_banned_ts     = None   # ip -> timestamp du dernier ban auto (0 si jamais)
_soc_cooldown_ok    = None
_ip_try_mark_banned = None
_save_auto_banned   = None
_ban_ip_ssh         = None
_soc_log            = None
_speak              = None
_stage_priority     = None   # dict stage -> priorité de tri (0 = plus prioritaire)
_cooldown_ip        = 0      # cooldown ban par IP, en secondes
_req_hour_seuil     = 0      # seuil req/h déclenchant l'alerte
_autoban_min_hits   = 0      # hits KC minimum pour qu'une IP soit candidate


def init(*, is_whitelisted, auto_banned_ts, soc_cooldown_ok, ip_try_mark_banned,
         save_auto_banned, ban_ip_ssh, soc_log, speak, stage_priority,
         cooldown_ip, req_hour_seuil, autoban_min_hits) -> None:
    """Injecte les dépendances ban/whitelist/TTS + constantes de soc.py."""
    global _is_whitelisted, _auto_banned_ts, _soc_cooldown_ok, _ip_try_mark_banned
    global _save_auto_banned, _ban_ip_ssh, _soc_log, _speak, _stage_priority
    global _cooldown_ip, _req_hour_seuil, _autoban_min_hits
    _is_whitelisted     = is_whitelisted
    _auto_banned_ts     = auto_banned_ts
    _soc_cooldown_ok    = soc_cooldown_ok
    _ip_try_mark_banned = ip_try_mark_banned
    _save_auto_banned   = save_auto_banned
    _ban_ip_ssh         = ban_ip_ssh
    _soc_log            = soc_log
    _speak              = speak
    _stage_priority     = stage_priority
    _cooldown_ip        = cooldown_ip
    _req_hour_seuil     = req_hour_seuil
    _autoban_min_hits   = autoban_min_hits


def _reqhour_candidates(active_ips, geo_map, cs_detail, now, min_hits):
    """Filtre les IPs actives éligibles au ban (non whitelist, non déjà bannies, hits >= seuil)."""
    return [
        ip_obj for ip_obj in active_ips
        if (ip_obj.get("ip") and
            not _is_whitelisted(ip_obj["ip"]) and
            not geo_map.get(ip_obj["ip"], {}).get("cs_banned") and
            not cs_detail.get(ip_obj["ip"]) and
            now - _auto_banned_ts(ip_obj["ip"]) >= _cooldown_ip and
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
                or now - _auto_banned_ts(ip) < _cooldown_ip
                or ip in existing):
            continue
        candidates.append({"ip": ip, "stage": "EXPLOIT", "country": "-",
                            "count": 1, "sur_alert": True})
        existing.add(ip)


def _soc_reqhour_check(data):
    """Equivalent Python de checkReqPerHour() JS — alerte + ban auto si pic >500 req/h.
    Appelé uniquement quand le dashboard est FERMÉ."""
    now    = time.time()
    rph    = data.get("traffic", {}).get("requests_per_hour", {})
    h_key  = time.strftime("%H")
    cur_val = 0
    for k, v in rph.items():
        if k == h_key or k[-2:] == h_key:
            cur_val = max(cur_val, v or 0)
    if cur_val < _req_hour_seuil:
        return
    if not _soc_cooldown_ok("reqhour_spike", minutes=20):
        return

    kc         = data.get("kill_chain", {})
    active_ips = kc.get("active_ips", [])
    geo_map    = {g["ip"]: g for g in (data.get("traffic", {}).get("recent_geoips", [])) if g.get("ip")}
    cs_detail  = data.get("crowdsec", {}).get("decisions_detail", {})
    min_hits   = _autoban_min_hits

    candidates = _reqhour_candidates(active_ips, geo_map, cs_detail, now, min_hits)
    _reqhour_inject_suricata(candidates, data.get("suricata", {}), cs_detail, now)
    candidates.sort(key=lambda x: (_stage_priority.get(x.get("stage", "RECON"), 9), -(x.get("count") or 0)))
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
