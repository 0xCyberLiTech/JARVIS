"""Tests chat_capture — wrapper SSE qui capture tokens pour mémoire historique."""
import json
from collections import deque

from chat.capture import capture_gen


def _sse_token(t, done=False):
    return f"data: {json.dumps({'type': 'token', 'token': t, 'done': done})}\n\n"


def test_capture_yield_les_chunks_inchanges():
    chunks_in = ["chunk1", "chunk2", "chunk3"]
    out = list(capture_gen(iter(chunks_in), "user", deque()))
    assert out == chunks_in


def test_capture_accumule_les_tokens_dans_la_deque():
    d = deque()
    chunks = [_sse_token("hello"), _sse_token(" world", done=True)]
    list(capture_gen(iter(chunks), "salut", d))
    assert len(d) == 1
    assert d[0]["assistant"] == "hello world"
    assert d[0]["user"] == "salut"


def test_capture_ignore_chunks_non_token():
    """Les chunks SSE qui ne sont pas des `type:token` sont juste passés à travers, pas accumulés."""
    d = deque()
    chunks = [
        f"data: {json.dumps({'type': 'speak', 'text': 'speak text'})}\n\n",
        _sse_token("vrai token"),
    ]
    list(capture_gen(iter(chunks), "u", d))
    assert d[0]["assistant"] == "vrai token"


def test_capture_ignore_chunks_non_json_apres_data():
    """Keep-alive `data: \\n\\n` ou commentaire → ignoré sans crash."""
    d = deque()
    chunks = ["data: \n\n", "data: not json {oops\n\n", _sse_token("ok")]
    list(capture_gen(iter(chunks), "u", d))
    assert d[0]["assistant"] == "ok"


def test_capture_ignore_chunks_qui_ne_commencent_pas_par_data():
    """Chunks ne commençant pas par 'data:' (ex: ':\\n\\n' commentaire) → ignorés."""
    d = deque()
    chunks = [": comment\n\n", _sse_token("ok")]
    list(capture_gen(iter(chunks), "u", d))
    assert d[0]["assistant"] == "ok"


def test_capture_n_ajoute_pas_si_aucun_token_recu():
    """Stream vide ou que des speak → rien dans la deque."""
    d = deque()
    list(capture_gen(iter([]), "u", d))
    assert len(d) == 0


def test_capture_n_ajoute_pas_si_full_text_vide():
    """Tokens vides accumulés → strip() = "" → rien dans la deque."""
    d = deque()
    chunks = [_sse_token(""), _sse_token("   ")]
    list(capture_gen(iter(chunks), "u", d))
    assert len(d) == 0


def test_capture_tronque_user_msg_a_500_chars():
    d = deque()
    long = "a" * 1000
    list(capture_gen(iter([_sse_token("ok")]), long, d))
    assert len(d[0]["user"]) == 500


def test_capture_ajoute_timestamp():
    d = deque()
    list(capture_gen(iter([_sse_token("ok")]), "u", d))
    assert "ts" in d[0]
    assert isinstance(d[0]["ts"], float)


def test_capture_finally_meme_si_exception_dans_le_generateur():
    """Si gen lève, finally doit quand même append si tokens accumulés."""
    d = deque()

    def gen_raises():
        yield _sse_token("avant")
        raise RuntimeError("boom")

    try:
        list(capture_gen(gen_raises(), "u", d))
    except RuntimeError:
        pass
    assert len(d) == 1
    assert d[0]["assistant"] == "avant"


def test_capture_chunk_non_string_ignore_silencieusement():
    """Chunks non-str (ex: bytes) → pas de crash, juste pass-through."""
    d = deque()
    chunks = [b"bytes chunk", _sse_token("text token")]
    out = list(capture_gen(iter(chunks), "u", d))
    assert out == chunks  # pass-through total
    assert d[0]["assistant"] == "text token"
