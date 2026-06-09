"""Tuile **system** — diagnostics matériel/OS/LLM exposés via /api/sysdiag.

Architecture par tuiles (refactor jarvis.py étape 3, 2026-05-23) — *première
tuile pilote*. Objectif structurel : chaque feature de JARVIS devient une
tuile **autoportante** (zéro import vers `jarvis.py`), réutilisable telle
quelle dans un autre projet Flask après un `app.register_blueprint(bp)`.

Public surface :
- `bp`     : Flask Blueprint à enregistrer dans l'ossature.
- `init()` : injection unique des dépendances (speak + limiter + URL +
             chemins + accesseurs runtime).

Sous-modules :
- `diag`   : 5 fonctions `_diag_*` (GPU/CPU/RAM/disk/Ollama/mémoire).
- `routes` : view function `api_sysdiag` qui agrège les diags + métadonnées
             transverses (LLM model/voice, DSP/DeepFilter).
"""
from flask import Blueprint

bp = Blueprint("system", __name__)

# Import des sous-modules APRÈS la création de bp pour que les décorateurs
# @bp.route s'attachent à l'objet déjà construit.
from . import diag, routes  # noqa: E402,F401


def init(*, speak, limiter, ollama_url, memory_file, nvml_handle, memory_limit,
         get_model, get_voice, get_dsp_avail, get_dsp_params, get_df_status,
         get_mode=None, get_toks_per_sec=None, get_rag_status=None,
         get_stt_state=None, get_speak_status=None, get_soc_status=None,
         get_active_tts=None) -> None:
    """Injecte toutes les dépendances de la tuile et applique les rate limits.

    Doit être appelée avant `app.register_blueprint(bp)` côté ossature.
    """
    diag.init(speak=speak, ollama_url=ollama_url, memory_file=memory_file)
    routes.init_routes(
        get_nvml_handle  = lambda: nvml_handle,
        get_memory_limit = lambda: memory_limit,
        get_model        = get_model,
        get_voice        = get_voice,
        get_dsp_avail    = get_dsp_avail,
        get_dsp_params   = get_dsp_params,
        get_df_status    = get_df_status,
        get_mode         = get_mode,
        get_toks_per_sec = get_toks_per_sec,
        get_rag_status   = get_rag_status,
        get_stt_state    = get_stt_state,
        get_speak_status = get_speak_status,
        get_soc_status   = get_soc_status,
        get_active_tts   = get_active_tts,
    )
    limiter.limit("30 per minute")(routes.api_sysdiag)
    limiter.limit("30 per minute")(routes.api_jarvis_state)
