"""Tests deferred_speak — flush queue messages TTS différés (background threads)."""
import json
import queue

from voice.deferred_speak import flush_deferred_speak


def test_queue_vide_yield_rien():
    out = list(flush_deferred_speak(queue.Queue()))
    assert out == []


def test_un_message_yield_un_event_speak():
    q = queue.Queue()
    q.put("alerte SOC critique")
    out = list(flush_deferred_speak(q))
    assert len(out) == 1
    payload = json.loads(out[0].replace("data: ", "").strip())
    assert payload == {"type": "speak", "text": "alerte SOC critique"}


def test_plusieurs_messages_yield_dans_l_ordre_FIFO():
    q = queue.Queue()
    q.put("premier")
    q.put("deuxième")
    q.put("troisième")
    out = list(flush_deferred_speak(q))
    payloads = [json.loads(o.replace("data: ", "").strip())["text"] for o in out]
    assert payloads == ["premier", "deuxième", "troisième"]


def test_drain_complet_la_queue():
    q = queue.Queue()
    for msg in ["a", "b", "c"]:
        q.put(msg)
    list(flush_deferred_speak(q))
    assert q.empty()


def test_format_sse_correct_data_json_double_newline():
    q = queue.Queue()
    q.put("test")
    out = list(flush_deferred_speak(q))
    assert out[0].startswith("data: ")
    assert out[0].endswith("\n\n")


def test_messages_avec_caracteres_speciaux_encodes_en_json():
    q = queue.Queue()
    q.put('quote " et \\backslash')
    out = list(flush_deferred_speak(q))
    payload = json.loads(out[0].replace("data: ", "").strip())
    assert payload["text"] == 'quote " et \\backslash'


def test_message_vide_est_quand_meme_yield():
    """Une chaîne vide est un message valide (différent de pas de message)."""
    q = queue.Queue()
    q.put("")
    out = list(flush_deferred_speak(q))
    assert len(out) == 1
    payload = json.loads(out[0].replace("data: ", "").strip())
    assert payload["text"] == ""
