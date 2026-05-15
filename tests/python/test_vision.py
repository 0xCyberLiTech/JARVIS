"""Tests vision — analyse image gemma4 (mock requests.post pour streaming SSE)."""
import json
from unittest.mock import MagicMock, patch

import vision
from vision import (
    DEFAULT_PIPELINE_SYSTEM,
    DEFAULT_TEMPERATURE,
    MODEL,
    stream_direct,
    stream_pipeline,
)


def _make_mock_response(chunks_text):
    """Construit un mock de Response Ollama streaming."""
    # Chaque ligne est un JSON {message:{content:...}, done:bool}
    lines = []
    for i, t in enumerate(chunks_text):
        is_last = i == len(chunks_text) - 1
        lines.append(json.dumps({
            "message": {"content": t}, "done": is_last,
        }).encode())

    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter(lines)
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


# ── Constantes ───────────────────────────────────────────────────────────


def test_model_est_gemma4_latest():
    assert MODEL == "gemma4:latest"


def test_default_temperature_est_03():
    assert DEFAULT_TEMPERATURE == 0.3


def test_default_pipeline_system_mentionne_jarvis_et_image():
    assert "JARVIS" in DEFAULT_PIPELINE_SYSTEM
    assert "image" in DEFAULT_PIPELINE_SYSTEM.lower()


def test_module_logger():
    assert vision._log.name == "jarvis.vision"


# ── stream_direct — happy path ───────────────────────────────────────────


def test_stream_direct_yield_tokens_puis_speak():
    mock_resp = _make_mock_response(["bonjour ", "Marc"])
    with patch("vision.requests.post", return_value=mock_resp):
        events = list(stream_direct("http://localhost:11434", "abc", "test", timeout=10))
    # 2 tokens + 1 speak
    assert len(events) == 3
    p1 = json.loads(events[0].replace("data: ", "").strip())
    assert p1["type"] == "token"
    assert p1["token"] == "bonjour "
    p3 = json.loads(events[2].replace("data: ", "").strip())
    assert p3["type"] == "speak"
    assert p3["text"] == "bonjour Marc"


def test_stream_direct_skip_lignes_vides():
    """`if not line: continue` → lignes vides ignorées."""
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter([
        b"",
        json.dumps({"message": {"content": "ok"}, "done": True}).encode(),
        b"",
    ])
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("vision.requests.post", return_value=mock_resp):
        events = list(stream_direct("u", "img", "p", timeout=5))
    # 1 token + 1 speak (lignes vides skip)
    assert len(events) == 2


def test_stream_direct_token_vide_pas_yield():
    """`if token:` → empty content skip."""
    mock_resp = _make_mock_response(["", "ok"])  # 1er token vide
    with patch("vision.requests.post", return_value=mock_resp):
        events = list(stream_direct("u", "img", "p", timeout=5))
    # 1 token (le vide skip) + 1 speak
    assert len(events) == 2


def test_stream_direct_prompt_vide_utilise_default():
    """prompt='' → 'Décris cette image en détail en français.'"""
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["payload"] = json
        return _make_mock_response(["x"])

    with patch("vision.requests.post", side_effect=fake_post):
        list(stream_direct("u", "img", "", timeout=5))
    user_msg = captured["payload"]["messages"][0]
    assert user_msg["role"] == "user"
    assert "Décris cette image en détail" in user_msg["content"]
    assert user_msg["images"] == ["img"]


def test_stream_direct_payload_contient_modele_et_options():
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["payload"] = json
        return _make_mock_response(["x"])

    with patch("vision.requests.post", side_effect=fake_post):
        list(stream_direct("u", "img", "test", timeout=5))
    assert captured["payload"]["model"] == "gemma4:latest"
    assert captured["payload"]["stream"] is True
    assert captured["payload"]["options"]["temperature"] == 0.3


# ── stream_direct — erreurs ──────────────────────────────────────────────


def test_stream_direct_connexion_ollama_echoue_yield_erreur():
    """requests.post lève → token d'erreur "Erreur connexion Ollama"."""
    with patch("vision.requests.post", side_effect=ConnectionError("refused")):
        events = list(stream_direct("u", "img", "p", timeout=5))
    assert len(events) == 1
    p = json.loads(events[0].replace("data: ", "").strip())
    assert p["type"] == "token"
    assert p["done"] is True
    assert "Erreur connexion Ollama (vision)" in p["token"]
    assert "refused" in p["token"]


def test_stream_direct_streaming_ligne_invalide_yield_erreur():
    """Si une ligne JSON invalide arrive, le try interne yield l'erreur."""
    mock_resp = MagicMock()
    mock_resp.iter_lines.return_value = iter([b"not-json"])
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("vision.requests.post", return_value=mock_resp):
        events = list(stream_direct("u", "img", "p", timeout=5))
    assert any("Erreur gemma4 vision" in e for e in events)


def test_stream_direct_pas_de_speak_si_full_text_vide():
    """Si aucun token reçu → pas de speak final."""
    mock_resp = _make_mock_response([])  # aucun chunk
    mock_resp.iter_lines.return_value = iter([])  # override pour vraiment vide
    with patch("vision.requests.post", return_value=mock_resp):
        events = list(stream_direct("u", "img", "p", timeout=5))
    assert events == []


def test_stream_direct_speak_tronque_a_500_chars():
    """full_text[:500] → tronqué à 500."""
    long = "X" * 1000
    mock_resp = _make_mock_response([long])
    with patch("vision.requests.post", return_value=mock_resp):
        events = list(stream_direct("u", "img", "p", timeout=5))
    speak = json.loads(events[-1].replace("data: ", "").strip())
    assert len(speak["text"]) == 500


# ── stream_pipeline ──────────────────────────────────────────────────────


def test_stream_pipeline_inclut_system_et_user_messages():
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["payload"] = json
        return _make_mock_response(["x"])

    with patch("vision.requests.post", side_effect=fake_post):
        list(stream_pipeline("u", "img", "SYSTEM_TEXT", "ma question", timeout=5))
    msgs = captured["payload"]["messages"]
    assert msgs[0] == {"role": "system", "content": "SYSTEM_TEXT"}
    assert msgs[1]["role"] == "user"
    assert msgs[1]["content"] == "ma question"
    assert msgs[1]["images"] == ["img"]


def test_stream_pipeline_speak_tronque_a_600_chars():
    """Pipeline tronque à 600 (au lieu de 500 pour direct)."""
    long = "Y" * 1000
    mock_resp = _make_mock_response([long])
    with patch("vision.requests.post", return_value=mock_resp):
        events = list(stream_pipeline("u", "img", "SYS", "q", timeout=5))
    speak = json.loads(events[-1].replace("data: ", "").strip())
    assert len(speak["text"]) == 600


def test_stream_pipeline_erreur_connexion():
    with patch("vision.requests.post", side_effect=ConnectionError("down")):
        events = list(stream_pipeline("u", "img", "SYS", "q", timeout=5))
    p = json.loads(events[0].replace("data: ", "").strip())
    assert "Erreur pipeline vision" in p["token"]


def test_stream_pipeline_endpoint_api_chat():
    """Vérifie que l'URL pointe bien sur /api/chat."""
    captured = {}

    def fake_post(url, json=None, **kwargs):
        captured["url"] = url
        return _make_mock_response(["x"])

    with patch("vision.requests.post", side_effect=fake_post):
        list(stream_pipeline("http://ollama-host", "img", "S", "Q", timeout=5))
    assert captured["url"] == "http://ollama-host/api/chat"
