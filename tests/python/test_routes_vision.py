"""Tests routes HTTP vision — /api/vision (Flask test_client).

Cible vision/routes.py (45% → cible ≥80%).
Stratégie : mock llava.stream_pipeline / stream_direct → pas de connexion Ollama.
"""
import json
from unittest.mock import patch

import pytest
import vision.routes as vr
from flask import Flask
from vision import bp as vision_bp


def _fake_stream(tokens):
    for tok in tokens:
        yield f"data: {json.dumps({'type': 'token', 'token': tok, 'done': False})}\n\n"
    yield f"data: {json.dumps({'type': 'token', 'token': '', 'done': True})}\n\n"


@pytest.fixture
def app():
    a = Flask(__name__)
    a.testing = True
    vr.init_routes(
        ollama_url="http://ollama-test",
        vision_timeout_s=5,
        sse_headers={"X-Accel-Buffering": "no"},
        rag_inject_fn=lambda sys_prompt, q: sys_prompt,
    )
    a.register_blueprint(vision_bp)
    return a


@pytest.fixture
def client(app):
    return app.test_client()


# ── Validation entrée ────────────────────────────────────────────────────

def test_api_vision_image_b64_manquante(client):
    rv = client.post("/api/vision", json={})
    assert rv.status_code == 400
    assert b"image_b64 manquante" in rv.data


def test_api_vision_mime_invalide_rejete(client):
    rv = client.post("/api/vision", json={"image_b64": "data:application/pdf;base64,abc"})
    assert rv.status_code == 400
    assert b"non support" in rv.data


def test_api_vision_mime_application_octet_rejete(client):
    rv = client.post("/api/vision", json={"image_b64": "data:application/octet-stream,abc"})
    assert rv.status_code == 400


# ── Pipeline true (défaut) ───────────────────────────────────────────────

def test_api_vision_pipeline_true_appelle_stream_pipeline(client):
    with patch("vision.routes.llava.stream_pipeline", return_value=_fake_stream(["ok"])) as m:
        rv = client.post("/api/vision", json={"image_b64": "abc123", "pipeline": True})
    assert rv.status_code == 200
    assert rv.content_type.startswith("text/event-stream")
    m.assert_called_once()


def test_api_vision_pipeline_defaut_est_true(client):
    """Sans clé 'pipeline', la valeur par défaut est True → stream_pipeline."""
    with patch("vision.routes.llava.stream_pipeline", return_value=_fake_stream(["x"])) as m:
        client.post("/api/vision", json={"image_b64": "abc123"})
    m.assert_called_once()


def test_api_vision_prompt_vide_utilise_message_defaut(client):
    captured = {}
    def _fake(url, b64, sys_p, q, timeout):
        captured["q"] = q
        return _fake_stream(["ok"])
    with patch("vision.routes.llava.stream_pipeline", side_effect=_fake):
        client.post("/api/vision", json={"image_b64": "abc123"})
    assert "Analyse" in captured["q"]


def test_api_vision_prompt_personnalise_transmis(client):
    captured = {}
    def _fake(url, b64, sys_p, q, timeout):
        captured["q"] = q
        return _fake_stream(["ok"])
    with patch("vision.routes.llava.stream_pipeline", side_effect=_fake):
        client.post("/api/vision", json={"image_b64": "abc", "prompt": "décrire le chat"})
    assert captured["q"] == "décrire le chat"


# ── Pipeline false ───────────────────────────────────────────────────────

def test_api_vision_pipeline_false_appelle_stream_direct(client):
    with patch("vision.routes.llava.stream_direct", return_value=_fake_stream(["ok"])) as m:
        rv = client.post("/api/vision", json={"image_b64": "abc123", "pipeline": False})
    assert rv.status_code == 200
    m.assert_called_once()


# ── Data URI avec MIME valide ────────────────────────────────────────────

def test_api_vision_data_uri_jpeg_accepte(client):
    with patch("vision.routes.llava.stream_pipeline", return_value=_fake_stream(["x"])):
        rv = client.post("/api/vision", json={"image_b64": "data:image/jpeg;base64,abc"})
    assert rv.status_code == 200


def test_api_vision_data_uri_png_accepte(client):
    with patch("vision.routes.llava.stream_pipeline", return_value=_fake_stream(["x"])):
        rv = client.post("/api/vision", json={"image_b64": "data:image/png;base64,abc"})
    assert rv.status_code == 200


def test_api_vision_data_uri_webp_accepte(client):
    with patch("vision.routes.llava.stream_pipeline", return_value=_fake_stream(["x"])):
        rv = client.post("/api/vision", json={"image_b64": "data:image/webp;base64,abc"})
    assert rv.status_code == 200


def test_api_vision_rag_inject_fn_appelee_avec_system(client):
    """rag_inject_fn est appelée avec le system prompt par défaut."""
    captured = {}
    def _rag(sys_p, q):
        captured["sys"] = sys_p
        return sys_p
    vr._rag_inject_fn = _rag
    with patch("vision.routes.llava.stream_pipeline", return_value=_fake_stream(["ok"])):
        client.post("/api/vision", json={"image_b64": "abc"})
    assert captured.get("sys") is not None
