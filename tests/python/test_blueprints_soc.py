"""Tests blueprints/soc.py — helpers purs + routes Flask via test_client.

Stratégie : focus sur les fonctions pures (regex, conversions, whitelist) +
quelques routes simples avec mock subprocess pour les SSH calls. Évite de
mocker tout l'écosystème CrowdSec/srv-ngix.
"""
from unittest.mock import patch

import pytest

# Import du blueprint (no-op au boot side effects : juste lecture fichiers locaux)
from blueprints import soc as soc_module
from flask import Flask


@pytest.fixture
def app():
    """Flask app de test avec le blueprint SOC + DI minimal."""
    app = Flask(__name__)
    app.testing = True

    class _StubLimiter:
        def limit(self, rate):
            def decorator(fn):
                return fn
            return decorator

    soc_module.init_soc(speak_fn=lambda txt: None, limiter_obj=_StubLimiter())
    app.register_blueprint(soc_module.soc_bp)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ── Helpers purs : _dur_to_tts ──────────────────────────────────────────


def test_dur_to_tts_24h_dans_dict():
    """24h est dans _DUR_TTS_MAP."""
    assert "vingt-quatre heures" in soc_module._dur_to_tts("24h")


def test_dur_to_tts_format_simple_heures():
    """Format `Nh` non dans dict → fallback 'N heures'."""
    assert soc_module._dur_to_tts("36h") == "36 heures"
    assert soc_module._dur_to_tts("999h") == "999 heures"


def test_dur_to_tts_chaine_inconnue_renvoie_brute():
    assert soc_module._dur_to_tts("xyz") == "xyz"
    assert soc_module._dur_to_tts("") == ""


def test_dur_to_tts_case_insensitive():
    """Le regex est insensible à la casse pour le suffixe."""
    out = soc_module._dur_to_tts("12H")
    assert "12" in out


# ── Helpers purs : _ip_to_tts ──────────────────────────────────────────


def test_ip_to_tts_remplace_points_par_point():
    assert soc_module._ip_to_tts("192.168.1.50") == "192 point 168 point 1 point 50"


def test_ip_to_tts_chaine_sans_point_inchangee():
    assert soc_module._ip_to_tts("hello") == "hello"


def test_ip_to_tts_chaine_vide():
    assert soc_module._ip_to_tts("") == ""


# ── Helpers purs : _is_whitelisted / _ip_skip ──────────────────────────


def test_is_whitelisted_lan_192_168():
    """LAN privé → toujours whitelisté."""
    assert soc_module._is_whitelisted("192.168.1.50")
    assert soc_module._is_whitelisted("192.168.99.99")


def test_is_whitelisted_lan_10():
    assert soc_module._is_whitelisted("10.0.0.1")


def test_is_whitelisted_localhost():
    assert soc_module._is_whitelisted("127.0.0.1")


def test_is_whitelisted_ip_publique_pas_dans_liste():
    """IP publique aléatoire → pas whitelisté."""
    assert not soc_module._is_whitelisted("8.8.8.8")


def test_ip_skip_chaine_vide():
    """IP vide → skip True (pas de ban)."""
    assert soc_module._ip_skip("") is True


def test_ip_skip_lan_skip():
    """LAN → skip (whitelisté)."""
    assert soc_module._ip_skip("192.168.1.50") is True


def test_ip_skip_publique_pas_skip():
    """IP publique non whitelistée → skip False (peut bannir)."""
    assert soc_module._ip_skip("1.2.3.4") is False


# ── Constantes ───────────────────────────────────────────────────────────


def test_lan_prefixes_couvre_les_classes_privees():
    """Sanity : les 3 classes RFC1918 sont couvertes."""
    prefixes = soc_module._LAN_PREFIXES
    assert any(p.startswith("10.") for p in prefixes)
    assert any(p.startswith("192.168") for p in prefixes)
    assert any(p.startswith("127.") for p in prefixes)


def test_route_limits_couvre_les_endpoints_critiques():
    """Sanity : les routes sensibles ont des rate limits déclarés."""
    for endpoint in ["api_soc_ban_ip", "api_soc_unban_ip", "api_soc_force_autoban"]:
        assert endpoint in soc_module._ROUTE_LIMITS


# ── _check_csrf ─────────────────────────────────────────────────────────


def test_check_csrf_refuse_sans_header(client):
    """POST sans X-Requested-With → 403."""
    r = client.post("/api/soc/whitelist", json={"ip": "1.2.3.4"})
    assert r.status_code == 403
    assert "CSRF" in r.get_json()["error"]


def test_check_csrf_accepte_avec_header(client):
    """POST avec X-Requested-With → pas de blocage CSRF (mais peut échouer pour autre raison)."""
    r = client.post("/api/soc/whitelist", json={"ip": ""},
                    headers={"X-Requested-With": "XMLHttpRequest"})
    # Pas 403 (CSRF ne bloque pas) — attend 400 (ip vide)
    assert r.status_code == 400


# ── /api/soc/whitelist GET / POST / DELETE ────────────────────────────


def test_get_whitelist_renvoie_liste(client):
    r = client.get("/api/soc/whitelist")
    assert r.status_code == 200
    body = r.get_json()
    assert "whitelist" in body
    assert isinstance(body["whitelist"], list)


def test_post_whitelist_ajoute_ip(client, monkeypatch):
    """Ajout IP → 200 + IP dans la liste retournée."""
    monkeypatch.setattr(soc_module, "_save_whitelist", lambda: None)
    r = client.post("/api/soc/whitelist", json={"ip": "203.0.113.42"},
                    headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert "203.0.113.42" in body["whitelist"]
    # Cleanup pour ne pas polluer les autres tests
    with soc_module._SOC_WHITELIST_LOCK:
        if "203.0.113.42" in soc_module._SOC_WHITELIST:
            soc_module._SOC_WHITELIST.remove("203.0.113.42")


def test_post_whitelist_doublon_renvoie_info(client, monkeypatch):
    monkeypatch.setattr(soc_module, "_save_whitelist", lambda: None)
    # 1er ajout
    client.post("/api/soc/whitelist", json={"ip": "203.0.113.99"},
                headers={"X-Requested-With": "XMLHttpRequest"})
    # 2e ajout
    r = client.post("/api/soc/whitelist", json={"ip": "203.0.113.99"},
                    headers={"X-Requested-With": "XMLHttpRequest"})
    body = r.get_json()
    assert body["ok"] is True
    assert "déjà présent" in body.get("info", "")
    # Cleanup
    with soc_module._SOC_WHITELIST_LOCK:
        if "203.0.113.99" in soc_module._SOC_WHITELIST:
            soc_module._SOC_WHITELIST.remove("203.0.113.99")


def test_post_whitelist_ip_vide_400(client):
    r = client.post("/api/soc/whitelist", json={"ip": ""},
                    headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 400


def test_delete_whitelist_inexistante_404(client):
    r = client.delete("/api/soc/whitelist", json={"ip": "999.999.999.999"},
                      headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 404


# ── /api/soc/ban-ip ─────────────────────────────────────────────────────


def test_ban_ip_invalide_400(client):
    """IP malformée → 400."""
    r = client.post("/api/soc/ban-ip", json={"ip": "not-an-ip", "reason": "test"},
                    headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 400


def test_ban_ip_lan_refuse_403(client):
    """Tentative de ban d'une IP LAN → 403 (sécurité)."""
    r = client.post("/api/soc/ban-ip", json={"ip": "192.168.1.50", "reason": "test"},
                    headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 403
    assert "LAN/whitelist" in r.get_json()["error"]


def test_ban_ip_publique_appelle_ssh(client, monkeypatch):
    """IP publique non LAN → call SSH ban (mocké)."""
    captured = {}

    def fake_ban(ip, reason, duration):
        captured.update(ip=ip, reason=reason, duration=duration)
        return True, "ban-ok"

    monkeypatch.setattr(soc_module, "_ban_ip_ssh", fake_ban)
    monkeypatch.setattr(soc_module, "_soc_log", lambda *a, **k: None)
    r = client.post("/api/soc/ban-ip",
                    json={"ip": "203.0.113.55", "reason": "test", "duration": "24h"},
                    headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200
    assert captured["ip"] == "203.0.113.55"
    assert captured["duration"] == "24h"


def test_ban_ip_duration_invalide_clamp_24h(client, monkeypatch):
    """Format duration invalide → clamp à '24h' (sécurité)."""
    captured = {}
    monkeypatch.setattr(soc_module, "_ban_ip_ssh",
                        lambda ip, reason, dur: (captured.update(dur=dur) or (True, "")))
    monkeypatch.setattr(soc_module, "_soc_log", lambda *a, **k: None)
    client.post("/api/soc/ban-ip",
                json={"ip": "203.0.113.66", "reason": "x", "duration": "invalid"},
                headers={"X-Requested-With": "XMLHttpRequest"})
    assert captured["dur"] == "24h"


def test_ban_ip_reason_sanitize_caracteres_speciaux(client, monkeypatch):
    """Reason avec caractères spéciaux → sanitized (regex strip non-alphanum)."""
    captured = {}
    monkeypatch.setattr(soc_module, "_ban_ip_ssh",
                        lambda ip, reason, dur: (captured.update(reason=reason) or (True, "")))
    monkeypatch.setattr(soc_module, "_soc_log", lambda *a, **k: None)
    client.post("/api/soc/ban-ip",
                json={"ip": "203.0.113.77", "reason": "rm -rf /; sql' OR 1=1--"},
                headers={"X-Requested-With": "XMLHttpRequest"})
    # Caractères dangereux supprimés (`;`, `'`, `=`)
    assert ";" not in captured["reason"]
    assert "'" not in captured["reason"]
    assert "=" not in captured["reason"]


# ── /api/soc/unban-ip ───────────────────────────────────────────────────


def test_unban_ip_invalide_400(client):
    r = client.post("/api/soc/unban-ip", json={"ip": "abc"},
                    headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 400


def test_unban_ip_appelle_ssh(client, monkeypatch):
    captured = {}

    def fake_ssh(cmd, timeout=20, retries=1):
        captured["cmd"] = cmd
        return True, "deleted"

    monkeypatch.setattr(soc_module, "_ssh_ngix", fake_ssh)
    monkeypatch.setattr(soc_module, "_soc_log", lambda *a, **k: None)
    r = client.post("/api/soc/unban-ip", json={"ip": "203.0.113.88"},
                    headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200
    assert "203.0.113.88" in captured["cmd"]
    assert "cscli decisions delete" in captured["cmd"]


# ── /api/soc/heartbeat + dashboard_open ────────────────────────────────


def test_heartbeat_post_met_a_jour_timestamp(client):
    """POST heartbeat → met à jour _SOC_HB_LAST."""
    before = soc_module._SOC_HB_LAST
    r = client.post("/api/soc/heartbeat", headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200
    assert soc_module._SOC_HB_LAST > before


def test_soc_dashboard_open_apres_heartbeat(client):
    """Après un heartbeat récent, _soc_dashboard_open() retourne True."""
    client.post("/api/soc/heartbeat", headers={"X-Requested-With": "XMLHttpRequest"})
    assert soc_module._soc_dashboard_open() is True


# ── /api/soc/actions ────────────────────────────────────────────────────


def test_get_actions_renvoie_liste(client):
    r = client.get("/api/soc/actions")
    assert r.status_code == 200
    body = r.get_json()
    assert "actions" in body
    assert isinstance(body["actions"], list)


def test_clear_actions_vide_la_liste(client, monkeypatch):
    monkeypatch.setattr(soc_module, "_soc_actions_save", lambda: None)
    # Ajoute une action de test
    with soc_module._SOC_LOCK:
        soc_module._SOC_ACTIONS.append({"ts": "2026-01-01 00:00:00", "type": "test", "detail": "x", "success": True, "result": ""})
    r = client.post("/api/soc/actions/clear", headers={"X-Requested-With": "XMLHttpRequest"})
    assert r.status_code == 200
    with soc_module._SOC_LOCK:
        assert len(soc_module._SOC_ACTIONS) == 0


# ── _soc_cooldown_ok ────────────────────────────────────────────────────


def test_soc_cooldown_ok_premier_appel_true(monkeypatch):
    """Premier appel pour une key → True + enregistre."""
    monkeypatch.setattr(soc_module, "_save_cooldowns", lambda: None)
    soc_module._SOC_MON_COOLDOWNS.pop("test_key_xyz", None)
    assert soc_module._soc_cooldown_ok("test_key_xyz", minutes=10) is True
    assert "test_key_xyz" in soc_module._SOC_MON_COOLDOWNS


def test_soc_cooldown_ok_dans_la_fenetre_false(monkeypatch):
    """2e appel < `minutes` → False."""
    monkeypatch.setattr(soc_module, "_save_cooldowns", lambda: None)
    soc_module._SOC_MON_COOLDOWNS["test_key_zzz"] = __import__("time").time()
    assert soc_module._soc_cooldown_ok("test_key_zzz", minutes=10) is False


# ── _fetch_monitoring (mock requests) ──────────────────────────────────


def test_fetch_monitoring_succes_via_http(monkeypatch):
    """HTTP GET réussit → retourne (True, raw)."""
    class FakeResp:
        text = '{"ok": true}'
        def raise_for_status(self): pass

    fake_requests = type("R", (), {"get": staticmethod(lambda url, timeout=8: FakeResp())})()
    monkeypatch.setitem(__import__("sys").modules, "requests", fake_requests)
    monkeypatch.setitem(soc_module._monitoring_cache, "raw", None)
    monkeypatch.setitem(soc_module._monitoring_cache, "ts", 0.0)

    ok, raw = soc_module._fetch_monitoring(force=True)
    assert ok is True
    assert raw == '{"ok": true}'


def test_fetch_monitoring_cache_hit_skip_http(monkeypatch):
    """Si cache valide < TTL → retourne le cache sans HTTP."""
    monkeypatch.setitem(soc_module._monitoring_cache, "raw", '{"cached": true}')
    monkeypatch.setitem(soc_module._monitoring_cache, "ts", __import__("time").time())

    # Remplace requests par une version qui crash si appelée
    crash_requests = type("R", (), {"get": staticmethod(lambda *a, **k: (_ for _ in ()).throw(RuntimeError("ne devrait pas être appelé")))})()
    with patch.dict(__import__("sys").modules, {"requests": crash_requests}):
        ok, raw = soc_module._fetch_monitoring(force=False)
    assert ok is True
    assert raw == '{"cached": true}'


# ── Routes /api/soc/* — lecture monitoring/defense (mockées) ─────────────


def test_api_soc_monitor_get(client):
    r = client.get("/api/soc/monitor")
    assert r.status_code == 200
    assert "enabled" in r.get_json()


def test_api_soc_threat_score_ok(client, monkeypatch):
    monkeypatch.setattr(soc_module, "_fetch_monitoring",
                        lambda *a, **k: (True, '{"threat_score": 40, "threat_level": "MOYEN"}'))
    r = client.get("/api/soc/threat-score")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["score"] == 40


def test_api_soc_threat_score_monitoring_ko_503(client, monkeypatch):
    monkeypatch.setattr(soc_module, "_fetch_monitoring", lambda *a, **k: (False, ""))
    r = client.get("/api/soc/threat-score")
    assert r.status_code == 503


def test_api_soc_defense_ok(client, monkeypatch):
    monkeypatch.setattr(soc_module, "_fetch_defense", lambda *a, **k: (True, '{"bans_24h": 7}'))
    r = client.get("/api/soc/defense")
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_api_soc_defense_ko_503(client, monkeypatch):
    monkeypatch.setattr(soc_module, "_fetch_defense", lambda *a, **k: (False, ""))
    r = client.get("/api/soc/defense")
    assert r.status_code == 503


def test_api_soc_ioc_ok(client, monkeypatch):
    monkeypatch.setattr(soc_module, "_fetch_monitoring",
                        lambda *a, **k: (True, '{"ioc": {"score": 12, "level": "OK"}}'))
    r = client.get("/api/soc/ioc")
    assert r.status_code == 200
    assert r.get_json()["ioc"]["level"] == "OK"


def test_api_soc_ioc_bloc_absent_503(client, monkeypatch):
    """monitoring.json sans clé `ioc` → 503 (déploiement SOC partiel)."""
    monkeypatch.setattr(soc_module, "_fetch_monitoring", lambda *a, **k: (True, "{}"))
    r = client.get("/api/soc/ioc")
    assert r.status_code == 503
