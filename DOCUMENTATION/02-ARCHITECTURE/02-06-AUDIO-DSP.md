---
title: "Pipeline audio â€” Web Audio + TTS chain + DSP"
code: "JARVIS-DOC-02-06"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "Architecture"
mots_cles: ["audio", "dsp", "tts", "kokoro", "edge-tts", "web-audio", "deepfilternet"]
---

# JARVIS â€” Architecture audio DSP

RÃ©fÃ©rence technique : la chaÃ®ne audio JARVIS (TTS â†’ DSP â†’ output) cÃ´tÃ© navigateur ET cÃ´tÃ© serveur Python.

**Inspiration architecturale :** Symetrix 528 voice processor + send/return broadcast architecture (refonte session 30, 2026-05-12).

---

## Vue d'ensemble â€” chaÃ®ne complÃ¨te

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  CÃ”TÃ‰ SERVEUR (Python Â· jarvis.py)                                       â”‚
â”‚                                                                          â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”‚
â”‚  â”‚ STT input   â”‚ â†’  â”‚ faster-whisper   â”‚ â†’  â”‚ texte transcrit       â”‚    â”‚
â”‚  â”‚ (mic WAV)   â”‚    â”‚ large-v3-turbo   â”‚    â”‚ + initial_prompt SOC  â”‚    â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â”‚ CUDA Â· int8      â”‚    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â”‚
â”‚                     â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                                 â”‚
â”‚                                                                          â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”   â”‚
â”‚  â”‚ texte LLM   â”‚ â†’  â”‚ TTS engine fallback chain    â”‚ â†’  â”‚ WAV stream â”‚   â”‚
â”‚  â”‚ Ollama      â”‚    â”‚ edge-tts â†’ Kokoro â†’ Piper    â”‚    â”‚ vers       â”‚   â”‚
â”‚  â”‚             â”‚    â”‚ â†’ SAPI5 (Win)                â”‚    â”‚ navigateur â”‚   â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜   â”‚
â”‚                                                                          â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     â”‚
â”‚  â”‚ DeepFilterNet (CUDA Â· denoising IA)                             â”‚     â”‚
â”‚  â”‚ Lazy init au 1er appel Â· 48 kHz Â· ~16 ms/frame                  â”‚     â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                    â”‚
                                    â–¼ (WAV stream HTTP)
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  CÃ”TÃ‰ NAVIGATEUR (Web Audio API Â· audio_viz.js + dsp_audio.js + mixing) â”‚
â”‚                                                                          â”‚
â”‚  source â”€â–º AnalyserL/R â”€â–º EQ 4 bandes â”€â–º Comp voix â”€â–º Limiter voix â”€â–º   â”‚
â”‚                                                                          â”‚
â”‚  outGain â”€â”¬â”€â–º dry â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                              â”‚
â”‚           â””â”€â–º ConvolverNode (FX) â”€â–º wet â”€â”€â”´â”€â–º masterLimiter â”€â–º destination
â”‚                                                                          â”‚
â”‚  Master limiter brick-wall : -0.3 dBFS Â· ratio 20 Â· attack 1ms           â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## 1. Web Audio Graph (cÃ´tÃ© navigateur)

ImplÃ©mentation (refactor JS 2026-05-14) : graphe Web Audio + visualiseurs dans [`scripts/static/js/audio_viz.js`](../scripts/static/js/audio_viz.js) Â· chaÃ®ne DSP UI (gain/comp/limiter/EQ, FX convolver) dans [`scripts/static/js/dsp_audio.js`](../scripts/static/js/dsp_audio.js) Â· EQ paramÃ©trique dans `js/eq_parametric.js` Â· helpers mixer dans `jarvis_mixing.js`.

### File de lecture voix â€” invariant AudioContext (correctif structurel 2026-05-20)

La file de lecture (`processQueue` / `playSentence`, `audio_viz.js`) respecte un **invariant unique** : une source TTS n'est JAMAIS dÃ©marrÃ©e sur un `AudioContext` suspendu. Avant ce correctif, la file pouvait **(a) geler dÃ©finitivement** (`playSentence` ne se rÃ©sout que sur `source.onended`, qui ne se dÃ©clenche jamais sur un contexte suspendu) ou **(b) provoquer un chevauchement** (`source.start()` sur contexte suspendu planifie une source Â« gelÃ©e Â» qui ressurgit au `resume` suivant par-dessus la parole en cours).

- `processQueue` appelle `_ensureAudioCtx()` puis resume-ou-abandonne **AVANT** `playSentence`.
- Verrou `isPlaying` pris avant tout `await` (anti rÃ©-entrance).
- Ancien Â« timeout filet Â» supprimÃ© (inutile une fois l'invariant garanti).
- DÃ©verrouillage audio armÃ© tÃ´t dans `_jarvisInit` (`boot_init.js`), multi-gestes (`click`/`keydown`/`pointerdown`/`touchstart`), flag `_userGestured` dÃ©couplÃ© du timing `/api/boot-id`.

### Voice channel (signal principal)

| Ã‰tage | Type Web Audio | ParamÃ¨tres |
|-------|---------------|------------|
| **EQ low** | `BiquadFilterNode` | type=`lowshelf` Â· freq=80 Hz Â· gain init=0 dB |
| **EQ mid** | `BiquadFilterNode` | type=`peaking` Â· freq=1 kHz Â· Q=1.0 Â· gain init=0 dB |
| **EQ high** | `BiquadFilterNode` | type=`highshelf` Â· gain init=0 dB |
| **EQ air** | `BiquadFilterNode` | type=`peaking` Â· freq=10 kHz Â· gain init=0 dB |
| **Compresseur voix** | `DynamicsCompressorNode` | threshold=-12 dBFS Â· ratio=2 Â· attack=10ms Â· release=150ms Â· knee=6 |
| **Makeup gain** | `GainNode` | gain=1.5 (compense ~3 dB de rÃ©duction du compresseur) |
| **Limiter voix** | `DynamicsCompressorNode` | threshold=-1.5 dBFS Â· ratio=20 Â· attack=2ms Â· release=80ms Â· knee=0 |

### FX bus send/return

| Ã‰tage | Type | DÃ©tail |
|-------|------|--------|
| **Dry bus** | `GainNode` | Signal direct (sans FX) |
| **FX Convolver** | `ConvolverNode` | `normalize=true` (anti-clipping) Â· IR cached pour anti re-FFT lag (~3-4s) |
| **Wet bus** | `GainNode` | Signal traitÃ© par convolver |
| **Mixer** | (sommation) | dry + wet â†’ masterLimiter |

### Master output

| Ã‰tage | Type | ParamÃ¨tres |
|-------|------|------------|
| **Master limiter brick-wall** | `DynamicsCompressorNode` | threshold=-0.3 dBFS Â· ratio=20 Â· attack=1ms Â· release=50ms |
| **Destination** | `audioCtx.destination` | Output haut-parleurs / casque navigateur |

### Analyseurs spectraux (visualisation)

- **Voice channel** : 2 `AnalyserNode` (L/R) Â· `fftSize=2048` Â· `smoothingTimeConstant=0.55-0.8`
- **DAT player & micros** : `fftSize=4096` (rÃ©solution + Ã©levÃ©e pour spectroscope)

### Cache IR (Impulse Response)

`_fxIrCacheKey` (`js/dsp_audio.js`) â€” l'IR est rÃ©gÃ©nÃ©rÃ©e uniquement si `(type, vals)` changent. Ã‰vite la re-FFT 3-4 secondes Ã  chaque ajustement de slider FX. Helper `_fxRefreshIr()`/`_fxEnsureIr()`.

---

## 2. DSP params (`scripts/jarvis_dsp_params.json`)

51 paramÃ¨tres persistÃ©s JSON, chargÃ©s au boot et synchronisÃ©s UI â†” backend via `/api/dsp/params`.

### EQ (4 bandes)
- `eq_low`, `eq_mid`, `eq_high`, `eq_air` (dB Â· -12 Ã  +12 Â· pas 0.5 Â· dÃ©faut 0.0)

### Compresseur voix
- `comp_threshold` (-32 dB) Â· `comp_ratio` (12.5) Â· `comp_attack` (91 ms) Â· `comp_release` (390 ms)

### Gain & stÃ©rÃ©o
- `gain` (3.0 dB) Â· `stereo_enabled` (true) Â· `stereo_width` (0.59) Â· `haas_delay_ms` (20)

### DeepFilterNet
- `df_enabled` (**true** par dÃ©faut Â· activÃ© en session 30) Â· `df_atten_lim` (100) Â· `df_post_filter` (false)

### FX (reverb / echo / delay / chorus / flanger / phaser / exciter)
- `fx_enabled` (false) Â· `fx_type` (`reverb`) Â· `fx_preset` (`room`) Â· `fx_wet` (0.34) Â· `fx_decay` (1.2 s) Â· `fx_predelay_ms` (22) Â· `fx_diffusion` (0.42) Â· + paramÃ¨tres dÃ©diÃ©s par type FX

### Enrich (saturation harmonique douce)
- `enrich_enabled` (true) Â· `enrich_drive` (2.5) Â· `enrich_tone` (2800 Hz) Â· `enrich_mix` (0.15) Â· `enrich_warmth` (0.06)

### TTS
- `tts_engine` (`edge`) Â· `tts_default_engine` (`edge`) Â· `tts_local_voice` (`ff_siwis` Â· Kokoro)

---

## 3. TTS Python â€” fallback chain (4 engines)

ImplÃ©mentation : [`scripts/tts_engines.py`](../scripts/tts_engines.py) (Phase 3 module 3 Â· 280L isolÃ©es) â€” drivers purs des 4 engines. Routes Flask + queues + DSP post-processing restent dans `jarvis.py` car couplÃ©s.

```
edge-tts (fr-CA-AntoineNeural Â· dÃ©faut)
     â”‚ internet KO
     â–¼
Kokoro neural (ff_siwis Â· CUDA Â· 82M params Â· 24 kHz mono WAV)
     â”‚ non disponible
     â–¼
Piper (fr_FR-upmc-medium.onnx Â· CPU Â· LRU cache 3 modÃ¨les)
     â”‚ non disponible
     â–¼
SAPI5 (pyttsx3 Hortense FR Â· Windows fallback)
```

| Engine | Fichier `jarvis.py` ligne | ParticularitÃ© |
|--------|---------------------------|---------------|
| edge-tts | ~5917 (`_edge_tts_async`) | Async Â· qualitÃ© broadcast Â· requiert internet |
| Kokoro | ~569-598 | CUDA lazy Â· voice prefixes `ff_/fm_/af_/am_/bf_/bm_` Â· 24 kHz |
| Piper | ~602-623 | LRU cache 3 modÃ¨les Â· sample voices dans `voices/` |
| SAPI5 | ~651-669 | Pure Windows Â· pas d'internet ni GPU |
| **XTTS v2** (coqui-tts 0.27.5) | Voice Lab | 58 voix natives + voice prints custom Â· GPU CUDA |

### Endpoints

| Route | MÃ©thode | RÃ´le |
|-------|---------|------|
| `/api/speak` | POST | SynthÃ¨se + lecture (params : text, blocking) |
| `/api/speak/stop` | POST | Stop immÃ©diat WinMM (`mciSendStringW("stop all")`) |
| `/api/speak/status` | GET | Ã‰tat queue (queued / deferred / stream_active) |
| `/api/tts` | GET | Liste engines disponibles |
| `/api/tts/local/voices` | GET | Liste voix Piper |

### Log rotatif TTS

`_TTS_LOG_PATH` Â· 2 MB max Â· 7 backups Â· preview 80 chars par appel (`jarvis.py:47-52`).

### DÃ©coupage TTS des textes longs (`_splitForTts` Â· 2026-05-20)

edge-tts a un temps de synthÃ¨se **proportionnel Ã  la longueur du texte** : une longue analyse SOC pouvait mettre 15-24 s avant que la voix ne dÃ©marre. `_splitForTts` (cÃ´tÃ© navigateur) dÃ©coupe les textes > 280 caractÃ¨res aux frontiÃ¨res de phrase â†’ les segments sont synthÃ©tisÃ©s et lus successivement, la voix dÃ©marre en **~1 s**.

### Instrumentation `[TTS-PERF]` (2026-05-20)

Sondes `[TTS-PERF]` ajoutÃ©es dans `jarvis.py`, `tts_engines.py` et `deepfilter.py` : dÃ©composition du temps `/api/tts` (edge_gen / dsp / total), timing edge-tts par tentative, temps de chargement DeepFilterNet, timings des threads de prÃ©chauffage boot. Log **persistant** `scripts/tts_perf.log` (RotatingFileHandler Â· filtre `[TTS-PERF]` sur le logger racine) â€” capture la latence intermittente sans surveiller la console.

---

## 4. STT Python â€” faster-whisper

ImplÃ©mentation : [`scripts/stt.py`](../scripts/stt.py) (Phase 3 module 1 Â· 97L isolÃ©es) â€” modÃ¨le + transcription. Route Flask `/api/stt` reste dans `jarvis.py` (gestion upload tempfile).

| Ã‰lÃ©ment | Valeur |
|---------|--------|
| **ModÃ¨le** | `large-v3-turbo` (Whisper distillÃ© Â· ~800M params) |
| **Device** | CUDA si `torch.cuda.device_count() > 0`, sinon CPU |
| **Compute type** | `int8` (~1 GB VRAM Â· coexiste avec phi4:14b 9.1 GB) |
| **VAD filter** | activÃ© (Silero VAD intÃ©grÃ©) |
| **Beam size** | 2 |
| **Endpoint** | `POST /api/stt` (file audio Â· max 25 MB Â· param `lang`) |

### `initial_prompt` SOC (vocabulaire injectÃ©)

AmÃ©liore la transcription du jargon cybersÃ©curitÃ© homelab :

```
CrowdSec, fail2ban, Suricata, Proxmox, nginx, Apache, JARVIS, SSH, VRAM, GPU, RTX,
Ollama, phi4, qwen, deepseek, gemma, IPv4, firewall, systemctl, journalctl, apt,
nftables, iptables, monitoring, dashboard, SOC, cybersÃ©curitÃ©, homelab
```

â†’ "fail to ban" est correctement transcrit "fail2ban", "phi quatre" â†’ "phi4", etc.

---

## 5. DeepFilterNet (denoising IA Â· CUDA)

ImplÃ©mentation : [`scripts/deepfilter.py`](../scripts/deepfilter.py) (Phase 3 module 4 Â· 132L isolÃ©es Â· 100% autonome â€” numpy + scipy + torch lazy).

| Ã‰lÃ©ment | DÃ©tail |
|---------|--------|
| **Chargement** | Lazy au 1er appel (`init_df()` silencieux â€” stderr fd2 rÃ©orientÃ© pour masquer logurus) |
| **State** | Tuple `(model, df_state, enhance)` stockÃ© dans `_df_model` global |
| **Sample rate** | 48 kHz (resample_poly si input â‰  48 kHz) |
| **CUDA FFT** | ActivÃ© si `torch.cuda.is_available()` |
| **Toggle** | Param `df_enabled` (dÃ©faut `true` depuis session 30) |
| **Latence** | ~500 ms cold start (lazy init) Â· ~16 ms/frame en steady state @ 48 kHz |

â†’ AmÃ©liore drastiquement la qualitÃ© de la voix de Marc (TTS reverse + post-process voice prints + nettoyage micros). ActivÃ© par dÃ©faut cÃ´tÃ© DSP params.

---

## 6. Voice Lab (XTTS v2 Â· voice prints)

Onglet `âœ¦ VOICE LAB` (`tab_voicelab.html`) â€” A/B testing 4 engines + analyse acoustique de voice prints.

| Ã‰lÃ©ment | DÃ©tail |
|---------|--------|
| **Voice prints actuels** | 1 fichier (`scripts/voice_prints/Test_voix_build_01.wav`) â€” extensible via UI |
| **Format** | WAV mono Â· sample rate variable (resample auto) |
| **Endpoints** | `/api/voice/prints` (GET liste) Â· `/api/voice/print/audio/<name>` (GET serve) Â· `/api/voice/print/delete` (POST) Â· `/api/voice/analyse` (POST upload + features) |
| **Analyse acoustique** | librosa : f0 Â· centroid Â· rolloff Â· MFCC Â· RMS Â· mel-spectrogram â†’ calcul `voice_type`, `brightness`, `breathiness`, `voicing`, `eq_preset` auto |

---

## 7. Hardware specs

| Composant | DÃ©tail |
|-----------|--------|
| **GPU** | RTX 5080 Blackwell Â· 16 GB GDDR7 Â· CUDA 12 |
| **Co-tenancy VRAM** | LLM (phi4:14b 9.1 GB) + STT (whisper int8 ~1 GB) + Kokoro/DFN (~1 GB) = ~11-12 GB Â· marge ~4 GB |
| **CPU** | Pas d'override `num_threads` explicite â€” torch/scipy utilisent les cÅ“urs systÃ¨me |
| **CUDA monitoring** | `pynvml.nvmlDeviceGetCudaComputeCapability` (`jarvis.py:1959`) pour reporting VRAM/GPU live dans le panel monitoring |

---

## Tests E2E (couverture)

Suite Playwright `tests/e2e/dsp-voicelab.spec.js` + `dsp-interactive.spec.js` :
- DAT player buttons prÃ©sents
- 4 engines TTS sÃ©lectionnables
- A/B comparison slots prÃ©sents
- Sliders EQ low/high/air â†’ labels mis Ã  jour temps rÃ©el

â†’ `npm test` â€” voir [README.md](../README.md#qualitÃ©--tests--linters).

---

## Historique refontes

| Session | Date | Changement |
|---------|------|------------|
| 30 | 2026-05-12 | **Refonte complÃ¨te DSP** broadcast architecture (Symetrix 528 inspiration) Â· cache IR FX Â· DeepFilterNet activÃ© par dÃ©faut |
| 30 | 2026-05-12 | Suppression `_masterAGC` (DynamicsCompressor sans makeup gain causait disparition signal) |
| 33 | 2026-05-13 | 3 fixes terminal CODE (clear xterm + retrait `&& clear` + PROMPT_COMMAND) â€” pas DSP mais mÃªme fichier `jarvis_main.js` |
| 33 | 2026-05-13 | **Phase 3 split monolithe** â€” extraction de 4 modules audio depuis `jarvis.py` : `stt.py` (97L) Â· `voice_lab.py` (167L) Â· `tts_engines.py` (280L) Â· `deepfilter.py` (132L). Maintenance audio dÃ©sormais ciblÃ©e. |
| 33 | 2026-05-13 | **Phase 3 complÃ¨te** â€” 30 modules extraits au total (audio + bypass + SSH + Proxmox API + RAG + chat orchestration + LLM CR). `jarvis.py` 6592â†’4520L (-31%). NDT script auto 100/100, score honnÃªte global 89/100 (JS toujours monolithique, pas de CI/CD). |
| 33c | 2026-05-13 | **Split JS partiel** â€” extraction `recorder.js` (660L Â· DAT RECORDER R-1) + `voice_print.js` (852L Â· Voice Print v2) en IIFE depuis `jarvis_main.js` 10507â†’8994L (-14.4%). Suppression artefacts obsolÃ¨tes (vp_iife_new.js + vp_rebuild.py). 23 E2E pass, ESLint 0 errors. |
| â€” | 2026-05-14 | **Chantier dette â€” extraction `audio_dsp.py`** â€” bloc DSP audio (25 fonctions ~470L) extrait de `jarvis.py` vers `audio_dsp.py` (508L) : reverb convolution + FX rack (delay/chorus/phaser/flanger/echo/exciter) + filtres biquad + enrichisseur voix + compresseur + `apply_dsp_to_mp3`. DÃ©couplage `DSP_PARAMS` via DI (wrapper jarvis.py prÃ©serve les 9 call sites). FIX bug F821 `_torch` (import lazy â†’ active rÃ©ellement le CUDA reverb). jarvis.py 5110â†’4633L. 23 E2E pass, test audio rÃ©el OK. |
| â€” | 2026-05-20 | **Correctif structurel pipeline de lecture voix** â€” invariant Â« jamais de source TTS sur AudioContext suspendu Â» dans `processQueue`/`playSentence` (`audio_viz.js`) : supprime le gel dÃ©finitif (`onended` jamais Ã©mis) et le chevauchement (source Â« gelÃ©e Â» qui ressurgit au `resume`). Verrou `isPlaying` anti rÃ©-entrance Â· timeout filet supprimÃ© Â· dÃ©verrouillage audio multi-gestes armÃ© tÃ´t dans `_jarvisInit` (`boot_init.js`). **DÃ©coupage TTS** `_splitForTts` (textes > 280 car. aux frontiÃ¨res de phrase) â†’ voix dÃ©marre en ~1 s au lieu de ~15-24 s sur longues analyses SOC. **Instrumentation** `[TTS-PERF]` + log persistant `tts_perf.log`. |

---

## RÃ©fÃ©rences code

| Ã‰lÃ©ment | Fichier:section |
|---------|----------------|
| Web Audio graph voice | `scripts/static/jarvis_main.js:~4815-4862` |
| Cache IR FX | `scripts/static/jarvis_main.js` (`_fxRefreshIr` / `_fxEnsureIr`) |
| Helpers mixing | `scripts/static/jarvis_mixing.js` |
| TTS engines | [`scripts/tts_engines.py`](../scripts/tts_engines.py) (drivers purs) + `jarvis.py` (routes/queues) |
| ChaÃ®ne DSP serveur | [`scripts/audio_dsp.py`](../scripts/audio_dsp.py) (reverb/FX/biquad/compress/`apply_dsp_to_mp3`) â€” wrapper DI dans `jarvis.py` |
| STT init | [`scripts/stt.py:_get_whisper`](../scripts/stt.py) (faster-whisper lazy CUDA) |
| STT initial_prompt | [`scripts/stt.py:_STT_INITIAL_PROMPT`](../scripts/stt.py) (vocabulaire SOC) |
| DeepFilterNet init | [`scripts/deepfilter.py:_load`](../scripts/deepfilter.py) (lazy + silence loguru) |
| DSP params JSON | `scripts/jarvis_dsp_params.json` |
| Voice Lab analyse | [`scripts/voice_lab.py:analyse_features`](../scripts/voice_lab.py) (librosa : pitch/MFCC/mel-spec) |

