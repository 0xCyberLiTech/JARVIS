"""Tests chat/file_correct — correction LLM mono/multi-fichiers + protect nginx directives.

Couvre :
- validate_protect_directives : restauration des directives nginx protégées
  (ssl_prefer_server_ciphers en particulier — faux positif LLM connu)
- file_correct_gen : lecture SSH + injection contexte + stream LLM + validation
- _file_correct_multi_inject : construction du payload multi-fichiers
- file_correct_multi_gen : N fichiers + stream LLM + validation per-fichier

Tous les SSH + LLM stream sont mockés.
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from chat import file_correct


@pytest.fixture(autouse=True)
def _reinit_file_correct():
    """DI propre + restauration teardown."""
    saved = {k: getattr(file_correct, k) for k in ("_log", "_sse_tok")}

    def sse_tok(text, done=False):
        return "data: " + json.dumps({"type": "token", "token": text, "done": done}) + "\n\n"

    file_correct.init(log=MagicMock(), sse_tok=sse_tok)
    yield
    for k, v in saved.items():
        setattr(file_correct, k, v)


def _make_ctx(user_content="Corrige ce fichier"):
    """Construit un LlmCtx minimal pour les tests (juste .messages mutable)."""
    ctx = MagicMock()
    ctx.messages = [
        {"role": "system",  "content": "system prompt"},
        {"role": "user",    "content": user_content},
    ]
    return ctx


def _parse_events(events):
    """Parse list of SSE events → list of dict payloads."""
    out = []
    for e in events:
        if not e.startswith("data: "):
            continue
        payload = e[6:].strip()
        try:
            out.append(json.loads(payload))
        except json.JSONDecodeError:
            out.append({"raw": payload})
    return out


# ── validate_protect_directives ────────────────────────────────────────────


def test_validate_protect_ssl_prefer_off_restauré():
    """LLM a mis 'ssl_prefer_server_ciphers on' alors que l'original = off → restauration."""
    orig = "    ssl_prefer_server_ciphers off;\n    other_config 1;"
    llm  = "    ssl_prefer_server_ciphers on;  # mieux selon best practices\n    other_config 1;"
    fixed, changes = file_correct.validate_protect_directives(orig, llm)
    assert "ssl_prefer_server_ciphers off;" in fixed
    assert len(changes) == 1
    assert "ssl_prefer_server_ciphers" in changes[0]
    assert "`on`" in changes[0] and "`off`" in changes[0]


def test_validate_protect_pas_de_changement_si_identique():
    """LLM a gardé la même valeur → 0 changement."""
    orig = "    ssl_prefer_server_ciphers off;"
    llm  = "    ssl_prefer_server_ciphers off;"
    fixed, changes = file_correct.validate_protect_directives(orig, llm)
    assert changes == []
    assert fixed == llm


def test_validate_protect_directive_absente_original_skip():
    """Si la directive n'existe pas dans l'original → on ne touche pas le LLM."""
    orig = "    server_name example.com;"
    llm  = "    ssl_prefer_server_ciphers on;\n    server_name example.com;"
    fixed, changes = file_correct.validate_protect_directives(orig, llm)
    assert changes == []
    assert fixed == llm


def test_validate_protect_directive_absente_llm_skip():
    """Si le LLM a SUPPRIMÉ la directive → on ne restaure pas (changement non détecté)."""
    orig = "    ssl_prefer_server_ciphers off;"
    llm  = "    other_config 1;"
    fixed, changes = file_correct.validate_protect_directives(orig, llm)
    # La détection ne s'applique que si la directive est PRÉSENTE dans les deux.
    assert changes == []
    assert fixed == llm


def test_validate_protect_case_insensitive():
    """Comparaison case-insensitive : 'ON' vs 'off' → restauration."""
    orig = "ssl_prefer_server_ciphers off;"
    llm  = "ssl_prefer_server_ciphers ON;  # capitales"
    fixed, changes = file_correct.validate_protect_directives(orig, llm)
    assert "off;" in fixed
    assert len(changes) == 1


# ── file_correct_gen ───────────────────────────────────────────────────────


def test_file_correct_gen_ssh_ko_yield_erreur():
    """ssh_fn renvoie (False, ...) → 1 token erreur + done True + return."""
    ssh = MagicMock(return_value=(False, ""))
    ctx = _make_ctx()
    events = _parse_events(list(file_correct.file_correct_gen("clt", ssh, "/etc/nginx/nginx.conf", ctx)))
    assert len(events) == 1
    assert events[0]["done"] is True
    assert "impossible de lire" in events[0]["token"]


def test_file_correct_gen_ssh_content_vide_yield_erreur():
    """ssh_fn renvoie (True, '') → traité comme erreur (content falsy)."""
    ssh = MagicMock(return_value=(True, ""))
    ctx = _make_ctx()
    events = _parse_events(list(file_correct.file_correct_gen("clt", ssh, "/etc/nginx/nginx.conf", ctx)))
    assert any(e.get("done") and "impossible de lire" in e.get("token", "") for e in events)


def test_file_correct_gen_succes_inject_content_dans_user_message():
    """ssh_fn OK → injecte le contenu dans le DERNIER message user du ctx."""
    ssh = MagicMock(return_value=(True, "server { listen 80; }"))
    ctx = _make_ctx(user_content="Corrige nginx.conf")
    with patch.object(file_correct.orchestrator, "_chat_stream_inner", return_value=iter([])), \
         patch.object(file_correct.orchestrator, "_chat_stream_active"):
        list(file_correct.file_correct_gen("clt", ssh, "/etc/nginx/nginx.conf", ctx))
    # Le user message a été enrichi avec le contenu lu
    user_msg = ctx.messages[-1]["content"]
    assert "Corrige nginx.conf" in user_msg
    assert "server { listen 80; }" in user_msg
    assert "/etc/nginx/nginx.conf" in user_msg
    assert "RÈGLE ABSOLUE" in user_msg  # garde-fou prompt
    assert "ssl_prefer_server_ciphers" in user_msg  # exclusions critiques


def test_file_correct_gen_emet_file_correct_start_et_ssh_file():
    """Avant injection, émet 2 events frontend : file_correct_start + ssh_file."""
    ssh = MagicMock(return_value=(True, "config content"))
    ctx = _make_ctx()
    with patch.object(file_correct.orchestrator, "_chat_stream_inner", return_value=iter([])), \
         patch.object(file_correct.orchestrator, "_chat_stream_active"):
        events = _parse_events(list(file_correct.file_correct_gen("clt", ssh, "/etc/foo.conf", ctx)))
    types = [e.get("type") for e in events]
    assert "file_correct_start" in types
    assert "ssh_file" in types
    ssh_file_evt = next(e for e in events if e.get("type") == "ssh_file")
    assert ssh_file_evt["vm"] == "clt"
    assert ssh_file_evt["path"] == "/etc/foo.conf"
    assert ssh_file_evt["content"] == "config content"


def test_file_correct_gen_directory_path_utilise_ls_la():
    """Si le path se termine par '/' → commande SSH = ls -la, pas cat."""
    ssh = MagicMock(return_value=(True, "drwxr-xr-x ..."))
    ctx = _make_ctx()
    with patch.object(file_correct.orchestrator, "_chat_stream_inner", return_value=iter([])), \
         patch.object(file_correct.orchestrator, "_chat_stream_active"):
        list(file_correct.file_correct_gen("clt", ssh, "/etc/nginx/", ctx))
    cmd_sent = ssh.call_args[0][0]
    assert cmd_sent.startswith("ls -la")


def test_file_correct_gen_basename_sans_extension_utilise_ls_la():
    """Si basename n'a pas de '.' → traité comme dossier → ls -la."""
    ssh = MagicMock(return_value=(True, ""))
    ctx = _make_ctx()
    list(file_correct.file_correct_gen("clt", ssh, "/etc/nginx", ctx))
    cmd_sent = ssh.call_args[0][0]
    assert cmd_sent.startswith("ls -la")


def test_file_correct_gen_stream_exception_logguee():
    """Si _chat_stream_inner lance → log.error + token erreur + return."""
    ssh = MagicMock(return_value=(True, "content"))
    ctx = _make_ctx()
    with patch.object(file_correct.orchestrator, "_chat_stream_inner",
                      side_effect=RuntimeError("ollama crash")), \
         patch.object(file_correct.orchestrator, "_chat_stream_active"):
        events = _parse_events(list(file_correct.file_correct_gen("clt", ssh, "/etc/foo.conf", ctx)))
    file_correct._log.error.assert_called_once()
    assert any("Erreur interne" in e.get("token", "") for e in events)


def test_file_correct_gen_validation_post_genere_si_directive_modifiee():
    """Si LLM modifie ssl_prefer_server_ciphers → émet file_correct_fix avec restauration."""
    ssh = MagicMock(return_value=(True, "    ssl_prefer_server_ciphers off;"))
    ctx = _make_ctx()
    # LLM stream émet un seul bloc code avec la directive modifiée
    fake_stream_event = "data: " + json.dumps({
        "type": "token",
        "token": "```\n    ssl_prefer_server_ciphers on;\n```\n"
    }) + "\n\n"
    with patch.object(file_correct.orchestrator, "_chat_stream_inner",
                      return_value=iter([fake_stream_event])), \
         patch.object(file_correct.orchestrator, "_chat_stream_active"):
        events = _parse_events(list(file_correct.file_correct_gen("clt", ssh, "/etc/nginx.conf", ctx)))
    fix_evt = next((e for e in events if e.get("type") == "file_correct_fix"), None)
    assert fix_evt is not None
    assert "ssl_prefer_server_ciphers off;" in fix_evt["code"]
    file_correct._log.warning.assert_called_once()


# ── _file_correct_multi_inject ─────────────────────────────────────────────


def test_multi_inject_construit_payload_avec_n_fichiers():
    """Injecte un bloc multi-fichiers dans le dernier user message."""
    ctx = _make_ctx(user_content="Corrige")
    files = [
        ("/etc/foo.conf", "server_name foo;"),
        ("/var/www/index.html", "<html></html>"),
    ]
    file_correct._file_correct_multi_inject(files, "clt", ctx)
    user_msg = ctx.messages[-1]["content"]
    assert "MULTI-FICHIERS" in user_msg
    assert "2 fichiers" in user_msg
    assert "/etc/foo.conf" in user_msg
    assert "/var/www/index.html" in user_msg
    assert "server_name foo;" in user_msg
    assert "<html></html>" in user_msg
    assert "dépendances" in user_msg


def test_multi_inject_extension_dans_bloc_code():
    """L'extension du fichier (ex: 'conf') est passée au bloc Markdown ```ext."""
    ctx = _make_ctx()
    file_correct._file_correct_multi_inject([("/etc/nginx.conf", "x")], "clt", ctx)
    user_msg = ctx.messages[-1]["content"]
    assert "```conf" in user_msg


def test_multi_inject_fichier_sans_extension_bloc_vide():
    """Fichier sans extension → bloc ``` sans langage."""
    ctx = _make_ctx()
    file_correct._file_correct_multi_inject([("/etc/Makefile", "all:"), ], "clt", ctx)
    user_msg = ctx.messages[-1]["content"]
    # Le bloc commence par '```\n' (string vide après ```)
    assert "```\n" in user_msg


# ── file_correct_multi_gen ─────────────────────────────────────────────────


def test_multi_gen_aucun_fichier_lu_yield_done():
    """Tous les ssh_fn renvoient KO → token 'Aucun fichier lu' + done True."""
    ssh = MagicMock(return_value=(False, ""))
    ctx = _make_ctx()
    events = _parse_events(list(file_correct.file_correct_multi_gen(
        "clt", ssh, ["/etc/a.conf", "/etc/b.conf"], ctx)))
    # 2 warnings (1 par fichier KO) + 1 final 'Aucun fichier lu' done=True
    final = events[-1]
    assert "Aucun fichier lu" in final.get("token", "")
    assert final.get("done") is True


def test_multi_gen_ssh_partiel_continue_avec_fichiers_ok():
    """Si 1/2 fichiers ko → continue avec celui qui est OK."""
    ssh = MagicMock(side_effect=[(False, ""), (True, "content2")])
    ctx = _make_ctx()
    with patch.object(file_correct.orchestrator, "_chat_stream_inner", return_value=iter([])), \
         patch.object(file_correct.orchestrator, "_chat_stream_active"):
        events = _parse_events(list(file_correct.file_correct_multi_gen(
            "clt", ssh, ["/etc/a.conf", "/etc/b.conf"], ctx)))
    types = [e.get("type") for e in events]
    assert "file_correct_start" in types
    # Le multi_inject a été appelé : ctx.messages[-1] contient content2
    assert "content2" in ctx.messages[-1]["content"]


def test_multi_gen_succes_emet_file_correct_start_multi():
    """2 fichiers OK → 1 event file_correct_start multi=True count=2."""
    ssh = MagicMock(side_effect=[(True, "c1"), (True, "c2")])
    ctx = _make_ctx()
    with patch.object(file_correct.orchestrator, "_chat_stream_inner", return_value=iter([])), \
         patch.object(file_correct.orchestrator, "_chat_stream_active"):
        events = _parse_events(list(file_correct.file_correct_multi_gen(
            "clt", ssh, ["/a.conf", "/b.conf"], ctx)))
    start_evt = next((e for e in events if e.get("type") == "file_correct_start"), None)
    assert start_evt is not None
    assert start_evt["multi"] is True
    assert start_evt["count"] == 2


def test_multi_gen_stream_exception_logguee_yield_erreur():
    """Si _chat_stream_inner lance → log + token erreur + return."""
    ssh = MagicMock(return_value=(True, "c1"))
    ctx = _make_ctx()
    with patch.object(file_correct.orchestrator, "_chat_stream_inner",
                      side_effect=RuntimeError("ollama down")), \
         patch.object(file_correct.orchestrator, "_chat_stream_active"):
        events = _parse_events(list(file_correct.file_correct_multi_gen(
            "clt", ssh, ["/a.conf"], ctx)))
    file_correct._log.error.assert_called_once()
    err_evt = next((e for e in events if e.get("done")), None)
    assert err_evt is not None
    assert "Erreur" in err_evt["token"]


def test_multi_gen_validation_par_fichier():
    """Pour N fichiers et N blocs de code, validate_protect_directives appelé par fichier."""
    ssh = MagicMock(side_effect=[
        (True, "ssl_prefer_server_ciphers off;"),
        (True, "ssl_prefer_server_ciphers off;"),
    ])
    ctx = _make_ctx()
    # LLM renvoie 2 blocs code (1 par fichier) — le 1er modifie la directive
    fake_event = "data: " + json.dumps({
        "type": "token",
        "token": "```\nssl_prefer_server_ciphers on;\n```\n\n```\nssl_prefer_server_ciphers off;\n```"
    }) + "\n\n"
    with patch.object(file_correct.orchestrator, "_chat_stream_inner",
                      return_value=iter([fake_event])), \
         patch.object(file_correct.orchestrator, "_chat_stream_active"):
        events = _parse_events(list(file_correct.file_correct_multi_gen(
            "clt", ssh, ["/a.conf", "/b.conf"], ctx)))
    fix_evt = next((e for e in events if e.get("type") == "file_correct_fix"), None)
    assert fix_evt is not None
    # Au moins 1 changement détecté (le 1er fichier où LLM a modifié)
    assert len(fix_evt["changes"]) >= 1
    assert any("a.conf" in c for c in fix_evt["changes"])
