"""Tests chat_tool_calls — boucle tool-calling Ollama (max iterations + parsing args)."""
import json

from chat_tool_calls import run_tool_calls


def _no_tool_msg(content="réponse directe"):
    """Réponse Ollama sans tool_calls (le LLM répond directement → break boucle)."""
    return {"message": {"content": content, "tool_calls": []}}


def _tool_msg(name, args, content=""):
    """Réponse Ollama avec un tool_call."""
    return {"message": {
        "content": content,
        "tool_calls": [{"function": {"name": name, "arguments": args}}],
    }}


def _make_args(**overrides):
    args = dict(
        call_llm_with_tools_fn=lambda msgs, model_override=None: _no_tool_msg(),
        execute_tool_fn=lambda name, args: f"result-of-{name}",
        tool_dispatch={"ssh_ngix": object(), "vm_status": object()},
        apt_host_map={"ssh_ngix": ("srv-ngix", lambda: None)},
        pending_infra_cmd={},
        parse_upgradable_packages_fn=lambda txt: [],
        log_info_fn=lambda msg: None,
        now_fn=lambda: 1000.0,
        tool_call_max=5,
        tool_result_trunc=300,
    )
    args.update(overrides)
    return args


def test_pas_de_tool_calls_break_immediatement():
    """LLM répond directement → break, 0 events yielded."""
    msgs = []
    out = list(run_tool_calls(msgs, "phi4:14b", **_make_args()))
    assert out == []


def test_un_tool_call_yield_tool_puis_tool_result():
    msgs = [{"role": "user", "content": "?"}]
    calls = [_tool_msg("vm_status", {"vm": "108"}), _no_tool_msg()]
    it = iter(calls)

    out = list(run_tool_calls(
        msgs, "phi4:14b",
        **_make_args(call_llm_with_tools_fn=lambda m, model_override=None: next(it)),
    ))
    parsed = [json.loads(o.replace("data: ", "").strip()) for o in out]
    assert parsed[0]["type"] == "tool"
    assert parsed[0]["name"] == "vm_status"
    assert parsed[0]["args"] == {"vm": "108"}
    assert parsed[1]["type"] == "tool_result"
    assert parsed[1]["result"] == "result-of-vm_status"


def test_args_str_json_sont_parses():
    """Les arguments peuvent venir en str JSON depuis Ollama → parsés."""
    msgs = []
    calls = [_tool_msg("vm_status", '{"vm": "108"}'), _no_tool_msg()]
    it = iter(calls)

    out = list(run_tool_calls(
        msgs, "phi4:14b",
        **_make_args(call_llm_with_tools_fn=lambda m, model_override=None: next(it)),
    ))
    parsed = json.loads(out[0].replace("data: ", "").strip())
    assert parsed["args"] == {"vm": "108"}


def test_args_str_json_invalide_devient_dict_vide():
    """Si parsing JSON échoue → args = {}."""
    msgs = []
    calls = [_tool_msg("vm_status", "not-json"), _no_tool_msg()]
    it = iter(calls)

    out = list(run_tool_calls(
        msgs, "phi4:14b",
        **_make_args(call_llm_with_tools_fn=lambda m, model_override=None: next(it)),
    ))
    parsed = json.loads(out[0].replace("data: ", "").strip())
    assert parsed["args"] == {}


def test_outil_inconnu_refuse_avec_warning():
    """Tool name absent du dispatch → warning + return immédiat."""
    msgs = []
    calls = [_tool_msg("outil_inexistant", {})]
    it = iter(calls)

    out = list(run_tool_calls(
        msgs, "phi4:14b",
        **_make_args(call_llm_with_tools_fn=lambda m, model_override=None: next(it)),
    ))
    # Doit yield 'tool' event puis warning (pas tool_result)
    parsed_warn = json.loads(out[-1].replace("data: ", "").strip())
    assert parsed_warn["type"] == "token"
    assert parsed_warn["done"] is True
    assert "Outil inconnu refusé" in parsed_warn["token"]
    assert "outil_inexistant" in parsed_warn["token"]


def test_exception_call_llm_yield_token_d_erreur_et_return():
    """Si call_llm lève → token d'erreur 'Ollama inaccessible' + return."""
    def raises(m, model_override=None):
        raise ConnectionError("connection refused")

    out = list(run_tool_calls([], "phi4:14b", **_make_args(call_llm_with_tools_fn=raises)))
    parsed = json.loads(out[0].replace("data: ", "").strip())
    assert parsed["type"] == "token"
    assert parsed["done"] is True
    assert "Ollama inaccessible" in parsed["token"]
    assert "connection refused" in parsed["token"]


def test_tool_result_tronque_a_la_limite():
    msgs = []
    long_result = "X" * 5000
    calls = [_tool_msg("vm_status", {}), _no_tool_msg()]
    it = iter(calls)

    out = list(run_tool_calls(
        msgs, "phi4:14b",
        **_make_args(
            call_llm_with_tools_fn=lambda m, model_override=None: next(it),
            execute_tool_fn=lambda n, a: long_result,
            tool_result_trunc=100,
        ),
    ))
    parsed = json.loads(out[1].replace("data: ", "").strip())
    assert len(parsed["result"]) == 100


def test_messages_appended_apres_tool_call():
    """messages doit être muté avec assistant + tool_results pour le tour suivant."""
    msgs = [{"role": "user", "content": "?"}]
    calls = [_tool_msg("vm_status", {}, content="je vais vérifier"), _no_tool_msg()]
    it = iter(calls)

    list(run_tool_calls(
        msgs, "phi4:14b",
        **_make_args(call_llm_with_tools_fn=lambda m, model_override=None: next(it)),
    ))
    # original user + assistant (avec tool_calls) + tool result
    assert len(msgs) == 3
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "je vais vérifier"
    assert "tool_calls" in msgs[1]
    assert msgs[2]["role"] == "tool"
    assert msgs[2]["content"] == "result-of-vm_status"


def test_apt_list_capture_dans_pending():
    """`apt list --upgradable` détecté → pending_infra_cmd peuplé."""
    msgs = []
    calls = [
        _tool_msg("ssh_ngix", {"commande": "apt list --upgradable"}),
        _no_tool_msg(),
    ]
    it = iter(calls)
    pending = {}

    list(run_tool_calls(
        msgs, "phi4:14b",
        **_make_args(
            call_llm_with_tools_fn=lambda m, model_override=None: next(it),
            execute_tool_fn=lambda n, a: "nginx/jammy 1.24 amd64",
            parse_upgradable_packages_fn=lambda t: ["nginx", "openssl"],
            pending_infra_cmd=pending,
        ),
    ))
    assert pending["host"] == "srv-ngix"
    assert pending["packages"] == ["nginx", "openssl"]
    assert pending["ts"] == 1000.0


def test_apt_capture_pas_si_pas_de_paquets_parses():
    """Si parse retourne [] → pas de capture."""
    msgs = []
    calls = [
        _tool_msg("ssh_ngix", {"commande": "apt list --upgradable"}),
        _no_tool_msg(),
    ]
    it = iter(calls)
    pending = {}

    list(run_tool_calls(
        msgs, "phi4:14b",
        **_make_args(
            call_llm_with_tools_fn=lambda m, model_override=None: next(it),
            execute_tool_fn=lambda n, a: "no packages",
            parse_upgradable_packages_fn=lambda t: [],
            pending_infra_cmd=pending,
        ),
    ))
    assert pending == {}


def test_max_iterations_respecte():
    """tool_call_max=2 → max 2 appels au LLM même si toujours tool_calls."""
    counter = {"n": 0}

    def llm(m, model_override=None):
        counter["n"] += 1
        return _tool_msg("vm_status", {})  # toujours tool_call → boucle infinie sans le max

    list(run_tool_calls([], "phi4:14b", **_make_args(call_llm_with_tools_fn=llm, tool_call_max=2)))
    assert counter["n"] == 2
