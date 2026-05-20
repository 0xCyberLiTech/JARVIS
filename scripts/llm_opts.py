"""LLM Opts builder — construction des options Ollama selon contexte (zéro IO).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 23 (Chat/LLM core).

Fonction pure : prend les flags runtime (np_override, soc_*, model, msg_len)
→ retourne un dict d'options Ollama optimisé.

Logique :
- Mode SOC (ctx injecté ou trigger) → température 0.2, num_ctx 8192, et plancher num_predict
  768 pour modèles reasoning (reasoning|deepseek-r1) pour éviter raisonnement tronqué
- Requête courte hors SOC (<200 chars) → num_ctx 4096 (économise KV cache VRAM)
- Sinon → defaults Ollama (retourne None si aucune option à override)
"""
import re

# ── Constantes par défaut (override possible via DI) ──────────
DEFAULT_SOC_TEMPERATURE = 0.2     # SOC déterministe
DEFAULT_SOC_NUM_CTX     = 8192    # contexte SOC — abaissé de 16384 le 2026-05-20 (KV cache -1.7 Go, anti-éviction VRAM)
DEFAULT_NUM_CTX_SHORT   = 4096    # requête courte → économie KV cache
DEFAULT_REASONING_NP_MIN = 768    # plancher num_predict modèles reasoning en SOC

# Pattern modèles reasoning (qwen3, phi4-reasoning, deepseek-r1, etc.)
REASONING_RE = re.compile(r'reasoning|deepseek-r1', re.I)


def build_llm_opts(
    np_override,
    soc_ctx_injected: bool,
    soc_trigger: bool,
    active_model: str | None,
    msg_len: int = 0,
    *,
    default_model: str,
    llm_params: dict,
    soc_temperature: float = DEFAULT_SOC_TEMPERATURE,
    soc_num_ctx: int = DEFAULT_SOC_NUM_CTX,
    num_ctx_short: int = DEFAULT_NUM_CTX_SHORT,
    reasoning_np_min: int = DEFAULT_REASONING_NP_MIN,
) -> dict | None:
    """Construit les options LLM adaptatives selon le contexte SOC, le modèle et la longueur du message.

    Retourne un dict d'options Ollama, ou None si aucune option à override (= defaults).
    """
    try:
        np = int(np_override) if np_override is not None else None
    except (ValueError, TypeError):
        np = None

    # Plancher num_predict pour modèles reasoning en mode SOC
    if np and soc_ctx_injected:
        if REASONING_RE.search(active_model or default_model):
            np = max(np, reasoning_np_min)

    opts: dict = {}
    if np:
        opts["num_predict"] = np

    if soc_ctx_injected or soc_trigger:
        opts["temperature"] = soc_temperature
        opts["num_ctx"] = soc_num_ctx
    elif msg_len > 0 and msg_len < 200:
        opts["num_ctx"] = min(num_ctx_short, llm_params.get("num_ctx", num_ctx_short))

    return opts or None
