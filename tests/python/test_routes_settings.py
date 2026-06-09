"""Tests routes HTTP settings — /api/llm-params, /api/prompt-profiles, /api/welcome (Flask test_client).

Cible settings/routes.py (44% → cible ≥55%).
Stratégie : stubs minimaux pour les 25 DI, tmp_path pour les fichiers JSON.
Couvre les routes CRUD simples ; évite api_welcome_evolve/api_model_test (Ollama live).
"""
import json
import logging
import threading
from unittest.mock import MagicMock

import pytest
import settings.routes as sr
from flask import Flask
from settings import bp as settings_bp

_LOG = logging.getLogger("test.settings_routes")


@pytest.fixture
def app(tmp_path):
    a = Flask(__name__)
    a.testing = True

    llm_params   = {"temperature": 0.7, "num_ctx": 4096, "num_predict": 512}
    sys_prompt   = ["Prompt initial"]   # liste mutable pour setter
    model_state  = ["phi4:14b"]
    dsp_params   = {"bass": 0.5, "reverb": 0.3}
    welcome_data = {"lines": ["Bonjour Marc"], "last_updated": "2026-01-01"}

    llm_params_f    = tmp_path / "llm_params.json"
    prompt_f        = tmp_path / "prompt.txt"
    profiles_f      = tmp_path / "profiles.json"
    welcome_f       = tmp_path / "welcome.json"
    dsp_f           = tmp_path / "dsp.json"

    llm_params_f.write_text(json.dumps(llm_params))
    prompt_f.write_text(sys_prompt[0])
    welcome_f.write_text(json.dumps(welcome_data))
    dsp_f.write_text(json.dumps(dsp_params))

    sr.init_routes(
        log                          = _LOG,
        ollama_circuit               = MagicMock(),
        ollama_url                   = "http://ollama-test",
        ollama_tool_detect_timeout_s = 5,
        dsp_max_bytes                = 50_000_000,
        get_llm_params               = lambda: llm_params,
        get_system_prompt            = lambda: sys_prompt[0],
        get_model                    = lambda: model_state[0],
        get_models                   = lambda: [],
        get_dsp_params               = lambda: dsp_params,
        get_welcome_data             = lambda: dict(welcome_data),
        get_auto_profile_model       = lambda: None,
        set_system_prompt            = lambda v: sys_prompt.__setitem__(0, v),
        set_model                    = lambda v: model_state.__setitem__(0, v),
        set_dsp_params               = lambda v: dsp_params.update(v),
        set_welcome_data             = lambda v: welcome_data.update(v),
        reset_welcome                = lambda: welcome_data.update({"lines": ["Reset"]}),
        save_model_fn                = lambda: None,
        set_auto_profile_model       = lambda v: None,
        llm_defaults                 = {"temperature": 0.7},
        default_system_prompt        = "Prompt par défaut",
        llm_params_file              = llm_params_f,
        prompt_file                  = prompt_f,
        prompt_profiles_file         = profiles_f,
        welcome_file                 = welcome_f,
        default_welcome              = {"lines": ["Défaut"]},
        dsp_params_file              = dsp_f,
        dsp_safe_str                 = lambda v: str(v),
        dsp_bounds                   = {},
        model_lock                   = threading.Lock(),
        get_model_profile_fn         = lambda: None,
        fetch_ollama_models_fn       = lambda: [],
        apply_dsp_to_mp3_fn          = MagicMock(),
    )
    a.register_blueprint(settings_bp)
    return a


@pytest.fixture
def client(app):
    return app.test_client()


# ── GET /api/llm-params ──────────────────────────────────────────────────

def test_api_llm_params_get_retourne_params(client):
    rv = client.get("/api/llm-params")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert "params" in data
    assert "defaults" in data
    assert "system_prompt" in data


# ── POST /api/llm-params ─────────────────────────────────────────────────

def test_api_llm_params_set_met_a_jour_params(client, tmp_path):
    rv = client.post("/api/llm-params", json={"params": {"temperature": 0.9}})
    assert rv.status_code == 200
    assert json.loads(rv.data)["ok"] is True


def test_api_llm_params_set_met_a_jour_system_prompt(client):
    rv = client.post("/api/llm-params", json={"system_prompt": "Nouveau prompt"})
    assert rv.status_code == 200
    assert json.loads(rv.data)["ok"] is True


def test_api_llm_params_set_sans_body_ok(client):
    rv = client.post("/api/llm-params", json={})
    assert rv.status_code == 200


# ── POST /api/llm-params/reset-prompt ────────────────────────────────────

def test_api_reset_prompt_retourne_prompt_defaut(client):
    rv = client.post("/api/llm-params/reset-prompt")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True
    assert "system_prompt" in data


# ── GET /api/prompt-profiles ─────────────────────────────────────────────

def test_api_prompt_profiles_get_vide(client):
    rv = client.get("/api/prompt-profiles")
    assert rv.status_code == 200
    assert json.loads(rv.data) == {}


def test_api_prompt_profiles_get_fichier_existant(client, tmp_path):
    sr._prompt_profiles_file = tmp_path / "p.json"
    sr._prompt_profiles_file.write_text(json.dumps({"soc": {"content": "x"}}))
    rv = client.get("/api/prompt-profiles")
    assert rv.status_code == 200
    assert "soc" in json.loads(rv.data)


# ── POST /api/prompt-profiles ────────────────────────────────────────────

def test_api_prompt_profiles_save_name_manquant_400(client):
    rv = client.post("/api/prompt-profiles", json={"content": "x"})
    assert rv.status_code == 400
    assert b"name required" in rv.data


def test_api_prompt_profiles_save_ok(client):
    rv = client.post("/api/prompt-profiles", json={"name": "soc", "content": "Prompt SOC"})
    assert rv.status_code == 200
    assert json.loads(rv.data)["ok"] is True
    profiles = json.loads(client.get("/api/prompt-profiles").data)
    assert "soc" in profiles
    assert profiles["soc"]["content"] == "Prompt SOC"


def test_api_prompt_profiles_save_avec_locked_provider(client):
    rv = client.post("/api/prompt-profiles", json={
        "name": "code", "content": "Prompt code", "locked_provider": "qwen2.5-coder:14b"
    })
    assert rv.status_code == 200
    profiles = json.loads(client.get("/api/prompt-profiles").data)
    assert profiles["code"]["locked_provider"] == "qwen2.5-coder:14b"


# ── DELETE /api/prompt-profiles/<name> ───────────────────────────────────

def test_api_prompt_profiles_delete_ok(client):
    client.post("/api/prompt-profiles", json={"name": "soc", "content": "x"})
    rv = client.delete("/api/prompt-profiles/soc")
    assert rv.status_code == 200
    profiles = json.loads(client.get("/api/prompt-profiles").data)
    assert "soc" not in profiles


def test_api_prompt_profiles_delete_inexistant_ok(client):
    rv = client.delete("/api/prompt-profiles/ghost")
    assert rv.status_code == 200


# ── GET/POST /api/welcome ────────────────────────────────────────────────

def test_api_welcome_get(client):
    rv = client.get("/api/welcome")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert "lines" in data


def test_api_welcome_post_met_a_jour(client):
    rv = client.post("/api/welcome", json={"lines": ["Bonsoir Marc"]})
    assert rv.status_code == 200
    assert json.loads(rv.data)["ok"] is True


# ── POST /api/welcome/reset ───────────────────────────────────────────────

def test_api_welcome_reset_ok(client):
    rv = client.post("/api/welcome/reset")
    assert rv.status_code == 200
    assert json.loads(rv.data)["ok"] is True
