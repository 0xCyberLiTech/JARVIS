"""Routes HTTP de la tuile **settings** — config LLM, prompt, profils, welcome, modèles, DSP.

16 endpoints regroupés (refactor jarvis.py étape 17, 2026-05-23). Trois sections :
- LLM params + system prompt + reset + prompt profiles (CRUD)
- Welcome message (CRUD + evolve via LLM)
- DSP params (sanitization) + DSP process audio + models (list/test/set)

DI lourd (~25 deps) — c'est inhérent : les routes config touchent au
runtime mutable (LLM_PARAMS, SYSTEM_PROMPT, DSP_PARAMS, MODEL, VOICE, …).
"""
import datetime
import json
import re
import time

import requests as req
from flask import Response, request

from . import bp

# Dépendances injectées par __init__.init()
_log = None
_ollama_circuit = None
_ollama_url = ""
_ollama_tool_detect_timeout_s = 15
_dsp_max_bytes = 50_000_000

# Accesseurs mutables (lambdas)
_get_llm_params      = None
_get_system_prompt   = None
_get_model           = None
_get_models          = None
_get_dsp_params      = None
_get_welcome_data    = None
_get_auto_profile_model = None

# Setters
_set_system_prompt   = None
_set_model           = None
_set_dsp_params      = None
_set_welcome_data    = None
_reset_welcome       = None
_save_model_fn       = None
_set_auto_profile_model = None

# Constantes / objets
_llm_defaults                = None
_default_system_prompt       = ""
_llm_params_file             = None
_prompt_file                 = None
_prompt_profiles_file        = None
_welcome_file                = None
_default_welcome             = None
_dsp_params_file             = None
_dsp_safe_str                = None
_dsp_bounds                  = None
_model_lock                  = None
_get_model_profile_fn        = None
_fetch_ollama_models_fn      = None
_apply_dsp_to_mp3_fn         = None


def init_routes(*, log, ollama_circuit, ollama_url,
                ollama_tool_detect_timeout_s, dsp_max_bytes,
                get_llm_params, get_system_prompt, get_model, get_models,
                get_dsp_params, get_welcome_data, get_auto_profile_model,
                set_system_prompt, set_model, set_dsp_params, set_welcome_data,
                reset_welcome, save_model_fn, set_auto_profile_model,
                llm_defaults, default_system_prompt,
                llm_params_file, prompt_file, prompt_profiles_file,
                welcome_file, default_welcome, dsp_params_file,
                dsp_safe_str, dsp_bounds,
                model_lock, get_model_profile_fn, fetch_ollama_models_fn,
                apply_dsp_to_mp3_fn) -> None:
    globals().update({
        "_log": log,
        "_ollama_circuit": ollama_circuit,
        "_ollama_url": ollama_url,
        "_ollama_tool_detect_timeout_s": ollama_tool_detect_timeout_s,
        "_dsp_max_bytes": dsp_max_bytes,
        "_get_llm_params": get_llm_params,
        "_get_system_prompt": get_system_prompt,
        "_get_model": get_model,
        "_get_models": get_models,
        "_get_dsp_params": get_dsp_params,
        "_get_welcome_data": get_welcome_data,
        "_get_auto_profile_model": get_auto_profile_model,
        "_set_system_prompt": set_system_prompt,
        "_set_model": set_model,
        "_set_dsp_params": set_dsp_params,
        "_set_welcome_data": set_welcome_data,
        "_reset_welcome": reset_welcome,
        "_save_model_fn": save_model_fn,
        "_set_auto_profile_model": set_auto_profile_model,
        "_llm_defaults": llm_defaults,
        "_default_system_prompt": default_system_prompt,
        "_llm_params_file": llm_params_file,
        "_prompt_file": prompt_file,
        "_prompt_profiles_file": prompt_profiles_file,
        "_welcome_file": welcome_file,
        "_default_welcome": default_welcome,
        "_dsp_params_file": dsp_params_file,
        "_dsp_safe_str": dsp_safe_str,
        "_dsp_bounds": dsp_bounds,
        "_model_lock": model_lock,
        "_get_model_profile_fn": get_model_profile_fn,
        "_fetch_ollama_models_fn": fetch_ollama_models_fn,
        "_apply_dsp_to_mp3_fn": apply_dsp_to_mp3_fn,
    })


# ───────────────────────────────────────────────────────────────────────
# LLM params + system prompt + reset
# ───────────────────────────────────────────────────────────────────────


@bp.route("/api/llm-params", methods=["GET"])
def api_llm_params_get():
    return Response(json.dumps({"params": _get_llm_params(), "defaults": _llm_defaults,
                                "system_prompt": _get_system_prompt()}),
                    mimetype="application/json")


@bp.route("/api/llm-params", methods=["POST"])
def api_llm_params_set():
    data = request.json or {}
    if "params" in data:
        llm_params = _get_llm_params()
        for k, v in data["params"].items():
            if k in llm_params:
                llm_params[k] = v
        _llm_params_file.write_text(json.dumps(llm_params, indent=2), encoding="utf-8")
    if "system_prompt" in data:
        _set_system_prompt(data["system_prompt"])
        _prompt_file.write_text(_get_system_prompt(), encoding="utf-8")
    return Response('{"ok":true}', mimetype="application/json")


@bp.route("/api/llm-params/reset-prompt", methods=["POST"])
def api_reset_prompt():
    _set_system_prompt(_default_system_prompt)
    _prompt_file.write_text(_get_system_prompt(), encoding="utf-8")
    return Response(json.dumps({"ok": True, "system_prompt": _get_system_prompt()}),
                    mimetype="application/json")


# ───────────────────────────────────────────────────────────────────────
# Prompt profiles (CRUD)
# ───────────────────────────────────────────────────────────────────────


@bp.route("/api/prompt-profiles", methods=["GET"])
def api_prompt_profiles_get():
    try:
        profiles = json.loads(_prompt_profiles_file.read_text(encoding="utf-8-sig")) if _prompt_profiles_file.exists() else {}
    except (OSError, ValueError):
        profiles = {}
    return Response(json.dumps(profiles), mimetype="application/json")


@bp.route("/api/prompt-profiles", methods=["POST"])
def api_prompt_profiles_save():
    data = request.json or {}
    name    = data.get("name", "").strip()
    content = data.get("content", "")
    if not name:
        return Response('{"error":"name required"}', status=400, mimetype="application/json")
    try:
        profiles = json.loads(_prompt_profiles_file.read_text(encoding="utf-8-sig")) if _prompt_profiles_file.exists() else {}
    except (OSError, ValueError):
        profiles = {}
    entry = {"content": content, "saved_at": time.strftime("%Y-%m-%d %H:%M")}
    locked = data.get("locked_provider", "")
    if locked:
        entry["locked_provider"] = locked
    profiles[name] = entry
    _prompt_profiles_file.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    return Response('{"ok":true}', mimetype="application/json")


@bp.route("/api/prompt-profiles/<name>", methods=["DELETE"])
def api_prompt_profiles_delete(name):
    try:
        profiles = json.loads(_prompt_profiles_file.read_text(encoding="utf-8-sig")) if _prompt_profiles_file.exists() else {}
        profiles.pop(name, None)
        _prompt_profiles_file.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING delete_prompt_profile: {e}")
    return Response('{"ok":true}', mimetype="application/json")


# ───────────────────────────────────────────────────────────────────────
# Welcome message (CRUD + evolve via LLM)
# ───────────────────────────────────────────────────────────────────────


@bp.route("/api/welcome", methods=["GET"])
def api_welcome_get():
    return Response(json.dumps(_get_welcome_data(), ensure_ascii=False), mimetype="application/json")


@bp.route("/api/welcome", methods=["POST"])
def api_welcome_post():
    data = request.get_json(force=True)
    welcome = _get_welcome_data()
    welcome.update(data)
    welcome["last_updated"] = datetime.date.today().isoformat()
    _welcome_file.write_text(json.dumps(welcome, indent=2, ensure_ascii=False), encoding="utf-8")
    return Response('{"ok":true}', mimetype="application/json")


@bp.route("/api/welcome/reset", methods=["POST"])
def api_welcome_reset():
    _reset_welcome()
    welcome = _get_welcome_data()
    _welcome_file.write_text(json.dumps(welcome, indent=2, ensure_ascii=False), encoding="utf-8")
    return Response('{"ok":true}', mimetype="application/json")


@bp.route("/api/welcome/evolve", methods=["POST"])
def api_welcome_evolve():
    """Demande à l'IA d'enrichir le message en fonction des nouveautés."""
    data = request.get_json(force=True)
    context = data.get("context", "")
    welcome = _get_welcome_data()
    current = "\n".join(welcome.get("lines", []))
    prompt = (
        f"Tu es JARVIS, IA personnelle de Marc. "
        f"Voici le message d'accueil actuel:\n{current}\n\n"
        f"Nouveauté à intégrer: {context}\n\n"
        f"Réécris le message d'accueil en JSON avec la clé 'lines' (liste de strings). "
        f"Garde le ton JARVIS: sobre, technique, immersif, en français. "
        f"Max 15 lignes. Réponds UNIQUEMENT avec le JSON."
    )
    try:
        resp = _ollama_circuit.call(req.post, f"{_ollama_url}/api/generate",
                        json={"model": _get_model(), "prompt": prompt, "stream": False, "keep_alive": 0},
                        timeout=60)
        text = resp.json().get("response", "")
        m = re.search(r'\{[\s\S]*"lines"[\s\S]*\}', text)
        if m:
            parsed = json.loads(m.group())
            welcome["lines"] = parsed["lines"]
            welcome["last_updated"] = datetime.date.today().isoformat()
            welcome["updated_by"] = "IA"
            _welcome_file.write_text(json.dumps(welcome, indent=2, ensure_ascii=False), encoding="utf-8")
            return Response(json.dumps({"ok": True, "data": welcome}, ensure_ascii=False), mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"ok": False, "error": str(e)}), mimetype="application/json")
    return Response('{"ok":false,"error":"parse failed"}', mimetype="application/json")


# ───────────────────────────────────────────────────────────────────────
# DSP params + DSP process audio
# ───────────────────────────────────────────────────────────────────────


@bp.route("/api/dsp/process-audio", methods=["POST"])
def api_dsp_process_audio():
    """Reçoit bytes audio (WAV/MP3/OGG), applique la chaîne DSP+FX complète, retourne audio traité."""
    cl = request.content_length or 0
    if cl > _dsp_max_bytes:
        return Response('{"error":"audio trop volumineux (max 50 MB)"}', status=413, mimetype="application/json")
    audio_bytes = request.data
    if not audio_bytes:
        return Response('{"error":"no data"}', status=400, mimetype="application/json")
    try:
        result, mime = _apply_dsp_to_mp3_fn(audio_bytes)
        return Response(result, mimetype=mime)
    except Exception as e:
        _log.error(f"[DSP/process-audio] Erreur: {e}")
        return Response(audio_bytes, mimetype="audio/wav")


@bp.route("/api/dsp-params", methods=["GET"])
def api_get_dsp_params():
    return Response(json.dumps(_get_dsp_params()), mimetype="application/json")


@bp.route("/api/dsp-params", methods=["POST"])
def api_set_dsp_params():
    data = request.json or {}
    dsp_params = _get_dsp_params()
    sanitized = {}
    for k, v in data.items():
        if k not in dsp_params:
            continue
        orig = dsp_params[k]
        if k in _dsp_safe_str:
            if isinstance(v, str) and v in _dsp_safe_str[k]:
                sanitized[k] = v
        elif isinstance(orig, bool):
            sanitized[k] = bool(v)
        elif isinstance(orig, (int, float)) and isinstance(v, (int, float)):
            lo, hi = _dsp_bounds.get(k, (-9999, 9999))
            clamped = max(lo, min(hi, v))
            sanitized[k] = int(round(clamped)) if isinstance(orig, int) else round(float(clamped), 6)
        elif isinstance(orig, str):
            sanitized[k] = str(v)[:128]
    dsp_params.update(sanitized)
    try:
        _dsp_params_file.write_text(json.dumps(dsp_params, indent=2), encoding="utf-8")
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING save_dsp_params: {e}")
    return Response(json.dumps({"ok": True}), mimetype="application/json")


# ───────────────────────────────────────────────────────────────────────
# Models (list / test / set)
# ───────────────────────────────────────────────────────────────────────


@bp.route("/api/models", methods=["GET"])
def api_models():
    models = _fetch_ollama_models_fn()
    return Response(json.dumps({"models": models, "current": _get_model()}), mimetype="application/json")


@bp.route("/api/models/test", methods=["POST"])
def api_model_test():
    """Teste le modèle LLM actif avec une requête minimale et mesure la latence."""
    model = (request.json or {}).get("model", _get_model())
    if model not in _get_models():
        return Response(json.dumps({"ok": False, "error": "Modèle inconnu"}), status=400, mimetype="application/json")
    try:
        t0 = time.time()
        r = _ollama_circuit.call(req.post,
            f"{_ollama_url}/api/chat",
            json={"model": model, "messages": [{"role": "user", "content": "Réponds uniquement: OK"}],
                  "stream": False, "options": {"num_predict": 5, "temperature": 0}},
            timeout=_ollama_tool_detect_timeout_s
        )
        latency = round((time.time() - t0) * 1000)
        if r.status_code == 200:
            reply = r.json().get("message", {}).get("content", "").strip()
            return Response(json.dumps({"ok": True, "model": model, "latency_ms": latency, "reply": reply}),
                            mimetype="application/json")
        return Response(json.dumps({"ok": False, "model": model, "error": f"HTTP {r.status_code}"}),
                        mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"ok": False, "model": model, "error": str(e)}), mimetype="application/json")


@bp.route("/api/models", methods=["POST"])
def api_set_model():
    model = (request.json or {}).get("model", "")
    if model in _get_models():
        with _model_lock:
            _set_model(model)
            _save_model_fn()
        profile_name, profile_content = _get_model_profile_fn(model)
        if profile_content is not None:
            _set_system_prompt(profile_content)
            _prompt_file.write_text(_get_system_prompt(), encoding="utf-8")
            _set_auto_profile_model(model)
        elif _get_auto_profile_model() is not None:
            _set_system_prompt(_default_system_prompt)
            _prompt_file.write_text(_get_system_prompt(), encoding="utf-8")
            _set_auto_profile_model(None)
            profile_name = None
        return Response(json.dumps({"ok": True, "model": _get_model(), "auto_profile": profile_name}),
                        mimetype="application/json")
    return Response(json.dumps({"ok": False}), mimetype="application/json", status=400)
