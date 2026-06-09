"""Stream LLM — generator SSE Ollama /api/chat + filtre think tags.

Extrait de jarvis.py étape 35 (2026-05-23). Cœur du streaming LLM :
appelle `Ollama /api/chat` en streaming, parse les chunks JSON ligne par
ligne, filtre les blocs `<think>...</think>` des modèles de raisonnement
(phi4-reasoning, deepseek-r1, qwen3 — qui émettent leur raisonnement
interne avant la réponse finale), et yield les tokens nettoyés au client.

- `think_filter_step(tbuf, in_think)` : un pas du filtre — gère les tags
  à cheval sur plusieurs tokens (buffer partiel en fin) et les `</think>`
  orphelins (émis sans `<think>` précédent par phi4-reasoning)
- `stream_llm(messages, model_override, options_override)` : generator
  principal — yield `(tokens, done)` pour chaque chunk Ollama. Circuit
  breaker actif : refus immédiat 1 ms si Ollama down (vs timeout 30 s).

DI via `init(...)` — circuit Ollama + getter MODEL + getter LLM_PARAMS +
URL + timeout + setter _last_toks_per_sec.
"""
import json

from .config import OLLAMA_URL as _OLLAMA_URL_DEFAULT

# ── DI placeholders ───────────────────────────────────────────────────────────
_log = None
_ollama_circuit = None
_OllamaUnavailable = None
_req = None
_ollama_url = _OLLAMA_URL_DEFAULT  # placeholder DI — remplacé par init()
_ollama_stream_timeout_s = 240
_get_model = None
_get_llm_params = None
_set_last_toks_per_sec = None


def init(
    *,
    log,
    ollama_circuit,
    ollama_unavailable_exc,
    req,
    ollama_url: str,
    ollama_stream_timeout_s: int,
    get_model,
    get_llm_params,
    set_last_toks_per_sec,
) -> None:
    """Injecte les deps streaming Ollama."""
    global _log, _ollama_circuit, _OllamaUnavailable, _req
    global _ollama_url, _ollama_stream_timeout_s
    global _get_model, _get_llm_params, _set_last_toks_per_sec
    _log = log
    _ollama_circuit = ollama_circuit
    _OllamaUnavailable = ollama_unavailable_exc
    _req = req
    _ollama_url = ollama_url
    _ollama_stream_timeout_s = ollama_stream_timeout_s
    _get_model = get_model
    _get_llm_params = get_llm_params
    _set_last_toks_per_sec = set_last_toks_per_sec


def think_filter_step(tbuf: str, in_think: bool):
    """Un pas du filtre <think>…</think> sur le buffer courant.

    Retourne (chars_à_émettre, nouveau_tbuf, nouveau_in_think, stop).
    Gère les tags à cheval sur plusieurs tokens (buffer partiel en fin).
    Gère aussi les </think> orphelins (émis sans <think> précédent par
    phi4-reasoning).
    """
    if not in_think:
        idx = tbuf.find('<think>')
        if idx == -1:
            ci = tbuf.find('</think>')
            if ci != -1:
                return tbuf[:ci] + tbuf[ci + 8:], "", False, True
            for plen in range(min(7, len(tbuf)), 0, -1):
                if tbuf[-plen:] == '<think>'[:plen]:
                    return tbuf[:-plen], tbuf[-plen:], False, True
            return tbuf, "", False, True
        return tbuf[:idx], tbuf[idx + 7:], True, False
    idx = tbuf.find('</think>')
    if idx == -1:
        return "", "", True, True   # tout le buffer est du thinking — jeter
    return "", tbuf[idx + 8:], False, False


def stream_llm(messages, model_override=None, options_override=None):
    """Generator — stream de tokens (Ollama local).

    `options_override` : dict partiel pour surcharger LLM_PARAMS (ex:
    `{"num_predict": 512}`). Filtre les blocs `<think>...</think>` des
    modèles de raisonnement (phi4-reasoning, deepseek-r1).
    """
    messages_with_prefill = messages + [{"role": "assistant", "content": ""}]
    llm_params = _get_llm_params()
    opts = {
        "temperature":    llm_params["temperature"],
        "num_predict":    llm_params["num_predict"],
        "top_p":          llm_params["top_p"],
        "top_k":          llm_params["top_k"],
        "repeat_penalty": llm_params["repeat_penalty"],
        "num_ctx":        llm_params.get("num_ctx", 2048),
    }
    if options_override:
        opts.update(options_override)
    # "think" appartient au payload top-level Ollama (pas à options dict) — extrait ici
    think_val = opts.pop("think", None)
    active_model_name = model_override or _get_model()
    payload = {
        "model":      active_model_name,
        "messages":   messages_with_prefill,
        "stream":     True,
        "keep_alive": "30m",
        "options":    opts,
        "think":      think_val if think_val is not None else llm_params.get("think", False),
    }
    _in_think = False
    _tbuf     = ""
    # Circuit breaker : si Ollama est down (3 erreurs récentes), refus immédiat
    # (1 ms au lieu de 30 s timeout)
    try:
        resp = _ollama_circuit.call(
            _req.post, f"{_ollama_url}/api/chat",
            json=payload, stream=True, timeout=_ollama_stream_timeout_s
        )
    except _OllamaUnavailable as e:
        yield f"[JARVIS] {e}", True
        return
    with resp:
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue  # ligne Ollama malformée — on saute sans casser le flux
            msg   = chunk.get("message", {})
            done  = chunk.get("done", False)
            if done:
                ec = chunk.get("eval_count", 0)
                ed = chunk.get("eval_duration", 0)
                if ec and ed:
                    _set_last_toks_per_sec(round(ec / (ed / 1e9), 1))
            # Nouvelle API Ollama : champ .thinking séparé → ignorer
            if msg.get("thinking"):
                if done:
                    yield "", True
                continue
            raw = msg.get("content", "")
            if not raw:
                if done:
                    yield "", True
                continue
            _tbuf += raw
            out = ""
            while _tbuf:
                chunk_out, _tbuf, _in_think, stop = think_filter_step(_tbuf, _in_think)
                out += chunk_out
                if stop:
                    break
            if out or done:
                yield out, done
