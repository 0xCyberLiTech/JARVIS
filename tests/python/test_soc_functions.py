"""Tests fonctions blueprints/soc.py — auto-engine, scoring, helpers purs.

Campagne couverture (étape 1 du plan « couverture d'abord, refactor ensuite ») :
soc.py est l'orchestrateur SOC le moins couvert. Ce fichier cible ses fonctions
pures et semi-pures (classification autoban, candidats ban, score de menace,
checks auto-engine) — testables sans réseau ni SSH.
"""
import base64

from blueprints import soc

# ── _b64py ───────────────────────────────────────────────────────────────

def test_b64py_construit_commande_ssh():
    """_b64py emballe un script Python en commande SSH `echo … | base64 -d | python3`."""
    cmd = soc._b64py("print('x')")
    assert cmd.startswith("echo ")
    assert cmd.endswith("| base64 -d | python3")


def test_b64py_payload_round_trip():
    """Le jeton base64 inséré décode bien le script d'origine."""
    cmd = soc._b64py("print('hello')")
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


# ── _sur_ban_sev1 — ban auto Suricata sévérité 1 ─────────────────────────

def test_sur_ban_sev1_aucune_alerte():
    assert soc._sur_ban_sev1({}, {}) == []


def test_sur_ban_sev1_ip_whitelistee_ignoree():
    assert soc._sur_ban_sev1({"recent_critical": [{"src_ip": "192.168.1.50"}]}, {}) == []


def test_sur_ban_sev1_ip_deja_bannie_cs_ignoree():
    sur = {"recent_critical": [{"src_ip": "203.0.113.60"}]}
    assert soc._sur_ban_sev1(sur, {"203.0.113.60": {"scenario": "x"}}) == []


def test_sur_ban_sev1_bannit_ip_critique(monkeypatch):
    monkeypatch.setattr(soc, "_ip_try_mark_banned", lambda ip: True)
    monkeypatch.setattr(soc, "_save_auto_banned", lambda: None)
    monkeypatch.setattr(soc, "_ban_ip_ssh", lambda ip, reason, dur: (True, "ok"))
    monkeypatch.setattr(soc, "_soc_log", lambda *a, **k: None)
    bans = soc._sur_ban_sev1({"recent_critical": [{"src_ip": "203.0.113.61"}]}, {})
    assert bans == ["203.0.113.61"]


# ── _sur_ban_scans — ban auto port scan ──────────────────────────────────

def test_sur_ban_scans_aucun_scan():
    assert soc._sur_ban_scans({}, {}) == []


def test_sur_ban_scans_ip_lan_ignoree():
    assert soc._sur_ban_scans({"recent_scans": [{"src_ip": "10.0.0.1", "count": 99}]}, {}) == []


def test_sur_ban_scans_bannit_port_scan(monkeypatch):
    monkeypatch.setattr(soc, "_ip_try_mark_banned", lambda ip: True)
    monkeypatch.setattr(soc, "_save_auto_banned", lambda: None)
    monkeypatch.setattr(soc, "_ban_ip_ssh", lambda ip, reason, dur: (True, "ok"))
    monkeypatch.setattr(soc, "_soc_log", lambda *a, **k: None)
    bans = soc._sur_ban_scans({"recent_scans": [{"src_ip": "203.0.113.70", "count": 40}]}, {})
    assert bans == ["203.0.113.70"]


# ── _sur_ban_sev2_surge — ban auto surge C2 ──────────────────────────────

def test_sur_ban_sev2_surge_aucune_ip():
    assert soc._sur_ban_sev2_surge(50, {}, {}) == []


def test_sur_ban_sev2_surge_limite_top_3(monkeypatch):
    """Au plus 3 IPs (top_ips[:3]) sont traitées."""
    monkeypatch.setattr(soc, "_ip_try_mark_banned", lambda ip: True)
    monkeypatch.setattr(soc, "_save_auto_banned", lambda: None)
    monkeypatch.setattr(soc, "_ban_ip_ssh", lambda ip, reason, dur: (True, "ok"))
    monkeypatch.setattr(soc, "_soc_log", lambda *a, **k: None)
    sur = {"top_ips": [{"ip": f"203.0.113.{i}"} for i in range(80, 90)]}
    bans = soc._sur_ban_sev2_surge(60, sur, {})
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
