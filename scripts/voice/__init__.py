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
from . import (  # noqa: F401
    audio_dsp,
    deepfilter,
    deferred_speak,
    stt,
    tts_cleaner,
    tts_dedup,
    tts_engines,
    voice_lab,
)
