"""Tests chat_generate — wrapper top-level avec error handling et signal stream actif."""
import json
import queue
import threading

from chat_generate import chat_generate


class _Ctx:
    """Stub minimal LlmCtx (juste un objet quelconque que le wrapper passe à stream_inner)."""


def _stub_inner_ok(ctx, no_tools):
    yield "data: token1\n\n"
    yield "data: token2\n\n"


def _stub_inner_raises(ctx, no_tools):
    yield "data: avant_exception\n\n"
    raise RuntimeError("boom")


def _make_args(stream_inner=_stub_inner_ok, **overrides):
    args = dict(
        deferred_queue=queue.Queue(),
        stream_active_event=threading.Event(),
        stream_inner_fn=stream_inner,
        log_error_fn=lambda msg: None,
    )
    args.update(overrides)
    return args


def test_chat_generate_yield_les_events_de_stream_inner():
    out = list(chat_generate(_Ctx(), **_make_args()))
    assert out == ["data: token1\n\n", "data: token2\n\n"]


def test_drain_la_queue_au_demarrage():
    """Messages laissés du tour précédent doivent être vidés."""
    q = queue.Queue()
    q.put("ancien message 1")
    q.put("ancien message 2")
    list(chat_generate(_Ctx(), **_make_args(deferred_queue=q)))
    assert q.empty()


def test_stream_active_event_set_pendant_le_stream():
    """Pendant le yield, stream_active_event doit être set."""
    ev = threading.Event()
    captured = {"set_during_yield": None}

    def inner(ctx, no_tools):
        captured["set_during_yield"] = ev.is_set()
        yield "x"

    list(chat_generate(_Ctx(), **_make_args(stream_inner=inner, stream_active_event=ev)))
    assert captured["set_during_yield"] is True


def test_stream_active_event_clear_apres_le_stream():
    ev = threading.Event()
    list(chat_generate(_Ctx(), **_make_args(stream_active_event=ev)))
    assert ev.is_set() is False


def test_exception_dans_stream_inner_yield_un_message_d_erreur():
    out = list(chat_generate(_Ctx(), **_make_args(stream_inner=_stub_inner_raises)))
    # On doit avoir le token avant + un token d'erreur
    assert len(out) == 2
    assert out[0] == "data: avant_exception\n\n"
    err_event = json.loads(out[1].replace("data: ", "").strip())
    assert err_event["type"] == "token"
    assert err_event["done"] is True
    assert "boom" in err_event["token"]
    assert "[JARVIS] Erreur interne" in err_event["token"]


def test_exception_appelle_log_error_avec_traceback():
    captured = {"msg": None}

    def log_err(msg):
        captured["msg"] = msg

    list(chat_generate(_Ctx(), **_make_args(stream_inner=_stub_inner_raises, log_error_fn=log_err)))
    assert captured["msg"] is not None
    assert "[api_chat] stream error:" in captured["msg"]
    assert "Traceback" in captured["msg"]


def test_event_clear_meme_si_exception():
    """Le finally doit toujours clear l'event."""
    ev = threading.Event()
    list(chat_generate(_Ctx(), **_make_args(stream_inner=_stub_inner_raises, stream_active_event=ev)))
    assert ev.is_set() is False


def test_no_tools_passe_a_stream_inner_fn():
    captured = {"no_tools": None}

    def inner(ctx, no_tools):
        captured["no_tools"] = no_tools
        yield "x"

    list(chat_generate(_Ctx(), no_tools=True, **_make_args(stream_inner=inner)))
    assert captured["no_tools"] is True


def test_no_tools_default_false():
    captured = {}

    def inner(ctx, no_tools):
        captured["no_tools"] = no_tools
        yield "x"

    list(chat_generate(_Ctx(), **_make_args(stream_inner=inner)))
    assert captured["no_tools"] is False
