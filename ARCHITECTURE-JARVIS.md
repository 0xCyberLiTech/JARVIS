# JARVIS — Architecture & Zones fonctionnelles
<!-- v2.7 — 2026-05-15 — Routing 4 branches + bypass · phi4:14b + qwen3:8b CR · mxbai-embed · NDT 100/100 (script auto) · score honnête global ~94/100 RECALIBRÉ post-audit pytest --cov (départ réel 62, +31 chantier dette) · refactor JS jarvis_main.js 7828→148L (−98,1%) 21 modules · 936 tests pytest sur 32 modules · 25 à 100% cov · coverage 51% lignes (tts_engines 83%, jarvis_mcp_server 91%, ollama_circuit 100%, proxmox_api 93%, bypass_backup 96%, voice_lab 71%, deepfilter 84%, ssh_terminal 100%, stt 98%, rag_live 92%, soc.py 33%, jarvis.py 26%) · fix perf IPv6 -97% latence interne · circuit breaker Ollama étendu 8 call-sites + bouton SOC enrichi · pré-warm Kokoro CUDA au boot · profiling TTS détaillé · hook pre-push pytest · 32 modules Python (jarvis.py 4633L) · jarvis.css → 8 fichiers · git local + pre-commit hooks bloquants + ruff.toml -->

---

## Vue d'ensemble — 5 zones

```
┌─────────────────────────────────────────────────────────────────────────┐
│  NAVIGATEUR  (localhost:5000)                                           │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  ZONE UI / TABS  │  │  ZONE AUDIO      │  │  ZONE SOC CLIENT     │  │
│  │  jarvis_main.js  │  │  jarvis_mixing   │  │  jarvis_main.js      │  │
│  │  4 013 lignes    │  │  1 375 lignes    │  │  (section SOC)       │  │
│  │  + 14 modules JS │  │                  │  │                      │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────────┬───────────┘  │
└───────────┼─────────────────────┼───────────────────────┼──────────────┘
            │  HTTP / SSE          │  Web Audio API        │  poll 30s
            ▼                     ▼                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  SERVEUR FLASK  (jarvis.py + blueprints/soc.py)   localhost:5000        │
│                                                                         │
│  ┌───────────────────────┐   ┌───────────────────────────────────────┐  │
│  │  ZONE IA              │   │  ZONE SOC SERVEUR                     │  │
│  │  jarvis.py            │   │  blueprints/soc.py                    │  │
│  │  4633 lignes          │   │  1689 lignes                          │  │
│  │  75 routes Flask      │   │  _soc_monitor_loop()  (60s Python)    │  │
│  │  + 31 modules Python  │   │                                       │  │
│  └───────────────────────┘   └───────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                  │ Ollama API                          │ SSH (srv-ngix)
                  ▼                                     ▼
         ┌────────────────┐                   ┌─────────────────┐
         │  Ollama local  │                   │  monitoring.json│
         │  phi4:14b      │                   │  CrowdSec / F2B │
         │  (mode SOC)    │                   │  (srv-ngix)     │
         │  gemma4:latest │                   └─────────────────┘
         │  (mode GÉNÉRAL)│
         └────────────────┘
```

---

## Zone 1 — UI / Onglets

```
jarvis.html  (208 lignes — shell minimaliste)
  └─→ include tab_chat.html       Chat LLM + STT + TTS
  └─→ include tab_dsp.html        AI AUDIO RACK (DSP, EQ, compresseur)
  └─→ include tab_monitor.html    Stats CPU/RAM/GPU RTX 5080
  └─→ include tab_soc.html        Journal SOC + graphiques + ⚡ FORCER
  └─→ include tab_settings.html   LLM params, profils prompt, presets
  └─→ include tab_voicelab.html   Synthèse vocale, A/B comparateur
  └─→ include modals.html         Modaux globaux (audio editor, fichiers, terminal, tâches)

Dispatchers centralisés (zéro handler inline) :
  data-action     → 288 boutons
  data-oninput    → 86 sliders/inputs
  DOMContentLoaded → 1 seul : _jarvisInit()   ← POINT D'ENTRÉE UNIQUE
```

---

## Zone 2 — IA (LLM + TTS + STT)

```
┌─────────────────────────────────────────────────────┐
│  jarvis.py — Routes IA principales                  │
│                                                     │
│  POST /api/chat ←── _buildChatPayload()  [CENTRALISÉ]
│       │               6/6 appels couverts           │
│       │               détection keywords SOC →      │
│       │               injection contexte 0ms        │
│       ▼                                             │
│  api_chat() → _chat_inject_soc()                    │
│             → _chat_build_messages()                │
│             → _chat_stream_inner()  (SSE streaming) │
│             → Ollama API                            │
│                                                     │
│  POST /api/tts  → _tts_edge_generate()              │
│                 → edge-tts  (fr-CA-AntoineNeural)   │
│                 → Kokoro ff_siwis  (fallback auto)  │
│                 → XTTS v2  (58 voix + voice prints) │
│                 → Piper hors-ligne  (fr-FR-upmc)    │
│                 → SAPI5 pyttsx3    (fallback final) │
│                 Lock _TTS_LOCK → séquentiel strict  │
│                                                     │
│  POST /api/stt  → faster-whisper "large-v3-turbo" FR         │
│                   CUDA float16 · beam_size=2        │
│                   vad_filter=True                   │
└─────────────────────────────────────────────────────┘

Profils LLM — 7 profils (jarvis_prompt_profiles.json)
  Profil auto-chargé selon le mode actif via _applyModeProfile()
  Tous : garde RFC1918 — IPs LAN jamais bannables
  SOC : temperature=0.2 · num_ctx=16384 · chain-of-thought imposé

Modèles Ollama actifs :
  phi4:14b             ← mode SOC (défaut · 9.1 GB · full VRAM · zéro swap)
  gemma4:latest        ← mode GÉNÉRAL + VOCAL + vision (multimodal natif)
  qwen2.5-coder:14b    ← mode CODE (boucle dev srv-dev-1 · 9.0 GB)
  mxbai-embed-large    ← RAG embeddings (1024 dims · keep_alive 2m — obligatoire)

⚠ Supprimés : phi4-reasoning:plus · qwen2.5:14b · deepseek-r1:14b · llava-phi3:latest · nomic-embed-text
```

---

## Zone 3 — SOC (intégration sécurité)

```
┌────────────────────────────────────────────────────────────────┐
│  CÔTÉ NAVIGATEUR — jarvis_main.js                             │
│                                                                │
│  window._jarvisMonData  ←── poll 30s monitoring.json          │
│       (buffer Nyquist = cron/2)                               │
│                                                                │
│  _buildChatPayload()  ── keywords SOC détectés ?              │
│       OUI → _monCtxStr(d)  injecte contexte instantané        │
│       NON → appel normal sans contexte SOC                    │
│                                                                │
│  _jvAutoCheck(data)  ← hook 17-fetch.js (chaque poll 60s)     │
│       → seuils CPU / bans / erreurs / kill chain              │
│       → alertes vocales TTS si score > voiceMinScore          │
│       → auto-ban JS (EXPLOIT/BRUTE/SCAN)                      │
│       → restart service si DOWN                               │
└─────────────────────┬──────────────────────────────────────────┘
                      │  POST /api/soc/*
                      ▼
┌────────────────────────────────────────────────────────────────┐
│  CÔTÉ SERVEUR — blueprints/soc.py                             │
│                                                                │
│  _soc_monitor_loop()  [thread Python — poll 60s]              │
│       → _fetch_monitoring(force=True) ← bypass cache 30s     │
│       → _soc_exploit_gap_check()  ← ban EXPLOIT avant gate   │
│       ─── gate : dashboard ouvert ? ──                        │
│       → _soc_autoban()        BRUTE/SCAN/honeypot             │
│       → _soc_reqhour_check()  spike >500 req/h               │
│       → _soc_suricata_check() sév.1/2/3                       │
│       → _soc_threat_level()   alerte vocale cooldown 30min    │
│                                                                │
│  _SSH_LOCK  ← VERROU CENTRALISÉ — une seule connexion SSH     │
│       timeout 20s · retry 1× · sérialisation stricte         │
│                                                                │
│  _SOC_AUTO_BANNED  ← persisté jarvis_soc_autobanned.json      │
│       cooldown 15min/IP survit aux redémarrages               │
└────────────────────────────────────────────────────────────────┘

Routes SOC (soc.py — extraits clés) :
  GET  /api/soc/monitor         → monitoring.json relayé
  POST /api/soc/ban-ip          → cscli decisions add
  POST /api/soc/unban-ip        → cscli decisions delete
  POST /api/soc/restart-service → systemctl restart (whitelist stricte)
  POST /api/soc/force-autoban   → scan immédiat candidats + raisons skip
  GET  /api/soc/actions         → journal 30j (1000 entrées max)
```

---

## Zone 4 — Audio (chaîne DSP broadcast)

Architecture inspirée d'un **Symetrix 528** (voice processor broadcast) +
**console aux send/return** + bus de **mastering** avec AGC final.
Refonte complète 2026-05-12 (session 30).

### Vue d'ensemble — 3 étages

```
[1] VOICE CHANNEL STRIP   →   [2] FX SEND/RETURN BUS   →   [3] MASTER BUS
     (canal voix dynamique)      (effets parallèles)         (AGC + brick-wall)
```

### Topologie complète

```
SOURCE TTS (edge-tts / Kokoro / Piper / SAPI5)
       ↓
   analyser  ──→ analyserL/R (VU)  ──→  _stereoMerger
       ↓
   _jarvisPreGain (input trim 1.0)
       ↓
   _dspAnalyser (FFT spectre — pour visualisation)
       ↓
┌─────────────────────────────────────────────┐
│  ÉTAGE 1 — VOICE CHANNEL STRIP              │
│                                              │
│  EQ 4 bandes : Low → Mid → High → Air        │
│       ↓                                      │
│  _dspCompressor                              │
│   threshold -24 dBFS · ratio 4:1             │
│   attack 3 ms · release 250 ms · knee 6      │
│       ↓                                      │
│  _dspLimiter (voice bus brick)               │
│   threshold -0.5 dBFS · ratio 20:1           │
│   attack 1 ms · release 100 ms · knee 0      │
│       ↓                                      │
│  _dspGainNode (output trim 1.0)              │
└──────────────────┬──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌─────────────┐      ┌────────────────────────────┐
│  DRY PATH   │      │  ÉTAGE 2 — AUX SEND (FX)   │
├─────────────┤      ├────────────────────────────┤
│ _fxDryGain  │      │ _fxSendGain (CALIBRÉ FX)   │
│  cos x-fade │      │  reverb  ×1.00   ( 0 dB)   │
│             │      │  echo    ×0.35   (-9 dB)   │
│             │      │  delay   ×0.45   (-7 dB)   │
│             │      │      ↓                     │
│             │      │ _fxConvolver               │
│             │      │  normalize=true (Web Audio)│
│             │      │      ↓                     │
│             │      │ _fxReturnGain (1.0)        │
│             │      │      ↓                     │
│             │      │ _fxWetGain (sin x-fade)    │
└──────┬──────┘      └────────────┬───────────────┘
       │                          │
       └──────────┬───────────────┘
                  ▼
┌────────────────────────────────────────┐
│  ÉTAGE 3 — MASTER BUS                  │
│                                         │
│  _fxMixBus (sommation dry + wet)        │
│        ↓                                │
│  _masterLimiter (brick-wall final)      │
│   threshold -0.3 dBFS · ratio 20:1      │
│   attack 1 ms · release 50 ms · knee 0  │
└─────────────────┬───────────────────────┘
                  ▼
        audioCtx.destination
```

⚠ **Pas d'AGC au master** : le voice channel contient déjà comp + limiter (étage 1).
Empiler un AGC supplémentaire au mix sans makeup gain causait une atténuation
cumulative qui finissait par éteindre le signal voix (incident 2026-05-12).

### Branche TASCAM DAT (musique parallèle)

```
TASCAM DAT
    ↓
datGain → _datLimiter → _datAnL/R (VU)
                              ↓
                     _datPreDsp
                              ↓
        ┌─────────────────────┴──────────────┐
        │  EQ MUSIC 4 BANDES (TASCAM)        │
        │  SUB    80 Hz  lowshelf  Q=0.7     │
        │  BASS  300 Hz  peaking   Q=0.8     │
        │  MIDS  3 kHz   peaking   Q=0.9     │
        │  TREBLE 10 kHz highshelf Q=0.7     │
        └─────────────────────┬──────────────┘
                              │
                    rejoint _dspCompressor (étage 1 partagé)
```

### Calibration loudness par type de FX (`_FX_SEND_CAL`)

La convolution avec N taps discrets (echo, delay) crée une perception de loudness
supérieure à une réverbération diffuse à RMS égal. Le SEND est trim par type :

| Effet | Send gain | dB | Raison |
|-------|-----------|-----|--------|
| reverb | 1.00 | 0 dB | Référence — réverb diffuse perçue douce |
| echo | 0.35 | -9 dB | Taps discrets stéréo, perception très forte |
| delay | 0.45 | -7 dB | Taps discrets mono, perception forte |

### Robustesse — 4 piliers

| # | Mesure | Bénéfice |
|---|--------|----------|
| 1 | `_fxConvolver.normalize = true` | Web Audio normalise nativement l'IR (RMS) |
| 2 | `_FX_SEND_CAL` par type | Loudness perçue uniforme entre tous les FX |
| 3 | IR Echo/Delay : 6 taps max + seuil -40 dB | Comportement matériel réaliste, énergie bornée |
| 4 | Master AGC + brick-wall final | Sortie absolue capée à -0.3 dBFS, peu importe l'amont |

### Helpers JS clés

```javascript
_fxSetWetDry(wet, smooth)     // equal-power crossfade cos/sin + send calibré
_normalizeIrRms(buf, target)  // normalisation RMS manuelle (debug / IR custom)
_generateFxIr(type, vals)     // synthèse IR reverb / echo / delay
```

### Crossfade equal-power (wet/dry)

Pas de creux à wet=0.5 (un crossfade linéaire perd 3 dB au milieu).
Garantit puissance perçue constante quelle que soit la valeur du wet :

```
wet_gain = sin(wet × π/2)
dry_gain = cos(wet × π/2)
```

| wet | dry_gain | wet_gain | somme énergie |
|-----|----------|----------|---------------|
| 0.0 | 1.000 | 0.000 | 1.000 |
| 0.5 | 0.707 | 0.707 | 1.000 |
| 1.0 | 0.000 | 1.000 | 1.000 |

### ⚠ Règles critiques

| # | Règle | Raison |
|---|-------|--------|
| 1 | Ne jamais reconnecter `analyser → analyserL/R` | Boucle de rétroaction — sifflement (incident 2026-04-02) |
| 2 | Tous les nouveaux FX doivent ajouter une entrée `_FX_SEND_CAL` | Sinon loudness incohérente vs reverb |
| 3 | Toute nouvelle IR custom doit passer le test : `_masterAGC.reduction > -6 dB` | Sinon l'AGC sature, signal compressé excessivement |
| 4 | Ne jamais connecter directement à `audioCtx.destination` | Bypass du brick-wall = risque de saturation hardware |

### Initialisation

```
_initDspCreateNodes()       → création nœuds Web Audio (étages 1+2+3)
_initDspWireChain()         → câblage send/return/master (sans boucle)
_initDspApplyAudioParams()  → gains / EQ / compresseur
_initDspApplyUiParams()     → sliders / rack UI
```

### DSP avancé

| Bloc | Rôle |
|------|------|
| DeepFilterNet | Débruitage IA (GPU RTX 5080 sm_120 · PyTorch 2.7.1+cu128 · `df_enabled=False` par défaut) |
| Haas stéréo | Élargissement image (canal R retardé 18 ms) |
| _dspCompressor | Partagé voix + musique (étage 1) |
| _masterAGC | NOUVEAU — Auto Gain Control loudness target -18 dBFS |
| Analyseur FFT | `_drawSpectrum` 4 modes : mirror / scope / piano / split |

---

## Zone 5 — GPU / Monitor

```
jarvis.py
  _gpu_temp_monitor_loop()  thread Python — poll 30s (_GPU_MON_POLL_S)
       → pynvml stats RTX 5080 : P-state, throttle, PCIe, VRAM, watts, temp
       → stocké dans window._jvLastStats (via /api/stats)

jarvis_main.js
  JV_CHECK = 10s → fetch /api/stats → window._jvLastStats
  updateMonitor() → 5 helpers :
       _updateMonArcs()            jauges annulaires CPU/RAM/GPU
       _updateMonGraphsAndPanels() graphiques 24h
       _updateMonSidebar()         sidebar métriques
       _updateMonRtxPanel()        panel RTX 5080 détaillé
       _updateMonCuda()            CUDA cores, compute capability
```

---

## Architecture modulaire — chantier dette 2026-05-14

`jarvis.py` n'est plus un monolithe : c'est désormais l'**orchestrateur Flask**
(4633 L) qui délègue à **31 modules Python** extraits dans `scripts/` (audio,
bypass SSH/VM/backup, infra/RAG, chat/LLM core, `audio_dsp.py`) — voir
[`docs/ROUTING-JARVIS.md`](docs/ROUTING-JARVIS.md) pour la liste complète.
Côté frontend (refactor JS 2026-05-14 soir) : `jarvis_main.js` **7828→4013 L
(−49%)** + **14 modules JS** — `jarvis_mixing.js`, `recorder.js`,
`voice_print.js` dans `static/` · **11 modules** dans `static/js/` :
terminal_code, voice_lab, stt, tasks_tab, welcome, eq_parametric, eq_music,
audio_mire, audio_viz, settings_llm, dsp_audio. L'ex-`jarvis.css` monolithique
est éclaté en **8 fichiers** `static/css/`. Dépôt **git local** (aucun remote)
+ **pre-commit hooks bloquants** (ruff + eslint) + `ruff.toml`.
Refactor JS **terminé** 2026-05-14/15 : `jarvis_main.js` 7828→148 L (−98,1% cumul), 15 modules extraits dans `static/js/` (18 modules total). **936 tests pytest** sur **32 modules (25 à 100% cov) Python (100%)** avec coverage **39% lignes** (audit pytest --cov rigoureux : tts_engines 83%, jarvis_mcp_server 91%, ollama_circuit 100%, proxmox_api 93%, bypass_backup 96%, voice_lab 71%, deepfilter 84%, ssh_terminal 100%, stt 98%, rag_live 92%, soc.py 33%, jarvis.py 26%). Fix perf IPv6 (`OLLAMA_URL` + `JARVIS_BASE` → `127.0.0.1` explicite) : −97% latence sur clients internes (MCP, soc.py auto-engine). **Circuit breaker Ollama** (`scripts/ollama_circuit.py` · 3 états + backoff exponentiel + indicateur HUD `● OLLAMA` · **étendu à 8 call-sites** dans `jarvis.py` · bouton SOC dashboard PING JARVIS enrichi état Ollama). **Pré-warm Kokoro CUDA au boot** (`_kokoro_prewarm` 60 s post-boot · élimine cold start 42.8 s mesuré par `tools/profile_tts.py`). Hook pre-push pytest installé. Score honnête global ~94/100 (recalibré post-audit honnête).

## Modules centralisés — synthèse

| Module | Centralise quoi | Fichier |
|--------|----------------|---------|
| `_buildChatPayload()` | 6/6 appels LLM — injection contexte SOC | jarvis_main.js |
| `_jarvisInit()` | 1/1 DOMContentLoaded — init complète | jarvis_main.js |
| `compute_threat_score()` | Score officiel — JAMAIS recalculé ailleurs | monitoring_gen.py |
| `_soc_monitor_loop()` | Auto-engine Python quand dashboard fermé | soc.py |
| `_SSH_LOCK` | Toutes les connexions SSH vers srv-ngix | soc.py |
| `_SOC_AUTO_BANNED` | Cooldowns ban — persisté JSON | soc.py |
| `_TTS_LOCK` | Séquencement TTS — évite doublons vocaux | jarvis.py |
| `data-action` dispatcher | 288 boutons — zéro handler inline | jarvis.html |

---

## Faut-il unifier d'autres circuits ?

**Non — architecture mature au 2026-05-03.**

| Vérification | État |
|---|---|
| Appels LLM | ✅ 6/6 via `_buildChatPayload()` |
| DOMContentLoaded | ✅ 1 seul `_jarvisInit()` |
| SSH vers srv-ngix | ✅ `_SSH_LOCK` sérialise tout |
| Score menace | ✅ `compute_threat_score()` — source unique |
| Contexte SOC chatbot | ✅ `_monCtxStr()` — même données que dashboard |
| Chaîne audio voix/musique | ✅ Nœuds compresseur/limiter partagés |
| Cooldown bans | ✅ `_SOC_AUTO_BANNED` persisté |
| Styles inline | ✅ 0 extractable CSS/JS/HTML |
| Fonctions >80 lignes | ✅ 0 violation |

---

## Polling — rappel architecture

```
monitoring_gen.py ── cron 60s ──→ monitoring.json
                                        │
  SOC dashboard    ── 60s ──────────────┤  (17-fetch.js)
  JARVIS chatbot   ── 30s ──────────────┤  (Nyquist buffer)
  JARVIS engine    ── 10s ──────────────┘  (/api/stats GPU live)
  Heartbeat        ── 15s →  JARVIS ping
  Proto live       ── 15s →  proto-live.py
  Router GT-BE98   ── 30s →  router.json

LCM(10,15,30,60) = 60s → alignement théorique — négligeable LAN
```

---

---

## Zone 6 — Multi-agent MCP (2026-05-04)

### Vue d'ensemble — deux agents, responsabilités distinctes

```
┌─────────────────────────────────────────────────────────────────────────┐
│  CLAUDE CODE  (VSCode — Anthropic API)                                  │
│                                                                         │
│  Orchestrateur — voit uniquement les problèmes à sa hauteur :           │
│  • Incident nouveau / pattern inconnu de JARVIS                         │
│  • Modification de code (jarvis.py, soc.py, nginx configs)              │
│  • Décisions architecturales                                            │
│  • Analyse multi-fichiers complexe                                      │
│  • Problème que JARVIS a explicitement escaladé                         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │  MCP stdio (.mcp.json)
                               │  12 outils : jarvis_chat · jarvis_soc_status
                               │              jarvis_stats · jarvis_soc_ask
                               │              jarvis_infra_status · jarvis_proxmox_vms
                               │              jarvis_read_file · jarvis_model_switch
                               │              jarvis_last_response · jarvis_code_exec
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  jarvis_mcp_server.py  (pythonw — stdio — port 0)                       │
│  Pont MCP — traduit appels Claude → requêtes HTTP JARVIS                │
│  SSE consommé entièrement (_collect_sse_tokens)                         │
│  Identifiant visuel : ╔══ ◈ JARVIS — phi4:14b ◈ ══╗                     │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │  HTTP localhost:5000
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  JARVIS  (Flask + phi4:14b via Ollama — local)                          │
│                                                                         │
│  Agent autonome SOC — traite localement :                               │
│  • Parsing / filtrage logs (Suricata, CrowdSec, fail2ban)               │
│  • Détection patterns connus → auto-ban sans escalade                   │
│  • Agrégation : 500 lignes logs → résumé structuré 5 points            │
│  • Monitoring routine → remonte uniquement les anomalies                │
│  • Questions SOC simples (état, compteurs, bans récents)                │
│  • Fonctions isolées, debugging simple à modéré                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Pourquoi cette architecture réduit les coûts API

Les coûts Anthropic viennent du **volume de tokens envoyés**, pas du nombre d'appels.

| Scénario | Sans architecture | Avec architecture |
|----------|-----------------|-----------------|
| Question SOC "état de la menace" | Logs bruts → Claude (~3 000 tokens) | JARVIS analyse → résumé 5 points → Claude (~200 tokens) |
| Monitoring routine (tout va bien) | Claude sollicité à chaque poll | JARVIS détecte → pas d'escalade → **0 token Claude** |
| Debugging fonction isolée | Claude voit le fichier entier | phi4 résout → **0 token Claude** si succès |
| Incident inconnu / code complex | Escalade vers Claude avec contexte ciblé | Claude voit uniquement l'extrait pertinent |

**Résultat** : Claude consomme des tokens uniquement sur des tâches justifiant son niveau. Le volume baisse, la valeur par appel monte.

---

### Règles de séparation — qui fait quoi

```
┌──────────────────────────────┬─────────────────────────────────────────┐
│  JARVIS / phi4:14b           │  Claude Code (escalade uniquement)       │
├──────────────────────────────┼─────────────────────────────────────────┤
│  Logs bruts → agrégation     │  Pattern inconnu de JARVIS               │
│  Patterns SOC connus         │  Modification jarvis.py / soc.py         │
│  Auto-ban RFC1918 protégé    │  Décision architecturale                 │
│  Restart whitelist services  │  Analyse multi-fichiers                  │
│  Questions SOC état/compteurs│  Problème phi4 a bloqué + contexte donné │
│  Fonctions isolées           │  Infra en panne (tous filtres levés)     │
│  Debugging simple→modéré     │                                          │
└──────────────────────────────┴─────────────────────────────────────────┘
```

---

### Garde-fous — ce que JARVIS ne fera jamais

- **RFC1918 intouchable** : `_LAN_PREFIXES` — IPs 192.168.x / 10.x / 172.16-31.x jamais bannables
- **`_ALLOWED_SERVICES`** : whitelist stricte (nginx / crowdsec / fail2ban / php) — pas d'élargissement sans validation
- **Code** : JARVIS propose, n'applique jamais sans validation utilisateur
- **Nouvelles actions autonomes** : mode "suggestion" avant activation en prod
- **Disponibilité** : si Claude est hors ligne, JARVIS continue seul — la chaîne ne se bloque pas

---

### Configuration MCP

**Fichier** : `C:\Users\mmsab\Documents\0xCyberLiTech\.mcp.json` (racine workspace VSCode)

```json
{
  "mcpServers": {
    "jarvis": {
      "command": "pythonw",
      "args": ["C:/Users/mmsab/Documents/0xCyberLiTech/JARVIS/scripts/jarvis_mcp_server.py"],
      "env": {}
    }
  }
}
```

`pythonw` : supprime la fenêtre console Windows tout en maintenant les pipes stdio — requis pour MCP sur Windows.
`settings.json` ne convient pas (schéma strict VSCode rejette `mcpServers`) → `.mcp.json` projet uniquement.

---

### Identifiant visuel dans VSCode

Toute réponse JARVIS est préfixée d'un cadre ASCII pour différencier immédiatement JARVIS de Claude :

```
╔══════════════════════════════════════╗
║  ◈  JARVIS  —  phi4:14b  ◈           ║
╚══════════════════════════════════════╝
[réponse de JARVIS]
```

Sans ce cadre = réponse Claude. Différence visuelle immédiate, important pour l'utilisateur malvoyant.

---

*ARCHITECTURE-JARVIS.md · 0xCyberLiTech · 2026-05-14*
