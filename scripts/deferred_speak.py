"""Deferred speak — flush des messages TTS différés (background threads).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 25 (Chat/LLM core).

Les threads background (autoban SOC, monitoring, alerts vocales) ne peuvent pas
appeler `speak()` directement pendant qu'un stream chat SSE est actif (sinon le
TTS se superpose au streaming voice). Ils mettent les messages dans la queue
`_speak_deferred` qui est flushée en fin de stream via ce générateur.

Dependency injection : la queue est passée en argument (instance globale dans jarvis.py).
"""
import json
import queue as _queue_mod


def flush_deferred_speak(deferred_queue):
    """Rejoue les messages speak en attente — yield SSE jusqu'à queue vide.

    `deferred_queue` : `queue.Queue` partagée avec les threads background.

    Yields : `data: {"type":"speak","text":...}\\n\\n` pour chaque message en attente.
    Termine sur Queue.Empty (drain complet).
    """
    while True:
        try:
            text = deferred_queue.get_nowait()
            yield f"data: {json.dumps({'type': 'speak', 'text': text})}\n\n"
        except _queue_mod.Empty:
            break
