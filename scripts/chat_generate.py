"""Chat generate — wrapper top-level avec error handling et signal stream actif.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 29 (Chat/LLM core).
DERNIER sous-module Chat/LLM core extractible avec ROI raisonnable.

Pré-conditions au démarrage du stream :
1. Drain la queue `_speak_deferred` (vide les messages non envoyés du tour précédent)
2. Set le flag `_chat_stream_active` (utilisé par `speak()` pour différer en queue)

Pendant le stream : délègue à `chat_stream_inner_fn`.
Si exception : log + yield message d'erreur SSE.
Finally : clear le flag (libère speak() pour reprendre l'enfilage direct).

Dependency injection : la queue, l'event et l'orchestrateur passés en kwargs.
"""
import json
import queue as _queue_mod
import traceback


def chat_generate(
    ctx,  # LlmCtx
    no_tools: bool = False,
    *,
    deferred_queue,
    stream_active_event,
    stream_inner_fn,
    log_error_fn,
):
    """Top-level chat generator avec error handling et signal stream actif.

    Yields : SSE events depuis `stream_inner_fn`, ou un token d'erreur si exception.

    `deferred_queue` : `_speak_deferred` (drain initial)
    `stream_active_event` : `_chat_stream_active` threading.Event
    `stream_inner_fn(ctx, no_tools) -> generator` : orchestrateur (ex: `_chat_stream_inner`)
    `log_error_fn(msg)` : `_log.error`
    """
    # Drain les messages TTS différés du tour précédent
    try:
        while True:
            deferred_queue.get_nowait()
    except _queue_mod.Empty:
        pass  # get_nowait() raises Empty when queue is drained — expected

    stream_active_event.set()
    try:
        yield from stream_inner_fn(ctx, no_tools)
    except Exception as exc:
        log_error_fn(f"[api_chat] stream error: {traceback.format_exc()}")
        yield f"data: {json.dumps({'type':'token','token':f'[JARVIS] Erreur interne : {exc}','done':True})}\n\n"
    finally:
        stream_active_event.clear()
