"""Tests runtime/speak — speak() + dedup + queue/deferred routing + drop-oldest."""
import threading
import time
from unittest.mock import MagicMock

import pytest
from runtime import speak as runtime_speak


@pytest.fixture(autouse=True)
def _reset_speak_state():
    """État partagé entre tests : vider les queues + reset dedup + DI mock."""
    # Drain les queues entre tests
    while not runtime_speak._speak_queue.empty():
        try:
            runtime_speak._speak_queue.get_nowait()
        except Exception:
            break
    while not runtime_speak._speak_deferred.empty():
        try:
            runtime_speak._speak_deferred.get_nowait()
        except Exception:
            break
    runtime_speak._chat_stream_active.clear()
    runtime_speak._speak_last_text = ''
    runtime_speak._speak_last_time = 0.0

    # Mock tts_dedup : check_and_register retourne False par défaut (pas un doublon)
    tts_dedup_mock = MagicMock()
    tts_dedup_mock.check_and_register = MagicMock(return_value=False)

    runtime_speak.init(
        log=MagicMock(),
        tts_logger=MagicMock(),
        clean_for_tts=lambda s: s.strip() if s else s,
        tts_dedup=tts_dedup_mock,
        tts_dedup_s=60.0,
        tts_log_preview=80,
    )
    yield


# ── Texte vide / blanchi par clean_for_tts ─────────────────────────────────


def test_speak_texte_vide_skip_silencieux():
    """clean_for_tts retourne '' → return immédiat, queue inchangée."""
    runtime_speak.speak("")
    assert runtime_speak._speak_queue.qsize() == 0


def test_speak_texte_whitespace_uniquement_skip():
    """Texte uniquement whitespace → clean_for_tts retourne '' → skip."""
    runtime_speak.speak("   \n\t  ")
    assert runtime_speak._speak_queue.qsize() == 0


# ── Routage simple : queue (pas de stream actif) ───────────────────────────


def test_speak_sans_stream_actif_ajoute_dans_speak_queue():
    """_chat_stream_active non set → message va dans _speak_queue."""
    runtime_speak.speak("hello jarvis")
    assert runtime_speak._speak_queue.qsize() == 1
    assert runtime_speak._speak_queue.get_nowait() == "hello jarvis"
    assert runtime_speak._speak_deferred.qsize() == 0


def test_speak_avec_stream_actif_ajoute_dans_deferred():
    """_chat_stream_active set → message va dans _speak_deferred."""
    runtime_speak._chat_stream_active.set()
    runtime_speak.speak("alerte SOC pendant chat")
    assert runtime_speak._speak_deferred.qsize() == 1
    assert runtime_speak._speak_queue.qsize() == 0
    assert runtime_speak._speak_deferred.get_nowait() == "alerte SOC pendant chat"


# ── Dedup intra-source 3s ──────────────────────────────────────────────────


def test_speak_meme_texte_repete_dans_3s_skip():
    """Même texte appelé 2 fois consécutivement <3s → 2ème skip (log debug)."""
    runtime_speak.speak("alerte critique")
    runtime_speak.speak("alerte critique")
    assert runtime_speak._speak_queue.qsize() == 1


def test_speak_meme_texte_apres_3s_reaccepte(monkeypatch):
    """Même texte mais >3s écart → re-accepté."""
    runtime_speak.speak("alerte critique")
    assert runtime_speak._speak_queue.qsize() == 1
    # Avance le temps de 4s : modifier directement _speak_last_time vers le passé
    runtime_speak._speak_last_time = time.monotonic() - 4.0
    runtime_speak.speak("alerte critique")
    assert runtime_speak._speak_queue.qsize() == 2


def test_speak_textes_differents_pas_de_dedup_intra():
    """Textes différents successifs → 2 entrées, pas de dedup intra."""
    runtime_speak.speak("message un")
    runtime_speak.speak("message deux")
    assert runtime_speak._speak_queue.qsize() == 2


# ── Dedup global cross-source (via tts_dedup mock) ─────────────────────────


def test_speak_dedup_global_check_and_register_appele():
    """tts_dedup.check_and_register est appelé à chaque speak() non-bloqué."""
    runtime_speak.speak("hello")
    runtime_speak._tts_dedup.check_and_register.assert_called_once()
    args = runtime_speak._tts_dedup.check_and_register.call_args[0]
    assert args[0] == "hello"


def test_speak_dedup_global_returns_true_skip_message():
    """Si tts_dedup.check_and_register retourne True → message skip (déjà dit ailleurs)."""
    runtime_speak._tts_dedup.check_and_register = MagicMock(return_value=True)
    runtime_speak.speak("hello deja dit ailleurs")
    assert runtime_speak._speak_queue.qsize() == 0


# ── Drop-oldest sur queue pleine ───────────────────────────────────────────


def test_speak_queue_pleine_drop_le_plus_ancien():
    """Queue pleine (maxsize=8) → l'ajout drop le plus ancien (alerte récente prioritaire)."""
    # Remplir directement la queue (saute la dedup en utilisant put_nowait)
    for i in range(8):
        runtime_speak._speak_queue.put_nowait(f"old_{i}")
    assert runtime_speak._speak_queue.full()
    runtime_speak.speak("nouveau message critique")
    # Le plus ancien (old_0) a été drop, 'nouveau message critique' est en bout de queue
    contents = []
    while not runtime_speak._speak_queue.empty():
        contents.append(runtime_speak._speak_queue.get_nowait())
    assert "old_0" not in contents
    assert "nouveau message critique" in contents
    assert len(contents) == 8


def test_speak_deferred_pleine_drop_le_plus_ancien():
    """_speak_deferred plein (stream actif) → drop oldest aussi."""
    runtime_speak._chat_stream_active.set()
    for i in range(8):
        runtime_speak._speak_deferred.put_nowait(f"old_{i}")
    assert runtime_speak._speak_deferred.full()
    runtime_speak.speak("nouveau pendant stream")
    contents = []
    while not runtime_speak._speak_deferred.empty():
        contents.append(runtime_speak._speak_deferred.get_nowait())
    assert "old_0" not in contents
    assert "nouveau pendant stream" in contents


# ── Logging ─────────────────────────────────────────────────────────────────


def test_speak_log_tts_logger_appele_avec_source_python_speak():
    """tts_logger.info est appelé avec 'source=python-speak'."""
    runtime_speak.speak("test log")
    runtime_speak._tts_logger.info.assert_called_once()
    args = runtime_speak._tts_logger.info.call_args[0]
    # Format string + source + texte
    assert "python-speak" in args[1]


def test_speak_log_differé_si_stream_actif():
    """Si stream actif, _log.info note 'Différé (stream SSE actif)'."""
    runtime_speak._chat_stream_active.set()
    runtime_speak.speak("alerte pendant stream")
    log_calls = [c.args[0] for c in runtime_speak._log.info.call_args_list]
    assert any("Différé" in c for c in log_calls)


# ── Concurrency basique : threading.Event ──────────────────────────────────


def test_chat_stream_active_est_un_threading_event():
    """API publique : _chat_stream_active doit être un threading.Event (utilisé par chat orch)."""
    assert isinstance(runtime_speak._chat_stream_active, threading.Event)
