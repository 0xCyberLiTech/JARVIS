"""speak() — file de messages TTS background partagée (Python → browser).

Extrait de jarvis.py étape 31 (2026-05-23). Une seule fonction publique
`speak(text)` + 3 objets d'état partagés exposés en attributs module pour
les autres tuiles qui les consomment (voice/routes, chat/orchestrator,
chat/file_correct, bootstrap/threads) :

- `_speak_queue`         : Queue(8) — textes en attente que le browser drain
                           via GET /api/speak/queue
- `_speak_deferred`      : Queue(8) — messages différés pendant un stream SSE
                           chat actif, rejoués comme event SSE en fin de stream
- `_chat_stream_active`  : threading.Event — set() pendant la génération chat

Garde-fous internes (dans `speak`) :
- Dedup intra-source 3 s (même texte rapproché → skip)
- Dedup global cross-source via `tts_dedup` (60 s par défaut)
- Nettoyage texte via `_clean_for_tts` avant tout
- Drop-oldest si queue pleine (alerte récente = plus pertinente)

DI via `init(log, tts_logger, clean_for_tts, tts_dedup, tts_dedup_s,
tts_log_preview)` — toutes les deps déjà existantes côté jarvis.py.
"""
import queue as _queue_mod
import threading
import time

# ── DI placeholders ───────────────────────────────────────────────────────────
_log = None
_tts_logger = None
_clean_for_tts = None
_tts_dedup = None
_tts_dedup_s = 60.0
_tts_log_preview = 80

# ── État partagé (consommé par d'autres tuiles via attributs module) ──────────
_speak_queue        = _queue_mod.Queue(maxsize=8)
_chat_stream_active = threading.Event()
_speak_deferred     = _queue_mod.Queue(maxsize=8)

# Dedup intra-source (race condition _speak_deferred → SSE et _speak_queue → poll)
_speak_last_text: str   = ''
_speak_last_time: float = 0.0


def init(
    *,
    log,
    tts_logger,
    clean_for_tts,
    tts_dedup,
    tts_dedup_s: float = 60.0,
    tts_log_preview: int = 80,
) -> None:
    """Injecte logger + nettoyeur + dedup global cross-source."""
    global _log, _tts_logger, _clean_for_tts, _tts_dedup
    global _tts_dedup_s, _tts_log_preview
    _log = log
    _tts_logger = tts_logger
    _clean_for_tts = clean_for_tts
    _tts_dedup = tts_dedup
    _tts_dedup_s = tts_dedup_s
    _tts_log_preview = tts_log_preview


def speak(text, blocking=False):
    """Enfile le texte dans _speak_queue — le browser le récupère via GET /api/speak/queue
    et le joue via queueSpeech() → Web Audio (fader JARVIS + DSP + mixer).
    Si un stream SSE chatbot est actif (_chat_stream_active), le message est différé dans
    _speak_deferred et sera injecté comme événement SSE à la fin du stream → playback séquentiel."""
    global _speak_last_text, _speak_last_time
    text = _clean_for_tts(text)
    if not text:
        return
    now = time.monotonic()
    if text == _speak_last_text and (now - _speak_last_time) < 3.0:
        _log.debug(f"[TTS] Dedup skip (même texte < 3s) : {text[:80]}")
        return
    _speak_last_text = text
    _speak_last_time = now
    if _tts_dedup.check_and_register(text, now):
        _log.debug(f"[TTS] Dedup global skip (python-speak, même texte < {_tts_dedup_s}s) : {text[:80]}")
        return
    preview = text[:_tts_log_preview].replace("\n", " ")
    suffix  = "..." if len(text) > _tts_log_preview else ""
    _tts_logger.info("source=%-20s | %s%s", "python-speak", preview, suffix)
    try:
        if _chat_stream_active.is_set():
            if _speak_deferred.full():
                try:
                    _speak_deferred.get_nowait()
                except _queue_mod.Empty:
                    pass  # get_nowait() raises Empty when queue is drained — expected
            _speak_deferred.put_nowait(text)
            _log.info(f"[TTS] Différé (stream SSE actif) : {text[:80]}")
        else:
            if _speak_queue.full():
                try:
                    _speak_queue.get_nowait()
                except _queue_mod.Empty:
                    pass  # get_nowait() raises Empty when queue is drained — expected
            _speak_queue.put_nowait(text)
    except _queue_mod.Full:
        _log.info(f"[TTS] Queue pleine — message ignoré : {text[:80]}")
