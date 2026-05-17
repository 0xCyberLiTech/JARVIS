# JARVIS — Assistant IA Personnel v3.3

Interface web locale type Iron Man : chat IA, terminal intégré, monitoring GPU/CPU, explorateur de fichiers, gestionnaire de tâches, DSP audio stéréo hardware-style, éditeur audio IA, Voice Lab, STT local.

> Créateur interface : **0xcyberlitech**

## Stack

| Composant | Technologie |
|-----------|-------------|
| Backend   | Python 3.11 + Flask (port 5000, loopback only) — jarvis.py 4739 lignes · ~150 routes · 33 modules Python extraits |
| LLM SOC   | Ollama — phi4:14b (SOC défaut · 9.1 GB · full VRAM · zéro swap) |
| LLM GÉNÉRAL | gemma4:latest (GÉNÉRAL + VOCAL + vision multimodal) |
| LLM CODE  | qwen2.5-coder:14b (mode CODE · dev srv-dev-1 · 9.0 GB) |
| LLM cloud | — (non configuré) |
| TTS défaut | edge-tts fr-CA-AntoineNeural → fallback auto Kokoro ff_siwis si internet KO |
| TTS neural local | Kokoro neural (CUDA) · XTTS v2 coqui-tts 0.27.5 (58 voix + voice prints) |
| TTS hors-ligne | Piper neural (fr_FR-upmc-medium.onnx) + SAPI5 pyttsx3 |
| STT local | faster-whisper `large-v3-turbo` FR, VAD filter, CUDA · initial_prompt vocabulaire SOC |
| RAG | mxbai-embed-large · 1024 dims · seuil 0.35 · TTL 300s · MEMORY.md + CIRCUIT_SOC_JARVIS + RUNBOOK |
| DSP audio | numpy/scipy — EQ biquad 5 bandes, compresseur, Haas stéréo, DeepFilterNet GPU |
| GPU stats | pynvml RTX 5080 Blackwell — P-state, PCIe, VRAM, watts |
| Frontend  | HTML/CSS/JS — thème JARVIS holographique · sources chargées directement (`?v={{ boot_id }}`) |
| Audio Web | Web Audio API — EQ+Compresseur live, waveform, analyseur spectral stéréo |

## Lancement

```bat
start_dashboard.bat
```

Gère automatiquement : venv, démarrage Ollama, ouverture navigateur → `http://localhost:5000`

Arrêt : `stop_jarvis.bat` ou raccourci `JARVIS - Arrêt.lnk` sur le bureau.

## Structure

```
JARVIS/
├── scripts/
│   ├── jarvis.py                      ← serveur Flask principal (4739 lignes · ~150 routes · réduit via Phase 3 split + audio_dsp.py)
│   ├── 31 modules dédiés/             ← Phase 3 : audio (5) + bypass (8) + infra (2) + chat/LLM (15) + audio_dsp.py (chantier 2026-05-14) — voir docs/ROUTING-JARVIS.md
│   ├── blueprints/
│   │   └── soc.py                     ← Blueprint SOC (1689 lignes · auto-engine · SSH 4 hôtes)
│   ├── jarvis_mcp_server.py           ← MCP bridge Claude Code ↔ JARVIS (12 outils (+jarvis_ioc_status Sprint 18d 2026-05-16))
│   ├── templates/
│   │   ├── jarvis.html                ← UI shell Jinja2 (204 lignes · 0 handler inline)
│   │   ├── tabs/                      ← 8 onglets inclus
│   │   └── partials/modals.html       ← modaux globaux
│   ├── static/
│   │   ├── jarvis_main.js             ← JS principal (4013 lignes · refactor JS 2026-05-14 : 7828→4013, −49%)
│   │   ├── jarvis_mixing.js           ← DSP mixer stéréo (1375 lignes)
│   │   ├── recorder.js                ← DAT RECORDER R-1 IIFE (660 lignes)
│   │   ├── voice_print.js             ← Voice Print v2 IIFE (852 lignes)
│   │   ├── js/                        ← 11 modules extraits : terminal_code·voice_lab·stt·tasks_tab·welcome·eq_parametric·eq_music·audio_mire·audio_viz·settings_llm·dsp_audio
│   │   └── css/                       ← 8 fichiers CSS par secteur (chantier 2026-05-14 · ex-jarvis.css 5270L)
│   ├── jarvis_rag/                    ← base de connaissances locale
│   │   ├── meta.json                  ← 599 chunks (MEMORY.md×2 + CIRCUIT_SOC + RUNBOOK)
│   │   └── embeddings.npy             ← vecteurs mxbai-embed-large float32 1024-dim
│   ├── jarvis_llm_params.json         ← paramètres LLM persistés
│   ├── jarvis_model.json              ← modèle actif Ollama
│   ├── jarvis_dsp_params.json         ← paramètres DSP audio + moteur TTS
│   ├── jarvis_memory.json             ← mémoire contextuelle JARVIS
│   ├── jarvis_memory_summary.json     ← résumés sessions inter-redémarrages
│   ├── jarvis_welcome.json            ← texte preloader d'accueil
│   ├── jarvis_system_prompt.txt       ← prompt système (override)
│   ├── jarvis_prompt_profiles.json    ← profils prompt sauvegardés
│   ├── start_dashboard.bat            ← démarrage complet
│   ├── stop_jarvis.bat                ← arrêt du serveur
│   ├── voices/                        ← modèles Piper TTS hors-ligne
│   │   └── fr_FR-upmc-medium.onnx    ← 74 MB
│   └── models/                        ← XTTS v2 (coqui-tts)
│       └── tts_models/multilingual/multi-dataset/xtts_v2
├── docs/
│   ├── DEPLOIEMENT.md                 ← exploitation, API, dépannage
│   ├── REINSTALLATION.md              ← réinstallation Windows complète
│   ├── AUDIT_JARVIS.md                ← audit sécurité (10/10)
│   └── REFERENCE-TECHNIQUE.md         ← référence complète (NDT 100/100 script auto · score honnête global 92/100 (933 tests, 32 modules · 22 à 100% cov, circuit breaker Ollama 8 call-sites, pré-warm Kokoro))
├── README.md
└── MEMORY.md
```

## Onglets UI

| Onglet | Fonctionnalité |
|--------|---------------|
| Chat IA | Conversation LLM streaming, TTS auto, tool calling, recherche web DDG, STT mic |
| Settings | LLM params (temp/top_p/num_ctx), profils prompt, provider IA, préréglages |
| ◈ DSP AUDIO | AI AUDIO RACK — EQ 5 bandes, compresseur, DeepFilter, Haas stéréo, analyseur spectral, VU-meter JARVIS, moteur TTS |
| ✂ AUDIO EDITOR | Éditeur audio IA — waveform L/R, transport, EQ paramétrique 5 bandes (live+offline), compresseur live, fade in/out, denoise, export multi-bitdepth |
| Voice Lab | Synthèse vocale — moteur TTS, paramètres voix, EQ, presets, comparateur A/B |
| Monitor | Stats temps réel CPU/RAM/GPU/RTX 5080 (P-state, PCIe, throttle, watts) |
| Terminal | Shell intégré (cmd/PowerShell), historique cd, taille police ajustable |
| Fichiers | Explorateur lecteurs auto-détectés, breadcrumb, éditeur code, analyse IA |
| Tâches | Tâches automatisées avec scheduling |
| Preloader | Écran d'accueil JARVIS — boot sequence animée, frame alu brossé, décos HUD |

## Moteurs TTS

| Moteur | Connexion | Config |
|--------|-----------|--------|
| `edge` (défaut) | En ligne | fr-CA-AntoineNeural · fallback auto Kokoro si internet KO |
| `kokoro` | Hors-ligne CUDA | ff_siwis FR · speed 0.5×–2.0× · préchargé au démarrage |
| `xtts` | Hors-ligne CUDA | coqui-tts 0.27.5 · 58 voix multilingues + voice prints |
| `piper` | Hors-ligne | fr_FR-upmc-medium.onnx (74 MB) |
| `sapi` | Hors-ligne | Microsoft Hortense FR (inclus Windows) |

Changement via UI DSP ou `jarvis_dsp_params.json` → `"tts_engine": "edge"|"kokoro"|"xtts"|"piper"|"sapi"`.

Chaîne fallback automatique : edge → Kokoro (si internet KO) → Piper → SAPI5.

## Modèles Ollama actifs

| Modèle | VRAM | Rôle |
|--------|------|------|
| phi4:14b | ~9.1 GB | SOC · full VRAM · zéro swap |
| gemma4:latest | ~9.6 GB | GÉNÉRAL + VOCAL + vision (multimodal) |
| qwen2.5-coder:14b | ~9.0 GB | CODE · multi-fichiers · dev srv-dev-1 |
| mxbai-embed-large | ~0.7 GB | RAG embeddings · 1024 dims · keep_alive 2m |

## Paramètres LLM (`jarvis_llm_params.json`)

| Paramètre | Valeur active |
|-----------|--------------|
| temperature | 0.5 |
| num_predict | 4096 |
| top_k | 40 |
| num_ctx | 16384 (adaptatif : SOC=16384 · court=4096) |

## Provider IA

- `ollama` (local, défaut) — 3 branches de routing :
  - **phi4:14b** (mode SOC défaut · 9.1 GB · full VRAM · zéro swap)
  - **gemma4:latest** (mode GÉNÉRAL+VOCAL+vision multimodal)
  - **qwen2.5-coder:14b** (mode CODE · boucle dev srv-dev-1)
  - **mxbai-embed-large** (RAG embeddings · 1024 dims · obligatoire)
- ⚠️ Supprimés : phi4-reasoning:plus · qwen2.5:14b · deepseek-r1:14b · llava-phi3:latest · nomic-embed-text

## Machine cible

- GPU : **RTX 5080** (Blackwell, CUDA 12, 16 GB GDDR7)
- OS : Windows 11 Pro
- Python : 3.11

## Intégration SOC Dashboard

JARVIS est intégré dans le dashboard SOC (`monitoring-index.html` v3.97.157) — **optionnel,
le SOC reste 100% opérationnel si JARVIS est éteint.**

| Élément | Description |
|---------|-------------|
| Tuile JARVIS | Dans la grille INFRASTRUCTURE — statut, modèle LLM, compteurs session |
| Panel JARVIS | FAB bas-droite + badge header — chat, quick prompts (14), historique |
| Auto-engine | Analyse auto déclenchée à chaque refresh 60s si JARVIS ONLINE |
| TTS | Lecture vocale via `edge-tts` (localhost:5000) |

**Démarrer JARVIS pour le SOC :**
```bat
cd C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\scripts
python jarvis.py
```
→ Ouvrir le dashboard SOC : http://192.168.1.50:8080/ (LAN)
→ JARVIS se connecte automatiquement depuis le navigateur via `http://localhost:5000`

## Documentation

| Fichier | Contenu |
|---------|---------|
| [`docs/DEPLOIEMENT.md`](docs/DEPLOIEMENT.md) | Exploitation, routes API, dépannage |
| [`docs/REINSTALLATION.md`](docs/REINSTALLATION.md) | Réinstallation Windows complète |
| [`docs/ROUTING-JARVIS.md`](docs/ROUTING-JARVIS.md) | **Routing automatique** : 4 modes · 9 bypass Python · sécurité (RFC1918, _BLOCKED_SSH, whitelists) |
| [`docs/MCP-SERVER.md`](docs/MCP-SERVER.md) | **MCP server** : pont Claude ↔ JARVIS · **12 outils (+jarvis_ioc_status Sprint 18d 2026-05-16)** détaillés (+`jarvis_defense_24h` 2026-05-16) · config Claude Desktop · watchdog |
| [`docs/AUDIO-DSP.md`](docs/AUDIO-DSP.md) | **Audio DSP** : Web Audio graph (EQ+Comp+Limiter+FX) · 4 engines TTS · STT large-v3-turbo · DeepFilterNet CUDA · Voice Lab |
| [`docs/AUDIT_JARVIS.md`](docs/AUDIT_JARVIS.md) | Audit sécurité — 10/10 — v2.6 — 0 gap |
| [`docs/REFERENCE-TECHNIQUE.md`](docs/REFERENCE-TECHNIQUE.md) | Référence v1.5 — NDT 100/100 (script auto) · **score honnête global 92/100** (recalibré depuis 62 réel · +31 via chantier dette 2026-05-14/15 : git + hooks + ruff.toml + CSS 8 fichiers + audio_dsp.py + refactor JS −98,1% + 933 tests pytest sur 32 modules · 22 à 100% cov (100%) avec coverage 51% lignes + fix perf IPv6 + circuit breaker Ollama étendu 8 call-sites + pré-warm Kokoro + hook pre-push) |
| [`docs/ROADMAP-V33.md`](docs/ROADMAP-V33.md) | Fonctionnalités v3.3 planifiées |
| [`MEMORY.md`](MEMORY.md) | État projet, stack, historique corrections |

## Qualité — chantier dette technique 2026-05-14/15

Audit honnête et chantier de dette : **score recalibré 62 → 92/100 honnête (39% coverage lignes, 933 tests, 32 modules · 22 à 100% cov, circuit breaker Ollama étendu 8 call-sites, pré-warm Kokoro CUDA)** (l'ancien
« 91/100 » / « 100/100 » étaient optimistes — le NDT script auto mesure le style,
pas l'architecture/tests/CI). Travaux du chantier :
- **Dépôt git LOCAL** initialisé (100% local, aucun remote — règle « rien sur le web ») · commits atomiques
- **Outillage qualité** : `ruff.toml` (Python, baseline 98 → 0 erreurs · 2 vrais bugs F821 corrigés) · `eslint.config.js` (JS, 0 erreur) · `.pre-commit-config.yaml` (hooks bloquants ruff + eslint, 100% locaux)
- **Architecture modulaire** : 31 modules Python extraits de `jarvis.py` (6592 → 4633 L) · `audio_dsp.py` (508 L, bloc DSP) · `jarvis.css` éclaté en 8 fichiers `static/css/` · **refactor JS 2026-05-14** : `jarvis_main.js` 7828 → 4013 L (−49%), **11 modules** extraits dans `static/js/`
- **Tests E2E** : 25 tests Playwright (dont 2 smoke tests LLM `/api/chat`)

| Commande | Rôle | Pré-requis |
|----------|------|------------|
| `npm test` | Suite Playwright E2E (25 tests · ~1m48s) | JARVIS up sur :5000 |
| `npm run test:headed` | Tests E2E avec navigateur visible | JARVIS up |
| `npm run test:ui` | Mode UI interactif Playwright | JARVIS up |
| `npm run lint:js` | ESLint sur les fichiers JS applicatifs | — |
| `npm run lint:py` | Ruff sur `scripts/` | — |
| `ruff check scripts/` | Lint Python (config `ruff.toml`) | — |

### Pre-commit hooks (bloquants)

Depuis le chantier dette 2026-05-14, un hook `pre-commit` **bloque tout commit**
qui ne passe pas les linters. Configuration `.pre-commit-config.yaml` — hooks
100% locaux (aucun téléchargement réseau) :
- **ruff-check** : lint Python sur les `*.py` modifiés
- **eslint** : lint JS sur les fichiers applicatifs `static/`

Installation après un clone / une réinstallation : `pre-commit install`
Bypass exceptionnel (commit urgent) : `git commit --no-verify`

Tests E2E couverts (`tests/e2e/` · **25 tests** · 11 fichiers spec) :
- **boot** · page charge sans erreur console · 7 tabs rendus
- **api** · `/api/health` · `/api/mode` GET · cycle mode soc↔general (REST)
- **tabs** · navigation Monitor / SETTINGS / DSP AUDIO
- **chat-ui** · tab JARVIS AI actif par défaut · `#user-input` éditable
- **soc-tab** · compteurs (ban/fail/ok/ids) · actions list · chart day
- **dsp-voicelab** · DAT player buttons · 4 engines TTS · A/B slots
- **settings-tasks** · facts list + prompt badge · task creation form
- **mode-ui** · clic boutons #btn-mode-general/soc → propagation `/api/mode` (UI ↔ backend)
- **modals** · DAT/MIXER modals open/close cycle complet
- **dsp-interactive** · sliders EQ low/high/air → labels mis à jour en temps réel
- **chat-llm-smoke** · 2 smoke tests LLM — flux SSE réel `/api/chat` (tokens + done:true) + capture historique
