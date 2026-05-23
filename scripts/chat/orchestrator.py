"""Orchestration chat — wrappers DI entre l'ossature et les sous-modules `chat.*`.

Tuile `chat` Phase B (refactor jarvis.py étape 12, 2026-05-23). Ces wrappers
étaient des fonctions 3-5 lignes dans `jarvis.py` qui jouaient le rôle de
**seam DI** entre l'état runtime (MODEL, LLM_PARAMS, queues, événements, …) et
les sous-modules `chat.{capture, generate, messages, …}` déjà extraits à plat.

En les déplaçant ici, la tuile **chat possède son orchestration** — `jarvis.py`
n'est plus que l'ossature qui injecte les dépendances une seule fois via
`init()`, puis appelle les wrappers via les aliases conservés pour
compatibilité jusqu'à ce que `api_chat` migre dans `routes.py` (étape 13).

Public surface :
- `LlmCtx`         : namedtuple `(messages, model, np_override, soc_ctx, soc_trigger)`.
- `_LAST_EXCHANGES`: deque max 10 — historique des derniers échanges chat.
- `init(...)`      : injection unique des ~25 dépendances runtime.
- Wrappers : `_chat_inject_soc`, `_run_tool_calls`, `_build_llm_opts`,
             `_stream_tokens_tts`, `_flush_deferred_speak`, `_code_reasoning_gen`,
             `_chat_stream_inner`, `_capture_gen`, `_chat_resolve_pending_bypass`,
             `_chat_generate`, `_chat_build_system_prompt`, `_chat_resolve_model`.
"""
from collections import deque, namedtuple

from . import (
    capture,
    generate,
    pending_bypass,
    routing,
    soc_inject,
    stream,
    system_prompt,
    tool_calls,
)

LlmCtx = namedtuple('LlmCtx', ['messages', 'model', 'np_override', 'soc_ctx', 'soc_trigger'])
_LAST_EXCHANGES: deque = deque(maxlen=10)

# ── Dépendances injectées par init() — depuis l'ossature jarvis.py ───────
# Modules / services / loggers
_log = None
_security = None
_llm_opts_mod = None
_stream_tokens_mod = None
_voice_deferred_speak = None
_code_reasoning_mod = None
_bypass_pve = None

# Fonctions injectées
_fetch_monitoring_fn = None
_build_monitoring_context_fn = None
_fetch_defense_fn = None
_call_llm_with_tools_fn = None
_execute_tool_fn = None
_ensure_vram_fn = None
_stream_llm_fn = None
_clean_for_tts_fn = None
_facts_inject_fn = None
_rag_inject_fn = None
_web_search_fn = None
_chat_inject_pve_fn = None
_apt_upgrade_sse_fn = None
_reboot_machine_sse_fn = None
_sse_response_fn = None
_sse_tok_fn = None

# Etats mutables (dicts/queues/events) — partagés par référence avec l'ossature
_tool_dispatch = None
_apt_host_map = None
_pending_infra_cmd = None
_pending_reboot = None
_speak_deferred = None
_chat_stream_active = None

# Accesseurs runtime (lambdas) — pour les valeurs réassignées (MODEL, _jarvis_mode)
_get_system_prompt = None
_get_model = None
_get_mode = None

# Constantes
_general_model = ""
_code_model = ""
_code_reasoning_analysis_model = ""
_code_system_suffix = ""
_ollama_url = ""
_llm_params = None
_soc_temperature = 0.0
_soc_num_ctx = 0
_num_ctx_short = 0
_reasoning_np_min = 0
_tts_phrase_min = 0
_tool_call_max = 0
_tool_result_trunc = 0
_pending_apt_ttl_s = 0
_confirm_re = None
_cancel_re = None
_rag_relevant_kw = None


def init(*,
         # services / modules
         log, security, llm_opts_mod, stream_tokens_mod, voice_deferred_speak,
         code_reasoning_mod, bypass_pve,
         # fonctions
         fetch_monitoring, build_monitoring_context, fetch_defense,
         call_llm_with_tools, execute_tool, ensure_vram, stream_llm,
         clean_for_tts, facts_inject, rag_inject, web_search, chat_inject_pve,
         apt_upgrade_sse, reboot_machine_sse, sse_response, sse_tok,
         # états mutables
         tool_dispatch, apt_host_map, pending_infra_cmd, pending_reboot,
         speak_deferred, chat_stream_active,
         # accesseurs runtime
         get_system_prompt, get_model, get_mode,
         # constantes
         general_model, code_model, code_reasoning_analysis_model,
         code_system_suffix, ollama_url, llm_params,
         soc_temperature, soc_num_ctx, num_ctx_short, reasoning_np_min,
         tts_phrase_min, tool_call_max, tool_result_trunc,
         pending_apt_ttl_s, confirm_re, cancel_re, rag_relevant_kw) -> None:
    """Injecte les ~30 dépendances runtime nécessaires aux wrappers."""
    global _log, _security, _llm_opts_mod, _stream_tokens_mod, _voice_deferred_speak
    global _code_reasoning_mod, _bypass_pve
    global _fetch_monitoring_fn, _build_monitoring_context_fn, _fetch_defense_fn
    global _call_llm_with_tools_fn, _execute_tool_fn, _ensure_vram_fn
    global _stream_llm_fn, _clean_for_tts_fn, _facts_inject_fn, _rag_inject_fn
    global _web_search_fn, _chat_inject_pve_fn
    global _apt_upgrade_sse_fn, _reboot_machine_sse_fn, _sse_response_fn, _sse_tok_fn
    global _tool_dispatch, _apt_host_map, _pending_infra_cmd, _pending_reboot
    global _speak_deferred, _chat_stream_active
    global _get_system_prompt, _get_model, _get_mode
    global _general_model, _code_model, _code_reasoning_analysis_model
    global _code_system_suffix, _ollama_url, _llm_params
    global _soc_temperature, _soc_num_ctx, _num_ctx_short, _reasoning_np_min
    global _tts_phrase_min, _tool_call_max, _tool_result_trunc
    global _pending_apt_ttl_s, _confirm_re, _cancel_re, _rag_relevant_kw

    _log = log
    _security = security
    _llm_opts_mod = llm_opts_mod
    _stream_tokens_mod = stream_tokens_mod
    _voice_deferred_speak = voice_deferred_speak
    _code_reasoning_mod = code_reasoning_mod
    _bypass_pve = bypass_pve
    _fetch_monitoring_fn = fetch_monitoring
    _build_monitoring_context_fn = build_monitoring_context
    _fetch_defense_fn = fetch_defense
    _call_llm_with_tools_fn = call_llm_with_tools
    _execute_tool_fn = execute_tool
    _ensure_vram_fn = ensure_vram
    _stream_llm_fn = stream_llm
    _clean_for_tts_fn = clean_for_tts
    _facts_inject_fn = facts_inject
    _rag_inject_fn = rag_inject
    _web_search_fn = web_search
    _chat_inject_pve_fn = chat_inject_pve
    _apt_upgrade_sse_fn = apt_upgrade_sse
    _reboot_machine_sse_fn = reboot_machine_sse
    _sse_response_fn = sse_response
    _sse_tok_fn = sse_tok
    _tool_dispatch = tool_dispatch
    _apt_host_map = apt_host_map
    _pending_infra_cmd = pending_infra_cmd
    _pending_reboot = pending_reboot
    _speak_deferred = speak_deferred
    _chat_stream_active = chat_stream_active
    _get_system_prompt = get_system_prompt
    _get_model = get_model
    _get_mode = get_mode
    _general_model = general_model
    _code_model = code_model
    _code_reasoning_analysis_model = code_reasoning_analysis_model
    _code_system_suffix = code_system_suffix
    _ollama_url = ollama_url
    _llm_params = llm_params
    _soc_temperature = soc_temperature
    _soc_num_ctx = soc_num_ctx
    _num_ctx_short = num_ctx_short
    _reasoning_np_min = reasoning_np_min
    _tts_phrase_min = tts_phrase_min
    _tool_call_max = tool_call_max
    _tool_result_trunc = tool_result_trunc
    _pending_apt_ttl_s = pending_apt_ttl_s
    _confirm_re = confirm_re
    _cancel_re = cancel_re
    _rag_relevant_kw = rag_relevant_kw


# ────────────────────────────────────────────────────────────────────────────
# Wrappers DI — délégation aux sous-modules chat.* avec deps runtime
# ────────────────────────────────────────────────────────────────────────────


def _chat_inject_soc(system, last_user, is_vocal, soc_ctx_injected, force_soc=False):
    """Délègue à chat.soc_inject.inject() avec les helpers monitoring + defense_24h."""
    return soc_inject.inject(
        system, last_user, is_vocal, soc_ctx_injected, force_soc,
        fetch_monitoring_fn=_fetch_monitoring_fn,
        build_monitoring_context_fn=_build_monitoring_context_fn,
        fetch_defense_fn=_fetch_defense_fn,
    )


def _run_tool_calls(messages: list, active_model):
    """Délègue à chat.tool_calls.run_tool_calls() avec runtime deps."""
    import time
    yield from tool_calls.run_tool_calls(
        messages, active_model,
        call_llm_with_tools_fn=_call_llm_with_tools_fn,
        execute_tool_fn=_execute_tool_fn,
        tool_dispatch=_tool_dispatch,
        apt_host_map=_apt_host_map,
        pending_infra_cmd=_pending_infra_cmd,
        parse_upgradable_packages_fn=_security.parse_upgradable_packages,
        log_info_fn=_log.info,
        now_fn=time.time,
        tool_call_max=_tool_call_max,
        tool_result_trunc=_tool_result_trunc,
    )


def _build_llm_opts(np_override, soc_ctx_injected: bool, soc_trigger: bool, active_model, msg_len: int = 0):
    """Délègue à llm_opts.build_llm_opts() avec constantes runtime."""
    return _llm_opts_mod.build_llm_opts(
        np_override, soc_ctx_injected, soc_trigger, active_model, msg_len,
        default_model=_get_model(),
        llm_params=_llm_params,
        soc_temperature=_soc_temperature,
        soc_num_ctx=_soc_num_ctx,
        num_ctx_short=_num_ctx_short,
        reasoning_np_min=_reasoning_np_min,
    )


def _stream_tokens_tts(messages: list, active_model, opts):
    """Délègue à stream_tokens.stream_tokens_tts() avec stream_llm + _clean_for_tts."""
    yield from _stream_tokens_mod.stream_tokens_tts(
        messages, active_model, opts,
        stream_llm_fn=_stream_llm_fn,
        clean_text_fn=_clean_for_tts_fn,
        phrase_min=_tts_phrase_min,
    )


def _flush_deferred_speak():
    """Délègue à voice.deferred_speak.flush_deferred_speak() avec la queue runtime."""
    yield from _voice_deferred_speak.flush_deferred_speak(_speak_deferred)


def _code_reasoning_gen(messages, np_override):
    """Délègue à code_reasoning.code_reasoning_gen() avec deps runtime."""
    return _code_reasoning_mod.code_reasoning_gen(
        messages, np_override,
        ensure_vram_fn=_ensure_vram_fn,
        model=_code_reasoning_analysis_model,
        system_suffix=_code_system_suffix,
        ollama_url=_ollama_url,
        llm_params=_llm_params,
    )


def _chat_stream_inner(ctx, no_tools=False, temp_override=None):
    """Délègue à chat.stream.stream_inner() avec runtime helpers."""
    yield from stream.stream_inner(
        ctx, no_tools, temp_override,
        ensure_vram_fn=_ensure_vram_fn,
        run_tool_calls_fn=_run_tool_calls,
        build_llm_opts_fn=_build_llm_opts,
        stream_tokens_tts_fn=_stream_tokens_tts,
        flush_deferred_speak_fn=_flush_deferred_speak,
    )


def _capture_gen(gen, user_msg: str):
    """Délègue à chat.capture.capture_gen() avec _LAST_EXCHANGES."""
    return capture.capture_gen(gen, user_msg, _LAST_EXCHANGES)


def _chat_resolve_pending_bypass(orig_last: str):
    """Délègue à chat.pending_bypass.resolve_pending_bypass() avec runtime deps."""
    import time
    return pending_bypass.resolve_pending_bypass(
        orig_last,
        pending_infra_cmd=_pending_infra_cmd,
        pending_reboot=_pending_reboot,
        ttl_s=_pending_apt_ttl_s,
        confirm_re=_confirm_re,
        cancel_re=_cancel_re,
        reboot_now_re=_bypass_pve.REBOOT_NOW_RE,
        reboot_defer_re=_bypass_pve.REBOOT_DEFER_RE,
        apt_upgrade_sse_fn=_apt_upgrade_sse_fn,
        reboot_machine_sse_fn=_reboot_machine_sse_fn,
        sse_response_fn=_sse_response_fn,
        sse_tok_fn=_sse_tok_fn,
        log_info_fn=_log.info,
        now_fn=time.time,
    )


def _chat_generate(ctx, no_tools=False):
    """Délègue à chat.generate.chat_generate() avec runtime deps."""
    yield from generate.chat_generate(
        ctx, no_tools,
        deferred_queue=_speak_deferred,
        stream_active_event=_chat_stream_active,
        stream_inner_fn=_chat_stream_inner,
        log_error_fn=_log.error,
    )


def _chat_build_system_prompt(last_user: str, web_enabled: bool,
                              soc_ctx_injected: bool, is_vocal: bool,
                              force_soc: bool = False) -> tuple:
    """Délègue à chat.system_prompt.build() avec les helpers runtime."""
    return system_prompt.build(
        last_user, web_enabled, soc_ctx_injected, is_vocal,
        system_prompt=_get_system_prompt(),
        facts_inject_fn=_facts_inject_fn,
        rag_relevant_re=_rag_relevant_kw,
        rag_inject_fn=_rag_inject_fn,
        web_search_fn=_web_search_fn,
        soc_inject_fn=_chat_inject_soc,
        pve_inject_fn=_chat_inject_pve_fn,
        force_soc=force_soc,
    )


def _chat_resolve_model(is_vocal: bool, no_tools: bool, model_override=None) -> tuple:
    """Délègue à chat.routing.resolve_model() avec les constantes runtime."""
    return routing.resolve_model(
        is_vocal, no_tools, model_override,
        general_model=_general_model,
        code_model=_code_model,
        current_mode=_get_mode(),
    )
