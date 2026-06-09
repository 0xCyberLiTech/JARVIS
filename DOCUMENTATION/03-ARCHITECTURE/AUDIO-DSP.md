# Architecture Audio DSP

> Chaîne de traitement audio broadcast inspirée d'un processeur voix Symetrix 528.
> 3 étages : Voice Channel Strip → FX Send/Return Bus → Master Bus.

---

## Vue d'ensemble — 3 étages

```
[1] VOICE CHANNEL STRIP   →   [2] FX SEND/RETURN BUS   →   [3] MASTER BUS
     (canal voix dynamique)      (effets parallèles)         (AGC + brick-wall)
```

---

## Topologie complète

```
SOURCE TTS (edge-tts / Kokoro / SAPI5)
       ↓
   analyser → VU mètre stéréo
       ↓
   _jarvisPreGain (input trim)
       ↓
   _dspAnalyser (FFT spectre — visualisation)
       ↓
┌─────────────────────────────────────────┐
│  ÉTAGE 1 — VOICE CHANNEL STRIP          │
│                                          │
│  EQ 4 bandes : Low → Mid → High → Air   │
│       ↓                                  │
│  _dspCompressor                          │
│   threshold -24 dBFS · ratio 4:1         │
│   attack 3 ms · release 250 ms           │
│       ↓                                  │
│  _dspLimiter (voice bus brick)           │
│   threshold -0.5 dBFS · ratio 20:1       │
│       ↓                                  │
│  _dspGainNode (output trim)              │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌─────────────┐      ┌────────────────────────────┐
│  DRY PATH   │      │  ÉTAGE 2 — AUX SEND (FX)   │
├─────────────┤      ├────────────────────────────┤
│ _fxDryGain  │      │ _fxSendGain (calibré FX)   │
│ cos x-fade  │      │  reverb  × 1.00  ( 0 dB)   │
│             │      │  echo    × 0.35  (-9 dB)   │
│             │      │  delay   × 0.45  (-7 dB)   │
│             │      │      ↓                     │
│             │      │ _fxConvolver               │
│             │      │  normalize = true           │
│             │      │      ↓                     │
│             │      │ _fxWetGain (sin x-fade)    │
└──────┬──────┘      └────────────┬───────────────┘
       └──────────┬───────────────┘
                  ▼
┌────────────────────────────────────────┐
│  ÉTAGE 3 — MASTER BUS                  │
│                                         │
│  _fxMixBus (sommation dry + wet)        │
│        ↓                                │
│  _masterLimiter (brick-wall final)      │
│   threshold -0.3 dBFS · ratio 20:1      │
└─────────────────────────────────────────┘
                  ↓
        audioCtx.destination
```

---

## Chaîne TTS — 4 moteurs en cascade

| # | Moteur | Statut | Notes |
|---|--------|--------|-------|
| 1 | **edge-tts** fr-CA-AntoineNeural | Défaut | Voix naturelle, nécessite internet |
| 2 | **Kokoro** ff_siwis (CUDA) | Fallback auto | 100 % local, CUDA RTX |
| 3 | **XTTS v2** | Optionnel | 58 voix + voice prints personnalisés |
| 4 | **SAPI5** pyttsx3 | Fallback final | Hors ligne absolu, voix système Windows |

La cascade est automatique : si le moteur n° 1 échoue (pas d'internet), le moteur n° 2 prend le relais.

---

## STT — Transcription vocale

| Paramètre | Valeur |
|-----------|--------|
| Modèle | faster-whisper `large-v3-turbo` |
| Accélération | CUDA float16 (RTX) |
| Langue | Français (FR) |
| beam_size | 2 |
| vad_filter | True (filtre silence) |
| initial_prompt | Vocabulaire SOC spécialisé |

---

## Calibration loudness FX

La convolution avec des taps discrets (echo, delay) crée une perception loudness
supérieure à une réverbération diffuse à RMS égal. Chaque type de FX est calibré :

| Effet | Send gain | dB | Raison |
|-------|-----------|-----|--------|
| reverb | 1.00 | 0 dB | Référence — réverb diffuse perçue douce |
| echo | 0.35 | -9 dB | Taps discrets stéréo, perception très forte |
| delay | 0.45 | -7 dB | Taps discrets mono, perception forte |

---

## Crossfade equal-power (wet/dry)

Évite le creux de -3 dB au milieu d'un crossfade linéaire :

```
wet_gain = sin(wet × π/2)
dry_gain = cos(wet × π/2)
```

| wet | dry_gain | wet_gain | énergie totale |
|-----|----------|----------|----------------|
| 0.0 | 1.000 | 0.000 | 1.000 |
| 0.5 | 0.707 | 0.707 | 1.000 |
| 1.0 | 0.000 | 1.000 | 1.000 |

---

## DSP avancé

| Bloc | Rôle |
|------|------|
| DeepFilterNet | Débruitage IA (GPU CUDA · désactivé par défaut) |
| Haas stéréo | Élargissement image (canal R retardé 18 ms) |
| Analyseur FFT | 4 modes de visualisation : mirror / scope / piano / split |

---

## Règles critiques

| # | Règle | Raison |
|---|-------|--------|
| 1 | Ne jamais reconnecter analyser → analyserL/R | Boucle de rétroaction — sifflement |
| 2 | Tout nouveau FX doit avoir une entrée `_FX_SEND_CAL` | Sinon loudness incohérente |
| 3 | Ne jamais connecter directement à `audioCtx.destination` | Bypass du brick-wall |

---

*AUDIO-DSP.md · 0xCyberLiTech · 2026-06-09*
