"""Tests routes HTTP dev — /api/dev/* + /api/code/exec + /api/save-code (Flask test_client).

Cible dev/routes.py (28% → cible ≥70%).
Stratégie : mock _ssh_dev1 (DI), subprocess.run (SCP), tmp_path pour generated_code_dir.
SSE : consume generator complet via test_client (stream response).
"""
import json
import logging
from pathlib import Path
from unittest.mock import patch

import dev.routes as dr
import pytest
from dev import bp as dev_bp
from flask import Flask

_LOG = logging.getLogger("test.dev_routes")


def _ssh_ok(cmd, timeout=30):
    return True, "output"


def _ssh_fail(cmd, timeout=30):
    return False, "ssh error"


@pytest.fixture
def app(tmp_path):
    a = Flask(__name__)
    a.testing = True
    dr.init_routes(
        log                   = _LOG,
        ssh_dev1              = _ssh_ok,
        code_scp_exec_sse_fn  = lambda filename, exec_it: iter([]),
        sse_tok               = lambda t, done=False: f"data: {json.dumps({'type':'token','token':t,'done':done})}\n\n",
        code_dev_ip           = "192.168.1.21",
        code_dev_port         = 2272,
        code_dev_key          = "/home/user/.ssh/id_dev",
        generated_code_dir    = tmp_path / "generated_code",
    )
    a.register_blueprint(dev_bp)
    return a


@pytest.fixture
def client(app):
    return app.test_client()


def _consume_sse(rv):
    """Lit tout le body SSE et renvoie la liste des events."""
    return rv.data.decode("utf-8").split("\n\n")


# ── POST /api/dev/exec ───────────────────────────────────────────────────

def test_api_dev_exec_cmd_manquante_400(client):
    rv = client.post("/api/dev/exec", json={})
    assert rv.status_code == 400
    assert b"cmd requis" in rv.data


def test_api_dev_exec_cmd_vide_400(client):
    rv = client.post("/api/dev/exec", json={"cmd": "   "})
    assert rv.status_code == 400


def test_api_dev_exec_retourne_sse(client):
    dr._ssh_dev1 = lambda cmd, timeout=30: (True, "bonjour\n__JARVIS_PWD__/root")
    rv = client.post("/api/dev/exec", json={"cmd": "echo bonjour"})
    assert rv.status_code == 200
    assert rv.content_type.startswith("text/event-stream")
    body = rv.data.decode("utf-8")
    assert "dev_output" in body


def test_api_dev_exec_cd_maj_cwd(client):
    """Commande 'cd' met à jour _dev_cwd (retourne dev_cwd event)."""
    dr._ssh_dev1 = lambda cmd, timeout=30: (True, "/tmp")
    rv = client.post("/api/dev/exec", json={"cmd": "cd /tmp"})
    body = rv.data.decode("utf-8")
    assert "dev_cwd" in body


def test_api_dev_exec_cd_echec_affiche_erreur(client):
    """cd échoué → message d'erreur dans la sortie."""
    dr._ssh_dev1 = lambda cmd, timeout=30: (False, "no such file")
    rv = client.post("/api/dev/exec", json={"cmd": "cd /inexistant"})
    body = rv.data.decode("utf-8")
    assert "dev_output" in body


# ── GET /api/dev/stats ───────────────────────────────────────────────────

def test_api_dev_stats_ssh_ok(client):
    stats_json = json.dumps({
        "load1": "0.5", "load5": "0.3",
        "ram_used": 512, "ram_total": 1024, "ram_pct": 50,
        "disk_used": 10, "disk_total": 50, "disk_pct": 20,
        "uptime": "2j 3h", "net_rx": "100M", "net_tx": "50M",
    })
    dr._ssh_dev1 = lambda cmd, timeout=30: (True, stats_json)
    dr._dev_stats_cache["ts"] = 0.0  # force cache miss
    rv = client.get("/api/dev/stats")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert "ram_pct" in data
    assert data["ram_pct"] == 50


def test_api_dev_stats_ssh_fail_503(client):
    dr._ssh_dev1 = _ssh_fail
    dr._dev_stats_cache["ts"] = 0.0
    rv = client.get("/api/dev/stats")
    assert rv.status_code == 500
    assert b"SSH dev1 failed" in rv.data


def test_api_dev_stats_cache_hit(client):
    dr._dev_stats_cache["ts"]   = 9_999_999_999.0  # ts futur → cache valide
    dr._dev_stats_cache["data"] = {"load1": "0.1"}
    called = {"n": 0}
    def _ssh_track(cmd, timeout=30):
        called["n"] += 1
        return True, "{}"
    dr._ssh_dev1 = _ssh_track
    rv = client.get("/api/dev/stats")
    assert rv.status_code == 200
    assert called["n"] == 0  # SSH non appelé grâce au cache


def test_api_dev_stats_json_invalide_500(client):
    dr._ssh_dev1 = lambda cmd, timeout=30: (True, "not-json")
    dr._dev_stats_cache["ts"] = 0.0
    rv = client.get("/api/dev/stats")
    assert rv.status_code == 500


# ── POST /api/save-code ──────────────────────────────────────────────────

def test_api_save_code_ok(client, tmp_path):
    dr._generated_code_dir = tmp_path / "generated_code"
    rv = client.post("/api/save-code", json={"filename": "test.py", "code": "print('ok')"})
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert "saved" in data
    saved_path = Path(data["saved"])
    assert saved_path.read_text(encoding="utf-8") == "print('ok')"


def test_api_save_code_filename_invalide_400(client):
    rv = client.post("/api/save-code", json={"filename": "../../evil.py", "code": "x"})
    assert rv.status_code == 400
    assert b"filename invalide" in rv.data


def test_api_save_code_sans_body_utilise_defaut(client, tmp_path):
    dr._generated_code_dir = tmp_path / "generated_code"
    rv = client.post("/api/save-code", json={})
    assert rv.status_code == 200


# ── POST /api/code/exec ──────────────────────────────────────────────────

def test_api_code_exec_params_manquants_400(client):
    rv = client.post("/api/code/exec", json={})
    assert rv.status_code == 400
    assert b"requis" in rv.data


def test_api_code_exec_filename_sans_code_400(client):
    rv = client.post("/api/code/exec", json={"filename": "test.py", "code": ""})
    assert rv.status_code == 400


def test_api_code_exec_filename_invalide_400(client):
    rv = client.post("/api/code/exec", json={"filename": "../../etc/passwd", "code": "x"})
    assert rv.status_code == 400


def test_api_code_exec_ok_retourne_sse(client, tmp_path):
    """api_code_exec : fichier écrit, SSE généré, fichier temp supprimé."""
    sse_events = [
        f"data: {json.dumps({'type':'token','token':'ok','done':False})}\n\n",
        f"data: {json.dumps({'type':'token','token':'','done':True})}\n\n",
    ]
    dr._code_scp_exec_sse_fn = lambda filename, exec_it: iter(sse_events)
    # Créer le répertoire Documents dans tmp_path pour que write_text réussisse
    docs_dir = tmp_path / "Documents"
    docs_dir.mkdir()
    with patch("dev.routes.Path.home", return_value=tmp_path):
        rv = client.post("/api/code/exec", json={"filename": "test_exec.py", "code": "print('ok')"})
    assert rv.status_code == 200
    assert rv.content_type.startswith("text/event-stream")
