"""Chat tool calls — boucle tool-calling LLM (Ollama tools API).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 27 (Chat/LLM core).

Le LLM peut décider d'appeler des outils (ex: ssh_nginx, vm_status) en mode SOC.
Cette boucle :
1. Appelle Ollama avec tools registrés
2. Si pas de tool_calls → break (LLM a répondu directement)
3. Sinon : pour chaque tool_call → execute_tool(args) → append result aux messages
4. Boucle (max TOOL_CALL_MAX itérations pour éviter loops)

Bonus : si l'outil renvoie une liste de paquets upgradables, capture dans `pending_infra_cmd`
pour proposer la confirmation upgrade au prochain message utilisateur.

Dependency injection : tous les helpers et state passés en kwargs.
"""
import json


def run_tool_calls(
    messages: list,
    active_model,
    *,
    call_llm_with_tools_fn,
    execute_tool_fn,
    tool_dispatch: dict,
    apt_host_map: dict,
    pending_infra_cmd: dict,
    parse_upgradable_packages_fn,
    log_info_fn,
    now_fn,
    tool_call_max: int = 5,
    tool_result_trunc: int = 300,
):
    """Boucle tool-calling : appelle les outils LLM, met à jour messages en place, yield SSE.

    `messages` est mutée (appended) avec assistant + tool results pour le tour suivant.
    """
    for _ in range(tool_call_max):
        try:
            result = call_llm_with_tools_fn(messages, model_override=active_model)
        except Exception as e:
            yield f"data: {json.dumps({'type':'token','token':f'[JARVIS] Ollama inaccessible : {e}','done':True})}\n\n"
            return
        msg = result.get("message", {})
        calls = msg.get("tool_calls", [])
        if not calls:
            break
        tool_results = []
        for call in calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            yield f"data: {json.dumps({'type': 'tool', 'name': name, 'args': args})}\n\n"
            if name not in tool_dispatch:
                warn = f"[JARVIS] Outil inconnu refusé : '{name}'. Outils disponibles : {sorted(tool_dispatch.keys())}"
                yield f"data: {json.dumps({'type':'token','token':warn,'done':True})}\n\n"
                return
            result_text = execute_tool_fn(name, args)
            yield f"data: {json.dumps({'type': 'tool_result', 'name': name, 'result': result_text[:tool_result_trunc]})}\n\n"
            tool_results.append({"role": "tool", "content": result_text, "name": name})

            # Capture paquets upgradables pour bypass confirmation
            if name in apt_host_map:
                cmd_arg = args.get("commande", "").lower()
                # Détection double : commande OU résultat contient des paquets upgradables
                is_apt_list = (
                    "upgradable" in cmd_arg or "apt list" in cmd_arg
                    or "apt-get upgrade" in cmd_arg or "apt upgrade" in cmd_arg
                )
                result_has_pkgs = "/stable" in result_text and "pouvant être" in result_text
                if is_apt_list or result_has_pkgs:
                    pkgs = parse_upgradable_packages_fn(result_text)
                    if pkgs:
                        host, ssh_fn = apt_host_map[name]
                        pending_infra_cmd.update({
                            "host": host,
                            "ssh_fn": ssh_fn,
                            "packages": pkgs,
                            "ts": now_fn(),
                        })
                        log_info_fn(f"[PENDING_APT] {host} → {pkgs}")

        messages.append({"role": "assistant", "content": msg.get("content", ""), "tool_calls": calls})
        messages.extend(tool_results)
