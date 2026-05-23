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
    "api_stt":                "10 per minute",
    "api_stt_status":         "60 per minute",
    "api_speak":              "20 per minute",
    "api_speak_stop":         "30 per minute",
    "api_speak_status":       "60 per minute",
    "api_speak_queue":        "60 per minute",
    "api_tts_log":            "60 per minute",
    # api_tts_status : pas de rate limit dans l'original
    "api_tts":                "20 per minute",
    "api_tts_local_voices":   "30 per minute",
    "api_tts_local_download": "5 per minute",
    "api_voices":             "60 per minute",
    "api_set_voice":          "20 per minute",
    "api_voice_analyse":      "10 per minute",
    "api_voice_print_audio":  "60 per minute",
    "api_voice_print_delete": "10 per minute",
    # api_voice_prints, api_voice_samples : pas de rate limit dans l'original
}


def init(*, limiter, log,
         tts_logger=None,
         speak_fn=None,
         speak_queue=None,
         speak_deferred=None,
         chat_stream_active=None,
         tts_log_path=None,
         get_dsp_params=None,
         get_voice=None,
         get_voices=None,
         set_voice=None,
         get_internet_up=None,
         clean_for_tts=None,
         tts_log_preview=200,
         tts_dedup_s=60) -> None:
    """Injecte les dépendances de la tuile et applique les rate limits.

    Phases B1 + B2 (étapes 13-14) : STT + TTS + speak routes. Voice_lab/voice
    routes en étape 15.
    """
    routes.init_routes(
        log               = log,
        tts_logger        = tts_logger,
        speak_fn          = speak_fn,
        speak_queue       = speak_queue,
        speak_deferred    = speak_deferred,
        chat_stream_active= chat_stream_active,
        tts_log_path      = tts_log_path,
        get_dsp_params    = get_dsp_params,
        get_voice         = get_voice,
        get_voices        = get_voices,
        set_voice         = set_voice,
        get_internet_up   = get_internet_up,
        clean_for_tts     = clean_for_tts,
        tts_log_preview   = tts_log_preview,
        tts_dedup_s       = tts_dedup_s,
    )
    for fn_name, limit_str in _ROUTE_LIMITS.items():
        fn = getattr(routes, fn_name, None)
        if fn is not None:
            limiter.limit(limit_str)(fn)
