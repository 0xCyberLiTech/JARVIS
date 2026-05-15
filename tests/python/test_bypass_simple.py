"""Tests bypass_simple — bypass datetime (heure/jour/date sans appel LLM)."""
import json
from datetime import datetime
from unittest.mock import patch

from bypass_simple import _JOURS, _MOIS, DATETIME_RE, datetime_sse

# ── DATETIME_RE — détection regex ────────────────────────────────────────


def test_datetime_re_match_quelle_heure():
    assert DATETIME_RE.search("quelle heure est-il ?")


def test_datetime_re_match_il_est_quelle_heure():
    assert DATETIME_RE.search("il est quelle heure")


def test_datetime_re_match_quel_jour():
    assert DATETIME_RE.search("quel jour sommes-nous")


def test_datetime_re_match_quelle_date():
    assert DATETIME_RE.search("quelle date aujourd'hui")


def test_datetime_re_match_on_est_quel_jour():
    assert DATETIME_RE.search("on est quel jour")


def test_datetime_re_match_on_est_le_combien():
    assert DATETIME_RE.search("on est le combien")


def test_datetime_re_match_aujourd_hui_on_est():
    assert DATETIME_RE.search("aujourd'hui on est")


def test_datetime_re_match_sommes_nous():
    assert DATETIME_RE.search("où sommes-nous dans la semaine")


def test_datetime_re_case_insensitive():
    assert DATETIME_RE.search("QUELLE HEURE")


def test_datetime_re_pas_match_phrase_quelconque():
    assert not DATETIME_RE.search("bonjour Marc")


def test_datetime_re_pas_match_phrase_neutre():
    assert not DATETIME_RE.search("ban cette IP")


# ── Constantes _JOURS / _MOIS ────────────────────────────────────────────


def test_jours_contient_7_jours_minuscules():
    assert _JOURS == ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def test_mois_contient_12_mois_minuscules():
    assert len(_MOIS) == 12
    assert _MOIS[0] == "janvier"
    assert _MOIS[11] == "décembre"


# ── datetime_sse — génération ────────────────────────────────────────────


def test_datetime_sse_yield_2_events():
    events = list(datetime_sse())
    assert len(events) == 2


def test_datetime_sse_premier_event_token_done_true():
    events = list(datetime_sse())
    payload = json.loads(events[0].replace("data: ", "").strip())
    assert payload["type"] == "token"
    assert payload["done"] is True
    assert payload["token"]  # non vide


def test_datetime_sse_deuxieme_event_speak():
    events = list(datetime_sse())
    payload = json.loads(events[1].replace("data: ", "").strip())
    assert payload["type"] == "speak"
    assert payload["text"]  # non vide


def test_datetime_sse_token_et_speak_sont_identiques():
    """Le texte parlé est le même que le token affiché."""
    events = list(datetime_sse())
    tok = json.loads(events[0].replace("data: ", "").strip())["token"]
    spk = json.loads(events[1].replace("data: ", "").strip())["text"]
    assert tok == spk


def test_datetime_sse_format_attendu_avec_date_fixe():
    """Mock datetime.now() pour vérifier le format exact."""
    fake = datetime(2026, 5, 15, 14, 7)  # vendredi 15 mai 2026 à 14h07
    with patch("bypass_simple.datetime") as mock_dt:
        mock_dt.now.return_value = fake
        events = list(datetime_sse())
    payload = json.loads(events[0].replace("data: ", "").strip())
    assert payload["token"] == "Il est 14h07. Nous sommes le vendredi 15 mai 2026."


def test_datetime_sse_padding_zero_minute():
    """3 minutes → '03', pas '3'."""
    fake = datetime(2026, 1, 1, 9, 3)
    with patch("bypass_simple.datetime") as mock_dt:
        mock_dt.now.return_value = fake
        events = list(datetime_sse())
    payload = json.loads(events[0].replace("data: ", "").strip())
    assert "09h03" in payload["token"]


def test_datetime_sse_padding_zero_heure():
    """0h05 → '00h05'."""
    fake = datetime(2026, 1, 1, 0, 5)
    with patch("bypass_simple.datetime") as mock_dt:
        mock_dt.now.return_value = fake
        events = list(datetime_sse())
    payload = json.loads(events[0].replace("data: ", "").strip())
    assert "00h05" in payload["token"]


def test_datetime_sse_dimanche():
    """weekday() → dimanche = 6."""
    fake = datetime(2026, 5, 17, 12, 0)  # dimanche 17 mai 2026
    with patch("bypass_simple.datetime") as mock_dt:
        mock_dt.now.return_value = fake
        events = list(datetime_sse())
    payload = json.loads(events[0].replace("data: ", "").strip())
    assert "dimanche" in payload["token"]


def test_datetime_sse_format_sse_data_double_newline():
    events = list(datetime_sse())
    for e in events:
        assert e.startswith("data: ")
        assert e.endswith("\n\n")
