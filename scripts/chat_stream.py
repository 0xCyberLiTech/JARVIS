"""Chat stream — orchestrateur du pipeline LLM streaming.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 28 (Chat/LLM core).

Coordonne les étapes du chat streaming :
1. Ensure VRAM (préchargement modèle Ollama)
2. Tool calling (appels d'outils LLM si activés)
3. Build LLM opts adaptatives (SOC ctx, msg_len, model)
4. Stream tokens + TTS (génération réponse + découpage phrases)
5. Flush deferred speak (rejoue messages background mis en attente)

Dependency injection : tous les helpers passés en kwargs.
"""


def stream_inner(
    ctx,  # LlmCtx namedtuple
    no_tools: bool = False,
    temp_override=None,
    *,
    ensure_vram_fn,
    run_tool_calls_fn,
    build_llm_opts_fn,
    stream_tokens_tts_fn,
    flush_deferred_speak_fn,
):
    """Orchestrateur SSE : tool calling → stream tokens+TTS → flush différés.

    `ctx` : LlmCtx(messages, model, np_override, soc_ctx, soc_trigger)
    `no_tools` : True pour mode CODE-TERM (pas d'appels d'outils)
    `temp_override` : surcharge température (None = défaut)

    Yields : SSE events (token + speak + tool + tool_result).
    """
    ensure_vram_fn(ctx.model)
    current_messages = list(ctx.messages)
    if not no_tools:
        yield from run_tool_calls_fn(current_messages, ctx.model)
    msg_len = len(next((m["content"] for m in reversed(current_messages) if m.get("role") == "user"), ""))
    opts = build_llm_opts_fn(ctx.np_override, ctx.soc_ctx, ctx.soc_trigger, ctx.model, msg_len)
    if temp_override is not None:
        if opts is None:
            opts = {}
        opts["temperature"] = temp_override
    yield from stream_tokens_tts_fn(current_messages, ctx.model, opts)
    yield from flush_deferred_speak_fn()
