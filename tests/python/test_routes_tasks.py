"""Tests routes HTTP tasks — /api/tasks* + /api/cr-poll (Flask test_client).

Cible tasks/routes.py (50% → cible ≥80%).
Stratégie : tmp_path pour tasks.json, mock subprocess.run pour api_tasks_run.
"""
import json
import logging
import subprocess
from unittest.mock import MagicMock, patch

import pytest
import tasks.routes as tr
from flask import Flask
from tasks import bp as tasks_bp

_LOG = logging.getLogger("test.tasks_routes")


@pytest.fixture
def app(tmp_path):
    a = Flask(__name__)
    a.testing = True
    tasks_file = tmp_path / "tasks.json"
    cr_store = {}
    tr.init_routes(
        log               = _LOG,
        get_tasks_file    = lambda: tasks_file,
        terminal_cwd      = [str(tmp_path)],
        terminal_timeout_s= 5,
        cr_tasks          = cr_store,
    )
    a.register_blueprint(tasks_bp)
    return a


@pytest.fixture
def client(app):
    return app.test_client()


# ── GET /api/tasks ───────────────────────────────────────────────────────

def test_api_tasks_get_vide(client):
    rv = client.get("/api/tasks")
    assert rv.status_code == 200
    assert json.loads(rv.data) == []


# ── POST /api/tasks ──────────────────────────────────────────────────────

def test_api_tasks_post_cree_tache(client):
    rv = client.post("/api/tasks", json={"name": "Test", "cmd": "echo hello"})
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True
    assert "id" in data


def test_api_tasks_post_cmd_vide_400(client):
    rv = client.post("/api/tasks", json={"cmd": "  "})
    assert rv.status_code == 400
    assert b"Commande vide" in rv.data


def test_api_tasks_post_met_a_jour_tache_existante(client):
    rv1 = client.post("/api/tasks", json={"name": "Tâche", "cmd": "ls"})
    tid = json.loads(rv1.data)["id"]
    rv2 = client.post("/api/tasks", json={"id": tid, "name": "Renommée", "cmd": "pwd"})
    assert rv2.status_code == 200
    tasks = json.loads(client.get("/api/tasks").data)
    assert len(tasks) == 1
    assert tasks[0]["name"] == "Renommée"
    assert tasks[0]["cmd"] == "pwd"


def test_api_tasks_post_champs_defaut(client):
    rv = client.post("/api/tasks", json={"name": "T", "cmd": "ls"})
    tid = json.loads(rv.data)["id"]
    tasks = json.loads(client.get("/api/tasks").data)
    t = next(x for x in tasks if x["id"] == tid)
    assert t["enabled"] is True
    assert t["notify"] is True
    assert t["status"] == "idle"


# ── DELETE /api/tasks/<tid> ──────────────────────────────────────────────

def test_api_tasks_delete_supprime(client):
    rv = client.post("/api/tasks", json={"name": "T", "cmd": "ls"})
    tid = json.loads(rv.data)["id"]
    rv_del = client.delete(f"/api/tasks/{tid}")
    assert rv_del.status_code == 200
    tasks = json.loads(client.get("/api/tasks").data)
    assert all(t["id"] != tid for t in tasks)


def test_api_tasks_delete_tid_inexistant_ok(client):
    rv = client.delete("/api/tasks/ghost-id")
    assert rv.status_code == 200
    assert json.loads(rv.data)["ok"] is True


# ── GET /api/cr-poll/<task_id> ───────────────────────────────────────────

def test_cr_poll_not_found(client):
    rv = client.get("/api/cr-poll/unknown-id")
    assert rv.status_code == 404
    assert b"not found" in rv.data


def test_cr_poll_found(client):
    tr._cr_tasks["abc123"] = {"status": "done", "text": "résultat"}
    rv = client.get("/api/cr-poll/abc123")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["status"] == "done"
    assert data["text"] == "résultat"


# ── POST /api/tasks/<tid>/run ────────────────────────────────────────────

def test_api_tasks_run_ok(client):
    rv = client.post("/api/tasks", json={"name": "Echo", "cmd": "echo bonjour"})
    tid = json.loads(rv.data)["id"]
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "bonjour\n"
    mock_result.stderr = ""
    with patch("tasks.routes.subprocess.run", return_value=mock_result):
        rv_run = client.post(f"/api/tasks/{tid}/run")
    assert rv_run.status_code == 200
    data = json.loads(rv_run.data)
    assert data["ok"] is True
    assert data["status"] == "ok"
    assert "bonjour" in data["output"]


def test_api_tasks_run_returncode_nonzero_status_error(client):
    rv = client.post("/api/tasks", json={"name": "Fail", "cmd": "false"})
    tid = json.loads(rv.data)["id"]
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "erreur"
    with patch("tasks.routes.subprocess.run", return_value=mock_result):
        rv_run = client.post(f"/api/tasks/{tid}/run")
    assert rv_run.status_code == 200
    data = json.loads(rv_run.data)
    assert data["status"] == "error"


def test_api_tasks_run_tid_inexistant_404(client):
    rv = client.post("/api/tasks/ghost-id/run")
    assert rv.status_code == 404
    assert b"introuvable" in rv.data


def test_api_tasks_run_cmd_vide_400(client):
    rv = client.post("/api/tasks", json={"name": "Vide", "cmd": ""})
    assert rv.status_code == 400


def test_api_tasks_run_exception_ssh_status_error(client):
    rv = client.post("/api/tasks", json={"name": "T", "cmd": "ls"})
    tid = json.loads(rv.data)["id"]
    with patch("tasks.routes.subprocess.run", side_effect=subprocess.TimeoutExpired("ls", 5)):
        rv_run = client.post(f"/api/tasks/{tid}/run")
    assert rv_run.status_code == 200
    data = json.loads(rv_run.data)
    assert data["status"] == "error"
