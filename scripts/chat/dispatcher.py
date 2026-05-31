"""Dispatcher /api/chat — carrefour bypass + correction + routing LLM.

Extrait de jarvis.py étape 28 (2026-05-23) — phase B du refactor chat.
Cette tuile regroupe les 3 dernières fonctions du carrefour chat encore
dans jarvis.py :

- `chat_try_bypass(orig_last, is_vocal)` : tente les bypass LLM
  (pending_apt, datetime, backup, VM, reboot, update, restart service,
  fichier lecture, code SCP/exec, terminal SSH) — renvoie Response ou None
- `detect_file_corrections(orig_last, is_vocal)` : détecte les commandes
  "lis + corrige" mono ou multi-fichiers
- `api_chat()` : route Flask `/api/chat` (Blueprint `chat_dispatcher`),
  orchestrateur final : bypass → corrections → CR sortie anticipée →
  system prompt + RAG + SOC/PVE → routing modèle → dispatch correction
  ou _chat_generate

DI : énorme (~25 deps) car ce dispatcher est le point de jonction entre
tous les autres sous-systèmes. Plutôt que de mocker chaque dep, on injecte
au boot via `init(...)`. Les getters lambda (`get_system_prompt`,
`get_model`, `get_mode`) permettent de relire les globals jarvis mutables.
"""
import json

from flask import Blueprint, Response, request, stream_with_context

bp = Blueprint("chat_dispatcher", __name__)

# ── DI placeholders ───────────────────────────────────────────────────────────
_log = None
_limiter = None

# Modules
_bypass_simple = None
_bypass_fs = None
_bypass_wrap = None
_chat_orch = None

# Helpers SSE
_sse_response = None
_capture_gen = None
_vm_command_sse = None
_reboot_machine_sse = None
_reboot_machine_request_sse = None
_update_machine_sse = None
_service_restart_sse = None
_ssh_terminal_sse = None

# Helpers chat
_chat_resolve_pending_bypass = None
_chat_build_system_prompt = None
_chat_resolve_model = None
_chat_generate = None
_code_reasoning_gen = None
_chat_build_messages = None
_facts_inject = None
_file_correct_gen = None
_file_correct_multi_gen = None

# Tables / constantes
_FILE_VM_SSH = None
_FCORR_RE = None
_SSH_TERMINAL_RE = None
_SSH_TERMINAL_MAP = None
_CODE_DEV_VM = None
_SSE_HEADERS = None
_CODE_REASONING_MODE = "code_reasoning"
_CODE_MODEL = None
_CODE_SYSTEM_SUFFIX = ""
_LlmCtx = None

# Getters jarvis globals mutables
_get_system_prompt = None
_get_model = None
_get_mode = None


def init(
    *,
    log,
    limiter,
    bypass_simple,
    bypass_fs,
    bypass_wrap,
    chat_orch,
    sse_response,
    capture_gen,
    vm_command_sse,
    reboot_machine_sse,
    reboot_machine_request_sse,
    update_machine_sse,
    service_restart_sse,
    ssh_terminal_sse,
    chat_resolve_pending_bypass,
    chat_build_system_prompt,
    chat_resolve_model,
    chat_generate,
    code_reasoning_gen,
    chat_build_messages,
    facts_inject,
    file_correct_gen,
    file_correct_multi_gen,
    file_vm_ssh: dict,
    fcorr_re,
    ssh_terminal_re: dict,
    ssh_terminal_map: dict,
    code_dev_vm: str,
    sse_headers: dict,
    code_reasoning_mode: str,
    code_model: str,
    code_system_suffix: str,
    llm_ctx_cls,
    get_system_prompt,
    get_model,
    get_mode,
) -> None:
    """Injecte les ~30 deps consommées par le dispatcher."""
    global _log, _limiter
    global _bypass_simple, _bypass_fs, _bypass_wrap, _chat_orch
    global _sse_response, _capture_gen, _vm_command_sse, _reboot_machine_sse
    global _reboot_machine_request_sse
    global _update_machine_sse, _service_restart_sse, _ssh_terminal_sse
    global _chat_resolve_pending_bypass, _chat_build_system_prompt, _chat_resolve_model
    global _chat_generate, _code_reasoning_gen, _chat_build_messages, _facts_inject
    global _file_correct_gen, _file_correct_multi_gen
    global _FILE_VM_SSH, _FCORR_RE, _SSH_TERMINAL_RE, _SSH_TERMINAL_MAP
    global _CODE_DEV_VM, _SSE_HEADERS, _CODE_REASONING_MODE, _CODE_MODEL
    global _CODE_SYSTEM_SUFFIX, _LlmCtx
    global _get_system_prompt, _get_model, _get_mode

    _log = log
    _limiter = limiter
    _bypass_simple = bypass_simple
    _bypass_fs = bypass_fs
    _bypass_wrap = bypass_wrap
    _chat_orch = chat_orch
    _sse_response = sse_response
    _capture_gen = capture_gen
    _vm_command_sse = vm_command_sse
    _reboot_machine_sse = reboot_machine_sse
    _reboot_machine_request_sse = reboot_machine_request_sse
    _update_machine_sse = update_machine_sse
    _service_restart_sse = service_restart_sse
    _ssh_terminal_sse = ssh_terminal_sse
    _chat_resolve_pending_bypass = chat_resolve_pending_bypass
    _chat_build_system_prompt = chat_build_system_prompt
    _chat_resolve_model = chat_resolve_model
    _chat_generate = chat_generate
    _code_reasoning_gen = code_reasoning_gen
    _chat_build_messages = chat_build_messages
    _facts_inject = facts_inject
    _file_correct_gen = file_correct_gen
    _file_correct_multi_gen = file_correct_multi_gen
    _FILE_VM_SSH = file_vm_ssh
    _FCORR_RE = fcorr_re
    _SSH_TERMINAL_RE = ssh_terminal_re
    _SSH_TERMINAL_MAP = ssh_terminal_map
    _CODE_DEV_VM = code_dev_vm
    _SSE_HEADERS = sse_headers
    _CODE_REASONING_MODE = code_reasoning_mode
    _CODE_MODEL = code_model
    _CODE_SYSTEM_SUFFIX = code_system_suffix
    _LlmCtx = llm_ctx_cls
    _get_system_prompt = get_system_prompt
    _get_model = get_model
    _get_mode = get_mode

    # Application tardive du rate-limiter Flask-Limiter sur la route Blueprint
    if _limiter is not None:
        _limiter.limit("60 per minute")(api_chat)


# ── _chat_try_bypass ──────────────────────────────────────────────────────────

def chat_try_bypass(orig_last: str, is_vocal: bool):
    """Retourne une Response SSE si un bypass LLM est applicable, sinon None."""
    import time
    pending = _chat_resolve_pending_bypass(orig_last)
    if pending:
        return pending
    if _bypass_simple.DATETIME_RE.search(orig_last):
        _log.info("[BYPASS] datetime → réponse directe (zéro LLM)")
        return _sse_response(_bypass_simple.datetime_sse())
    # Routine post-MAJ : déclencheur VOCAL LECTURE-SEULE. Placé AVANT le gate
    # is_vocal pour fonctionner à la voix ; read-only (probe smoke/health) donc
    # sans risque vocal. JARVIS lit le verdict, le MENU exécute. FAIL-CLOSED.
    routine_cmd = _bypass_wrap.detect_routine_postmaj_command(orig_last)
    if routine_cmd:
        host_label, ssh_fn, is_proxmox = routine_cmd
        _log.info(f"[BYPASS_ROUTINE_POSTMAJ] {host_label} (verdict lecture-seule)")
        return _sse_response(_bypass_wrap.routine_postmaj_sse(host_label, ssh_fn, is_proxmox))
    if _bypass_wrap.routine_postmaj_re_matches(orig_last):
        _log.info("[BYPASS_ROUTINE_POSTMAJ] hôte ambigu → clarification vocale")
        return _sse_response(_bypass_wrap.routine_postmaj_clarify_sse())
    if is_vocal:
        return None
    backup_cmd = _bypass_wrap.detect_backup_command(orig_last)
    if backup_cmd:
        if backup_cmd == "backup-jarvis":
            return _sse_response(_bypass_wrap.jarvis_backup_sse())
        if backup_cmd == "backup-jarvis-log":
            return _sse_response(_bypass_wrap.jarvis_backup_log_sse())
        return _sse_response(_bypass_wrap.backup_sse(backup_cmd))
    vm_cmd = _bypass_wrap.detect_vm_command(orig_last)
    if vm_cmd:
        action, vm_list = vm_cmd
        return _sse_response(_vm_command_sse(action, vm_list))
    reboot_cmd = _bypass_wrap.detect_reboot_command(orig_last)
    if reboot_cmd:
        host_label, ssh_fn, is_proxmox = reboot_cmd
        _log.info(f"[BYPASS_REBOOT_REQUEST] reboot {host_label} → confirmation requise")
        pending = {"host": host_label, "ssh_fn": ssh_fn, "is_proxmox": is_proxmox, "ts": time.time()}
        return _sse_response(_reboot_machine_request_sse(pending))
    upd_cmd = _bypass_wrap.detect_update_command(orig_last)
    if upd_cmd:
        host_label, ssh_fn, is_proxmox = upd_cmd
        _log.info(f"[BYPASS_UPDATE] mise à jour {host_label}")
        return _sse_response(_update_machine_sse(host_label, ssh_fn, is_proxmox))
    svc_cmd = _bypass_wrap.detect_service_restart(orig_last)
    if svc_cmd:
        host_label, ssh_func, svc_name = svc_cmd
        if host_label != "ambiguous":
            return _sse_response(_service_restart_sse(host_label, ssh_func, svc_name))
    file_cmd = _bypass_fs.detect_file_command(orig_last, _FILE_VM_SSH)
    if file_cmd:
        f_action, f_vm, f_ssh_fn, f_path = file_cmd
        if f_action == "read" and not _FCORR_RE.search(orig_last):
            return _sse_response(_bypass_fs.file_command_sse(f_action, f_vm, f_ssh_fn, f_path))
    code_cmd = _bypass_wrap.detect_code_command(orig_last)
    if code_cmd:
        action, filename = code_cmd
        exec_it = (action == "exec")
        _log.info(f"[BYPASS_CODE] {action} `{filename}` → {_CODE_DEV_VM}")
        return _sse_response(_bypass_wrap.code_scp_exec_sse(filename, exec_it))
    for _hkey, _hrx in _SSH_TERMINAL_RE.items():
        if _hrx.search(orig_last):
            _hcfg = _SSH_TERMINAL_MAP[_hkey]
            _hlabel = _hcfg["label"]
            _huser = _hcfg.get("user", "root")
            _log.info(f"[BYPASS_SSH_{_hkey.upper()}] connexion {_hlabel} → open_ssh_terminal")
            return _sse_response(_ssh_terminal_sse(_hkey, _hlabel, _huser))
    return None


# ── _detect_file_corrections ──────────────────────────────────────────────────

def detect_file_corrections(orig_last, is_vocal):
    """Détecte les commandes mono/multi fichier + correction LLM."""
    file_corr_cmd = file_corr_multi = None
    if not is_vocal:
        _fmc = _bypass_fs.detect_multi_file_command(orig_last, _FILE_VM_SSH)
        if _fmc and _FCORR_RE.search(orig_last):
            file_corr_multi = _fmc
        else:
            _fc = _bypass_fs.detect_file_command(orig_last, _FILE_VM_SSH)
            if _fc and _fc[0] == "read" and _FCORR_RE.search(orig_last):
                file_corr_cmd = _fc
    return file_corr_cmd, file_corr_multi


# ── Route /api/chat ───────────────────────────────────────────────────────────

@bp.route("/api/chat", methods=["POST"])
def api_chat():
    data             = request.json or {}
    history          = data.get("history", [])
    web_enabled      = data.get("web_search", False)
    soc_ctx_injected = data.get("soc_ctx_injected", False)
    np_override      = data.get("num_predict")
    no_tools         = data.get("no_tools", False)
    model_override   = data.get("model_override")  # 'soc' | 'general' | None

    last_user = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")
    is_vocal  = last_user.startswith("[VOCAL]")
    _orig_last = last_user.split("\n\n", 1)[-1] if soc_ctx_injected and "\n\n" in last_user else last_user

    # ── 1. Bypass instantané — AVANT tout calcul coûteux ─────────────────────
    bypass = chat_try_bypass(_orig_last, is_vocal)
    if bypass:
        return bypass

    # ── 1b. Détection "lis + corrige" mono ou multi-fichiers ─────────────────
    _file_corr_cmd, _file_corr_multi = detect_file_corrections(_orig_last, is_vocal)

    # ── 2. Routing C·R — sortie anticipée avant injection SOC/PVE ────────────
    if _get_mode() == _CODE_REASONING_MODE:
        system_prompt = _get_system_prompt()
        messages = _chat_build_messages(_facts_inject(system_prompt), history, is_vocal)
        _log.info(f"[ROUTE] CODE-REASONING | q={_orig_last[:80]!r}")
        return Response(
            stream_with_context(_capture_gen(_code_reasoning_gen(messages, np_override), _orig_last)),
            mimetype="text/event-stream", headers=_SSE_HEADERS)

    # ── 3. System prompt + RAG + web + SOC/PVE live ───────────────────────────
    system, soc_trigger = _chat_build_system_prompt(
        last_user, web_enabled, soc_ctx_injected, is_vocal,
        force_soc=(model_override == "soc"))

    # ── 4. Routing modèle ─────────────────────────────────────────────────────
    active_model, route = _chat_resolve_model(is_vocal, no_tools, model_override)
    if active_model == _CODE_MODEL:
        system += _CODE_SYSTEM_SUFFIX
    _log.info(f"[ROUTE] {route}/{active_model or _get_model()} | soc={soc_trigger} | q={_orig_last[:80]!r}")

    messages = _chat_build_messages(system, history, is_vocal)

    # ── 5. Dispatch "lis + corrige" mono ou multi-fichiers ───────────────────
    _llm_ctx = _LlmCtx(messages, active_model, np_override, soc_ctx_injected, soc_trigger)
    if _file_corr_multi:
        _, f_vm, f_ssh_fn, f_paths = _file_corr_multi
        _log.info(f"[FILE_CORRECT_MULTI] {f_vm}:{f_paths} → LLM {active_model or _get_model()}")
        return Response(
            stream_with_context(_capture_gen(_file_correct_multi_gen(f_vm, f_ssh_fn, f_paths, _llm_ctx), _orig_last)),
            mimetype="text/event-stream", headers=_SSE_HEADERS)
    if _file_corr_cmd:
        _, f_vm, f_ssh_fn, f_path = _file_corr_cmd
        _log.info(f"[FILE_CORRECT] {f_vm}:{f_path} → LLM {active_model or _get_model()}")
        return Response(
            stream_with_context(_capture_gen(_file_correct_gen(f_vm, f_ssh_fn, f_path, _llm_ctx), _orig_last)),
            mimetype="text/event-stream", headers=_SSE_HEADERS)

    return Response(
        stream_with_context(_capture_gen(_chat_generate(_llm_ctx, no_tools), _orig_last)),
        mimetype="text/event-stream", headers=_SSE_HEADERS)


@bp.route("/api/history/last", methods=["GET"])
def api_history_last():
    """Retourne les N derniers échanges chat (user + assistant). Utilisé par le MCP.
    Déménagée de jarvis.py étape 32 (2026-05-23) — consomme _chat_orch._LAST_EXCHANGES."""
    n = min(int(request.args.get("n", 3)), 10)
    entries = list(_chat_orch._LAST_EXCHANGES)[-n:]
    return Response(json.dumps({"ok": True, "count": len(entries), "exchanges": entries}),
                    mimetype="application/json")
