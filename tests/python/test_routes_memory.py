"""Tests routes HTTP memory — /api/memory* (Flask test_client).

Cible memory/routes.py (37% → cible ≥80%).
Stratégie : mock memory.store + tmp_path pour les fichiers.
"""
import json
import logging
from unittest.mock import patch

import memory.routes as mr
import memory.store as ms
import pytest
from flask import Flask
from memory import bp as memory_bp

_LOG = logging.getLogger("test.memory_routes")


@pytest.fixture
def app(tmp_path):
    a = Flask(__name__)
    a.testing = True
    mem_file = tmp_path / "memory.json"
    sum_file = tmp_path / "summary.json"
    cor_file = tmp_path / "corrections.md"
    mr.init_routes(
        get_memory_file      = lambda: mem_file,
        get_summary_file     = lambda: sum_file,
        summary_min_msgs     = 3,
        log                  = _LOG,
        get_corrections_file = lambda: cor_file,
    )
    # Initialise store avec des stubs minimaux
    ms.init(
        get_memory_file  = lambda: mem_file,
        get_summary_file = lambda: sum_file,
        get_model        = lambda: "phi4:14b",
        get_mode         = lambda: "soc",
        memory_limit     = 100,
        summary_keep     = 3,
        summary_min_msgs = 3,
        general_model    = "gemma4:latest",
        code_model       = "qwen2.5-coder:14b",
        ollama_url       = "http://ollama-test",
        ollama_circuit   = None,
        log              = _LOG,
    )
    a.register_blueprint(memory_bp)
    return a


@pytest.fixture
def client(app):
    return app.test_client()


# ── GET /api/memory ──────────────────────────────────────────────────────

def test_api_memory_get_liste_vide(client):
    with patch("memory.routes.store.load_memory", return_value=[]):
        rv = client.get("/api/memory")
    assert rv.status_code == 200
    assert json.loads(rv.data) == []


def test_api_memory_get_retourne_historique(client):
    history = [{"role": "user", "content": "bonjour"}]
    with patch("memory.routes.store.load_memory", return_value=history):
        rv = client.get("/api/memory")
    assert json.loads(rv.data) == history


# ── POST /api/memory ─────────────────────────────────────────────────────

def test_api_memory_save_ok(client):
    captured = {}
    def _save(h):
        captured["h"] = h
    with patch("memory.routes.store.save_memory", side_effect=_save):
        rv = client.post("/api/memory", json={"history": [{"role": "user", "content": "x"}]})
    assert rv.status_code == 200
    assert json.loads(rv.data)["ok"] is True
    assert len(captured["h"]) == 1


def test_api_memory_save_sans_body_ok(client):
    with patch("memory.routes.store.save_memory"):
        rv = client.post("/api/memory", json={})
    assert rv.status_code == 200


# ── DELETE /api/memory ───────────────────────────────────────────────────

def test_api_memory_clear_supprime_fichier(client, tmp_path):
    f = tmp_path / "memory.json"
    f.write_text("[]")
    mr._get_memory_file = lambda: f
    rv = client.delete("/api/memory")
    assert rv.status_code == 200
    assert not f.exists()


def test_api_memory_clear_fichier_absent_ok(client, tmp_path):
    mr._get_memory_file = lambda: tmp_path / "ghost.json"
    rv = client.delete("/api/memory")
    assert rv.status_code == 200
    assert json.loads(rv.data)["ok"] is True


# ── GET /api/memory-summary ──────────────────────────────────────────────

def test_api_memory_summary_get_fichier_absent(client, tmp_path):
    mr._get_summary_file = lambda: tmp_path / "ghost_summary.json"
    rv = client.get("/api/memory-summary")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["summaries"] == []


def test_api_memory_summary_get_retourne_summaries(client, tmp_path):
    f = tmp_path / "summary.json"
    f.write_text(json.dumps({"summaries": ["résumé 1", "résumé 2"]}))
    mr._get_summary_file = lambda: f
    rv = client.get("/api/memory-summary")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert len(data["summaries"]) == 2


# ── DELETE /api/memory-summary ───────────────────────────────────────────

def test_api_memory_summary_clear_supprime_fichier(client, tmp_path):
    f = tmp_path / "summary.json"
    f.write_text("{}")
    mr._get_summary_file = lambda: f
    rv = client.delete("/api/memory-summary")
    assert rv.status_code == 200
    assert not f.exists()


def test_api_memory_summary_clear_fichier_absent_ok(client, tmp_path):
    mr._get_summary_file = lambda: tmp_path / "ghost.json"
    rv = client.delete("/api/memory-summary")
    assert rv.status_code == 200


# ── GET /api/memory/stats ────────────────────────────────────────────────

def test_api_memory_stats_fichiers_absents(client, tmp_path):
    mr._get_memory_file      = lambda: tmp_path / "ghost_mem.json"
    mr._get_summary_file     = lambda: tmp_path / "ghost_sum.json"
    mr._get_corrections_file = lambda: tmp_path / "ghost_cor.md"
    rv = client.get("/api/memory/stats")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["count"] == 0
    assert data["size_kb"] == 0.0
    assert data["summary_count"] == 0


def test_api_memory_stats_avec_fichiers(client, tmp_path):
    mem_f = tmp_path / "memory.json"
    sum_f = tmp_path / "summary.json"
    cor_f = tmp_path / "corrections.md"
    mem_f.write_text(json.dumps([{"role": "user"}, {"role": "assistant"}]), encoding="utf-8")
    sum_f.write_text(json.dumps({"summaries": ["s1", "s2", "s3"]}), encoding="utf-8")
    # 3 sections "## " → 2 occurrences de "\n## " → lessons_count=2
    cor_f.write_text("## leçon 1\n## leçon 2\n## leçon 3\n", encoding="utf-8")
    mr._get_memory_file      = lambda: mem_f
    mr._get_summary_file     = lambda: sum_f
    mr._get_corrections_file = lambda: cor_f
    rv = client.get("/api/memory/stats")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["count"] == 2
    assert data["summary_count"] == 3
    assert data["lessons_count"] == 2


def test_api_memory_stats_sans_corrections_file(client, tmp_path):
    """_get_corrections_file=None → lessons_count=0, pas de crash."""
    mr._get_corrections_file = None
    mr._get_memory_file  = lambda: tmp_path / "ghost.json"
    mr._get_summary_file = lambda: tmp_path / "ghost.json"
    rv = client.get("/api/memory/stats")
    assert rv.status_code == 200
    assert json.loads(rv.data)["lessons_count"] == 0


# ── POST /api/memory/summarize-session ───────────────────────────────────

def test_api_memory_summarize_pas_assez_messages(client):
    with patch("memory.routes.store.load_memory", return_value=[{"role": "user"}]):
        rv = client.post("/api/memory/summarize-session")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is False
    assert data["reason"] == "not_enough_messages"


def test_api_memory_summarize_succes(client):
    msgs = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
    with patch("memory.routes.store.load_memory", return_value=msgs), \
         patch("memory.routes.store._summarize_messages", return_value="résumé test"), \
         patch("memory.routes.store._append_memory_summary"):
        rv = client.post("/api/memory/summarize-session")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True
    assert data["messages"] == 5


def test_api_memory_summarize_llm_timeout_fallback(client):
    """LLM timeout → fallback extrait brut (résumé non-vide, ok=True)."""
    msgs = [{"role": "user", "content": f"bonjour {i}"} for i in range(5)]
    with patch("memory.routes.store.load_memory", return_value=msgs), \
         patch("memory.routes.store._summarize_messages", return_value=""), \
         patch("memory.routes.store._append_memory_summary") as m_app:
        rv = client.post("/api/memory/summarize-session")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True
    m_app.assert_called_once()
