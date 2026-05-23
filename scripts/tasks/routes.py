"""Routes HTTP de la tuile **tasks** — tâches planifiées + polling Code Reasoning.

5 endpoints :
- GET    /api/tasks            — liste des tâches
- POST   /api/tasks            — créer/mettre à jour une tâche
- DELETE /api/tasks/<tid>      — supprimer
- POST   /api/tasks/<tid>/run  — exécuter une tâche (shell, blocking)
- GET    /api/cr-poll/<task_id>— polling Code Reasoning (qwen3:8b)
"""
import json
import subprocess
import time
import uuid as _uuid

from flask import Response, request

from . import bp

_log = None
_get_tasks_file = None    # callable → Path
_terminal_cwd = None      # list (mutable container)
_terminal_timeout_s = 60
_cr_tasks = None          # dict (mutable container, shared with code_reasoning)


def init_routes(*, log, get_tasks_file, terminal_cwd, terminal_timeout_s, cr_tasks) -> None:
    global _log, _get_tasks_file, _terminal_cwd, _terminal_timeout_s, _cr_tasks
    _log = log
    _get_tasks_file = get_tasks_file
    _terminal_cwd = terminal_cwd
    _terminal_timeout_s = terminal_timeout_s
    _cr_tasks = cr_tasks


def _load_tasks():
    try:
        f = _get_tasks_file()
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING load_tasks: {e}")
    return []


def _save_tasks(tasks):
    _get_tasks_file().write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")


@bp.route("/api/cr-poll/<task_id>")
def cr_poll(task_id):
    task = _cr_tasks.get(task_id)
    if not task:
        return Response('{"error":"not found"}', status=404, mimetype="application/json")
    return Response(json.dumps({"status": task["status"], "text": task["text"]}),
                    mimetype="application/json")


@bp.route("/api/tasks", methods=["GET"])
def api_tasks_get():
    return Response(json.dumps(_load_tasks(), ensure_ascii=False), mimetype="application/json")


@bp.route("/api/tasks", methods=["POST"])
def api_tasks_post():
    data  = request.json or {}
    tasks = _load_tasks()
    tid   = data.get("id") or str(_uuid.uuid4())[:8]
    raw_cmd = str(data.get("cmd", "")).replace('\x00', '').strip()[:500]
    if "cmd" in data and not raw_cmd:
        return Response('{"error":"Commande vide"}', status=400, mimetype="application/json")
    task  = next((t for t in tasks if t["id"] == tid), None)
    if task:
        if "cmd" in data:
            data["cmd"] = raw_cmd
        task.update({k: v for k, v in data.items() if k != "id"})
    else:
        tasks.append({
            "id":       tid,
            "name":     data.get("name", "Tâche"),
            "cmd":      raw_cmd,
            "schedule": data.get("schedule", ""),
            "enabled":  data.get("enabled", True),
            "notify":   data.get("notify", True),
            "last_run": None,
            "last_out": "",
            "last_err": "",
            "status":   "idle",
        })
    _save_tasks(tasks)
    return Response(json.dumps({"ok": True, "id": tid}), mimetype="application/json")


@bp.route("/api/tasks/<tid>", methods=["DELETE"])
def api_tasks_delete(tid):
    tasks = [t for t in _load_tasks() if t["id"] != tid]
    _save_tasks(tasks)
    return Response('{"ok":true}', mimetype="application/json")


@bp.route("/api/tasks/<tid>/run", methods=["POST"])
def api_tasks_run(tid):
    tasks = _load_tasks()
    task  = next((t for t in tasks if t["id"] == tid), None)
    if not task:
        return Response('{"error":"Tâche introuvable"}', status=404, mimetype="application/json")
    cmd = task.get("cmd", "").strip()
    if not cmd:
        return Response('{"error":"Commande vide"}', status=400, mimetype="application/json")
    task["status"]   = "running"
    task["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_tasks(tasks)
    try:
        # shell=True intentionnel : les commandes utilisateur peuvent contenir pipes/redirections
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           cwd=_terminal_cwd[0], timeout=_terminal_timeout_s, encoding="utf-8", errors="replace")
        task["last_out"] = r.stdout[:4000]
        task["last_err"] = r.stderr[:2000]
        if r.returncode != 0:
            _log.error(f"[JARVIS] tasks_run '{task.get('name',tid)}' — returncode={r.returncode} err={r.stderr[:200]!r}")
        task["status"]   = "ok" if r.returncode == 0 else "error"
    except Exception as e:
        _log.error(f"[JARVIS] tasks_run error: {e}")
        task["last_err"] = "Erreur d'exécution"
        task["status"]   = "error"
    _save_tasks(tasks)
    return Response(json.dumps({"ok": True, "output": task["last_out"], "error": task["last_err"], "status": task["status"]}, ensure_ascii=False), mimetype="application/json")
