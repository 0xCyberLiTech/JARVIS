"""Tests mode/routes — /api/mode GET + POST (étape 37).

Couvre la nouvelle tuile mode/ : validation des 4 modes valides,
swap VRAM uniquement si mode différent, GET retourne {mode, model}.
"""
import json
from unittest.mock import MagicMock

import pytest
from flask import Flask
from mode import bp as mode_bp
from mode import routes as mode_routes


@pytest.fixture
def client():
    """Flask app de test avec la tuile mode/ câblée + DI minimale."""
    app = Flask(__name__)
    app.register_blueprint(mode_bp)

    state = {"mode": "soc"}
    ensure_vram_calls = []

    mode_routes.init(
        limiter=MagicMock(limit=lambda s: lambda fn: fn),  # no-op limiter
        log=MagicMock(),
        get_jarvis_mode=lambda: state["mode"],
        set_jarvis_mode=lambda v: state.update({"mode": v}),
        get_model=lambda: "phi4:14b",
        general_model="gemma4:latest",
        code_model="qwen2.5-coder:14b",
        code_reasoning_model="qwen3:8b",
        ensure_vram=lambda m: ensure_vram_calls.append(m),
    )
    return app.test_client(), state, ensure_vram_calls


# ── GET /api/mode ──────────────────────────────────────────────────────────


def test_get_mode_soc_renvoie_phi4(client):
    """Mode SOC par défaut → model = MODEL (phi4:14b)."""
    cli, state, _ = client
    state["mode"] = "soc"
    r = cli.get("/api/mode")
    assert r.status_code == 200
    d = json.loads(r.data)
    assert d == {"mode": "soc", "model": "phi4:14b"}


def test_get_mode_general_renvoie_gemma4(client):
    cli, state, _ = client
    state["mode"] = "general"
    r = cli.get("/api/mode")
    d = json.loads(r.data)
    assert d == {"mode": "general", "model": "gemma4:latest"}


def test_get_mode_code_renvoie_qwen_coder(client):
    cli, state, _ = client
    state["mode"] = "code"
    r = cli.get("/api/mode")
    d = json.loads(r.data)
    assert d == {"mode": "code", "model": "qwen2.5-coder:14b"}


def test_get_mode_code_reasoning_renvoie_qwen3(client):
    cli, state, _ = client
    state["mode"] = "code_reasoning"
    r = cli.get("/api/mode")
    d = json.loads(r.data)
    assert d == {"mode": "code_reasoning", "model": "qwen3:8b"}


# ── POST /api/mode ─────────────────────────────────────────────────────────


def test_post_mode_valide_change_et_swap_vram(client):
    """POST mode valide différent → set_jarvis_mode + ensure_vram appelé."""
    cli, state, ensure_calls = client
    state["mode"] = "soc"
    r = cli.post("/api/mode", json={"mode": "code"})
    assert r.status_code == 200
    d = json.loads(r.data)
    assert d == {"mode": "code", "model": "qwen2.5-coder:14b"}
    assert state["mode"] == "code"
    assert ensure_calls == ["qwen2.5-coder:14b"]


def test_post_mode_identique_pas_de_swap(client):
    """POST même mode que courant → pas de ensure_vram (économie VRAM)."""
    cli, state, ensure_calls = client
    state["mode"] = "soc"
    r = cli.post("/api/mode", json={"mode": "soc"})
    assert r.status_code == 200
    assert ensure_calls == []  # pas de swap


def test_post_mode_invalide_renvoie_400(client):
    """Mode inconnu → 400 avec message erreur, pas de modification."""
    cli, state, ensure_calls = client
    state["mode"] = "soc"
    r = cli.post("/api/mode", json={"mode": "invalid"})
    assert r.status_code == 400
    d = json.loads(r.data)
    assert "mode invalide" in d["error"]
    assert state["mode"] == "soc"  # inchangé
    assert ensure_calls == []      # pas de swap


def test_post_mode_case_insensitive(client):
    """Mode en majuscules → normalisé en lowercase."""
    cli, state, _ = client
    state["mode"] = "soc"
    r = cli.post("/api/mode", json={"mode": "CODE"})
    assert r.status_code == 200
    assert state["mode"] == "code"


def test_post_mode_vide_renvoie_400(client):
    """Mode absent ('') → 400 invalide."""
    cli, state, _ = client
    r = cli.post("/api/mode", json={})
    assert r.status_code == 400


def test_post_mode_log_transition(client):
    """Switch mode → log info '[JARVIS] Mode X → Y'."""
    cli, state, _ = client
    state["mode"] = "general"
    cli.post("/api/mode", json={"mode": "code"})
    log_msg = mode_routes._log.info.call_args[0][0]
    assert "Mode general" in log_msg
    assert "code" in log_msg


def test_post_all_4_modes_acceptes(client):
    """Les 4 modes valides sont tous acceptés."""
    cli, _, _ = client
    for m in ("soc", "general", "code", "code_reasoning"):
        r = cli.post("/api/mode", json={"mode": m})
        assert r.status_code == 200, f"Mode {m} refusé"
