"""Tuile **voice** — pipeline audio (TTS, STT, DSP, voice prints, dedup).

Architecture par tuiles (refactor jarvis.py étape 11 phase A, 2026-05-23) —
9ème tuile. Cette phase regroupe les 8 modules audio déjà extraits à plat
dans un dossier dédié. La phase B (étape ultérieure) extraira les routes
`/api/tts`, `/api/speak`, `/api/voices`, `/api/stt` + helpers TTS-side
encore dans `jarvis.py`.

Sous-modules (regroupés ici, pas modifiés sur le fond) :
- `tts_engines`   : 4 moteurs TTS (edge → kokoro CUDA → piper → sapi5)
- `tts_cleaner`   : prétraitement texte avant TTS (IPs, dates, ponctuation)
- `tts_dedup`     : déduplication LLM hallucinations (anti-répétition)
- `audio_dsp`     : Web Audio graph wrapper (4 BiquadFilter + 2 Comp + Convolver)
- `deepfilter`    : DeepFilterNet CUDA (denoising) — consommé par audio_dsp
- `deferred_speak`: file d'attente TTS asynchrone (anti-double-speak)
- `stt`           : faster-whisper large-v3-turbo (transcription locale)
- `voice_lab`     : voice prints + clonage XTTS v2

Pas de fonction `init()` à ce niveau : chaque sous-module gère ses propres
dépendances via signatures de fonctions (DI per-call, pas global state).
"""
from flask import Blueprint

bp = Blueprint("voice", __name__)

from . import (  # noqa: E402,F401
    audio_dsp,
    deepfilter,
    deferred_speak,
    routes,
    stt,
    tts_cleaner,
    tts_dedup,
    tts_engines,
    voice_lab,
)

# Rate limits par route (appliqués dans init() après injection du limiter).
_ROUTE_LIMITS = {
    "api_stt":        "10 per minute",
    "api_stt_status": "60 per minute",
}


def init(*, limiter, log) -> None:
    """Injecte les dépendances communes + applique les rate limits.

    Phase B1 (étape 13) : STT routes seulement. Les routes TTS/speak/voice_lab
    seront ajoutées par init_routes_tts/init_routes_voicelab (étapes 14-16).
    """
    routes.init_routes(log=log)
    for fn_name, limit_str in _ROUTE_LIMITS.items():
        fn = getattr(routes, fn_name, None)
        if fn is not None:
            limiter.limit(limit_str)(fn)
