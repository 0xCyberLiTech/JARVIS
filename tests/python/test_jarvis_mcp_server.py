"""Tests jarvis_mcp_server — 10 outils MCP + helpers + sanitize.

Sans dépendance pytest-asyncio : on utilise asyncio.run() directement.
httpx est mocké via classes async context manager fakes.
"""
import asyncio

import jarvis_mcp_server as mcp

# ── Fakes httpx ─────────────────────────────────────────────────────────


class _FakeResp:
    def __init__(self, status_code=200, json_data=None, lines=None):
        self.status_code = status_code
        self._json = json_data or {}
        self._lines = lines or []

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    async def aiter_lines(self):
        for line in self._lines:
            yield line

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _FakeStreamCtx:
    def __init__(self, resp):
        self._resp = resp

    async def __aenter__(self):
        return self._resp

    async def __aexit__(self, *a):
        return False


class _FakeClient:
    """Mock httpx.AsyncClient avec routes paramétrables."""

    routes_get = {}     # url → _FakeResp
    routes_post = {}    # url → _FakeResp
    routes_stream = {}  # url → _FakeResp
    raise_get = None
    raise_post = None

    def __init__(self, *a, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, **kw):
        if _FakeClient.raise_get:
            raise _FakeClient.raise_get
        return _FakeClient.routes_get.get(url, _FakeResp(404))

    async def post(self, url, **kw):
        if _FakeClient.raise_post:
            raise _FakeClient.raise_post
        return _FakeClient.routes_post.get(url, _FakeResp(404))

    def stream(self, method, url, **kw):
        return _FakeStreamCtx(_FakeClient.routes_stream.get(url, _FakeResp(404)))


def _reset_fake():
    _FakeClient.routes_get = {}
    _FakeClient.routes_post = {}
    _FakeClient.routes_stream = {}
    _FakeClient.raise_get = None
    _FakeClient.raise_post = None


def _run(coro):
    return asyncio.run(coro)


# ── Constantes ──────────────────────────────────────────────────────────


def test_jarvis_base_127001():
    """IPv4 explicite (bug IPv6 sur Windows résolu avant)."""
    assert mcp.JARVIS_BASE == "http://127.0.0.1:5000"


def test_timeout_chat_120s():
    assert mcp.TIMEOUT_CHAT == 120.0


def test_timeout_fast_10s():
    assert mcp.TIMEOUT_FAST == 10.0


def test_jarvis_header_format():
    """Header ASCII non vide qui contient 'JARVIS' et 'phi4'."""
    assert "JARVIS" in mcp.JARVIS_HEADER
    assert "phi4" in mcp.JARVIS_HEADER


def test_re_ipv4_match():
    m = mcp._RE_IPV4.search("attaque depuis 192.168.1.42 hier")
    assert m is not None
    assert m.group(1) == "192.168.1.42"


def test_re_ipv4_pas_de_faux_positif():
    """Pas de match sur version 1.2.3 ou texte sans 4 octets."""
    assert mcp._RE_IPV4.search("foo bar") is None


# ── _sanitize ───────────────────────────────────────────────────────────


def test_sanitize_remplace_ipv4():
    result = mcp._sanitize("ban de 8.8.8.8 et 1.1.1.1")
    assert "8.8.8.8" not in result
    assert "1.1.1.1" not in result
    assert "[IP]" in result


def test_sanitize_pas_de_changement_sans_ip():
    assert mcp._sanitize("hello world") == "hello world"


def test_sanitize_tronque_au_dela_max_chars():
    long_text = "a" * 5000
    result = mcp._sanitize(long_text, max_chars=100)
    assert len(result) < len(long_text)
    assert "tronqué" in result
    assert "5000" in result


def test_sanitize_garde_si_sous_max():
    result = mcp._sanitize("court", max_chars=100)
    assert result == "court"


def test_sanitize_max_chars_default_3000():
    """Vérifie que 3001 chars sont tronqués."""
    text = "a" * 3001
    result = mcp._sanitize(text)
    assert "tronqué" in result


# ── _TOOLS_DEFS ─────────────────────────────────────────────────────────


def test_tools_defs_compte_10_outils():
    assert len(mcp._TOOLS_DEFS) == 10


def test_tools_defs_noms_uniques():
    names = [t.name for t in mcp._TOOLS_DEFS]
    assert len(names) == len(set(names))


def test_tools_defs_contient_jarvis_chat():
    names = [t.name for t in mcp._TOOLS_DEFS]
    assert "jarvis_chat" in names
    assert "jarvis_soc_status" in names
    assert "jarvis_soc_ask" in names
    assert "jarvis_stats" in names
    assert "jarvis_infra_status" in names
    assert "jarvis_proxmox_vms" in names
    assert "jarvis_read_file" in names
    assert "jarvis_model_switch" in names
    assert "jarvis_last_response" in names
    assert "jarvis_code_exec" in names


def test_tool_handlers_compte_10_handlers():
    assert len(mcp._TOOL_HANDLERS) == 10


def test_tool_handlers_correspondent_aux_defs():
    """Chaque outil défini dans _TOOLS_DEFS a un handler."""
    handler_names = set(mcp._TOOL_HANDLERS.keys())
    def_names = {t.name for t in mcp._TOOLS_DEFS}
    assert handler_names == def_names


# ── _collect_sse_tokens ────────────────────────────────────────────────


def test_collect_sse_tokens_concatenation(monkeypatch):
    """Tokens accumulés et retournés en string."""
    _reset_fake()
    lines = [
        'data: {"type":"token","token":"Hello "}',
        'data: {"type":"token","token":"world"}',
    ]
    _FakeClient.routes_stream["http://x/api/chat"] = _FakeResp(200, lines=lines)
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._collect_sse_tokens("http://x/api/chat", {}))
    assert result == "Hello world"


def test_collect_sse_tokens_ignore_lignes_non_data(monkeypatch):
    """Lignes ne commençant pas par 'data:' sont ignorées."""
    _reset_fake()
    lines = [
        ': comment',
        'data: {"type":"token","token":"OK"}',
        'event: ping',
    ]
    _FakeClient.routes_stream["http://x/api/chat"] = _FakeResp(200, lines=lines)
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._collect_sse_tokens("http://x/api/chat", {}))
    assert result == "OK"


def test_collect_sse_tokens_ignore_json_invalide(monkeypatch):
    _reset_fake()
    lines = [
        'data: not json',
        'data: {"type":"token","token":"valid"}',
    ]
    _FakeClient.routes_stream["http://x/api/chat"] = _FakeResp(200, lines=lines)
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._collect_sse_tokens("http://x/api/chat", {}))
    assert result == "valid"


def test_collect_sse_tokens_ssh_file_prend_priorite(monkeypatch):
    """Type 'ssh_file' → retourne contenu brut formatté."""
    _reset_fake()
    lines = [
        'data: {"type":"token","token":"junk"}',
        'data: {"type":"ssh_file","vm":"clt","path":"/etc/test","content":"ligne1\\nligne2"}',
    ]
    _FakeClient.routes_stream["http://x/api/chat"] = _FakeResp(200, lines=lines)
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._collect_sse_tokens("http://x/api/chat", {}))
    assert "[SSH FILE]" in result
    assert "CLT" in result
    assert "/etc/test" in result
    assert "ligne1" in result


def test_collect_sse_tokens_data_vide_ignore(monkeypatch):
    _reset_fake()
    lines = [
        'data:   ',
        'data: {"type":"token","token":"x"}',
    ]
    _FakeClient.routes_stream["http://x/api/chat"] = _FakeResp(200, lines=lines)
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._collect_sse_tokens("http://x/api/chat", {}))
    assert result == "x"


# ── _get_ip_history ────────────────────────────────────────────────────


def test_get_ip_history_404_renvoie_vide(monkeypatch):
    _reset_fake()
    _FakeClient.routes_post[f"{mcp.JARVIS_BASE}/api/soc/ip-history"] = _FakeResp(500)
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._get_ip_history("8.8.8.8"))
    assert result == ""


def test_get_ip_history_aucun_historique(monkeypatch):
    """Si crowdsec et fail2ban tous deux à 0 → string vide."""
    _reset_fake()
    _FakeClient.routes_post[f"{mcp.JARVIS_BASE}/api/soc/ip-history"] = _FakeResp(
        200, json_data={"crowdsec": {"alerts_30d": 0}, "fail2ban": {"total_records": 0}}
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._get_ip_history("8.8.8.8"))
    assert result == ""


def test_get_ip_history_avec_donnees(monkeypatch):
    _reset_fake()
    _FakeClient.routes_post[f"{mcp.JARVIS_BASE}/api/soc/ip-history"] = _FakeResp(
        200, json_data={
            "crowdsec": {
                "alerts_30d": 12,
                "count": 3,
                "alerts_detail": [{"ts": "2026-05-15T10:00:00", "scenario": "scan-bf"}],
            },
            "fail2ban": {"total_records": 5, "active": ["jail1", "jail2"]},
        }
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._get_ip_history("1.2.3.4"))
    assert "1.2.3.4" in result
    assert "12 alertes" in result
    assert "scan-bf" in result
    assert "Fail2ban : 5" in result


def test_get_ip_history_exception_renvoie_vide(monkeypatch):
    _reset_fake()
    _FakeClient.raise_post = ConnectionError("boom")
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._get_ip_history("1.2.3.4"))
    assert result == ""


# ── _get_soc_context_live ──────────────────────────────────────────────


def test_get_soc_context_live_succes(monkeypatch):
    _reset_fake()
    _FakeClient.routes_get[f"{mcp.JARVIS_BASE}/api/soc/context"] = _FakeResp(
        200, json_data={"ok": True, "context": "[CTX SOC] menace 42/100"}
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._get_soc_context_live())
    assert "menace 42" in result


def test_get_soc_context_live_fallback_status(monkeypatch):
    """Si /api/soc/context ne renvoie pas ok → fallback /api/status."""
    _reset_fake()
    _FakeClient.routes_get[f"{mcp.JARVIS_BASE}/api/soc/context"] = _FakeResp(
        200, json_data={"ok": False}
    )
    _FakeClient.routes_get[f"{mcp.JARVIS_BASE}/api/status"] = _FakeResp(
        200, json_data={"bans_24h": 7, "alerts_24h": 22, "soc_engine_active": True}
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._get_soc_context_live())
    assert "Bans 24h: 7" in result
    assert "actif" in result


def test_get_soc_context_live_tout_ko(monkeypatch):
    _reset_fake()
    _FakeClient.raise_get = ConnectionError("offline")
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._get_soc_context_live())
    assert result == ""


# ── _handle_jarvis_chat ────────────────────────────────────────────────


def test_handle_jarvis_chat_succes(monkeypatch):
    _reset_fake()
    lines = ['data: {"type":"token","token":"Bonjour"}']
    _FakeClient.routes_stream[f"{mcp.JARVIS_BASE}/api/chat"] = _FakeResp(200, lines=lines)
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_chat({"message": "salut"}))
    assert len(result) == 1
    assert "Bonjour" in result[0].text
    assert "JARVIS" in result[0].text  # header


def test_handle_jarvis_chat_pas_de_reponse(monkeypatch):
    _reset_fake()
    _FakeClient.routes_stream[f"{mcp.JARVIS_BASE}/api/chat"] = _FakeResp(200, lines=[])
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_chat({"message": "salut"}))
    assert "Pas de réponse" in result[0].text


# ── _handle_jarvis_soc_status ───────────────────────────────────────────


def test_handle_jarvis_soc_status(monkeypatch):
    _reset_fake()
    _FakeClient.routes_get[f"{mcp.JARVIS_BASE}/api/status"] = _FakeResp(
        200, json_data={"model": "phi4:14b", "soc_engine_active": True,
                        "bans_24h": 3, "alerts_24h": 17}
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_soc_status({}))
    text = result[0].text
    assert "phi4:14b" in text
    assert "actif" in text
    assert "Bans 24h        : 3" in text


# ── _handle_jarvis_stats ────────────────────────────────────────────────


def test_handle_jarvis_stats(monkeypatch):
    _reset_fake()
    _FakeClient.routes_get[f"{mcp.JARVIS_BASE}/api/stats"] = _FakeResp(
        200, json_data={"uptime": 1234, "sessions": 5}
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_stats({}))
    text = result[0].text
    assert "uptime" in text
    assert "1234" in text


# ── _handle_jarvis_read_file ────────────────────────────────────────────


def test_handle_jarvis_read_file_vm_manquant(monkeypatch):
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_read_file({"vm": "", "path": "/etc/test"}))
    assert "requis" in result[0].text


def test_handle_jarvis_read_file_path_manquant(monkeypatch):
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_read_file({"vm": "clt", "path": ""}))
    assert "requis" in result[0].text


def test_handle_jarvis_read_file_succes(monkeypatch):
    _reset_fake()
    lines = ['data: {"type":"token","token":"contenu fichier"}']
    _FakeClient.routes_stream[f"{mcp.JARVIS_BASE}/api/chat"] = _FakeResp(200, lines=lines)
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_read_file({"vm": "clt", "path": "/etc/test"}))
    assert "contenu fichier" in result[0].text


# ── _handle_jarvis_model_switch ────────────────────────────────────────


def test_handle_jarvis_model_switch_vide(monkeypatch):
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_model_switch({"model": ""}))
    assert "requis" in result[0].text


def test_handle_jarvis_model_switch_succes(monkeypatch):
    _reset_fake()
    _FakeClient.routes_post[f"{mcp.JARVIS_BASE}/api/models"] = _FakeResp(
        200, json_data={"ok": True, "model": "qwen2.5-coder:14b", "auto_profile": "code"}
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_model_switch({"model": "qwen2.5-coder:14b"}))
    text = result[0].text
    assert "qwen2.5-coder:14b" in text
    assert "code" in text


def test_handle_jarvis_model_switch_echec(monkeypatch):
    _reset_fake()
    _FakeClient.routes_post[f"{mcp.JARVIS_BASE}/api/models"] = _FakeResp(
        200, json_data={"ok": False}
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_model_switch({"model": "inconnu"}))
    assert "Échec" in result[0].text


# ── _handle_jarvis_last_response ───────────────────────────────────────


def test_handle_jarvis_last_response_vide(monkeypatch):
    _reset_fake()
    _FakeClient.routes_get[f"{mcp.JARVIS_BASE}/api/history/last"] = _FakeResp(
        200, json_data={"exchanges": []}
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_last_response({"n": 1}))
    assert "Aucun échange" in result[0].text


def test_handle_jarvis_last_response_avec_echanges(monkeypatch):
    _reset_fake()
    _FakeClient.routes_get[f"{mcp.JARVIS_BASE}/api/history/last"] = _FakeResp(
        200, json_data={"exchanges": [
            {"ts": 1700000000, "user": "salut", "assistant": "Bonjour Marc"},
        ]}
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_last_response({"n": 1}))
    text = result[0].text
    assert "USER" in text
    assert "salut" in text
    assert "Bonjour Marc" in text


def test_handle_jarvis_last_response_n_clamped(monkeypatch):
    """n=99 → clamped à 5."""
    _reset_fake()
    captured = {}
    class _CC(_FakeClient):
        async def get(self, url, **kw):
            captured["params"] = kw.get("params")
            return _FakeResp(200, json_data={"exchanges": []})
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _CC)
    _run(mcp._handle_jarvis_last_response({"n": 99}))
    assert captured["params"] == {"n": 5}


def test_handle_jarvis_last_response_n_negatif_clamped_a_1(monkeypatch):
    _reset_fake()
    captured = {}
    class _CC(_FakeClient):
        async def get(self, url, **kw):
            captured["params"] = kw.get("params")
            return _FakeResp(200, json_data={"exchanges": []})
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _CC)
    _run(mcp._handle_jarvis_last_response({"n": -5}))
    assert captured["params"] == {"n": 1}


def test_handle_jarvis_last_response_sanitize_ips(monkeypatch):
    """Les IPv4 dans 'assistant' doivent être remplacées par [IP]."""
    _reset_fake()
    _FakeClient.routes_get[f"{mcp.JARVIS_BASE}/api/history/last"] = _FakeResp(
        200, json_data={"exchanges": [
            {"ts": 1700000000, "user": "infos sur 8.8.8.8",
             "assistant": "L'IP 1.2.3.4 a été bannie"},
        ]}
    )
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_last_response({"n": 1}))
    text = result[0].text
    assert "[IP]" in text
    assert "8.8.8.8" not in text
    assert "1.2.3.4" not in text


# ── _handle_jarvis_code_exec ───────────────────────────────────────────


def test_handle_jarvis_code_exec_filename_vide(monkeypatch):
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_code_exec({"filename": "", "code": "print(1)"}))
    assert "requis" in result[0].text


def test_handle_jarvis_code_exec_code_vide(monkeypatch):
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_code_exec({"filename": "x.py", "code": ""}))
    assert "requis" in result[0].text


def test_handle_jarvis_code_exec_succes(monkeypatch):
    _reset_fake()
    lines = ['data: {"type":"token","token":"sortie OK"}']
    _FakeClient.routes_stream[f"{mcp.JARVIS_BASE}/api/code/exec"] = _FakeResp(200, lines=lines)
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp._handle_jarvis_code_exec({"filename": "x.py", "code": "print(1)"}))
    assert "sortie OK" in result[0].text


# ── _handle_jarvis_soc_ask (avec injection IP) ─────────────────────────


def test_handle_jarvis_soc_ask_avec_ip_dans_question(monkeypatch):
    """Question contenant IP → contexte IP injecté + contexte SOC."""
    _reset_fake()
    _FakeClient.routes_get[f"{mcp.JARVIS_BASE}/api/soc/context"] = _FakeResp(
        200, json_data={"ok": True, "context": "[SOC LIVE]"}
    )
    _FakeClient.routes_post[f"{mcp.JARVIS_BASE}/api/soc/ip-history"] = _FakeResp(
        200, json_data={"crowdsec": {"alerts_30d": 5}, "fail2ban": {"total_records": 0}}
    )
    captured_payload = {}
    lines = ['data: {"type":"token","token":"analyse OK"}']

    class _CC(_FakeClient):
        def stream(self, method, url, **kw):
            captured_payload["json"] = kw.get("json")
            return _FakeStreamCtx(_FakeResp(200, lines=lines))

    monkeypatch.setattr(mcp.httpx, "AsyncClient", _CC)
    result = _run(mcp._handle_jarvis_soc_ask({"question": "que penses-tu de 1.2.3.4 ?"}))
    assert "analyse OK" in result[0].text
    sent = captured_payload["json"]["history"][0]["content"]
    assert "[SOC LIVE]" in sent
    assert "1.2.3.4" in sent
    assert captured_payload["json"]["soc_ctx_injected"] is True


# ── call_tool (dispatcher) ─────────────────────────────────────────────


def test_call_tool_outil_inconnu(monkeypatch):
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    result = _run(mcp.call_tool("outil_qui_existe_pas", {}))
    assert "inconnu" in result[0].text


def test_call_tool_jarvis_offline(monkeypatch):
    """ConnectError → message 'JARVIS hors ligne'."""
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    async def _fail(_):
        raise mcp.httpx.ConnectError("refused")
    monkeypatch.setitem(mcp._TOOL_HANDLERS, "jarvis_chat", _fail)
    result = _run(mcp.call_tool("jarvis_chat", {"message": "x"}))
    assert "hors ligne" in result[0].text


def test_call_tool_exception_generique(monkeypatch):
    """Exception non-ConnectError → message 'Erreur : ...'."""
    monkeypatch.setattr(mcp.httpx, "AsyncClient", _FakeClient)
    async def _fail(_):
        raise ValueError("boom interne")
    monkeypatch.setitem(mcp._TOOL_HANDLERS, "jarvis_chat", _fail)
    result = _run(mcp.call_tool("jarvis_chat", {"message": "x"}))
    assert "Erreur" in result[0].text
    assert "boom interne" in result[0].text


# ── list_tools ─────────────────────────────────────────────────────────


def test_list_tools_renvoie_les_10():
    result = _run(mcp.list_tools())
    assert len(result) == 10


# ── _build_starlette_app ───────────────────────────────────────────────


def test_build_starlette_app_routes_presentes():
    app_starlette = mcp._build_starlette_app(5010)
    paths = [r.path for r in app_starlette.routes if hasattr(r, "path")]
    assert "/health" in paths
    assert "/sse" in paths
    assert "/mcp" in paths
