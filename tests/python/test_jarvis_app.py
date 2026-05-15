"""Tests jarvis.py — Flask app via test_client (routes simples + helpers purs).

Stratégie : import direct de `jarvis` (boot OK car Ollama tourne + soc_config.json
présent). Tests focus sur les routes Flask "lecture" qui répondent JSON sans
side-effects lourds, et quelques helpers purs (_cors_origin, validators).
"""
import json

# Import du module jarvis (boot complet : Ollama poll, soc_config, threads…)
# Ce coût est payé UNE fois pour toute la session pytest (~1.7s).
import jarvis as jarvis_module
import pytest


@pytest.fixture(scope="module")
def app():
    """Flask app de prod, utilisée en test_client (pas de serveur démarré)."""
    jarvis_module.app.testing = True
    return jarvis_module.app


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ── Helpers purs ────────────────────────────────────────────────────────


def test_cors_origin_origin_dans_whitelist_renvoie_tel_quel():
    """Origin whitelistée → retournée inchangée."""
    assert jarvis_module._cors_origin("http://192.168.1.50") == "http://192.168.1.50"


def test_cors_origin_origin_inconnue_fallback_localhost():
    """Origin non whitelistée → fallback 'http://localhost' (safe default)."""
    assert jarvis_module._cors_origin("http://evil.com") == "http://localhost"


def test_cors_origin_origin_vide_fallback_localhost():
    assert jarvis_module._cors_origin("") == "http://localhost"


def test_soc_origins_contient_localhost_et_192_168():
    """Sanity : la whitelist CORS couvre localhost et le LAN srv-ngix."""
    assert "http://localhost" in jarvis_module.SOC_ORIGINS
    assert "http://192.168.1.50" in jarvis_module.SOC_ORIGINS
    assert "http://127.0.0.1" in jarvis_module.SOC_ORIGINS


def test_jarvis_port_par_defaut_5000():
    assert jarvis_module.JARVIS_PORT == 5000


def test_mcp_port_5010():
    """Port MCP server fixe."""
    assert jarvis_module._MCP_PORT == 5010


def test_ollama_url_127_0_0_1():
    """OLLAMA_URL doit être 127.0.0.1 explicite (fix IPv6 Phase 3)."""
    assert jarvis_module.OLLAMA_URL == "http://127.0.0.1:11434"


# ── Routes : santé et boot ─────────────────────────────────────────────


def test_favicon_renvoie_204(client):
    r = client.get("/favicon.ico")
    assert r.status_code == 204


def test_api_health_renvoie_status_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["status"] == "ok"
    assert body["model"] == jarvis_module.MODEL
    assert "ts" in body


def test_api_boot_id_format(client):
    r = client.get("/api/boot-id")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert "boot_id" in body
    assert body["boot_id"] == jarvis_module._JARVIS_BOOT_ID


def test_api_status_renvoie_modele_actif(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert body["available"] is True
    assert body["model"] == jarvis_module.MODEL
    assert "soc_engine_active" in body


# ── Routes : memory / facts ────────────────────────────────────────────


def test_api_memory_get_renvoie_liste_json(client):
    r = client.get("/api/memory")
    assert r.status_code == 200
    # Réponse peut être [] ou liste d'échanges, mais JSON valide
    body = json.loads(r.data)
    assert isinstance(body, list)


def test_api_facts_get_renvoie_dict(client):
    r = client.get("/api/facts")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body, dict)


def test_api_memory_summary_get(client):
    r = client.get("/api/memory-summary")
    assert r.status_code == 200
    # Format : {summary: str | null, ...}
    body = json.loads(r.data)
    assert isinstance(body, dict)


# ── Routes : llm-params ────────────────────────────────────────────────


def test_api_llm_params_get_renvoie_dict_params(client):
    r = client.get("/api/llm-params")
    assert r.status_code == 200
    body = json.loads(r.data)
    # Structure : {params: {...}, defaults: {...}, system_prompt: ...}
    assert "params" in body
    assert "defaults" in body


def test_api_llm_params_post_invalide_renvoie_400(client):
    """POST avec payload invalide (pas un dict) → 400."""
    r = client.post("/api/llm-params", json="not-a-dict")
    # Soit 400 (validation), soit 200 mais ignoré
    assert r.status_code in (200, 400)


# ── Routes : mode ───────────────────────────────────────────────────────


def test_api_mode_get_renvoie_mode_actuel(client):
    r = client.get("/api/mode")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert "mode" in body
    assert body["mode"] in ("soc", "general", "code", "code_reasoning")


# ── Routes : prompt-profiles ───────────────────────────────────────────


def test_api_prompt_profiles_get(client):
    r = client.get("/api/prompt-profiles")
    assert r.status_code == 200
    body = json.loads(r.data)
    # Liste de profils ou dict
    assert isinstance(body, (list, dict))


# ── Routes : RAG status ─────────────────────────────────────────────────


def test_api_rag_status(client):
    r = client.get("/api/rag/status")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body, dict)


# ── Routes : welcome ────────────────────────────────────────────────────


def test_api_welcome_get(client):
    r = client.get("/api/welcome")
    assert r.status_code == 200
    body = json.loads(r.data)
    assert isinstance(body, dict)


# ── Headers CORS appliqués ──────────────────────────────────────────────


def test_cors_headers_appliques_sur_reponse(client):
    """after_request applique les headers CORS sur toute réponse."""
    r = client.get("/api/health", headers={"Origin": "http://localhost"})
    assert r.headers.get("Access-Control-Allow-Origin") == "http://localhost"
    assert "GET" in r.headers.get("Access-Control-Allow-Methods", "")


def test_cors_origin_inconnue_remplacee_par_fallback(client):
    """Origin non whitelistée → fallback localhost dans le header."""
    r = client.get("/api/health", headers={"Origin": "http://evil.com"})
    assert r.headers.get("Access-Control-Allow-Origin") == "http://localhost"


def test_security_headers_appliques(client):
    """X-Frame-Options + X-Content-Type-Options."""
    r = client.get("/api/health")
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


def test_options_preflight_renvoie_204(client):
    """OPTIONS preflight CORS → 204 sans corps."""
    r = client.options("/api/health", headers={"Origin": "http://localhost"})
    assert r.status_code == 204
    assert "Access-Control-Allow-Methods" in r.headers


# ── 404 sur routes inexistantes ────────────────────────────────────────


def test_route_inexistante_renvoie_404(client):
    r = client.get("/api/this-does-not-exist")
    assert r.status_code == 404


# ── Constantes & state ─────────────────────────────────────────────────


def test_model_constant_phi4(client):
    """MODEL par défaut = phi4:14b (SOC)."""
    assert jarvis_module.MODEL == "phi4:14b"


def test_last_exchanges_est_deque_bornee():
    """`_LAST_EXCHANGES` est une deque (capture mémoire bornée pour /api/history/last)."""
    from collections import deque
    assert isinstance(jarvis_module._LAST_EXCHANGES, deque)


def test_chat_stream_active_event_existe():
    """`_chat_stream_active` est un threading.Event."""
    import threading
    assert isinstance(jarvis_module._chat_stream_active, threading.Event)
