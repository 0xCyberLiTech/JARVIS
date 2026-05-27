"""Tests ssh_terminal — détection regex + générateur SSE PTY (4 hôtes — router retiré 2026-05-17)."""
import json

import ssh_terminal

# ── TERMINAL_MAP ────────────────────────────────────────────────────────


def test_terminal_map_couvre_4_hotes():
    """retiré 2026-05-17"""
    assert set(ssh_terminal.TERMINAL_MAP.keys()) == {"dev1", "nginx", "clt", "pa85"}


def test_terminal_map_dev1_pointe_sur_srv_dev_1():
    """dev1 réutilise les constantes de bypass_code (CODE_DEV_IP/PORT/KEY)."""
    from bypass import code as bypass_code
    entry = ssh_terminal.TERMINAL_MAP["dev1"]
    assert entry["ip"] == bypass_code.CODE_DEV_IP
    assert entry["port"] == bypass_code.CODE_DEV_PORT
    assert entry["key"] == bypass_code.CODE_DEV_KEY
    assert entry["label"] == "srv-dev-1"


def test_terminal_map_nginx_ip_192_168_1_50():
    assert ssh_terminal.TERMINAL_MAP["nginx"]["ip"] == "192.168.1.50"
    assert ssh_terminal.TERMINAL_MAP["nginx"]["port"] == 2272


def test_terminal_map_clt_ip_192_168_1_12():
    assert ssh_terminal.TERMINAL_MAP["clt"]["ip"] == "192.168.1.12"


def test_terminal_map_pa85_ip_192_168_1_13():
    assert ssh_terminal.TERMINAL_MAP["pa85"]["ip"] == "192.168.1.13"


# test_terminal_map_router_user_admin_clt retiré 2026-05-17 — 


def test_terminal_map_chaque_hote_a_les_5_champs():
    """Sanity : ip/port/user/key/label présents pour chaque hôte."""
    expected_keys = {"ip", "port", "user", "key", "label"}
    for host_key, entry in ssh_terminal.TERMINAL_MAP.items():
        assert set(entry.keys()) == expected_keys, f"Hôte {host_key} mal formé"


# ── TERMINAL_RE — détection regex (4 hôtes — router retiré 2026-05-17) ──


def test_re_dev1_match_ouvre_terminal_srv_dev_1():
    assert ssh_terminal.TERMINAL_RE["dev1"].search("ouvre terminal srv-dev-1")


def test_re_dev1_match_connecte_moi_dev1():
    assert ssh_terminal.TERMINAL_RE["dev1"].search("connecte-moi dev-1")


def test_re_dev1_pas_match_sans_verbe():
    assert not ssh_terminal.TERMINAL_RE["dev1"].search("info srv-dev-1")


def test_re_nginx_match_ssh_nginx():
    assert ssh_terminal.TERMINAL_RE["nginx"].search("ssh nginx")


def test_re_nginx_match_terminal_nginx():
    """Alias 'nginx' couvert."""
    assert ssh_terminal.TERMINAL_RE["nginx"].search("ouvre terminal nginx")


def test_re_clt_match():
    assert ssh_terminal.TERMINAL_RE["clt"].search("connecte-moi à clt")


def test_re_pa85_match():
    assert ssh_terminal.TERMINAL_RE["pa85"].search("ssh pa85")


# Tests regex router retirés 2026-05-17 (architecture LAN unique — regex router supprimée)


def test_re_case_insensitive():
    """Les regex sont insensibles à la casse."""
    assert ssh_terminal.TERMINAL_RE["nginx"].search("OUVRE TERMINAL NGINX")


def test_re_aucun_match_phrase_quelconque():
    """Phrase neutre → aucun hôte matché."""
    for re_key in ssh_terminal.TERMINAL_RE.values():
        assert not re_key.search("bonjour Marc")


# ── _sse_tok ────────────────────────────────────────────────────────────


def test_sse_tok_format_standard():
    out = ssh_terminal._sse_tok("hello", done=True)
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload == {"type": "token", "token": "hello", "done": True}


def test_sse_tok_done_default_false():
    payload = json.loads(ssh_terminal._sse_tok("x").replace("data: ", "").strip())
    assert payload["done"] is False


# ── terminal_sse ────────────────────────────────────────────────────────


def test_terminal_sse_yield_2_events():
    events = list(ssh_terminal.terminal_sse("nginx", "srv-nginx"))
    assert len(events) == 2


def test_terminal_sse_premier_event_open_ssh_terminal():
    events = list(ssh_terminal.terminal_sse("nginx", "srv-nginx", user="root"))
    payload = json.loads(events[0].replace("data: ", "").strip())
    assert payload["type"] == "open_ssh_terminal"
    assert payload["host"] == "nginx"
    assert payload["label"] == "srv-nginx"
    assert payload["user"] == "root"


def test_terminal_sse_deuxieme_event_token_done_avec_label():
    events = list(ssh_terminal.terminal_sse("clt", "srv-clt"))
    payload = json.loads(events[1].replace("data: ", "").strip())
    assert payload["type"] == "token"
    assert payload["done"] is True
    assert "srv-clt" in payload["token"]


def test_terminal_sse_user_default_root():
    events = list(ssh_terminal.terminal_sse("dev1", "srv-dev-1"))
    payload = json.loads(events[0].replace("data: ", "").strip())
    assert payload["user"] == "root"


def test_terminal_sse_user_custom():
    """Sanity : user explicite passé tel quel dans le payload SSE (user='admin-clt' arbitraire)."""
    events = list(ssh_terminal.terminal_sse("dev1", "srv-dev-1", user="admin-clt"))
    payload = json.loads(events[0].replace("data: ", "").strip())
    assert payload["user"] == "admin-clt"
