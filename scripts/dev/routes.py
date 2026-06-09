"""Routes HTTP de la tuile **dev** — exécution code/dev sur srv-dev-1.

4 endpoints + 1 générateur SSE (sans WebSocket — les routes WS terminal
restent dans jarvis.py jusqu'à étape ultérieure).

- POST /api/code/exec    — écrit + SCP + exec un fichier code sur srv-dev-1
- POST /api/dev/exec     — exécute une commande shell sur srv-dev-1 (SSE)
- GET  /api/dev/stats    — stats système srv-dev-1 (cache 12s, SSH via _ssh_dev1 DI)
- POST /api/save-code    — sauvegarde locale dans scripts/generated_code/
"""
import json
import re
import shlex
import time
from pathlib import Path

from flask import Response, jsonify, request, stream_with_context

from . import bp

# ── État interne (mutable, propre à dev) ──
_dev_cwd: str = "/root"
_dev_stats_cache: dict = {"ts": 0.0, "data": {}}

# Bash script utilitaire — collecte stats /proc + disk + uptime + net en un seul appel SSH
_STATS_CMD = r"""python3 -c '
import json, shutil
la = open("/proc/loadavg").read().split()
m = {}
for l in open("/proc/meminfo"):
    if ":" in l:
        k, v = l.split(":", 1)
        try: m[k.strip()] = int(v.strip().split()[0])
        except Exception: pass
mt = m.get("MemTotal",0)//1024
mf = (m.get("MemFree",0)+m.get("Buffers",0)+m.get("Cached",0)+m.get("SReclaimable",0))//1024
mu = mt-mf; mp = int(mu*100/mt) if mt else 0
du = shutil.disk_usage("/")
up = float(open("/proc/uptime").read().split()[0])
d=int(up//86400); h=int((up%86400)//3600); mn=int((up%3600)//60)
ut = f"{d}j {h}h" if d else f"{h}h {mn}m"
rx=tx=0
for l in open("/proc/net/dev"):
    if ":" not in l: continue
    iface,cols=l.strip().split(":",1); cols=cols.split()
    if iface.strip()=="lo": continue
    rx+=int(cols[0]); tx+=int(cols[8])
def hb(b): return f"{b//2**30}G" if b>=2**30 else f"{b//2**20}M" if b>=2**20 else f"{b//2**10}K"
print(json.dumps({"load1":la[0],"load5":la[1],"ram_used":mu,"ram_total":mt,"ram_pct":mp,
"disk_used":du.used//2**30,"disk_total":du.total//2**30,"disk_pct":int(du.used*100/du.total),
"uptime":ut,"net_rx":hb(rx),"net_tx":hb(tx)}))
'"""

# Dépendances injectées par init()
_log = None
_ssh_dev1 = None
_code_scp_exec_sse_fn = None
_sse_tok = None
_code_dev_ip = ""
_code_dev_port = 22
_code_dev_key = ""
_generated_code_dir = None


def init_routes(*, log, ssh_dev1, code_scp_exec_sse_fn, sse_tok,
                code_dev_ip, code_dev_port, code_dev_key,
                generated_code_dir) -> None:
    globals().update({
        "_log": log,
        "_ssh_dev1": ssh_dev1,
        "_code_scp_exec_sse_fn": code_scp_exec_sse_fn,
        "_sse_tok": sse_tok,
        "_code_dev_ip": code_dev_ip,
        "_code_dev_port": code_dev_port,
        "_code_dev_key": code_dev_key,
        "_generated_code_dir": generated_code_dir,
    })


def _dev_exec_sse(cmd: str):
    """Mode terminal DEV — exécute une commande sur srv-dev-1, maintient _dev_cwd."""
    global _dev_cwd
    cmd = cmd.strip()
    if not cmd:
        yield _sse_tok("", done=True)
        return

    # cd : mise à jour cwd sans sortie visible
    cd_m = re.match(r'^cd\s*(.*)', cmd)
    if cd_m:
        target = cd_m.group(1).strip() or "/root"
        ok, out = _ssh_dev1(
            f"cd {shlex.quote(_dev_cwd)} 2>/dev/null && cd {target} 2>&1 && pwd",
            timeout=10)
        if ok and out and out.strip().startswith('/'):
            _dev_cwd = out.strip()
            yield f"data: {json.dumps({'type':'dev_cwd','cwd':_dev_cwd})}\n\n"
            yield f"data: {json.dumps({'type':'dev_output','prompt':f'root@srv-dev-1:{_dev_cwd} $','cmd':cmd,'output':''})}\n\n"
        else:
            err = (out or "").strip() or f"bash: cd: {target}: No such file or directory"
            yield f"data: {json.dumps({'type':'dev_output','prompt':f'root@srv-dev-1:{_dev_cwd} $','cmd':cmd,'output':err})}\n\n"
        yield _sse_tok("", done=True)
        return

    # Commande générale — capture le nouveau cwd via marqueur
    full_cmd = (
        f"cd {shlex.quote(_dev_cwd)} 2>/dev/null; "
        f"{cmd}; "
        "echo '__JARVIS_PWD__'\"$(pwd)\""
    )
    ok, out = _ssh_dev1(full_cmd, timeout=30)

    new_cwd = _dev_cwd
    if out and '__JARVIS_PWD__' in out:
        parts = out.rsplit('__JARVIS_PWD__', 1)
        out = parts[0].rstrip('\n')
        new_cwd = parts[1].strip() or _dev_cwd
    _dev_cwd = new_cwd

    output_text = out if ok else (out or "✗ Erreur SSH.")
    yield f"data: {json.dumps({'type':'dev_output','prompt':f'root@srv-dev-1:{_dev_cwd} $','cmd':cmd,'output':output_text})}\n\n"
    yield f"data: {json.dumps({'type':'dev_cwd','cwd':_dev_cwd})}\n\n"
    yield _sse_tok("", done=True)


@bp.route("/api/code/exec", methods=["POST"])
def api_code_exec():
    """Écrit un fichier code localement, SCP sur srv-dev-1, exécute, retourne SSE."""
    data     = request.get_json(force=True, silent=True) or {}
    filename = (data.get("filename") or "").strip()
    code     = (data.get("code")     or "").strip()
    if not filename or not code:
        return Response(json.dumps({"error": "filename et code requis"}), status=400, mimetype="application/json")
    if not re.match(r'^[\w.-]+\.(py|sh|js|ts|html|css|json|yml|yaml|rb|go|php|sql|txt)$', filename) or ".." in filename:
        return Response(json.dumps({"error": "filename invalide"}), status=400, mimetype="application/json")
    local_path = Path.home() / "Documents" / filename
    local_path.write_text(code, encoding="utf-8")
    _log.info(f"[CODE/EXEC] Fichier écrit : {local_path}")
    def _gen_and_cleanup():
        yield from _code_scp_exec_sse_fn(filename, exec_it=True)
        try:
            local_path.unlink(missing_ok=True)
            _log.info(f"[CODE/EXEC] Fichier temp supprimé : {local_path}")
        except Exception:
            pass
    return Response(stream_with_context(_gen_and_cleanup()), content_type="text/event-stream")


@bp.route("/api/dev/exec", methods=["POST"])
def api_dev_exec():
    data = request.get_json(silent=True) or {}
    cmd  = data.get("cmd", "").strip()
    if not cmd:
        return Response(json.dumps({"error": "cmd requis"}), status=400, mimetype="application/json")
    return Response(stream_with_context(_dev_exec_sse(cmd)), content_type="text/event-stream")


@bp.route("/api/dev/stats")
def dev_stats():
    """Stats système srv-dev-1 via SSH · cache 12s · utilise _ssh_dev1 DI."""
    now = time.time()
    if now - _dev_stats_cache["ts"] < 12 and _dev_stats_cache["data"]:
        return jsonify(_dev_stats_cache["data"])
    try:
        ok, raw = _ssh_dev1(_STATS_CMD)
        if not ok:
            return jsonify({"error": "SSH dev1 failed"}), 500
        data = json.loads(raw)
        _dev_stats_cache["ts"]   = time.time()
        _dev_stats_cache["data"] = data
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@bp.route("/api/save-code", methods=["POST"])
def api_save_code():
    data     = request.get_json(silent=True) or {}
    filename = data.get("filename", "untitled.py")
    code     = data.get("code", "")
    if not re.match(r'^[\w\-. ]+$', filename):
        return Response(json.dumps({"error": "filename invalide"}), status=400, mimetype="application/json")
    _generated_code_dir.mkdir(exist_ok=True)
    filepath = _generated_code_dir / filename
    filepath.write_text(code, encoding="utf-8")
    _log.info(f"[CODE] Fichier sauvegardé : {filepath}")
    return Response(json.dumps({"saved": str(filepath)}), mimetype="application/json")
