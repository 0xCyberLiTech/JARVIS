"""Tests ollama_circuit — state machine FERMÉ/OUVERT/SEMI-OUVERT + backoff exponentiel."""
import time

import pytest
from ollama_circuit import (
    BACKOFF_MAX_S,
    FAILURE_THRESHOLD,
    RECOVERY_TIMEOUT_S,
    STATE_CLOSED,
    STATE_HALF_OPEN,
    STATE_OPEN,
    OllamaUnavailable,
    circuit,
)


@pytest.fixture(autouse=True)
def _reset():
    """Reset circuit avant chaque test pour isolation."""
    circuit.reset()
    yield
    circuit.reset()


# ── Constantes ────────────────────────────────────────────────────────────


def test_failure_threshold_3():
    assert FAILURE_THRESHOLD == 3


def test_recovery_timeout_30s():
    assert RECOVERY_TIMEOUT_S == 30


def test_backoff_max_5min():
    assert BACKOFF_MAX_S == 300


def test_etats_constantes():
    assert STATE_CLOSED == "closed"
    assert STATE_OPEN == "open"
    assert STATE_HALF_OPEN == "half_open"


# ── État initial ──────────────────────────────────────────────────────────


def test_etat_initial_closed():
    status = circuit.get_status()
    assert status["state"] == STATE_CLOSED
    assert status["failures"] == 0
    assert status["retry_in_s"] == 0


# ── CLOSED : succès passent ──────────────────────────────────────────────


def test_call_succes_renvoie_resultat():
    result = circuit.call(lambda: "OK")
    assert result == "OK"


def test_call_succes_passe_args_kwargs():
    def fn(a, b, c=None):
        return f"{a}-{b}-{c}"
    result = circuit.call(fn, "x", "y", c="z")
    assert result == "x-y-z"


def test_succes_reset_failures():
    """Une erreur isolée + un succès → failures reset à 0."""
    with pytest.raises(ConnectionError):
        circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    assert circuit.get_status()["failures"] == 1
    circuit.call(lambda: "OK")
    assert circuit.get_status()["failures"] == 0


# ── 1-2 erreurs : reste CLOSED ───────────────────────────────────────────


def test_une_erreur_reste_closed():
    with pytest.raises(RuntimeError):
        circuit.call(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    assert circuit.get_status()["state"] == STATE_CLOSED
    assert circuit.get_status()["failures"] == 1


def test_deux_erreurs_reste_closed():
    for _ in range(2):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    assert circuit.get_status()["state"] == STATE_CLOSED
    assert circuit.get_status()["failures"] == 2


# ── FAILURE_THRESHOLD erreurs → OPEN ──────────────────────────────────────


def test_trois_erreurs_consecutives_ouvre_circuit():
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    assert circuit.get_status()["state"] == STATE_OPEN


def test_circuit_ouvert_raise_ollama_unavailable_immediatement():
    """En OPEN, tout call raise OllamaUnavailable sans appeler fn."""
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    # fn ne doit PAS être appelé
    captured = {"called": False}
    def fn():
        captured["called"] = True
        return "OK"
    with pytest.raises(OllamaUnavailable):
        circuit.call(fn)
    assert captured["called"] is False


def test_ouverture_circuit_immediate_pas_de_delai():
    """Le 3e échec ouvre le circuit, le 4e raise OllamaUnavailable directement."""
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    t0 = time.monotonic()
    with pytest.raises(OllamaUnavailable):
        circuit.call(lambda: "won't happen")
    elapsed = time.monotonic() - t0
    assert elapsed < 0.01  # raise quasi-instantané


# ── HALF_OPEN après recovery timeout ─────────────────────────────────────


def test_half_open_apres_recovery_timeout(monkeypatch):
    """Après RECOVERY_TIMEOUT_S, le circuit passe HALF_OPEN au prochain call."""
    # Force OPEN
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    # Avance le temps virtuel via monkeypatch
    fake_now = time.monotonic() + RECOVERY_TIMEOUT_S + 1
    monkeypatch.setattr("ollama_circuit.time", type("T", (), {"monotonic": staticmethod(lambda: fake_now)})())

    # Le call passe (state interne devient HALF_OPEN puis test fn)
    result = circuit.call(lambda: "RECOVERED")
    assert result == "RECOVERED"
    # Succès en HALF_OPEN → retour CLOSED
    assert circuit.get_status()["state"] == STATE_CLOSED


def test_half_open_succes_retour_closed(monkeypatch):
    """HALF_OPEN + succès → CLOSED + reset failures + reset timeout."""
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    fake_now = time.monotonic() + RECOVERY_TIMEOUT_S + 1
    monkeypatch.setattr("ollama_circuit.time", type("T", (), {"monotonic": staticmethod(lambda: fake_now)})())

    circuit.call(lambda: "OK")
    status = circuit.get_status()
    assert status["state"] == STATE_CLOSED
    assert status["failures"] == 0
    assert status["current_timeout_s"] == RECOVERY_TIMEOUT_S


def test_half_open_echec_retour_open_avec_backoff(monkeypatch):
    """HALF_OPEN + échec → OPEN avec backoff exponentiel ×2."""
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    fake_now = time.monotonic() + RECOVERY_TIMEOUT_S + 1
    monkeypatch.setattr("ollama_circuit.time", type("T", (), {"monotonic": staticmethod(lambda: fake_now)})())

    with pytest.raises(ConnectionError):
        circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))

    status = circuit.get_status()
    assert status["state"] == STATE_OPEN
    # Backoff doublé : 30 → 60
    assert status["current_timeout_s"] == RECOVERY_TIMEOUT_S * 2


def test_backoff_plafonne_a_max(monkeypatch):
    """Backoff exponentiel plafonné à BACKOFF_MAX_S (5 min)."""
    # Ouvre le circuit + force backoff jusqu'au plafond
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))

    base = time.monotonic()
    fake_time = {"now": base}

    def fake_monotonic():
        return fake_time["now"]

    monkeypatch.setattr("ollama_circuit.time",
                        type("T", (), {"monotonic": staticmethod(fake_monotonic)})())

    # Plusieurs cycles HALF_OPEN→échec pour escalader
    for _ in range(10):
        fake_time["now"] += circuit.get_status()["current_timeout_s"] + 1
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))

    assert circuit.get_status()["current_timeout_s"] == BACKOFF_MAX_S


# ── get_status format ────────────────────────────────────────────────────


def test_get_status_format():
    status = circuit.get_status()
    assert set(status.keys()) == {"state", "failures", "retry_in_s", "current_timeout_s"}
    assert isinstance(status["state"], str)
    assert isinstance(status["failures"], int)
    assert isinstance(status["retry_in_s"], int)
    assert isinstance(status["current_timeout_s"], int)


def test_get_status_retry_in_s_zero_si_closed():
    assert circuit.get_status()["retry_in_s"] == 0


def test_get_status_retry_in_s_positif_si_open():
    """En OPEN, retry_in_s décompte vers 0."""
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    status = circuit.get_status()
    assert status["state"] == STATE_OPEN
    assert 0 < status["retry_in_s"] <= RECOVERY_TIMEOUT_S


# ── reset() ─────────────────────────────────────────────────────────────


def test_reset_force_closed_zero_failures():
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    assert circuit.get_status()["state"] == STATE_OPEN

    circuit.reset()
    status = circuit.get_status()
    assert status["state"] == STATE_CLOSED
    assert status["failures"] == 0
    assert status["current_timeout_s"] == RECOVERY_TIMEOUT_S


# ── Sanity exception type ───────────────────────────────────────────────


def test_ollama_unavailable_est_une_exception():
    assert issubclass(OllamaUnavailable, Exception)


def test_ollama_unavailable_message_indique_circuit_ouvert():
    for _ in range(FAILURE_THRESHOLD):
        with pytest.raises(ConnectionError):
            circuit.call(lambda: (_ for _ in ()).throw(ConnectionError()))
    try:
        circuit.call(lambda: "x")
    except OllamaUnavailable as e:
        assert "circuit ouvert" in str(e).lower()
        assert "retry" in str(e).lower()
