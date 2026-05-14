"""TTS Dedup global — empêche le doublon cross-source python-speak ↔ /api/tts.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 19 (Chat/LLM core).

Problème résolu : le SOC engine Python (`speak()`) et l'auto-engine JS (`/api/tts`) peuvent
détecter la même alerte au même moment et déclencher deux synthèses TTS du même texte
→ on entend 2 fois la même phrase. Ce dedup global avec fenêtre 60s coupe le doublon.

Fonction unique `check_and_register(text)` :
- Si même texte vu il y a moins de 60s → retourne True (= dupliqué, à skipper)
- Sinon → enregistre + retourne False (= nouveau, à prononcer)

Thread-safe via lock module-level.
"""
import threading

# ── Constantes ────────────────────────────────────────────────
DEDUP_WINDOW_S = 60.0  # fenêtre dédup cross-source (python-speak ↔ /api/tts)

# ── State (module-level) ──────────────────────────────────────
_text: str = ""
_time: float = 0.0
_lock = threading.Lock()


def check_and_register(text: str, now: float) -> bool:
    """Vérifie si `text` a été prononcé dans la fenêtre DEDUP_WINDOW_S.

    `now` : `time.monotonic()` au moment de l'appel (passé par l'appelant pour cohérence).

    Retourne :
    - True  → DUPLIQUÉ, l'appelant doit skip la synthèse
    - False → NOUVEAU, le texte est enregistré et l'appelant peut prononcer

    Thread-safe (lock module-level).
    """
    global _text, _time
    with _lock:
        if text == _text and (now - _time) < DEDUP_WINDOW_S:
            return True
        _text = text
        _time = now
    return False
