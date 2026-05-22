"""Tests fonctions blueprints/soc.py — auto-engine, scoring, helpers purs.

Campagne couverture (étape 1 du plan « couverture d'abord, refactor ensuite ») :
soc.py est l'orchestrateur SOC le moins couvert. Ce fichier cible ses fonctions
pures et semi-pures (classification autoban, candidats ban, score de menace,
checks auto-engine) — testables sans réseau ni SSH.
"""
import base64
import time

import soc_ip_deep
import soc_reqhour
import soc_suricata_ban
from blueprints import soc

# ── _b64py ───────────────────────────────────────────────────────────────

def test_b64py_construit_commande_ssh():
    """_b64py emballe un script Python en commande SSH `echo … | base64 -d | python3`."""
    cmd = soc_ip_deep._b64py("print('x')")
    assert cmd.startswith("echo ")
    assert cmd.endswith("| base64 -d | python3")


def test_b64py_payload_round_trip():
    """Le jeton base64 inséré décode bien le script d'origine."""
    cmd = soc_ip_deep._b64py("print('hello')")
    token = cmd.split("echo ", 1)[1].split(" |", 1)[0]
    assert base64.b64decode(token).decode() == "print('hello')"


# ── _autoban_classify ────────────────────────────────────────────────────

def test_autoban_classify_suricata_prioritaire():
    """Une alerte Suricata prime sur tout → 48h."""
    th, lbl, dur = soc._autoban_classify({"sur_alert": True, "stage": "SCAN"})
    assert (th, lbl, dur) == (1, "suricata-ids", "48h")


def test_autoban_classify_honeypot():
    """Sources toutes 'NH' (honeypot) → label honeypot."""
    _th, lbl, dur = soc._autoban_classify({"sources": ["NH", "NH"]})
    assert lbl == "honeypot" and dur == "24h"


def test_autoban_classify_exploit():
    _th, lbl, dur = soc._autoban_classify({"stage": "EXPLOIT"})
    assert lbl == "exploit-cve" and dur == "24h"


def test_autoban_classify_scan():
    _th, lbl, _dur = soc._autoban_classify({"stage": "SCAN"})
    assert lbl == "nginx-logs"


def test_autoban_classify_brute_par_defaut():
    """Stage inconnu / BRUTE → profil nginx-logs par défaut."""
    _th, lbl, _dur = soc._autoban_classify({"stage": "BRUTE"})
    assert lbl == "nginx-logs"


# ── _reqhour_candidates ──────────────────────────────────────────────────

def test_reqhour_candidates_ip_publique_eligible():
    now = 10_000_000_000
    cands = soc._reqhour_candidates(
        [{"ip": "203.0.113.7", "count": 800}], {}, {}, now, min_hits=500)
    assert len(cands) == 1


def test_reqhour_candidates_lan_exclue():
    """IP LAN (whitelist RFC1918) → jamais candidate."""
    now = 10_000_000_000
    cands = soc._reqhour_candidates(
        [{"ip": "192.168.1.50", "count": 9999}], {}, {}, now, min_hits=500)
    assert cands == []


def test_reqhour_candidates_deja_bannie_cs_exclue():
    """IP déjà dans decisions_detail CrowdSec → exclue."""
    now = 10_000_000_000
    cands = soc._reqhour_candidates(
        [{"ip": "203.0.113.8", "count": 800}], {},
        {"203.0.113.8": {"scenario": "http-probing"}}, now, 500)
    assert cands == []


def test_reqhour_candidates_sous_le_seuil_exclue():
    now = 10_000_000_000
    cands = soc._reqhour_candidates(
        [{"ip": "203.0.113.9", "count": 100}], {}, {}, now, min_hits=500)
    assert cands == []


# ── _reqhour_inject_suricata ─────────────────────────────────────────────

def test_reqhour_inject_suricata_indispo_aucun_ajout():
    cands = []
    soc._reqhour_inject_suricata(cands, {"available": False}, {}, 10_000_000_000)
    assert cands == []


def test_reqhour_inject_suricata_ajoute_ip_critique():
    cands = []
    sur = {"available": True, "recent_critical": [{"src_ip": "203.0.113.20"}]}
    soc._reqhour_inject_suricata(cands, sur, {}, 10_000_000_000)
    assert len(cands) == 1
    assert cands[0]["ip"] == "203.0.113.20"
    assert cands[0]["sur_alert"] is True


def test_reqhour_inject_suricata_pas_de_doublon():
    """IP déjà candidate → pas réinjectée."""
    cands = [{"ip": "203.0.113.21", "stage": "SCAN"}]
    sur = {"available": True, "recent_critical": [{"src_ip": "203.0.113.21"}]}
    soc._reqhour_inject_suricata(cands, sur, {}, 10_000_000_000)
    assert len(cands) == 1


# ── _threat_score_from_json ──────────────────────────────────────────────

def test_threat_score_dict_vide():
    ts = soc._threat_score_from_json({}, set())
    assert ts["score"] == 0
    assert ts["kc_active_count"] == 0
    assert ts["kc_stages"] == {}


def test_threat_score_reprend_valeurs_backend():
    ts = soc._threat_score_from_json(
        {"threat_score": 65, "threat_level": "ÉLEVÉ", "threat_exploit_unblocked": 3}, set())
    assert ts["score"] == 65
    assert ts["threat"] == "ÉLEVÉ"
    assert ts["exploit_unblocked"] == 3


def test_threat_score_gap_banned_soustrait_exploit():
    """Les IPs bannies ce cycle (gap_banned) sont retirées de exploit_unblocked."""
    ts = soc._threat_score_from_json(
        {"threat_exploit_unblocked": 3}, {"1.1.1.1", "2.2.2.2"})
    assert ts["exploit_unblocked"] == 1


def test_threat_score_exploit_unblocked_jamais_negatif():
    ts = soc._threat_score_from_json(
        {"threat_exploit_unblocked": 1}, {"a", "b", "c", "d"})
    assert ts["exploit_unblocked"] == 0


def test_threat_score_recap_kill_chain():
    """Récap KC : compte par stage + pays distincts."""
    d = {"kill_chain": {"active_ips": [
        {"ip": "9.9.9.1", "stage": "EXPLOIT", "country": "CN"},
        {"ip": "9.9.9.2", "stage": "SCAN", "country": "RU"},
        {"ip": "9.9.9.3", "stage": "SCAN", "country": "CN"},
    ]}}
    ts = soc._threat_score_from_json(d, set())
    assert ts["kc_active_count"] == 3
    assert ts["kc_stages"]["SCAN"] == 2
    assert ts["kc_stages"]["EXPLOIT"] == 1
    assert set(ts["kc_countries"]) == {"CN", "RU"}


# ── _check_threat_level ──────────────────────────────────────────────────

def test_check_threat_level_faible_silencieux():
    assert soc._check_threat_level({"threat": "FAIBLE"}) == []


def test_check_threat_level_none_silencieux():
    assert soc._check_threat_level({"threat": None}) == []


def test_check_threat_level_eleve_annonce(monkeypatch):
    """Niveau ÉLEVÉ + cooldown libre → annonce TTS non vide."""
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    soc._SOC_MON_COOLDOWNS.pop("threat_ÉLEVÉ", None)
    ts = soc._threat_score_from_json(
        {"threat_level": "ÉLEVÉ", "threat_score": 60, "threat_exploit_unblocked": 2}, set())
    parts = soc._check_threat_level(ts)
    assert parts and any("EXPLOIT" in p for p in parts)


# ── _check_errors ────────────────────────────────────────────────────────

def test_check_errors_taux_normal_silencieux():
    assert soc._check_errors({"error_rate": 5}) == []


def test_check_errors_sans_donnees_silencieux():
    assert soc._check_errors({}) == []


def test_check_errors_taux_eleve_alerte(monkeypatch):
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    soc._SOC_MON_COOLDOWNS.pop("err_5xx", None)
    parts = soc._check_errors({"error_rate": 25})
    assert parts and "25" in parts[0]


# ── _check_escalation ────────────────────────────────────────────────────

def test_check_escalation_aucune_ip_silencieux():
    assert soc._check_escalation({}) == []
    assert soc._check_escalation({"escalated_ips": []}) == []


def test_check_escalation_ip_escaladee_annonce(monkeypatch):
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    soc._SOC_MON_COOLDOWNS.pop("kc_escalation", None)
    parts = soc._check_escalation(
        {"escalated_ips": [{"ip": "9.9.9.9", "stage": "EXPLOIT", "country": "CN"}]})
    assert parts and "escalation" in parts[0].lower()


# ── _check_services ──────────────────────────────────────────────────────

def test_check_services_tout_up_silencieux():
    assert soc._check_services({"nginx": True, "crowdsec": True}) == []


def test_check_services_service_inconnu_down_signale(monkeypatch):
    """Service DOWN hors whitelist → signalé, sans tentative de restart SSH."""
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    soc._SOC_MON_COOLDOWNS.pop("svc_servicexyz", None)
    parts = soc._check_services({"servicexyz": False})
    assert parts and "servicexyz" in parts[0]


def test_check_services_service_whiteliste_down_restart(monkeypatch):
    """Service DOWN ∈ whitelist → tentative de restart SSH (mockée)."""
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    monkeypatch.setattr(soc, "_ssh_ngix", lambda cmd, timeout=20: (True, ""))
    monkeypatch.setattr(soc, "_soc_log", lambda *a, **k: None)
    soc._SOC_MON_COOLDOWNS.pop("svc_nginx", None)
    parts = soc._check_services({"nginx": False})
    assert parts and "nginx" in parts[0].lower()


# ── _sur_ban_* — ban auto Suricata (module soc_suricata_ban) ─────────────

def test_sur_ban_sev1_aucune_alerte():
    assert soc_suricata_ban._sur_ban_sev1({}, {}) == []


def test_sur_ban_sev1_ip_whitelistee_ignoree():
    assert soc_suricata_ban._sur_ban_sev1({"recent_critical": [{"src_ip": "192.168.1.50"}]}, {}) == []


def test_sur_ban_sev1_ip_deja_bannie_cs_ignoree():
    sur = {"recent_critical": [{"src_ip": "203.0.113.60"}]}
    assert soc_suricata_ban._sur_ban_sev1(sur, {"203.0.113.60": {"scenario": "x"}}) == []


def test_sur_ban_sev1_bannit_ip_critique(monkeypatch):
    monkeypatch.setattr(soc_suricata_ban, "_ip_try_mark_banned", lambda ip: True)
    monkeypatch.setattr(soc_suricata_ban, "_save_auto_banned", lambda: None)
    monkeypatch.setattr(soc_suricata_ban, "_ban_ip_ssh", lambda ip, reason, dur: (True, "ok"))
    monkeypatch.setattr(soc_suricata_ban, "_soc_log", lambda *a, **k: None)
    bans = soc_suricata_ban._sur_ban_sev1({"recent_critical": [{"src_ip": "203.0.113.61"}]}, {})
    assert bans == ["203.0.113.61"]


def test_sur_ban_scans_aucun_scan():
    assert soc_suricata_ban._sur_ban_scans({}, {}) == []


def test_sur_ban_scans_ip_lan_ignoree():
    assert soc_suricata_ban._sur_ban_scans({"recent_scans": [{"src_ip": "10.0.0.1", "count": 99}]}, {}) == []


def test_sur_ban_scans_bannit_port_scan(monkeypatch):
    monkeypatch.setattr(soc_suricata_ban, "_ip_try_mark_banned", lambda ip: True)
    monkeypatch.setattr(soc_suricata_ban, "_save_auto_banned", lambda: None)
    monkeypatch.setattr(soc_suricata_ban, "_ban_ip_ssh", lambda ip, reason, dur: (True, "ok"))
    monkeypatch.setattr(soc_suricata_ban, "_soc_log", lambda *a, **k: None)
    bans = soc_suricata_ban._sur_ban_scans({"recent_scans": [{"src_ip": "203.0.113.70", "count": 40}]}, {})
    assert bans == ["203.0.113.70"]


def test_sur_ban_sev2_surge_aucune_ip():
    assert soc_suricata_ban._sur_ban_sev2_surge(50, {}, {}) == []


def test_sur_ban_sev2_surge_limite_top_3(monkeypatch):
    """Au plus 3 IPs (top_ips[:3]) sont traitées."""
    monkeypatch.setattr(soc_suricata_ban, "_ip_try_mark_banned", lambda ip: True)
    monkeypatch.setattr(soc_suricata_ban, "_save_auto_banned", lambda: None)
    monkeypatch.setattr(soc_suricata_ban, "_ban_ip_ssh", lambda ip, reason, dur: (True, "ok"))
    monkeypatch.setattr(soc_suricata_ban, "_soc_log", lambda *a, **k: None)
    sur = {"top_ips": [{"ip": f"203.0.113.{i}"} for i in range(80, 90)]}
    bans = soc_suricata_ban._sur_ban_sev2_surge(60, sur, {})
    assert len(bans) == 3


# ── get_soc_status ───────────────────────────────────────────────────────

def test_get_soc_status_structure():
    st = soc.get_soc_status()
    assert {"soc_engine_active", "bans_24h", "alerts_24h"} <= set(st)
    assert isinstance(st["bans_24h"], int)
    assert isinstance(st["alerts_24h"], int)


# ── _check_threat_level — branches enrichies ─────────────────────────────

def test_check_threat_level_suricata_et_multi(monkeypatch):
    """Niveau CRITIQUE avec alertes Suricata + recon multi-cible → détail annoncé."""
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    soc._SOC_MON_COOLDOWNS.pop("threat_CRITIQUE", None)
    ts = soc._threat_score_from_json(
        {"threat_level": "CRITIQUE", "threat_score": 80,
         "threat_sur_sev1": 2, "threat_multi_count": 4}, set())
    parts = soc._check_threat_level(ts)
    joined = " ".join(parts)
    assert parts and ("Suricata" in joined or "Recon" in joined)


def test_check_threat_level_cooldown_bloque(monkeypatch):
    """2e appel dans la fenêtre cooldown → silencieux."""
    import time as _t
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    soc._SOC_MON_COOLDOWNS["threat_ÉLEVÉ"] = _t.time()
    ts = soc._threat_score_from_json({"threat_level": "ÉLEVÉ", "threat_score": 55}, set())
    assert soc._check_threat_level(ts) == []
    soc._SOC_MON_COOLDOWNS.pop("threat_ÉLEVÉ", None)


# ── _deep_* — investigation IP approfondie (module soc_ip_deep, SSH mocké) ─

def test_deep_crowdsec_aucune_decision(monkeypatch):
    monkeypatch.setattr(soc_ip_deep, "_ssh_ngix", lambda cmd, timeout=10: (True, "[]"))
    res = soc_ip_deep._deep_crowdsec("203.0.113.5")
    assert res["banned"] is False
    assert res["count"] == 0


def test_deep_crowdsec_avec_decision(monkeypatch):
    decisions = ('[{"decisions":[{"id":1,"scenario":"http-probing",'
                 '"duration":"24h","origin":"crowdsec","type":"ban"}]}]')
    monkeypatch.setattr(
        soc_ip_deep, "_ssh_ngix",
        lambda cmd, timeout=10: (True, decisions) if "decisions list" in cmd else (True, "[]"))
    res = soc_ip_deep._deep_crowdsec("203.0.113.6")
    assert res["banned"] is True
    assert res["count"] == 1
    assert res["decisions"][0]["scenario"] == "http-probing"


def test_deep_fail2ban_parse(monkeypatch):
    monkeypatch.setattr(
        soc_ip_deep, "_ssh_json_exec",
        lambda script, timeout=10: {"active": ["sshd"],
                                    "history": [{"jail": "sshd", "ts": 1, "bantime": 2, "count": 1}],
                                    "total_records": 1})
    res = soc_ip_deep._deep_fail2ban("203.0.113.7")
    assert res["banned"] is True
    assert res["jails"] == ["sshd"]
    assert res["total_records"] == 1


def test_deep_fail2ban_aucun_ban(monkeypatch):
    monkeypatch.setattr(soc_ip_deep, "_ssh_json_exec",
                        lambda script, timeout=10: {"active": [], "history": [], "total_records": 0})
    assert soc_ip_deep._deep_fail2ban("203.0.113.8")["banned"] is False


def test_deep_autoban_compte_recidive(monkeypatch):
    monkeypatch.setattr(soc_ip_deep, "_ssh_json_exec",
                        lambda script, timeout=10: {"count": 3, "history": [{"ip": "x"}]})
    assert soc_ip_deep._deep_autoban("203.0.113.9")["count"] == 3


def test_deep_nginx_hits_nombre(monkeypatch):
    monkeypatch.setattr(soc_ip_deep, "_ssh_ngix", lambda cmd, timeout=15: (True, "42\n"))
    assert soc_ip_deep._deep_nginx_hits("203.0.113.10") == 42


def test_deep_nginx_hits_sortie_invalide(monkeypatch):
    monkeypatch.setattr(soc_ip_deep, "_ssh_ngix", lambda cmd, timeout=15: (True, "erreur"))
    assert soc_ip_deep._deep_nginx_hits("203.0.113.11") == 0


def test_deep_nginx_hits_ssh_ko(monkeypatch):
    monkeypatch.setattr(soc_ip_deep, "_ssh_ngix", lambda cmd, timeout=15: (False, ""))
    assert soc_ip_deep._deep_nginx_hits("203.0.113.12") == 0


def test_deep_nginx_last_lignes(monkeypatch):
    monkeypatch.setattr(soc_ip_deep, "_ssh_ngix", lambda cmd, timeout=10: (True, "ligne1\nligne2\n"))
    assert soc_ip_deep._deep_nginx_last("203.0.113.13") == ["ligne1", "ligne2"]


def test_deep_nginx_last_ssh_ko(monkeypatch):
    monkeypatch.setattr(soc_ip_deep, "_ssh_ngix", lambda cmd, timeout=10: (False, ""))
    assert soc_ip_deep._deep_nginx_last("203.0.113.14") == []


def test_deep_rsyslog_agrege_compteurs(monkeypatch):
    out = "/var/log/central/srv-ngix/auth.log:5\n/var/log/central/clt/access.log:3"
    monkeypatch.setattr(soc_ip_deep, "_ssh_ngix", lambda cmd, timeout=25: (True, out))
    res = soc_ip_deep._deep_rsyslog("203.0.113.15")
    assert res["total"] == 8
    assert len(res["sources"]) == 2


# ── _check_net_spikes — alerte pic bande passante ────────────────────────

def test_check_net_spikes_aucun_pic():
    assert soc._check_net_spikes({}) is None


def test_check_net_spikes_pic_recent_alerte(monkeypatch):
    import time as _t
    spoke = []
    monkeypatch.setattr(soc, "_speak", lambda msg, **k: spoke.append(msg))
    monkeypatch.setattr(soc, "_soc_log", lambda *a, **k: None)
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    soc._SOC_MON_COOLDOWNS.pop("net_spike", None)
    soc._check_net_spikes({"net_spikes": [{"ts": _t.time(), "tx_mbps": 120, "rx_mbps": 40}]})
    assert spoke and "bande passante" in spoke[0].lower()


def test_check_net_spikes_pic_ancien_silencieux(monkeypatch):
    spoke = []
    monkeypatch.setattr(soc, "_speak", lambda msg, **k: spoke.append(msg))
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    soc._SOC_MON_COOLDOWNS.pop("net_spike", None)
    soc._check_net_spikes({"net_spikes": [{"ts": 1.0, "tx_mbps": 99, "rx_mbps": 99}]})
    assert spoke == []


# ── _soc_subnet_campaign_check — campagne /24 coordonnée ─────────────────

def test_subnet_campaign_aucune():
    assert soc._soc_subnet_campaign_check({}) is None


def test_subnet_campaign_sous_seuil_silencieux(monkeypatch):
    spoke = []
    monkeypatch.setattr(soc, "_speak", lambda msg, **k: spoke.append(msg))
    soc._soc_subnet_campaign_check({"slow_campaigns": [{"subnet": "1.2.3.0/24", "count": 3}]})
    assert spoke == []


def test_subnet_campaign_au_dessus_seuil_alerte(monkeypatch):
    spoke = []
    monkeypatch.setattr(soc, "_speak", lambda msg, **k: spoke.append(msg))
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    soc._SOC_MON_COOLDOWNS.pop("campaign_45_146_165_0_24", None)
    soc._soc_subnet_campaign_check(
        {"slow_campaigns": [{"subnet": "45.146.165.0/24", "count": 8, "countries": ["RU"]}]})
    assert spoke and "45.146.165.0/24" in spoke[0]


# ── _soc_autoban / _soc_exploit_gap_check — chemins de garde ─────────────

def test_soc_autoban_aucune_ip():
    assert soc._soc_autoban({}) is None


def test_soc_autoban_ip_lan_jamais_bannie(monkeypatch):
    banned = []
    monkeypatch.setattr(soc, "_speak", lambda *a, **k: None)
    monkeypatch.setattr(soc, "_ban_ip_ssh", lambda *a, **k: (banned.append(a), (True, ""))[1])
    soc._soc_autoban({"kill_chain": {"active_ips": [
        {"ip": "192.168.1.50", "stage": "EXPLOIT", "count": 9999}]}})
    assert banned == []


def test_soc_exploit_gap_check_aucune_ip():
    assert soc._soc_exploit_gap_check({}) == set()


def test_soc_exploit_gap_check_stage_non_exploit_ignore(monkeypatch):
    banned = []
    monkeypatch.setattr(soc, "_ban_ip_ssh", lambda *a, **k: (banned.append(a), (True, ""))[1])
    res = soc._soc_exploit_gap_check({"kill_chain": {"active_ips": [
        {"ip": "203.0.113.200", "stage": "SCAN", "count": 9999}]}})
    assert res == set() and banned == []


# ── _check_daily_report — rapport vocal 8h (temps figé) ──────────────────

def test_check_daily_report_hors_fenetre_silencieux(monkeypatch):
    """En dehors du créneau 08h00-08h09 → aucun rapport (sauf hasard du wall-clock)."""
    import datetime as _dt

    class _Fixe(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _dt.datetime(2026, 5, 22, 14, 30, 0)

    monkeypatch.setattr(soc.datetime, "datetime", _Fixe)
    spoke = []
    monkeypatch.setattr(soc, "_speak", lambda msg, **k: spoke.append(msg))
    soc._check_daily_report({}, {"threat": "MOYEN", "score": 35})
    assert spoke == []


def test_check_daily_report_fenetre_8h_annonce(monkeypatch):
    """Créneau 08h03 + cooldown libre → rapport vocal quotidien émis."""
    import datetime as _dt

    class _Fixe(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _dt.datetime(2026, 5, 22, 8, 3, 0)

    monkeypatch.setattr(soc.datetime, "datetime", _Fixe)
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    spoke = []
    monkeypatch.setattr(soc, "_speak", lambda msg, **k: spoke.append(msg))
    soc._SOC_MON_COOLDOWNS.pop("daily_report_2026-05-22", None)
    ts = soc._threat_score_from_json({"threat_level": "MOYEN", "threat_score": 35}, set())
    soc._check_daily_report({"traffic": {"req_last_hour": 100}}, ts)
    assert spoke and "Rapport SOC" in spoke[0]


# ── _soc_*_check — orchestrateurs auto-engine, chemins de garde ──────────

def test_soc_suricata_check_donnees_vides(monkeypatch):
    monkeypatch.setattr(soc, "_speak", lambda *a, **k: None)
    assert soc._soc_suricata_check({}) is None


def test_soc_reqhour_check_donnees_vides(monkeypatch):
    monkeypatch.setattr(soc, "_speak", lambda *a, **k: None)
    assert soc._soc_reqhour_check({}) is None


def test_soc_reqhour_check_sous_seuil_silencieux(monkeypatch):
    """Trafic sous le seuil req/h → aucune annonce vocale."""
    spoke = []
    monkeypatch.setattr(soc, "_speak", lambda *a, **k: spoke.append(a))
    data = {"traffic": {"requests_per_hour": {time.strftime("%H"): 100}}}
    soc._soc_reqhour_check(data)
    assert spoke == []


def test_soc_reqhour_check_cooldown_actif_silencieux(monkeypatch):
    """Pic réel mais cooldown global encore actif → pas d'action."""
    spoke = []
    monkeypatch.setattr(soc, "_speak", lambda *a, **k: spoke.append(a))
    monkeypatch.setattr(soc_reqhour, "_soc_cooldown_ok", lambda *a, **k: False)
    data = {"traffic": {"requests_per_hour": {time.strftime("%H"): 900}}}
    soc._soc_reqhour_check(data)
    assert spoke == []


def test_soc_reqhour_check_pic_bannit_et_annonce(monkeypatch):
    """Pic >500 req/h + IP EXPLOIT candidate → ban auto + annonce vocale."""
    spoke, logged = [], []
    monkeypatch.setattr(soc, "_speak", lambda *a, **k: spoke.append(a[0] if a else ""))
    monkeypatch.setattr(soc_reqhour, "_soc_cooldown_ok", lambda *a, **k: True)
    monkeypatch.setattr(soc_reqhour, "_ip_try_mark_banned", lambda ip: True)
    monkeypatch.setattr(soc_reqhour, "_save_auto_banned", lambda: None)
    monkeypatch.setattr(soc_reqhour, "_ban_ip_ssh", lambda ip, reason, dur: (True, "ok"))
    monkeypatch.setattr(soc_reqhour, "_soc_log", lambda *a, **k: logged.append(a))
    data = {
        "traffic": {"requests_per_hour": {time.strftime("%H"): 900}},
        "kill_chain": {"active_ips": [
            {"ip": "203.0.113.50", "count": 800, "stage": "EXPLOIT"}]},
    }
    soc._soc_reqhour_check(data)
    assert spoke and "Pic de trafic" in spoke[0]
    assert "1 IP bannie" in spoke[0]
    assert logged  # ban journalisé via _soc_log


def test_soc_rsyslog_check_donnees_vides(monkeypatch):
    monkeypatch.setattr(soc, "_speak", lambda *a, **k: None)
    assert soc._soc_rsyslog_check({}) is None


# ── _check_hourly_report — rapport vocal heure pleine (temps figé) ───────

def test_check_hourly_report_hors_minute_silencieux(monkeypatch):
    import datetime as _dt

    class _Fixe(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _dt.datetime(2026, 5, 22, 14, 30, 0)

    monkeypatch.setattr(soc.datetime, "datetime", _Fixe)
    spoke = []
    monkeypatch.setattr(soc, "_speak", lambda msg, **k: spoke.append(msg))
    soc._check_hourly_report({}, {"threat": "MOYEN", "score": 40})
    assert spoke == []


def test_check_hourly_report_heure_pleine_annonce(monkeypatch):
    import datetime as _dt

    class _Fixe(_dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return _dt.datetime(2026, 5, 22, 14, 2, 0)

    monkeypatch.setattr(soc.datetime, "datetime", _Fixe)
    monkeypatch.setattr(soc, "_save_cooldowns", lambda: None)
    spoke = []
    monkeypatch.setattr(soc, "_speak", lambda msg, **k: spoke.append(msg))
    soc._SOC_MON_COOLDOWNS.pop("hourly_report_2026-05-22_14", None)
    ts = soc._threat_score_from_json({"threat_level": "ÉLEVÉ", "threat_score": 60}, set())
    soc._check_hourly_report({}, ts)
    assert spoke and "heure pleine" in spoke[0].lower()


# ── _dur_to_tts — conversion durée brute en TTS ──────────────────────────

def test_dur_to_tts_valeurs_predefinies():
    assert soc._dur_to_tts("24h") == "vingt-quatre heures"
    assert soc._dur_to_tts("48h") == "quarante-huit heures"
    assert soc._dur_to_tts("8760h") == "un an"


def test_dur_to_tts_regex_heures_generique():
    """Une durée hors map (ex: 5h) doit être convertie via le regex."""
    assert soc._dur_to_tts("5h") == "5 heures"


def test_dur_to_tts_format_invalide_retour_tel_quel():
    assert soc._dur_to_tts("durée bizarre") == "durée bizarre"


# ── _ip_to_tts — conversion IP en TTS prononceable ───────────────────────

def test_ip_to_tts_ipv4_point_a_point():
    assert soc._ip_to_tts("203.0.113.50") == "203 point 0 point 113 point 50"


def test_ip_to_tts_chaine_vide():
    assert soc._ip_to_tts("") == ""


# ── _is_whitelisted / _ip_skip — politique whitelist anti-ban ────────────

def test_is_whitelisted_lan_192():
    assert soc._is_whitelisted("192.168.1.50") is True


def test_is_whitelisted_lan_10():
    assert soc._is_whitelisted("10.0.0.1") is True


def test_is_whitelisted_lan_172_16():
    """172.16-31 = plage privée RFC1918."""
    assert soc._is_whitelisted("172.20.0.1") is True


def test_is_whitelisted_ip_publique_non_listee():
    assert soc._is_whitelisted("8.8.8.8") is False


def test_is_whitelisted_entree_exacte_dynamique(monkeypatch):
    monkeypatch.setattr(soc, "_SOC_WHITELIST", ["198.51.100.7"])
    assert soc._is_whitelisted("198.51.100.7") is True


def test_is_whitelisted_prefixe_dynamique(monkeypatch):
    """Une entrée se terminant par '.' couvre tout le préfixe."""
    monkeypatch.setattr(soc, "_SOC_WHITELIST", ["198.51.100."])
    assert soc._is_whitelisted("198.51.100.99") is True


def test_ip_skip_vide_renvoie_true():
    assert soc._ip_skip("") is True


def test_ip_skip_lan_renvoie_true():
    assert soc._ip_skip("192.168.1.50") is True


def test_ip_skip_ip_publique_renvoie_false():
    assert soc._ip_skip("8.8.8.8") is False


# ── _load_soc_config — fusion overrides + défauts ────────────────────────

def test_load_soc_config_fichier_absent_renvoie_defauts(monkeypatch, tmp_path):
    monkeypatch.setattr(soc, "_SOC_CONFIG_PATH", tmp_path / "absent.json")
    cfg = soc._load_soc_config()
    assert cfg == soc._SOC_CONFIG_DEFAULTS


def test_load_soc_config_override_partiel(monkeypatch, tmp_path):
    """Un override partiel ne remplace que les clés présentes ET connues."""
    import json as _j
    f = tmp_path / "soc_config.json"
    f.write_text(_j.dumps({"ngix_host": "10.0.0.99", "cle_inconnue": "ignorée"}),
                 encoding="utf-8")
    monkeypatch.setattr(soc, "_SOC_CONFIG_PATH", f)
    cfg = soc._load_soc_config()
    assert cfg["ngix_host"] == "10.0.0.99"
    assert "cle_inconnue" not in cfg
    # Les autres clés gardent leurs défauts
    assert cfg["proxmox_host"] == soc._SOC_CONFIG_DEFAULTS["proxmox_host"]


# ── Wrappers SSH par hôte — délégation vers _ssh_host ────────────────────

def test_ssh_ngix_delegue_a_ssh_host(monkeypatch):
    calls = []
    monkeypatch.setattr(soc, "_ssh_host",
                        lambda arr, cmd, t, r: calls.append((arr, cmd)) or (True, "ok"))
    ok, out = soc._ssh_ngix("uptime")
    assert (ok, out) == (True, "ok")
    assert calls[0][0] is soc._SSH_NGIX and calls[0][1] == "uptime"


def test_ssh_proxmox_delegue_a_ssh_host(monkeypatch):
    calls = []
    monkeypatch.setattr(soc, "_ssh_host",
                        lambda arr, cmd, t, r: calls.append(arr) or (True, ""))
    soc._ssh_proxmox("qm list")
    assert calls[0] is soc._SSH_PROXMOX


def test_ssh_dev1_delegue_a_ssh_host(monkeypatch):
    calls = []
    monkeypatch.setattr(soc, "_ssh_host",
                        lambda arr, cmd, t, r: calls.append(arr) or (True, ""))
    soc._ssh_dev1("ls")
    assert calls[0] is soc._SSH_DEV1


# ── _ssh_host — invocation subprocess + gestion erreurs ──────────────────

def test_ssh_host_succes_renvoie_stdout(monkeypatch):
    """returncode == 0 → (True, stdout+stderr)."""
    class _R:
        returncode = 0
        stdout = "uptime line"
        stderr = ""
    monkeypatch.setattr(soc.subprocess, "run", lambda *a, **k: _R())
    ok, out = soc._ssh_host(["ssh", "host"], "uptime", timeout=2, retries=0)
    assert (ok, out) == (True, "uptime line")


def test_ssh_host_timeout_renvoie_message(monkeypatch):
    def _raise(*a, **k):
        raise soc.subprocess.TimeoutExpired(cmd="ssh", timeout=2)
    monkeypatch.setattr(soc.subprocess, "run", _raise)
    ok, out = soc._ssh_host(["ssh", "host"], "uptime", timeout=2, retries=0)
    assert ok is False and "Timeout" in out


# ── _ban_ip_ssh — délégation à cscli via _ssh_ngix ───────────────────────

def test_ban_ip_ssh_construit_commande_cscli(monkeypatch):
    captured = {}
    def _fake(cmd, **k):
        captured["cmd"] = cmd
        return True, "Decision added"
    monkeypatch.setattr(soc, "_ssh_ngix", _fake)
    ok, out = soc._ban_ip_ssh("203.0.113.7", "test-jarvis", "24h")
    assert ok is True
    assert "cscli decisions add" in captured["cmd"]
    assert "203.0.113.7" in captured["cmd"]
    assert "24h" in captured["cmd"]


# ── _load_whitelist / _save_whitelist — round-trip persistance ───────────

def test_save_puis_load_whitelist_round_trip(monkeypatch, tmp_path):
    f = tmp_path / "jarvis_soc_whitelist.json"
    monkeypatch.setattr(soc, "_SOC_WHITELIST_PATH", f)
    monkeypatch.setattr(soc, "_SOC_WHITELIST", ["198.51.100.42"])
    soc._save_whitelist()
    # Reset puis recharge
    monkeypatch.setattr(soc, "_SOC_WHITELIST", [])
    soc._load_whitelist()
    assert soc._SOC_WHITELIST == ["198.51.100.42"]


# ── _soc_log — journal d'actions proactives ──────────────────────────────

def test_soc_log_ajoute_entree(monkeypatch):
    """_soc_log doit ajouter une entrée au journal en mémoire."""
    monkeypatch.setattr(soc, "_soc_actions_save", lambda: None)
    before = len(soc._SOC_ACTIONS)
    soc._soc_log("ban_ip", "détail-test-unique", True, "result-test")
    assert len(soc._SOC_ACTIONS) == before + 1
    last = soc._SOC_ACTIONS[-1]
    assert (last["type"], last["detail"], last["success"]) == (
        "ban_ip", "détail-test-unique", True)
