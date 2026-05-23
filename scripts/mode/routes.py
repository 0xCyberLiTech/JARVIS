"""Route /api/mode — GET (état) + POST (change mode + swap VRAM).

Extrait de jarvis.py étape 37 (2026-05-23). Le mode = dispatcher haut niveau
qui détermine quel modèle LLM JARVIS utilise (et accessoirement si l'auto-engine
SOC est actif — uniquement en mode soc, règle ABSOLUE `feedback_jarvis_no_regression`).

Au switch de mode (POST), `ensure_vram` est appelé pour décharger l'ancien
modèle Ollama et préload le nouveau — opération qui prend 1-3s sur RTX 5080.
L'UI a un indicateur visuel `mode-loading` (étape 36) pour signaler ce délai.
"""
import json

from flask import Response, request

from . import bp

# ── DI placeholders ───────────────────────────────────────────────────────────
_log = None
_limiter = None
_get_jarvis_mode = None
_set_jarvis_mode = None
_get_model = None              # callable → MODEL courant (SOC par défaut)
_general_model = ""
_code_model = ""
_code_reasoning_model = ""
_ensure_vram = None            # callable(model_str) → swap VRAM


def init(*, limiter, log, get_jarvis_mode, set_jarvis_mode, get_model,
         general_model, code_model, code_reasoning_model, ensure_vram) -> None:
    """Injecte les deps nécessaires à la route /api/mode."""
    global _log, _limiter, _get_jarvis_mode, _set_jarvis_mode, _get_model
    global _general_model, _code_model, _code_reasoning_model, _ensure_vram
    _log = log
    _limiter = limiter
    _get_jarvis_mode = get_jarvis_mode
    _set_jarvis_mode = set_jarvis_mode
    _get_model = get_model
    _general_model = general_model
    _code_model = code_model
    _code_reasoning_model = code_reasoning_model
    _ensure_vram = ensure_vram
    # Rate limit appliqué tardivement (route déjà enregistrée par @bp.route ci-dessous)
    _limiter.limit("30 per minute")(api_mode)


def _model_for_mode(mode: str) -> str:
    """Résout le nom Ollama du modèle correspondant au mode."""
    if mode == "general":         return _general_model
    if mode == "code":            return _code_model
    if mode == "code_reasoning":  return _code_reasoning_model
    return _get_model()  # soc + fallback = MODEL Ollama actif


@bp.route("/api/mode", methods=["GET", "POST"])
def api_mode():
    """GET : état courant. POST : change le mode + déclenche swap VRAM si différent."""
    if request.method == "POST":
        data = request.json or {}
        new_mode = data.get("mode", "").lower()
        if new_mode not in ("soc", "general", "code", "code_reasoning"):
            return Response(
                json.dumps({"error": "mode invalide (soc|general|code|code_reasoning)"}),
                status=400, mimetype="application/json")
        prev_mode = _get_jarvis_mode()
        if new_mode != prev_mode:
            _set_jarvis_mode(new_mode)
            _log.info(f"[JARVIS] Mode {prev_mode} → {new_mode}")
            # _ensure_vram est protégé par _VRAM_LOCK (llm/vram.py) : sérialise
            # check + swap + mutation. Plus de chemin direct vers _ollama_swap
            # qui contournerait le lock.
            _ensure_vram(_model_for_mode(new_mode))
    current_mode = _get_jarvis_mode()
    return Response(
        json.dumps({"mode": current_mode, "model": _model_for_mode(current_mode)}),
        mimetype="application/json")
