"""Tests chat_stream — orchestrateur pipeline LLM streaming."""
from collections import namedtuple

from chat.stream import stream_inner

LlmCtx = namedtuple("LlmCtx", "messages model np_override soc_ctx soc_trigger")


def _make_helpers():
    """Helpers stub avec capture des appels."""
    capture = {"vram": [], "tools": False, "opts_called_with": None, "tts": False, "deferred": False}

    def ensure_vram(model):
        capture["vram"].append(model)

    def run_tool_calls(messages, model):
        capture["tools"] = True
        yield "tool_event"

    def build_opts(np, soc_ctx, soc_trigger, model, msg_len):
        capture["opts_called_with"] = (np, soc_ctx, soc_trigger, model, msg_len)
        return {"num_predict": 100}

    def stream_tts(messages, model, opts):
        capture["tts"] = True
        capture["tts_opts"] = opts
        yield "token_event"

    def flush_deferred():
        capture["deferred"] = True
        yield "flush_event"

    return capture, dict(
        ensure_vram_fn=ensure_vram,
        run_tool_calls_fn=run_tool_calls,
        build_llm_opts_fn=build_opts,
        stream_tokens_tts_fn=stream_tts,
        flush_deferred_speak_fn=flush_deferred,
    )


def _ctx(**overrides):
    args = dict(
        messages=[{"role": "user", "content": "salut"}],
        model="phi4:14b",
        np_override=None,
        soc_ctx=False,
        soc_trigger=False,
    )
    args.update(overrides)
    return LlmCtx(**args)


def test_pipeline_appelle_ensure_vram_avec_le_modele():
    capture, helpers = _make_helpers()
    list(stream_inner(_ctx(model="custom"), **helpers))
    assert capture["vram"] == ["custom"]


def test_pipeline_appelle_tools_par_defaut():
    capture, helpers = _make_helpers()
    list(stream_inner(_ctx(), **helpers))
    assert capture["tools"] is True


def test_pipeline_skippe_tools_si_no_tools_true():
    capture, helpers = _make_helpers()
    list(stream_inner(_ctx(), no_tools=True, **helpers))
    assert capture["tools"] is False


def test_pipeline_yield_les_events_dans_l_ordre():
    """tool_event puis token_event puis flush_event."""
    _, helpers = _make_helpers()
    out = list(stream_inner(_ctx(), **helpers))
    assert out == ["tool_event", "token_event", "flush_event"]


def test_pipeline_no_tools_yield_sans_tool_event():
    _, helpers = _make_helpers()
    out = list(stream_inner(_ctx(), no_tools=True, **helpers))
    assert out == ["token_event", "flush_event"]


def test_msg_len_calcule_sur_dernier_user_msg():
    capture, helpers = _make_helpers()
    msgs = [
        {"role": "user", "content": "court"},
        {"role": "assistant", "content": "ok"},
        {"role": "user", "content": "ce dernier user fait 30 caractères"},
    ]
    list(stream_inner(_ctx(messages=msgs), **helpers))
    assert capture["opts_called_with"][4] == len("ce dernier user fait 30 caractères")


def test_msg_len_zero_si_pas_de_message_user():
    capture, helpers = _make_helpers()
    list(stream_inner(_ctx(messages=[{"role": "system", "content": "sys"}]), **helpers))
    assert capture["opts_called_with"][4] == 0


def test_temp_override_ajoute_temperature_aux_opts():
    capture, helpers = _make_helpers()
    list(stream_inner(_ctx(), temp_override=0.9, **helpers))
    assert capture["tts_opts"]["temperature"] == 0.9
    assert capture["tts_opts"]["num_predict"] == 100  # opts existants préservés


def test_temp_override_avec_opts_none_cree_dict():
    """Si build_opts retourne None, l'override crée un dict {temperature}."""
    capture = {}

    def build_opts(*a, **kw):
        return None

    def stream_tts(messages, model, opts):
        capture["opts"] = opts
        yield "x"

    helpers = dict(
        ensure_vram_fn=lambda m: None,
        run_tool_calls_fn=lambda m, mo: iter([]),
        build_llm_opts_fn=build_opts,
        stream_tokens_tts_fn=stream_tts,
        flush_deferred_speak_fn=lambda: iter([]),
    )
    list(stream_inner(_ctx(), temp_override=0.5, **helpers))
    assert capture["opts"] == {"temperature": 0.5}


def test_pas_de_temp_override_garde_opts_originaux():
    capture, helpers = _make_helpers()
    list(stream_inner(_ctx(), **helpers))
    assert "temperature" not in capture["tts_opts"]


def test_messages_passes_a_tts_sont_une_copie_pas_la_ref():
    """`current_messages = list(ctx.messages)` → copie indépendante."""
    capture = {}
    msgs = [{"role": "user", "content": "salut"}]

    def stream_tts(messages, model, opts):
        capture["msgs_id"] = id(messages)
        yield "x"

    helpers = dict(
        ensure_vram_fn=lambda m: None,
        run_tool_calls_fn=lambda m, mo: iter([]),
        build_llm_opts_fn=lambda *a, **k: None,
        stream_tokens_tts_fn=stream_tts,
        flush_deferred_speak_fn=lambda: iter([]),
    )
    list(stream_inner(_ctx(messages=msgs), **helpers))
    assert capture["msgs_id"] != id(msgs)
