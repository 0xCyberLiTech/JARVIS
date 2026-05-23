"""Tests proxmox_api — fetch état Proxmox VE + cache + injection LLM (mock requests)."""
import json
from unittest.mock import MagicMock

from proxmox import api as proxmox_api


def _reset_cache():
    """Réinitialise le cache module-level entre tests."""
    proxmox_api._cache = {"ts": 0.0, "data": None}


# ── Constantes ────────────────────────────────────────────────────────────


def test_pve_cache_ttl_30s():
    assert proxmox_api.PVE_CACHE_TTL == 30


def test_chat_pve_kw_couvre_termes_essentiels():
    """Sanity : keywords PVE essentiels présents."""
    for kw in ["proxmox", "pve", "hyperviseur", "machine virtuelle", "lxc"]:
        assert kw in proxmox_api.CHAT_PVE_KW


def test_pve_config_path_pointe_sur_jarvis_pve_json():
    assert proxmox_api.PVE_CONFIG_PATH.name == "jarvis_pve.json"


def test_module_logger():
    assert proxmox_api._log.name == "jarvis.proxmox_api"


def test_cache_initial_vide():
    """Sanity : le cache module-level commence vide (ts=0, data=None)."""
    # Reset pour ne pas dépendre d'un test précédent qui aurait peuplé
    _reset_cache()
    assert proxmox_api._cache == {"ts": 0.0, "data": None}


# ── _auth_session ─────────────────────────────────────────────────────────


def test_auth_session_avec_token_id_secret(monkeypatch):
    """token_id + token_secret → header Authorization PVEAPIToken."""
    fake_session = MagicMock()
    fake_session.headers = {}
    monkeypatch.setattr(proxmox_api.requests, "Session", lambda: fake_session)

    cfg = {"token_id": "user@pam!mytoken", "token_secret": "abc-def-123"}
    result = proxmox_api._auth_session(cfg, "https://h:8006/api2/json", "host")

    assert result is fake_session
    assert "Authorization" in fake_session.headers
    assert "PVEAPIToken=user@pam!mytoken=abc-def-123" in fake_session.headers["Authorization"]


def test_auth_session_sans_token_ni_password_renvoie_none(monkeypatch):
    """Pas de token ET pas de password → None (auth impossible)."""
    monkeypatch.setattr(proxmox_api.requests, "Session", MagicMock)
    cfg = {}  # vide
    assert proxmox_api._auth_session(cfg, "https://h:8006/api2/json", "host") is None


def test_auth_session_password_succes(monkeypatch):
    """Auth ticket+CSRF via password → session avec headers + cookies."""
    fake_session = MagicMock()
    fake_session.headers = {}
    fake_session.cookies = MagicMock()
    response_mock = MagicMock()
    response_mock.json.return_value = {"data": {"CSRFPreventionToken": "csrf-xyz", "ticket": "tkt-abc"}}
    response_mock.raise_for_status = MagicMock()
    fake_session.post.return_value = response_mock
    monkeypatch.setattr(proxmox_api.requests, "Session", lambda: fake_session)

    cfg = {"user": "root@pam", "password": "secret"}
    result = proxmox_api._auth_session(cfg, "https://h:8006/api2/json", "myhost")

    assert result is fake_session
    assert fake_session.headers.get("CSRFPreventionToken") == "csrf-xyz"
    fake_session.cookies.set.assert_called_once()


def test_auth_session_password_echec_renvoie_none(monkeypatch):
    """Si l'auth ticket lève une exception → None."""
    fake_session = MagicMock()
    fake_session.post.side_effect = ConnectionError("PVE down")
    monkeypatch.setattr(proxmox_api.requests, "Session", lambda: fake_session)

    cfg = {"user": "root", "password": "x"}
    assert proxmox_api._auth_session(cfg, "https://h:8006/api2/json", "host") is None


# ── fetch_state ───────────────────────────────────────────────────────────


def test_fetch_state_pas_de_config_renvoie_none(monkeypatch):
    """Si jarvis_pve.json absent → None."""
    _reset_cache()
    fake_path = MagicMock()
    fake_path.exists.return_value = False
    monkeypatch.setattr(proxmox_api, "PVE_CONFIG_PATH", fake_path)
    assert proxmox_api.fetch_state() is None


def test_fetch_state_cache_hit(monkeypatch):
    """Cache valide < TTL → retourne le cache sans appel HTTP."""
    proxmox_api._cache = {"ts": __import__("time").time(), "data": {"node": {"cpu": 0.5}}}
    # _auth_session ne doit PAS être appelé
    crash = MagicMock(side_effect=RuntimeError("ne devrait pas être appelé"))
    monkeypatch.setattr(proxmox_api, "_auth_session", crash)
    result = proxmox_api.fetch_state()
    assert result == {"node": {"cpu": 0.5}}


def test_fetch_state_auth_echoue_renvoie_none(monkeypatch, tmp_path):
    """Si _auth_session retourne None → fetch_state renvoie None."""
    _reset_cache()
    cfg_file = tmp_path / "pve.json"
    cfg_file.write_text(json.dumps({"host": "h", "node": "n"}))
    monkeypatch.setattr(proxmox_api, "PVE_CONFIG_PATH", cfg_file)
    monkeypatch.setattr(proxmox_api, "_auth_session", lambda *a, **k: None)
    assert proxmox_api.fetch_state() is None


def test_fetch_state_succes_remplit_cache(monkeypatch, tmp_path):
    """Auth OK + responses OK → state rempli + cache mis à jour."""
    _reset_cache()
    cfg_file = tmp_path / "pve.json"
    cfg_file.write_text(json.dumps({"host": "h", "node": "n", "token_id": "x", "token_secret": "y"}))
    monkeypatch.setattr(proxmox_api, "PVE_CONFIG_PATH", cfg_file)

    fake_session = MagicMock()

    def fake_get(url, timeout=5):
        resp = MagicMock()
        if "/status" in url:
            resp.json.return_value = {"data": {"cpu": 0.42, "memory": {"used": 8 * 1024**3, "total": 16 * 1024**3}, "uptime": 3600}}
        elif "/qemu" in url:
            resp.json.return_value = {"data": [{"vmid": 108, "name": "srv-ngix", "status": "running"}]}
        elif "/lxc" in url:
            resp.json.return_value = {"data": []}
        elif "/storage" in url:
            resp.json.return_value = {"data": [{"storage": "local", "active": 1, "total": 100, "used": 50}]}
        return resp

    fake_session.get = fake_get
    monkeypatch.setattr(proxmox_api, "_auth_session", lambda *a, **k: fake_session)

    state = proxmox_api.fetch_state()
    assert state is not None
    assert "node" in state
    assert state["vms"][0]["vmid"] == 108
    # Cache mis à jour
    assert proxmox_api._cache["data"] is state


def test_fetch_state_config_json_corrompu_renvoie_none(monkeypatch, tmp_path):
    """Fichier config JSON malformé → exception attrapée → None."""
    _reset_cache()
    cfg_file = tmp_path / "pve.json"
    cfg_file.write_text("not-valid-json{{{")
    monkeypatch.setattr(proxmox_api, "PVE_CONFIG_PATH", cfg_file)
    assert proxmox_api.fetch_state() is None


# ── context_summary ─────────────────────────────────────────────────────


def test_context_summary_state_vide_renvoie_juste_header():
    out = proxmox_api.context_summary({})
    assert "État Proxmox VE" in out


def test_context_summary_avec_node_formate_cpu_ram_uptime():
    state = {"node": {"cpu": 0.65, "memory": {"used": 8 * 1024**3, "total": 16 * 1024**3}, "uptime": 7200}}
    out = proxmox_api.context_summary(state)
    assert "65.0%" in out
    assert "8.0/16.0" in out
    assert "uptime 2h" in out


def test_context_summary_vm_running_avec_uptime():
    state = {"vms": [{"vmid": 108, "name": "srv-ngix", "status": "running",
                      "cpu": 0.1, "maxmem": 4 * 1024**3, "mem": 2 * 1024**3, "uptime": 86400}]}
    out = proxmox_api.context_summary(state)
    assert "VMs QEMU (1)" in out
    assert "VM108 srv-ngix" in out
    assert "running" in out
    assert "▶" in out


def test_context_summary_vm_stopped_icone_carre():
    state = {"vms": [{"vmid": 109, "name": "test", "status": "stopped", "maxmem": 0, "mem": 0}]}
    out = proxmox_api.context_summary(state)
    assert "■" in out
    assert "stopped" in out


def test_context_summary_lxc_listes():
    state = {"lxc": [{"vmid": 200, "name": "ct-test", "status": "running"}]}
    out = proxmox_api.context_summary(state)
    assert "Conteneurs LXC (1)" in out
    assert "CT200 ct-test" in out


def test_context_summary_storage_actif_seulement():
    """Storage non-actif (active=0) doit être skippé."""
    state = {"storage": [
        {"storage": "active-store", "active": 1, "total": 100 * 1024**3, "used": 50 * 1024**3},
        {"storage": "inactive-store", "active": 0, "total": 100, "used": 50},
    ]}
    out = proxmox_api.context_summary(state)
    assert "active-store" in out
    assert "inactive-store" not in out


def test_context_summary_vms_triees_par_vmid():
    """Les VMs sont triées par vmid croissant."""
    state = {"vms": [
        {"vmid": 200, "name": "z", "status": "stopped", "maxmem": 0, "mem": 0},
        {"vmid": 100, "name": "a", "status": "stopped", "maxmem": 0, "mem": 0},
    ]}
    out = proxmox_api.context_summary(state)
    pos_100 = out.find("VM100")
    pos_200 = out.find("VM200")
    assert pos_100 < pos_200


# ── chat_inject ─────────────────────────────────────────────────────────


def test_chat_inject_aucun_keyword_pas_d_injection(monkeypatch):
    """Sans keyword PVE → system prompt inchangé."""
    monkeypatch.setattr(proxmox_api, "fetch_state", lambda: {"node": {}})
    out = proxmox_api.chat_inject("SYS", "bonjour Marc")
    assert out == "SYS"


def test_chat_inject_keyword_proxmox_declenche_fetch(monkeypatch):
    """Mot-clé 'proxmox' → fetch_state appelé."""
    captured = {"called": False}

    def fake_fetch():
        captured["called"] = True
        return {"node": {"cpu": 0.5, "memory": {"used": 1024**3, "total": 2 * 1024**3}, "uptime": 3600}}

    monkeypatch.setattr(proxmox_api, "fetch_state", fake_fetch)
    out = proxmox_api.chat_inject("SYS", "état du proxmox")
    assert captured["called"] is True
    assert "État Proxmox VE" in out


def test_chat_inject_keyword_pve_declenche_aussi(monkeypatch):
    monkeypatch.setattr(proxmox_api, "fetch_state", lambda: {"node": {"cpu": 0, "memory": {"used": 0, "total": 1}, "uptime": 0}})
    out = proxmox_api.chat_inject("SYS", "liste des vms sur pve")
    assert "État Proxmox VE" in out


def test_chat_inject_keyword_mais_fetch_none_pas_d_injection(monkeypatch):
    """Si fetch_state retourne None → system inchangé (pas d'injection vide)."""
    monkeypatch.setattr(proxmox_api, "fetch_state", lambda: None)
    out = proxmox_api.chat_inject("SYS", "état proxmox")
    assert out == "SYS"


def test_chat_inject_case_insensitive(monkeypatch):
    """Détection PVE en majuscules → trigger."""
    monkeypatch.setattr(proxmox_api, "fetch_state", lambda: {"node": {"cpu": 0, "memory": {"used": 0, "total": 1}, "uptime": 0}})
    out = proxmox_api.chat_inject("SYS", "STATUT PROXMOX MAINTENANT")
    assert "État Proxmox VE" in out


def test_chat_inject_inclut_consigne_finale(monkeypatch):
    """L'injection ajoute la consigne 'Utilise ces données'."""
    monkeypatch.setattr(proxmox_api, "fetch_state", lambda: {"node": {"cpu": 0, "memory": {"used": 0, "total": 1}, "uptime": 0}})
    out = proxmox_api.chat_inject("SYS", "vm 108 status")
    assert "Utilise ces données" in out
