"""Tests routes HTTP RAG — /api/rag/* (Flask test_client).

Cible rag/routes.py (38% → cible ≥80%).
Stratégie : mock rag.engine pour éviter l'initialisation vectorielle.
"""
import json
import logging
from unittest.mock import patch

import pytest
import rag.routes as rr
from flask import Flask
from rag import bp as rag_bp

_LOG = logging.getLogger("test.rag_routes")


@pytest.fixture
def app():
    a = Flask(__name__)
    a.testing = True
    rr.init_routes(
        get_refresh_paths=lambda: [],
        log=_LOG,
    )
    a.register_blueprint(rag_bp)
    return a


@pytest.fixture
def client(app):
    return app.test_client()


# ── GET /api/rag/status ──────────────────────────────────────────────────

def test_api_rag_status_renvoie_chunks_et_sources(client):
    import rag.engine as eng
    eng._embed_model = "mxbai-embed-large"
    meta = [{"source": "MEMORY.md"}, {"source": "JARVIS.md"}, {"source": "MEMORY.md"}]
    with patch("rag.routes.engine._rag_load", return_value=(meta, [])):
        rv = client.get("/api/rag/status")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["chunks"] == 3
    assert set(data["sources"]) == {"MEMORY.md", "JARVIS.md"}


def test_api_rag_status_embed_model_present(client):
    import rag.engine as eng
    eng._embed_model = "test-model"
    with patch("rag.routes.engine._rag_load", return_value=([], [])):
        rv = client.get("/api/rag/status")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert "embed_model" in data


# ── POST /api/rag/note ───────────────────────────────────────────────────

def test_api_rag_note_contenu_manquant_400(client):
    rv = client.post("/api/rag/note", json={})
    assert rv.status_code == 400
    assert b"content required" in rv.data


def test_api_rag_note_contenu_vide_400(client):
    rv = client.post("/api/rag/note", json={"content": "  "})
    assert rv.status_code == 400


def test_api_rag_note_ok_retourne_chunks_added(client):
    with patch("rag.routes.engine._rag_index_text", return_value=3):
        rv = client.post("/api/rag/note", json={"content": "mémo important"})
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True
    assert data["chunks_added"] == 3


def test_api_rag_note_source_personnalisee(client):
    captured = {}
    def _fake(text, src):
        captured["src"] = src
        return 1
    with patch("rag.routes.engine._rag_index_text", side_effect=_fake):
        client.post("/api/rag/note", json={"content": "texte", "source": "custom/src"})
    assert captured["src"] == "custom/src"


def test_api_rag_note_source_defaut_contient_date(client):
    captured = {}
    def _fake(text, src):
        captured["src"] = src
        return 1
    with patch("rag.routes.engine._rag_index_text", side_effect=_fake):
        client.post("/api/rag/note", json={"content": "texte"})
    assert captured["src"].startswith("note/")


# ── POST /api/rag/index-file ─────────────────────────────────────────────

def test_api_rag_index_file_path_manquant_400(client):
    rv = client.post("/api/rag/index-file", json={})
    assert rv.status_code == 400
    assert b"path required" in rv.data


def test_api_rag_index_file_inexistant_404(client, tmp_path):
    rv = client.post("/api/rag/index-file", json={"path": str(tmp_path / "ghost.md")})
    assert rv.status_code == 404


def test_api_rag_index_file_ok(client, tmp_path):
    f = tmp_path / "doc.md"
    f.write_text("# contenu du doc", encoding="utf-8")
    with patch("rag.routes.engine._rag_index_text", return_value=2):
        rv = client.post("/api/rag/index-file", json={"path": str(f)})
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True
    assert data["chunks_added"] == 2
    assert data["file"] == "doc.md"


# ── DELETE /api/rag/clear ────────────────────────────────────────────────

def test_api_rag_clear_ok(client, tmp_path):
    meta_f = tmp_path / "meta.json"
    emb_f  = tmp_path / "emb.npy"
    meta_f.write_text("[]")
    emb_f.write_bytes(b"\x00")
    import rag.engine as eng
    eng._rag_meta_file = meta_f
    eng._rag_emb_file  = emb_f
    rv = client.delete("/api/rag/clear")
    assert rv.status_code == 200
    assert json.loads(rv.data)["ok"] is True
    assert not meta_f.exists()
    assert not emb_f.exists()


def test_api_rag_clear_fichiers_absents_ok(client, tmp_path):
    import rag.engine as eng
    eng._rag_meta_file = tmp_path / "ghost_meta.json"
    eng._rag_emb_file  = tmp_path / "ghost_emb.npy"
    rv = client.delete("/api/rag/clear")
    assert rv.status_code == 200


# ── POST /api/rag/refresh ────────────────────────────────────────────────

def test_api_rag_refresh_aucun_chemin(client):
    with patch("rag.routes._get_refresh_paths", return_value=lambda: []):
        rr._get_refresh_paths = lambda: []
        rv = client.post("/api/rag/refresh")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True
    assert data["chunks_added"] == 0


def test_api_rag_refresh_indexe_fichiers_existants(client, tmp_path):
    f = tmp_path / "MEMORY.md"
    f.write_text("# Memory\ncontenu", encoding="utf-8")
    rr._get_refresh_paths = lambda: [str(f)]
    with patch("rag.routes.engine._rag_index_text", return_value=2):
        rv = client.post("/api/rag/refresh")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True
    assert data["chunks_added"] == 2


def test_api_rag_refresh_fichier_inexistant_skip(client, tmp_path):
    rr._get_refresh_paths = lambda: [str(tmp_path / "ghost.md")]
    with patch("rag.routes.engine._rag_index_text", return_value=0) as m:
        rv = client.post("/api/rag/refresh")
    assert rv.status_code == 200
    m.assert_not_called()
