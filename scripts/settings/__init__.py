"""Tuile **settings** — config LLM, prompt, profils, welcome, modèles, DSP.

11ème tuile autoportante (refactor jarvis.py étape 17, 2026-05-23).
16 endpoints `/api/llm-params`, `/api/prompt-profiles*`, `/api/welcome*`,
`/api/dsp-params`, `/api/dsp/process-audio`, `/api/models*`.

DI lourd (~25 deps) — c'est inhérent : les routes config touchent au
runtime mutable (LLM_PARAMS, SYSTEM_PROMPT, DSP_PARAMS, MODEL, MODELS).
"""
from flask import Blueprint

bp = Blueprint("settings", __name__)

from . import routes  # noqa: E402,F401

_ROUTE_LIMITS = {
    "api_llm_params_get":         "60 per minute",
    "api_llm_params_set":         "20 per minute",
    "api_reset_prompt":           "10 per minute",
    "api_prompt_profiles_get":    "60 per minute",
    "api_prompt_profiles_save":   "20 per minute",
    "api_prompt_profiles_delete": "10 per minute",
    "api_welcome_get":            "60 per minute",
    "api_welcome_post":           "20 per minute",
    "api_welcome_reset":          "10 per minute",
    "api_welcome_evolve":         "5 per minute",
    "api_dsp_process_audio":      "30 per minute",
    "api_get_dsp_params":         "60 per minute",
    "api_set_dsp_params":         "20 per minute",
    "api_models":                 "30 per minute",
    "api_model_test":             "5 per minute",
    "api_set_model":              "20 per minute",
}


def init(*, limiter, **kwargs) -> None:
    """Injecte toutes les dépendances et applique les rate limits."""
    routes.init_routes(**kwargs)
    for fn_name, limit_str in _ROUTE_LIMITS.items():
        fn = getattr(routes, fn_name, None)
        if fn is not None:
            limiter.limit(limit_str)(fn)
