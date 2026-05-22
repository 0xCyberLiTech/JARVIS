"""Scoring de menace SOC + alertes vocales niveau / escalation Kill Chain.

Extrait de blueprints/soc.py le 2026-05-22 (refactor incrémental, étape 3).

- `_threat_score_from_json` : lit le score pré-calculé de monitoring.json et
  enrichit avec un récap Kill Chain (fonction pure, aucune dépendance).
- `_check_threat_level` / `_check_escalation` : génèrent les phrases TTS du
  niveau de menace et des IPs en escalation.

Dépendances injectées par `init()` : `_soc_cooldown_ok` et `_ip_to_tts` (soc.py).
Consommé par la route `/api/soc/threat-score` et `_soc_monitor_loop` (soc.py),
via des alias légers conservés dans soc.py.
"""

# Dépendances injectées par init() — fonctions de soc.py.
_soc_cooldown_ok = None
_ip_to_tts       = None


def init(soc_cooldown_ok, ip_to_tts) -> None:
    """Injecte les dépendances cooldown + TTS de soc.py."""
    global _soc_cooldown_ok, _ip_to_tts
    _soc_cooldown_ok = soc_cooldown_ok
    _ip_to_tts       = ip_to_tts


def _threat_score_from_json(d: dict, gap_banned: set) -> dict:
    """Lit le score de menace pré-calculé par monitoring_gen.py depuis monitoring.json.
    gap_banned : IPs bannies ce cycle → soustraites d'exploit_unblocked pour éviter double TTS.

    Enrichit avec un récap des IPs Kill Chain actives (compte total + détail par stage
    + top 3 pays) pour permettre à _check_threat_level d'annoncer vocalement la KC,
    même quand exploit_unblocked=0 (cas IPs en RECON/SCAN seulement).

    KC v4 enrichissement (2026-05-18) : ajoute aussi max_score, top_asn, escalated_ips
    depuis les nouvelles données backend (sprints 1+2+6 SOC).
    """
    exploit_unblocked = max(
        0, d.get("threat_exploit_unblocked", 0) - len(gap_banned))
    # Récap Kill Chain par stage (2026-05-17 : annonce vocale KC active enrichie)
    kc_active = (d.get("kill_chain") or {}).get("active_ips") or []
    kc_stages: dict = {}
    kc_countries: list = []
    asn_counts: dict = {}
    max_score = 0
    max_score_ip = ""
    escalated_ips: list = []
    for ip_obj in kc_active:
        stage = ip_obj.get("stage") or "?"
        kc_stages[stage] = kc_stages.get(stage, 0) + 1
        c = ip_obj.get("country")
        if c and c not in ("-", "?", "") and c not in kc_countries:
            kc_countries.append(c)
        # Sprint 7 KC v4 : extraction max_score + escalated + ASN
        sc = ip_obj.get("score") or 0
        if sc > max_score:
            max_score = sc
            max_score_ip = ip_obj.get("ip", "")
        if ip_obj.get("escalated"):
            escalated_ips.append({
                "ip":      ip_obj.get("ip", ""),
                "country": ip_obj.get("country", "-"),
                "stage":   ip_obj.get("stage", ""),
            })
        asn_name = (ip_obj.get("asn_name") or "").strip()
        if asn_name:
            asn_counts[asn_name] = asn_counts.get(asn_name, 0) + 1
    top_asn = sorted(asn_counts.items(), key=lambda x: -x[1])[:2]
    return {
        "score":             d.get("threat_score", 0),
        "threat":            d.get("threat_level"),
        "exploit_unblocked": exploit_unblocked,
        "sur_sev1":          d.get("threat_sur_sev1", 0),
        "cs_bans":           d.get("threat_cs_bans", 0),
        "f2b_sat_bans":      d.get("threat_f2b_sat_bans", 0),
        "err_rate":          d.get("threat_err_rate", 0),
        "multi_count":       d.get("threat_multi_count", 0),
        "kc_active_count":   len(kc_active),
        "kc_stages":         kc_stages,
        "kc_countries":      kc_countries[:3],
        # KC v4 enrichissement (sprints 1+2+6 SOC)
        "max_score":         max_score,
        "max_score_ip":      max_score_ip,
        "escalated_ips":     escalated_ips,
        "top_asn":           top_asn,
    }


def _check_threat_level(ts: dict) -> list:
    """Génère les parties TTS liées au niveau de menace. Retourne une liste de phrases.

    KC v4 (2026-05-18) : aligné sur 5 maillons offensifs purs (WAF/PROBE retirés
    car couches défensives séparées). Enrichi avec score IP max, ASN top, et
    annonce escalation séparée (cooldown court).
    """
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
    if ts.get("multi_count", 0) > 0:
        detail.append(f"Recon multi-cible {ts['multi_count']} hôtes")
    # Récap KC active — KC v4 : seuls les 4 stages offensifs présents dans active_ips.
    # WAF/PROBE retirés (couches défensives visualisées séparément dans defense_aggregator).
    kc_count = ts.get("kc_active_count", 0)
    if kc_count > 0:
        stages = ts.get("kc_stages") or {}
        order = ["EXPLOIT", "BRUTE", "SCAN", "RECON"]   # KC v4 — 4 offensifs
        stage_parts = [f"{stages[s]} {s}" for s in order if stages.get(s)]
        # Stages non standards (BLOCKED si IP arrivée directement, etc.) ajoutés en fin
        for s, n in stages.items():
            if s not in order and n > 0:
                stage_parts.append(f"{n} {s}")
        stages_tts = " " + ", ".join(stage_parts).lower() if stage_parts else ""
        countries = ts.get("kc_countries") or []
        countries_tts = f" ({', '.join(countries)})" if countries else ""
        detail.append(
            f"{kc_count} IP{'s' if kc_count>1 else ''} en kill chain"
            f"{stages_tts}{countries_tts}"
        )
    # KC v4 Sprint 7 : score IP max + ASN top (enrichit l'annonce sans noyer)
    max_score = ts.get("max_score", 0)
    if max_score >= 60:
        max_ip = ts.get("max_score_ip", "")
        ip_tts = _ip_to_tts(max_ip) if max_ip else ""
        sev_lbl = "critique" if max_score >= 80 else "élevé"
        detail.append(f"IP la plus dangereuse {ip_tts} score {max_score} {sev_lbl}")
    top_asn = ts.get("top_asn") or []
    if top_asn and len(top_asn) >= 1:
        # Annonce les 1-2 AS les plus représentés si >=2 IPs chacun
        asn_significant = [name for name, cnt in top_asn if cnt >= 2]
        if asn_significant:
            asn_tts = " et ".join(name[:24] for name in asn_significant[:2])
            detail.append(f"hébergeurs récurrents {asn_tts}")
    if ts["cs_bans"] > 0:
        detail.append(f"{ts['cs_bans']} IPs bannies CrowdSec")
    suffix = (", ".join(detail) + ".") if detail else f"{ts['cs_bans']} décisions actives."
    parts.append(f"Niveau {threat}. Score {ts['score']} sur 100. {suffix}")
    return parts


def _check_escalation(ts: dict) -> list:
    """Sprint 7 KC v4 (2026-05-18) : annonce vocale dédiée pour IPs en escalation
    (badge 🔥 backend : progression >=2 stages offensifs en 15min). Cooldown
    court (10 min) car signal critique nécessitant action rapide.

    Annonce 1 phrase par IP escaladée (max 3) avec IP + pays + stage actuel.
    """
    parts = []
    escalated = ts.get("escalated_ips") or []
    if not escalated:
        return parts
    if not _soc_cooldown_ok("kc_escalation", minutes=10):
        return parts
    n = len(escalated)
    intro = f"Alerte escalation Kill Chain. {n} IP{'s' if n>1 else ''} en progression rapide :"
    detail_parts = []
    for ip_obj in escalated[:3]:
        ip = ip_obj.get("ip", "")
        stage = (ip_obj.get("stage") or "").upper()
        country = ip_obj.get("country", "")
        country_tts = f" depuis {country}" if country and country not in ("-", "?", "") else ""
        ip_tts = _ip_to_tts(ip) if ip else ""
        detail_parts.append(f"IP {ip_tts}{country_tts} stage {stage.lower()}")
    if n > 3:
        detail_parts.append(f"et {n - 3} autre{'s' if n - 3 > 1 else ''}")
    parts.append(f"{intro} {', '.join(detail_parts)}. Investigation prioritaire requise.")
    return parts
