"""Tests llm/vram — ensure_vram + ollama_swap (étape 35).

Couvre le swap synchrone VRAM Ollama (unload SYNC + preload BACKGROUND thread)
sous protection _vram_lock. Tous les urllib.request + thread sont mockés.
"""
import threading
from unittest.mock import MagicMock, patch

import pytest
from llm import vram


@pytest.fixture(autouse=True)
def _reinit_vram():
    """DI propre avant chaque test + restauration en teardown."""
    saved = {k: getattr(vram, k) for k in (
        "_log", "_get_model", "_get_vram_model", "_set_vram_model",
        "_vram_lock", "_ollama_url",
    )}

    state = {"model": None}

    vram.init(
        log=MagicMock(),
        get_model=lambda: "phi4:14b",          # MODEL par défaut SOC
        get_vram_model=lambda: state["model"],
        set_vram_model=lambda v: state.update({"model": v}),
        vram_lock=threading.Lock(),
        ollama_url="http://127.0.0.1:11434",
    )
    try:
        yield state
    finally:
        for k, v in saved.items():
            setattr(vram, k, v)


# ── ensure_vram ────────────────────────────────────────────────────────────


def test_ensure_vram_aucun_modele_charge_set_directement(_reinit_vram):
    """_vram_model = None → pas de swap, juste set au modèle cible."""
    vram.ensure_vram("qwen2.5-coder:14b")
    assert _reinit_vram["model"] == "qwen2.5-coder:14b"
    vram._log.info.assert_not_called()  # pas de log 'Routing switch'


def test_ensure_vram_meme_modele_pas_de_swap(_reinit_vram):
    """_vram_model identique au prochain → pas de swap, juste réaffirme."""
    _reinit_vram["model"] = "phi4:14b"
    with patch.object(vram, "ollama_swap") as mock_swap:
        vram.ensure_vram("phi4:14b")
    mock_swap.assert_not_called()
    assert _reinit_vram["model"] == "phi4:14b"


def test_ensure_vram_modele_different_declenche_swap(_reinit_vram):
    """_vram_model != next → ollama_swap appelé + log 'Routing switch'."""
    _reinit_vram["model"] = "phi4:14b"
    with patch.object(vram, "ollama_swap") as mock_swap:
        vram.ensure_vram("qwen2.5-coder:14b")
    mock_swap.assert_called_once_with("phi4:14b", "qwen2.5-coder:14b")
    log_msg = vram._log.info.call_args[0][0]
    assert "Routing switch" in log_msg
    assert "phi4:14b" in log_msg and "qwen2.5-coder:14b" in log_msg
    assert _reinit_vram["model"] == "qwen2.5-coder:14b"


def test_ensure_vram_next_model_vide_fallback_get_model(_reinit_vram):
    """next_model='' → utilise get_model() (default 'phi4:14b')."""
    _reinit_vram["model"] = "qwen3:8b"
    with patch.object(vram, "ollama_swap"):
        vram.ensure_vram("")
    assert _reinit_vram["model"] == "phi4:14b"  # = get_model()


def test_ensure_vram_lock_serialise_acces(_reinit_vram):
    """Le _vram_lock est bien pris pendant ensure_vram (pas de race)."""
    # Vérification indirecte : si on remplace le lock par un Mock, son __enter__
    # doit être appelé exactement 1 fois.
    mock_lock = MagicMock()
    vram._vram_lock = mock_lock
    with patch.object(vram, "ollama_swap"):
        vram.ensure_vram("any-model")
    mock_lock.__enter__.assert_called_once()
    mock_lock.__exit__.assert_called_once()


# ── ollama_swap ────────────────────────────────────────────────────────────


def test_ollama_swap_unload_synchrone_appel_ollama(_reinit_vram):
    """unload via urllib /api/generate keep_alive=0 timeout 8 + log 'déchargé (sync)'."""
    fake_resp = MagicMock()
    fake_resp.__enter__ = MagicMock(return_value=fake_resp)
    fake_resp.__exit__  = MagicMock(return_value=False)
    with patch.object(vram.urllib.request, "urlopen", return_value=fake_resp) as mock_open, \
         patch.object(vram.threading, "Thread") as MockThread:
        # Empêche le thread preload de s'exécuter (on teste juste l'unload sync)
        MockThread.return_value = MagicMock()
        vram.ollama_swap("phi4:14b", "qwen2.5-coder:14b")
    # urlopen appelé au moins 1 fois (unload sync)
    assert mock_open.call_count >= 1
    # Log 'déchargé (sync)' présent
    msgs = [c.args[0] for c in vram._log.info.call_args_list]
    assert any("déchargé (sync)" in m and "phi4:14b" in m for m in msgs)


def test_ollama_swap_unload_exception_logguee_warning(_reinit_vram):
    """Si urlopen unload lance → log warning, pas de crash."""
    with patch.object(vram.urllib.request, "urlopen", side_effect=OSError("connection refused")), \
         patch.object(vram.threading, "Thread"):
        vram.ollama_swap("phi4:14b", "qwen2.5-coder:14b")
    warnings = [c.args[0] for c in vram._log.warning.call_args_list]
    assert any("unload phi4:14b" in m for m in warnings)


def test_ollama_swap_preload_lance_thread_daemon(_reinit_vram):
    """Le preload du nouveau modèle est lancé dans un thread daemon."""
    fake_resp = MagicMock()
    fake_resp.__enter__ = MagicMock(return_value=fake_resp)
    fake_resp.__exit__  = MagicMock(return_value=False)
    with patch.object(vram.urllib.request, "urlopen", return_value=fake_resp), \
         patch.object(vram.threading, "Thread") as MockThread:
        thread_instance = MagicMock()
        MockThread.return_value = thread_instance
        vram.ollama_swap("phi4:14b", "qwen2.5-coder:14b")
    MockThread.assert_called_once()
    kwargs = MockThread.call_args.kwargs
    assert kwargs["daemon"] is True
    thread_instance.start.assert_called_once()


def test_ollama_swap_preload_execute_charge_modele(_reinit_vram):
    """Le _preload() interne (inner func du thread) appelle urlopen avec keep_alive=30m."""
    fake_resp = MagicMock()
    fake_resp.__enter__ = MagicMock(return_value=fake_resp)
    fake_resp.__exit__  = MagicMock(return_value=False)
    captured_calls = []

    def _capture_urlopen(req, timeout=None):
        # Capture l'URL + le body JSON pour vérifier que keep_alive='30m'
        import json as _json
        data = _json.loads(req.data.decode())
        captured_calls.append({"timeout": timeout, "model": data.get("model"),
                               "keep_alive": data.get("keep_alive")})
        return fake_resp

    with patch.object(vram.urllib.request, "urlopen", side_effect=_capture_urlopen):
        # Pas de patch threading.Thread → le preload s'exécute pour de vrai (mocké urlopen)
        vram.ollama_swap("phi4:14b", "qwen2.5-coder:14b")
        # Laisse le thread daemon s'exécuter
        import time
        for _ in range(20):  # 200ms max
            if any(c["keep_alive"] == "30m" for c in captured_calls):
                break
            time.sleep(0.01)

    # On doit avoir au moins l'unload (keep_alive=0) ET le preload (keep_alive='30m')
    unloads = [c for c in captured_calls if c["keep_alive"] == 0]
    preloads = [c for c in captured_calls if c["keep_alive"] == "30m"]
    assert any(c["model"] == "phi4:14b" for c in unloads)
    assert any(c["model"] == "qwen2.5-coder:14b" for c in preloads)


def test_ollama_swap_preload_exception_logguee_warning(_reinit_vram):
    """Si le preload urlopen lance → log warning, pas de crash."""
    call_count = [0]

    def _flaky_urlopen(req, timeout=None):
        call_count[0] += 1
        if call_count[0] == 1:
            # 1er appel = unload OK
            r = MagicMock()
            r.__enter__ = MagicMock(return_value=r)
            r.__exit__  = MagicMock(return_value=False)
            return r
        # 2e appel = preload KO
        raise OSError("ollama down")

    with patch.object(vram.urllib.request, "urlopen", side_effect=_flaky_urlopen):
        vram.ollama_swap("phi4:14b", "qwen2.5-coder:14b")
        import time
        time.sleep(0.2)  # laisse le thread daemon s'exécuter

    warnings = [c.args[0] for c in vram._log.warning.call_args_list]
    assert any("preload qwen2.5-coder:14b" in m for m in warnings)
