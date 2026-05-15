"""Tests sse_helpers — sse_tok (pure) + SSE_HEADERS constants."""
import json

from sse_helpers import SSE_HEADERS, sse_tok


def test_sse_tok_format_data_json_double_newline():
    """Format SSE standard : `data: {json}\\n\\n`."""
    out = sse_tok("hello")
    assert out.startswith("data: ")
    assert out.endswith("\n\n")


def test_sse_tok_contenu_json_parseable():
    out = sse_tok("hello")
    # Extraire et parser
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload == {"type": "token", "token": "hello", "done": False}


def test_sse_tok_done_true_propage():
    out = sse_tok("fin", done=True)
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload["done"] is True


def test_sse_tok_done_default_false():
    out = sse_tok("test")
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload["done"] is False


def test_sse_tok_token_avec_caracteres_speciaux():
    """JSON encode bien les caractères spéciaux."""
    out = sse_tok('quote " et \\backslash et \nnewline')
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload["token"] == 'quote " et \\backslash et \nnewline'


def test_sse_tok_token_vide_est_valide():
    out = sse_tok("")
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload["token"] == ""


def test_sse_headers_anti_buffering_nginx():
    """X-Accel-Buffering: no est CRITIQUE pour Nginx (sinon le SSE ne stream pas)."""
    assert SSE_HEADERS.get("X-Accel-Buffering") == "no"


def test_sse_headers_no_cache():
    assert SSE_HEADERS.get("Cache-Control") == "no-cache"
