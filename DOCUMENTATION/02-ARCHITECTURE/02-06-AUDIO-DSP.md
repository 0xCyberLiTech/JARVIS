---
title: "Pipeline audio — Web Audio + TTS chain + DSP"
code: "JARVIS-DOC-02-06"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "Architecture"
mots_cles: ["audio", "dsp", "tts", "kokoro", "edge-tts", "web-audio", "deepfilternet"]
---

# JARVIS — Architecture audio DSP

Référence technique : la chaîne audio JARVIS (TTS → DSP → output) côté navigateur ET côté serveur Python.

**Inspiration architecturale :** Symetrix 528 voice processor + send/return broadcast architecture (refonte session 30, 2026-05-12).

---

## Vue d'ensemble — chaîne complète

```
┌──────────────────────────────────────────────────────────────────────────┐
│  CÔTÉ SERVEUR (Python · jarvis.py)                                       │
│                                                                          │
│  ┌─────────────┐    ┌──────────────────┐    ┌───────────────────────┐    │
│  │ STT input   │ →  │ faster-whisper   │ →  │ texte transcrit       │    │
│  │ (mic WAV)   │    │ large-v3-turbo   │    │ + initial_prompt SOC  │    │
│  └─────────────┘    │ CUDA · int8      │    └───────────────────────┘    │
│                     └──────────────────┘                                 │
│                                                                          │
│  ┌─────────────┐    ┌──────────────────────────────┐    ┌────────────┐   │
│  │ texte LLM   │ →  │ TTS engine fallback chain    │ →  │ WAV stream │   │
│  │ Ollama      │    │ edge-tts → Kokoro → Piper    │    │ vers       │   │
│  │             │    │ → SAPI5 (Win)                │    │ navigateur │   │
│  └─────────────┘    └──────────────────────────────┘    └────────────┘   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐     │
│  │ DeepFilterNet (CUDA · denoising IA)                             │     │
│  │ Lazy init au 1er appel · 48 kHz · ~16 ms/frame                  │     │
│  └─────────────────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ (WAV stream HTTP)
┌──────────────────────────────────────────────────────────────────────────┐
│  CÔTÉ NAVIGATEUR (Web Audio API · audio_viz.js + dsp_audio.js + mixing) │
│                                                                          │
│  source ─► AnalyserL/R ─► EQ 4 bandes ─► Comp voix ─► Limiter voix ─►   │
│                                                                          │
│  outGain ─┬─► dry ────────────────────────┐                              │
│           └─► ConvolverNode (FX) ─► wet ──┴─► masterLimiter ─► destination
│                                                                          │
│  Master limiter brick-wall : -0.3 dBFS · ratio 20 · attack 1ms           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Web Audio Graph (côté navigateur)

Implémentation (refactor JS 2026-05-14) : graphe Web Audio + visualiseurs dans [`scripts/static/js/audio_viz.js`](../scripts/static/js/audio_viz.js) · chaîne DSP UI (gain/comp/limiter/EQ, FX convolver) dans [`scripts/static/js/dsp_audio.js`](../scripts/static/js/dsp_audio.js) · EQ paramétrique dans `js/eq_parametric.js` · helpers mixer dans `jarvis_mixing.js`.

### File de lecture voix — invariant AudioContext (correctif structurel 2026-05-20)

La file de lecture (`processQueue` / `playSentence`, `audio_viz.js`) respecte un **invariant unique** : une source TTS n'est JAMAIS démarrée sur un `AudioContext` suspendu. Avant ce correctif, la file pouvait **(a) geler définitivement** (`playSentence` ne se résout que sur `source.onended`, qui ne se déclenche jamais sur un contexte suspendu) ou **(b) provoquer un chevauchement** (`source.start()` sur contexte suspendu planifie une source « gelée » qui ressurgit au `resume` suivant par-dessus la parole en cours).

- `processQueue` appelle `_ensureAudioCtx()` puis resume-ou-abandonne **AVANT** `playSentence`.
- Verrou `isPlaying` pris avant tout `await` (anti ré-entrance).
- Ancien « timeout filet » supprimé (inutile une fois l'invariant garanti).
- Déverrouillage audio armé tôt dans `_jarvisInit` (`boot_init.js`), multi-gestes (`click`/`keydown`/`pointerdown`/`touchstart`), flag `_userGestured` découplé du timing `/api/boot-id`.

### Voice channel (signal principal)

| Étage | Type Web Audio | Paramètres |
|-------|---------------|------------|
| **EQ low** | `BiquadFilterNode` | type=`lowshelf` · freq=80 Hz · gain init=0 dB |
| **EQ mid** | `BiquadFilterNode` | type=`peaking` · freq=1 kHz · Q=1.0 · gain init=0 dB |
| **EQ high** | `BiquadFilterNode` | type=`highshelf` · gain init=0 dB |
| **EQ air** | `BiquadFilterNode` | type=`peaking` · freq=10 kHz · gain init=0 dB |
| **Compresseur voix** | `DynamicsCompressorNode` | threshold=-12 dBFS · ratio=2 · attack=10ms · release=150ms · knee=6 |
| **Makeup gain** | `GainNode` | gain=1.5 (compense ~3 dB de réduction du compresseur) |
| **Limiter voix** | `DynamicsCompressorNode` | threshold=-1.5 dBFS · ratio=20 · attack=2ms · release=80ms · knee=0 |

### FX bus send/return

| Étage | Type | Détail |
|-------|------|--------|
| **Dry bus** | `GainNode` | Signal direct (sans FX) |
| **FX Convolver** | `ConvolverNode` | `normalize=true` (anti-clipping) · IR cached pour anti re-FFT lag (~3-4s) |
| **Wet bus** | `GainNode` | Signal traité par convolver |
| **Mixer** | (sommation) | dry + wet → masterLimiter |

### Master output

| Étage | Type | Paramètres |
|-------|------|------------|
| **Master limiter brick-wall** | `DynamicsCompressorNode` | threshold=-0.3 dBFS · ratio=20 · attack=1ms · release=50ms |
| **Destination** | `audioCtx.destination` | Output haut-parleurs / casque navigateur |

### Analyseurs spectraux (visualisation)

- **Voice channel** : 2 `AnalyserNode` (L/R) · `fftSize=2048` · `smoothingTimeConstant=0.55-0.8`
- **DAT player & micros** : `fftSize=4096` (résolution + élevée pour spectroscope)

### Cache IR (Impulse Response)

`_fxIrCacheKey` (`js/dsp_audio.js`) — l'IR est régénérée uniquement si `(type, vals)` changent. Évite la re-FFT 3-4 secondes à chaque ajustement de slider FX. Helper `_fxRefreshIr()`/`_fxEnsureIr()`.

---

## 2. DSP params (`scripts/jarvis_dsp_params.json`)

51 paramètres persistés JSON, chargés au boot et synchronisés UI ↔ backend via `/api/dsp/params`.

### EQ (4 bandes)
- `eq_low`, `eq_mid`, `eq_high`, `eq_air` (dB · -12 à +12 · pas 0.5 · défaut 0.0)

### Compresseur voix
- `comp_threshold` (-32 dB) · `comp_ratio` (12.5) · `comp_attack` (91 ms) · `comp_release` (390 ms)

### Gain & stéréo
- `gain` (3.0 dB) · `stereo_enabled` (true) · `stereo_width` (0.59) · `haas_delay_ms` (20)

### DeepFilterNet
- `df_enabled` (**true** par défaut · activé en session 30) · `df_atten_lim` (100) · `df_post_filter` (false)

### FX (reverb / echo / delay / chorus / flanger / phaser / exciter)
- `fx_enabled` (false) · `fx_type` (`reverb`) · `fx_preset` (`room`) · `fx_wet` (0.34) · `fx_decay` (1.2 s) · `fx_predelay_ms` (22) · `fx_diffusion` (0.42) · + paramètres dédiés par type FX

### Enrich (saturation harmonique douce)
- `enrich_enabled` (true) · `enrich_drive` (2.5) · `enrich_tone` (2800 Hz) · `enrich_mix` (0.15) · `enrich_warmth` (0.06)

### TTS
- `tts_engine` (`edge`) · `tts_default_engine` (`edge`) · `tts_local_voice` (`ff_siwis` · Kokoro)

---

## 3. TTS Python — fallback chain (4 engines)

Implémentation : [`scripts/tts_engines.py`](../scripts/tts_engines.py) (Phase 3 module 3 · 280L isolées) — drivers purs des 4 engines. Routes Flask + queues + DSP post-processing restent dans `jarvis.py` car couplés.

```
edge-tts (fr-CA-AntoineNeural · défaut)
     │ internet KO
     ▼
Kokoro neural (ff_siwis · CUDA · 82M params · 24 kHz mono WAV)
     │ non disponible
     ▼
Piper (fr_FR-upmc-medium.onnx · CPU · LRU cache 3 modèles)
     │ non disponible
     ▼
SAPI5 (pyttsx3 Hortense FR · Windows fallback)
```

| Engine | Fichier `jarvis.py` ligne | Particularité |
|--------|---------------------------|---------------|
| edge-tts | ~5917 (`_edge_tts_async`) | Async · qualité broadcast · requiert internet |
| Kokoro | ~569-598 | CUDA lazy · voice prefixes `ff_/fm_/af_/am_/bf_/bm_` · 24 kHz |
| Piper | ~602-623 | LRU cache 3 modèles · sample voices dans `voices/` |
| SAPI5 | ~651-669 | Pure Windows · pas d'internet ni GPU |
| **XTTS v2** (coqui-tts 0.27.5) | Voice Lab | 58 voix natives + voice prints custom · GPU CUDA |

### Endpoints

| Route | Méthode | Rôle |
|-------|---------|------|
| `/api/speak` | POST | Synthèse + lecture (params : text, blocking) |
| `/api/speak/stop` | POST | Stop immédiat WinMM (`mciSendStringW("stop all")`) |
| `/api/speak/status` | GET | État queue (queued / deferred / stream_active) |
| `/api/tts` | GET | Liste engines disponibles |
| `/api/tts/local/voices` | GET | Liste voix Piper |

### Log rotatif TTS

`_TTS_LOG_PATH` · 2 MB max · 7 backups · preview 80 chars par appel (`jarvis.py:47-52`).

### Découpage TTS des textes longs (`_splitForTts` · 2026-05-20)

edge-tts a un temps de synthèse **proportionnel à la longueur du texte** : une longue analyse SOC pouvait mettre 15-24 s avant que la voix ne démarre. `_splitForTts` (côté navigateur) découpe les textes > 280 caractères aux frontières de phrase → les segments sont synthétisés et lus successivement, la voix démarre en **~1 s**.

### Instrumentation `[TTS-PERF]` (2026-05-20)

Sondes `[TTS-PERF]` ajoutées dans `jarvis.py`, `tts_engines.py` et `deepfilter.py` : décomposition du temps `/api/tts` (edge_gen / dsp / total), timing edge-tts par tentative, temps de chargement DeepFilterNet, timings des threads de préchauffage boot. Log **persistant** `scripts/tts_perf.log` (RotatingFileHandler · filtre `[TTS-PERF]` sur le logger racine) — capture la latence intermittente sans surveiller la console.

---

## 4. STT Python — faster-whisper

Implémentation : [`scripts/stt.py`](../scripts/stt.py) (Phase 3 module 1 · 97L isolées) — modèle + transcription. Route Flask `/api/stt` reste dans `jarvis.py` (gestion upload tempfile).

| Élément | Valeur |
|---------|--------|
| **Modèle** | `large-v3-turbo` (Whisper distillé · ~800M params) |
| **Device** | CUDA si `torch.cuda.device_count() > 0`, sinon CPU |
| **Compute type** | `int8` (~1 GB VRAM · coexiste avec phi4:14b 9.1 GB) |
| **VAD filter** | activé (Silero VAD intégré) |
| **Beam size** | 2 |
| **Endpoint** | `POST /api/stt` (file audio · max 25 MB · param `lang`) |

### `initial_prompt` SOC (vocabulaire injecté)

Améliore la transcription du jargon cybersécurité homelab :

```
CrowdSec, fail2ban, Suricata, Proxmox, nginx, Apache, JARVIS, SSH, VRAM, GPU, RTX,
Ollama, phi4, qwen, deepseek, gemma, IPv4, firewall, systemctl, journalctl, apt,
nftables, iptables, monitoring, dashboard, SOC, cybersécurité, homelab
```

→ "fail to ban" est correctement transcrit "fail2ban", "phi quatre" → "phi4", etc.

---

## 5. DeepFilterNet (denoising IA · CUDA)

Implémentation : [`scripts/deepfilter.py`](../scripts/deepfilter.py) (Phase 3 module 4 · 132L isolées · 100% autonome — numpy + scipy + torch lazy).

| Élément | Détail |
|---------|--------|
| **Chargement** | Lazy au 1er appel (`init_df()` silencieux — stderr fd2 réorienté pour masquer logurus) |
| **State** | Tuple `(model, df_state, enhance)` stocké dans `_df_model` global |
| **Sample rate** | 48 kHz (resample_poly si input ≠ 48 kHz) |
| **CUDA FFT** | Activé si `torch.cuda.is_available()` |
| **Toggle** | Param `df_enabled` (défaut `true` depuis session 30) |
| **Latence** | ~500 ms cold start (lazy init) · ~16 ms/frame en steady state @ 48 kHz |

→ Améliore drastiquement la qualité de la voix de Marc (TTS reverse + post-process voice prints + nettoyage micros). Activé par défaut côté DSP params.

---

## 6. Voice Lab (XTTS v2 · voice prints)

Onglet `✦ VOICE LAB` (`tab_voicelab.html`) — A/B testing 4 engines + analyse acoustique de voice prints.

| Élément | Détail |
|---------|--------|
| **Voice prints actuels** | 1 fichier (`scripts/voice_prints/Test_voix_build_01.wav`) — extensible via UI |
| **Format** | WAV mono · sample rate variable (resample auto) |
| **Endpoints** | `/api/voice/prints` (GET liste) · `/api/voice/print/audio/<name>` (GET serve) · `/api/voice/print/delete` (POST) · `/api/voice/analyse` (POST upload + features) |
| **Analyse acoustique** | librosa : f0 · centroid · rolloff · MFCC · RMS · mel-spectrogram → calcul `voice_type`, `brightness`, `breathiness`, `voicing`, `eq_preset` auto |

---

## 7. Hardware specs

| Composant | Détail |
|-----------|--------|
| **GPU** | RTX 5080 Blackwell · 16 GB GDDR7 · CUDA 12 |
| **Co-tenancy VRAM** | LLM (phi4:14b 9.1 GB) + STT (whisper int8 ~1 GB) + Kokoro/DFN (~1 GB) = ~11-12 GB · marge ~4 GB |
| **CPU** | Pas d'override `num_threads` explicite — torch/scipy utilisent les cœurs système |
| **CUDA monitoring** | `pynvml.nvmlDeviceGetCudaComputeCapability` (`jarvis.py:1959`) pour reporting VRAM/GPU live dans le panel monitoring |

---

## Tests E2E (couverture)

Suite Playwright `tests/e2e/dsp-voicelab.spec.js` + `dsp-interactive.spec.js` :
- DAT player buttons présents
- 4 engines TTS sélectionnables
- A/B comparison slots présents
- Sliders EQ low/high/air → labels mis à jour temps réel

→ `npm test` — voir [README.md](../README.md#qualité--tests--linters).

---

## Historique refontes

| Session | Date | Changement |
|---------|------|------------|
| 30 | 2026-05-12 | **Refonte complète DSP** broadcast architecture (Symetrix 528 inspiration) · cache IR FX · DeepFilterNet activé par défaut |
| 30 | 2026-05-12 | Suppression `_masterAGC` (DynamicsCompressor sans makeup gain causait disparition signal) |
| 33 | 2026-05-13 | 3 fixes terminal CODE (clear xterm + retrait `&& clear` + PROMPT_COMMAND) — pas DSP mais même fichier `jarvis_main.js` |
| 33 | 2026-05-13 | **Phase 3 split monolithe** — extraction de 4 modules audio depuis `jarvis.py` : `stt.py` (97L) · `voice_lab.py` (167L) · `tts_engines.py` (280L) · `deepfilter.py` (132L). Maintenance audio désormais ciblée. |
| 33 | 2026-05-13 | **Phase 3 complète** — 30 modules extraits au total (audio + bypass + SSH + Proxmox API + RAG + chat orchestration + LLM CR). `jarvis.py` 6592→4520L (-31%). NDT script auto 100/100, score honnête global 89/100 (JS toujours monolithique, pas de CI/CD). |
| 33c | 2026-05-13 | **Split JS partiel** — extraction `recorder.js` (660L · DAT RECORDER R-1) + `voice_print.js` (852L · Voice Print v2) en IIFE depuis `jarvis_main.js` 10507→8994L (-14.4%). Suppression artefacts obsolètes (vp_iife_new.js + vp_rebuild.py). 23 E2E pass, ESLint 0 errors. |
| — | 2026-05-14 | **Chantier dette — extraction `audio_dsp.py`** — bloc DSP audio (25 fonctions ~470L) extrait de `jarvis.py` vers `audio_dsp.py` (508L) : reverb convolution + FX rack (delay/chorus/phaser/flanger/echo/exciter) + filtres biquad + enrichisseur voix + compresseur + `apply_dsp_to_mp3`. Découplage `DSP_PARAMS` via DI (wrapper jarvis.py préserve les 9 call sites). FIX bug F821 `_torch` (import lazy → active réellement le CUDA reverb). jarvis.py 5110→4633L. 23 E2E pass, test audio réel OK. |
| — | 2026-05-20 | **Correctif structurel pipeline de lecture voix** — invariant « jamais de source TTS sur AudioContext suspendu » dans `processQueue`/`playSentence` (`audio_viz.js`) : supprime le gel définitif (`onended` jamais émis) et le chevauchement (source « gelée » qui ressurgit au `resume`). Verrou `isPlaying` anti ré-entrance · timeout filet supprimé · déverrouillage audio multi-gestes armé tôt dans `_jarvisInit` (`boot_init.js`). **Découpage TTS** `_splitForTts` (textes > 280 car. aux frontières de phrase) → voix démarre en ~1 s au lieu de ~15-24 s sur longues analyses SOC. **Instrumentation** `[TTS-PERF]` + log persistant `tts_perf.log`. |

---

## Références code

| Élément | Fichier:section |
|---------|----------------|
| Web Audio graph voice | `scripts/static/jarvis_main.js:~4815-4862` |
| Cache IR FX | `scripts/static/jarvis_main.js` (`_fxRefreshIr` / `_fxEnsureIr`) |
| Helpers mixing | `scripts/static/jarvis_mixing.js` |
| TTS engines | [`scripts/tts_engines.py`](../scripts/tts_engines.py) (drivers purs) + `jarvis.py` (routes/queues) |
| Chaîne DSP serveur | [`scripts/audio_dsp.py`](../scripts/audio_dsp.py) (reverb/FX/biquad/compress/`apply_dsp_to_mp3`) — wrapper DI dans `jarvis.py` |
| STT init | [`scripts/stt.py:_get_whisper`](../scripts/stt.py) (faster-whisper lazy CUDA) |
| STT initial_prompt | [`scripts/stt.py:_STT_INITIAL_PROMPT`](../scripts/stt.py) (vocabulaire SOC) |
| DeepFilterNet init | [`scripts/deepfilter.py:_load`](../scripts/deepfilter.py) (lazy + silence loguru) |
| DSP params JSON | `scripts/jarvis_dsp_params.json` |
| Voice Lab analyse | [`scripts/voice_lab.py:analyse_features`](../scripts/voice_lab.py) (librosa : pitch/MFCC/mel-spec) |
