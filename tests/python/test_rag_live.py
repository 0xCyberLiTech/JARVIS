"""Tests rag_live — fetch logs SOC + cache + injection conditionnelle (mock ssh_fn)."""
import threading
import time

import rag_live


def _reset_state():
    """Reset state module-level entre tests."""
    rag_live._text = ""
    rag_live._last_refresh = 0.0


# ── Constantes ────────────────────────────────────────────────────────────


def test_live_ttl_300s():
    assert rag_live.LIVE_TTL == 300


def test_live_kw_match_termes_essentiels():
    """Sanity : keywords SOC essentiels matchés."""
    for kw in ["log", "alert", "alerte", "suricata", "fail2ban", "ban", "crowdsec",
               "attaque", "menace", "intrusion", "exploit"]:
        assert rag_live.LIVE_KW.search(f"j'ai vu un {kw} hier")


def test_live_kw_pas_match_phrase_neutre():
    assert not rag_live.LIVE_KW.search("bonjour Marc")


def test_live_kw_case_insensitive():
    assert rag_live.LIVE_KW.search("ALERT crowdsec")


def test_ssh_log_cmd_couvre_4_sources():
    """Sanity : la commande SSH couvre Suricata + CrowdSec + fail2ban + nginx."""
    cmd = rag_live.SSH_LOG_CMD
    assert "SURICATA" in cmd
    assert "CROWDSEC" in cmd
    assert "FAIL2BAN" in cmd
    assert "NGINX" in cmd


def test_module_logger():
    assert rag_live._log.name == "jarvis.rag_live"


# ── should_inject ───────────────────────────────────────────────────────


def test_should_inject_keyword_alerte_renvoie_true():
    assert rag_live.should_inject("Y a-t-il une alerte ?") is True


def test_should_inject_keyword_crowdsec_renvoie_true():
    assert rag_live.should_inject("Combien d'IPs bannies par crowdsec ?") is True


def test_should_inject_aucun_keyword_renvoie_false():
    assert rag_live.should_inject("Bonjour Marc, comment vas-tu ?") is False


def test_should_inject_query_vide_renvoie_false():
    assert rag_live.should_inject("") is False


# ── get_text + refresh ──────────────────────────────────────────────────


def test_get_text_initial_vide():
    """Au démarrage, get_text() renvoie chaîne vide (pas encore refreshé)."""
    _reset_state()
    assert rag_live.get_text() == ""


def test_refresh_succes_remplit_cache():
    """Refresh OK → _text peuplé + _last_refresh mis à jour."""
    _reset_state()
    long_output = "=== SURICATA ===\n" + "x" * 100  # >50 chars

    def fake_ssh(cmd, timeout=18):
        return True, long_output

    rag_live.refresh(fake_ssh)
    assert rag_live.get_text() == long_output[:3000]
    assert rag_live._last_refresh > 0


def test_refresh_ttl_skip_si_cache_recent():
    """Si _last_refresh récent (< TTL), refresh skip (n'appelle pas ssh_fn)."""
    _reset_state()
    rag_live._last_refresh = time.time()  # juste maintenant
    rag_live._text = "cached"
    captured = {"called": False}

    def fake_ssh(cmd, timeout=18):
        captured["called"] = True
        return True, "should not be called"

    rag_live.refresh(fake_ssh)
    assert captured["called"] is False
    assert rag_live.get_text() == "cached"


def test_refresh_output_trop_court_skip():
    """Output < 50 chars → considéré comme erreur, pas mis en cache."""
    _reset_state()
    rag_live._text = "previous"

    def fake_ssh(cmd, timeout=18):
        return True, "tiny"  # < 50 chars

    rag_live.refresh(fake_ssh)
    assert rag_live.get_text() == "previous"  # cache préservé


def test_refresh_ssh_echec_skip():
    """ssh_fn renvoie (False, ...) → skip refresh."""
    _reset_state()
    rag_live._text = "previous"

    def fake_ssh(cmd, timeout=18):
        return False, "ssh failed"

    rag_live.refresh(fake_ssh)
    assert rag_live.get_text() == "previous"


def test_refresh_ssh_exception_logged_pas_de_crash():
    """ssh_fn lève → exception attrapée + warn log."""
    _reset_state()

    def fake_ssh(cmd, timeout=18):
        raise ConnectionError("network down")

    # Ne doit pas crasher
    rag_live.refresh(fake_ssh)
    assert rag_live.get_text() == ""  # rien injecté


def test_refresh_tronque_a_3000_chars():
    """Output > 3000 chars → tronqué à 3000."""
    _reset_state()
    huge = "X" * 5000

    def fake_ssh(cmd, timeout=18):
        return True, huge

    rag_live.refresh(fake_ssh)
    assert len(rag_live.get_text()) == 3000


def test_refresh_passe_timeout_a_ssh_fn():
    """Le timeout custom est bien transmis à ssh_fn."""
    _reset_state()
    captured = {}

    def fake_ssh(cmd, timeout=18):
        captured["timeout"] = timeout
        return True, "x" * 100

    rag_live.refresh(fake_ssh, timeout=42)
    assert captured["timeout"] == 42


# ── trigger_async_refresh ───────────────────────────────────────────────


def test_trigger_async_refresh_lance_thread_daemon():
    """trigger_async_refresh lance un thread daemon non-bloquant."""
    _reset_state()
    started = threading.Event()

    def fake_ssh(cmd, timeout=18):
        started.set()
        return True, "x" * 100

    rag_live.trigger_async_refresh(fake_ssh)
    # Le thread doit s'exécuter dans un délai raisonnable
    assert started.wait(timeout=2.0) is True
