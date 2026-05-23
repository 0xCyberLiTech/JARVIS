"""Routes HTTP de la tuile **health** — santé runtime + stats + ping + security.

9 endpoints :
- GET /api/boot-id        — ID unique de session JARVIS (changement = restart)
- GET /api/health         — health check léger (<10ms, sans appel Ollama)
- GET /api/stats          — CPU/RAM/GPU/VRAM (cache 5s)
- GET /api/status         — état JARVIS pour defense chain SOC (model + bans/alerts 24h)
- GET /api/ollama-status  — Ollama running + état circuit breaker
- GET /api/vram           — modèles chargés en VRAM (Ollama /api/ps)
- GET /api/security       — journal sécurité (tentatives bloquées)
- POST /api/security/clear — vide le journal sécurité
- POST /api/ping          — ping IP/host depuis la machine Windows
"""
import json
import re
import subprocess
import time
import urllib.request as _ur

from flask import Response, request

from . import bp

_log = None
_ollama_circuit = None
_ollama_status_timeout_s = 2
_ssh_proxmox_cmd_timeout_s = 15
_stats_cache = None     # dict mutable
_stats_ttl = 5.0
_sec_events = None      # list mutable
_sec_lock = None        # threading.Lock
_get_boot_id = None
_get_stats_fn = None
_get_model = None
_get_last_toks_per_sec = None
_get_llm_params = None
_get_soc_status = None  # callable → {soc_engine_active, bans_24h, alerts_24h}
_code_reasoning_model = ""
_code_model = ""
_general_model = ""


def init_routes(*, log, ollama_circuit,
                ollama_status_timeout_s, ssh_proxmox_cmd_timeout_s,
                stats_cache, stats_ttl, sec_events, sec_lock,
                get_boot_id, get_stats_fn, get_model, get_last_toks_per_sec,
                get_llm_params, get_soc_status,
                code_reasoning_model, code_model, general_model) -> None:
    globals().update({
        "_log": log,
        "_ollama_circuit": ollama_circuit,
        "_ollama_status_timeout_s": ollama_status_timeout_s,
        "_ssh_proxmox_cmd_timeout_s": ssh_proxmox_cmd_timeout_s,
        "_stats_cache": stats_cache,
        "_stats_ttl": stats_ttl,
        "_sec_events": sec_events,
        "_sec_lock": sec_lock,
        "_get_boot_id": get_boot_id,
        "_get_stats_fn": get_stats_fn,
        "_get_model": get_model,
        "_get_last_toks_per_sec": get_last_toks_per_sec,
        "_get_llm_params": get_llm_params,
        "_get_soc_status": get_soc_status,
        "_code_reasoning_model": code_reasoning_model,
        "_code_model": code_model,
        "_general_model": general_model,
    })


@bp.route("/api/boot-id")
def api_boot_id():
    return Response(json.dumps({"boot_id": _get_boot_id()}), mimetype="application/json")


@bp.route("/api/health", methods=["GET"])
def api_health():
    """Health check léger — répond en <10ms, sans appel Ollama. Utilisé par watchdog et MCP."""
    import datetime as _dt
    return Response(json.dumps({
        "status": "ok",
        "model":  _get_model(),
        "ts":     _dt.datetime.utcnow().isoformat() + "Z"
    }), mimetype="application/json")


@bp.route("/api/stats")
def api_stats():
    now = time.time()
    if _stats_cache["data"] is not None and (now - _stats_cache["ts"]) < _stats_ttl:
        return Response(json.dumps(_stats_cache["data"]), mimetype="application/json")
    data = _get_stats_fn()
    _stats_cache["data"] = data
    _stats_cache["ts"] = now
    return Response(json.dumps(data), mimetype="application/json")


@bp.route("/api/status")
def api_status():
    """État JARVIS — utilisé par la defense chain SOC (_dcPollJarvis)."""
    soc = _get_soc_status()
    return Response(json.dumps({
        "available":          True,
        "model":              _get_model(),
        "soc_engine_active":  soc["soc_engine_active"],
        "bans_24h":           soc["bans_24h"],
        "alerts_24h":         soc["alerts_24h"],
    }), mimetype="application/json")


@bp.route("/api/ollama-status", methods=["GET"])
def api_ollama_status():
    try:
        with _ur.urlopen("http://127.0.0.1:11434/api/tags", timeout=_ollama_status_timeout_s) as r:
            running = r.status == 200
    except Exception:
        running = False
    circuit_status = _ollama_circuit.get_status()
    return Response(json.dumps({"running": running, **circuit_status}), mimetype="application/json")


@bp.route("/api/vram", methods=["GET"])
def api_vram():
    """Retourne les modèles Ollama chargés en VRAM via /api/ps."""
    try:
        import pynvml as _nv
        _nv.nvmlInit()
        _h = _nv.nvmlDeviceGetHandleByIndex(0)
        vram_cap = _nv.nvmlDeviceGetMemoryInfo(_h).total
    except Exception:
        vram_cap = 0
    try:
        with _ur.urlopen("http://127.0.0.1:11434/api/ps", timeout=3) as r:
            data = json.loads(r.read())
        models = []
        total_vram = 0
        total_swap = 0
        active_model = _get_model()
        for m in data.get("models", []):
            sv       = m.get("size_vram", 0)
            st       = m.get("size", 0)
            swap     = max(0, st - sv)
            name     = m.get("name", "?")
            nl       = name.lower()
            is_embed = "embed" in nl
            details  = m.get("details", {})
            quant    = details.get("quantization_level", "")
            params   = details.get("parameter_size", "")
            expires  = m.get("expires_at", "")
            if is_embed:
                role = "RAG"
            elif _code_reasoning_model.lower().split(":")[0] in nl:
                role = "C·R"
            elif _code_model.lower().split(":")[0] in nl:
                role = "CODE"
            elif _general_model.lower().split(":")[0] in nl:
                role = "GÉNÉRAL"
            else:
                role = "SOC"
            pct = round(sv / vram_cap * 100, 1) if vram_cap else 0
            total_vram += sv
            if not is_embed:
                total_swap += swap
            models.append({"name": name, "size_vram": sv, "size_swap": swap,
                           "is_embed": is_embed, "role": role,
                           "pct": pct, "quant": quant, "params": params, "expires_at": expires})
        return Response(json.dumps({
            "models": models, "total_vram": total_vram,
            "total_swap": total_swap, "vram_total_bytes": vram_cap,
            "active_model": active_model,
            "tokens_per_sec": _get_last_toks_per_sec(),
            "num_ctx": _get_llm_params().get("num_ctx", 0),
        }), mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"models": [], "total_vram": 0, "total_swap": 0,
                                    "vram_total_bytes": vram_cap, "active_model": active_model, "error": str(e)}),
                        mimetype="application/json")


@bp.route("/api/security", methods=["GET"])
def api_security():
    """Journal sécurité — tentatives bloquées depuis le démarrage."""
    with _sec_lock:
        total  = len(_sec_events)
        by_lvl = {"hard": 0, "args": 0, "terminal": 0}
        for e in _sec_events:
            by_lvl[e["level"]] = by_lvl.get(e["level"], 0) + 1
        snapshot = _sec_events[-10:][::-1]
    return Response(json.dumps({
        "total":         total,
        "by_level":      by_lvl,
        "last":          snapshot,
        "uptime_events": total,
    }, ensure_ascii=False), mimetype="application/json")


@bp.route("/api/security/clear", methods=["POST"])
def api_security_clear():
    """Vide le journal sécurité."""
    with _sec_lock:
        _sec_events.clear()
    return Response('{"ok":true}', mimetype="application/json")


@bp.route("/api/ping", methods=["POST"])
def api_ping():
    """Ping une IP/host depuis la machine Windows et retourne le résultat."""
    host = (request.json or {}).get("host", "")
    if not host or not re.match(r'^[a-zA-Z0-9.\-_]+$', host):
        return Response('{"error":"host invalide"}', mimetype="application/json", status=400)
    try:
        result = subprocess.run(
            ["ping", "-n", "4", host],
            capture_output=True, text=True, timeout=_ssh_proxmox_cmd_timeout_s, encoding="cp850", errors="replace"
        )
        output = result.stdout or result.stderr or ""
        lines  = [ln.strip() for ln in output.splitlines() if ln.strip()]
        ok     = result.returncode == 0
        return Response(
            json.dumps({"ok": ok, "host": host, "output": output, "lines": lines}, ensure_ascii=False),
            mimetype="application/json"
        )
    except Exception as e:
        return Response(json.dumps({"ok": False, "host": host, "error": str(e)}), mimetype="application/json")
