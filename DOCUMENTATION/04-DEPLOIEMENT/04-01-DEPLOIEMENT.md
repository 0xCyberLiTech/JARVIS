---
title: "ProcÃ©dure de dÃ©ploiement (production)"
code: "JARVIS-DOC-04-01"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "DÃ©ploiement"
mots_cles: ["deploiement", "production", "setup", "install"]
---

# JARVIS â€” ProcÃ©dure de DÃ©ploiement, Exploitation & AmÃ©liorations

> Version 3.3 â€” Mai 2026 (mise Ã  jour 2026-05-14 â€” chantier dette technique)
> Machine cible : Windows 11 Pro Â· RTX 5080 (Blackwell 16 GB GDDR7, sm_120) Â· Python 3.11

---

## 1. PRÃ‰REQUIS

### 1.1 Logiciels obligatoires

| Logiciel | Version min | RÃ´le |
|----------|-------------|------|
| Python | 3.11 | Runtime backend Flask |
| Ollama | DerniÃ¨re | Serveur LLM local |
| CUDA Toolkit | 12.x | AccÃ©lÃ©ration GPU |
| Edge-TTS | auto-install | Voix Microsoft neurale (en ligne) |

### 1.2 VÃ©rification de l'environnement

```powershell
python --version          # doit afficher 3.11.x
ollama --version          # doit rÃ©pondre
nvidia-smi                # RTX 5080 visible
```

### 1.3 ModÃ¨les Ollama installÃ©s

```bash
ollama pull phi4:14b              # mode SOC dÃ©faut (keep_alive 24h Â· 9.1 GB)
ollama pull gemma4:latest         # mode GÃ‰NÃ‰RAL + VOCAL + vision (multimodal Â· ~9.6 GB)
ollama pull qwen2.5-coder:14b     # mode CODE Â· dev srv-dev-1 (9.0 GB)
ollama pull mxbai-embed-large     # embeddings RAG (obligatoire Â· 1024 dims Â· 0.7 GB)
```

> âš  SupprimÃ©s : phi4-reasoning:plus Â· qwen2.5:14b Â· deepseek-r1:14b Â· llava-phi3:latest (2026-05-08) Â· nomic-embed-text (2026-05-10)

---

## 2. INSTALLATION INITIALE

### 2.1 Structure du projet

```
JARVIS/
â”œâ”€â”€ scripts/
â”‚   â”œâ”€â”€ jarvis.py                  â† orchestrateur Flask (~150 routes Â· 33 modules Python extraits)
â”‚   â”œâ”€â”€ blueprints/
â”‚   â”‚   â””â”€â”€ soc.py                 â† Blueprint SOC Â· SSH 4 hÃ´tes
â”‚   â”œâ”€â”€ jarvis_mcp_server.py       â† MCP bridge Claude Code â†” JARVIS (12 outils)
â”‚   â”œâ”€â”€ templates/
â”‚   â”‚   â”œâ”€â”€ jarvis.html            â† shell Jinja2 (204 lignes Â· 0 handler inline)
â”‚   â”‚   â”œâ”€â”€ tabs/                  â† 8 onglets modulaires
â”‚   â”‚   â””â”€â”€ partials/modals.html
â”‚   â”œâ”€â”€ static/
â”‚   â”‚   â”œâ”€â”€ jarvis_main.js         â† point d'entrÃ©e JS (refactor JS terminÃ© Â· 18 modules)
â”‚   â”‚   â”œâ”€â”€ jarvis_mixing.js       â† DSP mixer (1375 lignes)
â”‚   â”‚   â”œâ”€â”€ recorder.js            â† DAT RECORDER R-1 IIFE (660 lignes)
â”‚   â”‚   â”œâ”€â”€ voice_print.js         â† Voice Print v2 IIFE (852 lignes)
â”‚   â”‚   â”œâ”€â”€ js/                    â† 11 modules extraits : terminal_code Â· voice_lab Â· stt Â· tasks_tab Â· welcome Â· eq_parametric Â· eq_music Â· audio_mire Â· audio_viz Â· settings_llm Â· dsp_audio
â”‚   â”‚   â””â”€â”€ css/                   â† 8 fichiers CSS par secteur (ex-jarvis.css 5270L Â· chantier 2026-05-14)
â”‚   â”œâ”€â”€ jarvis_llm_params.json     â† paramÃ¨tres LLM persistÃ©s
â”‚   â”œâ”€â”€ jarvis_prompt_profiles.json â† 7 profils (Qwen2.5/DeepSeek/LLaVA/SOC-Rapide/Infra supprimÃ©s)
â”‚   â”œâ”€â”€ jarvis_dsp_params.json     â† paramÃ¨tres DSP audio
â”‚   â”œâ”€â”€ jarvis_model.json          â† modÃ¨le actif Ollama
â”‚   â”œâ”€â”€ jarvis_memory.json         â† mÃ©moire contextuelle JARVIS
â”‚   â”œâ”€â”€ jarvis_welcome.json        â† texte preloader d'accueil
â”‚   â”œâ”€â”€ voices/                    â† modÃ¨les Piper TTS local
â”‚   â”‚   â””â”€â”€ fr_FR-upmc-medium.onnx
â”‚   â””â”€â”€ stop_jarvis.bat            â† arrÃªt forcÃ© du serveur
â”œâ”€â”€ logs/
â”‚   â””â”€â”€ tts.log                    â† logs TTS rotation 50KBÃ—3
â”œâ”€â”€ models/
â”‚   â””â”€â”€ tts_models/                â† XTTS v2 (coqui-tts)
â”œâ”€â”€ docs/                          â† documentation technique
â”œâ”€â”€ README.md
â””â”€â”€ MEMORY.md
```

### 2.2 DÃ©pendances Python

Les packages s'installent automatiquement au premier dÃ©marrage via `install()`.
Pour un environnement isolÃ© (recommandÃ©) :

```bash
python -m venv .venv
.venv\Scripts\activate
pip install flask pynvml psutil requests edge-tts playsound==1.2.2 pydub numpy scipy
pip install faster-whisper pyttsx3        # STT local + TTS SAPI5
# Piper TTS : tÃ©lÃ©charger via l'UI (onglet DSP â†’ moteur voix)
```

### 2.3 Provider IA

JARVIS utilise **Ollama local uniquement**.

```json
{ "base_url": "http://localhost:11434", "model": "phi4:14b" }
```

Le modÃ¨le actif est persistÃ© dans `jarvis_model.json`.

---

## 3. DÃ‰MARRAGE

### 3.1 DÃ©marrage standard

```bat
cd c:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\scripts
python jarvis.py
```

Le navigateur s'ouvre automatiquement sur `http://localhost:5000`.

### 3.2 DÃ©marrage Ollama (si non lancÃ© en service)

```bat
ollama serve
```

Ollama doit Ã©couter sur `http://localhost:11434` avant de lancer JARVIS.

### 3.3 VÃ©rification dÃ©marrage

```powershell
curl http://localhost:5000          # Flask actif ?
curl http://localhost:11434/api/tags  # Ollama actif ?
```

Dans l'UI â†’ onglet Monitor â†’ toutes les jauges GPU vertes = RTX 5080 dÃ©tectÃ©e.

---

## 4. ARRÃŠT

### 4.1 ArrÃªt propre

`Ctrl+C` dans le terminal Python.

### 4.2 ArrÃªt forcÃ© (port bloquÃ©)

```bat
c:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\scripts\stop_jarvis.bat
```

---

## 5. EXPLOITATION QUOTIDIENNE

### 5.1 Cycle de vie normal

```
Matin    â†’ python jarvis.py            (preloader JARVIS animÃ©)
Usage    â†’ Chat IA / DSP / Audio Editor / Terminal / Monitor
Soir     â†’ Ctrl+C  ou  stop_jarvis.bat
```

### 5.2 Logs et historique

```
logs/jarvis.log          â† toutes les conversations horodatÃ©es
```

Rotation manuelle :
```bat
copy logs\jarvis.log logs\jarvis_%date:~-4%%date:~3,2%%date:~0,2%.log
echo. > logs\jarvis.log
```

### 5.3 Backup des JSON de configuration

| Fichier | Contenu critique |
|---------|-----------------|
| `jarvis_memory.json` | MÃ©moire contextuelle IA |
| `jarvis_welcome.json` | Texte preloader personnalisÃ© |
| `jarvis_llm_params.json` | PrÃ©rÃ©glages LLM choisis |
| `jarvis_dsp_params.json` | PrÃ©rÃ©glages DSP audio |
| `jarvis_model.json` | ModÃ¨le actif Ollama |

Backup rapide :
```bat
xcopy scripts\*.json backup\%date:~-4%%date:~3,2%%date:~0,2%\ /Y
```

### 5.4 Mise Ã  jour des modÃ¨les Ollama

```bash
ollama pull phi4:14b              # met Ã  jour
ollama pull gemma4:latest         # met Ã  jour
ollama pull qwen2.5-coder:14b     # met Ã  jour
ollama pull mxbai-embed-large     # met Ã  jour
ollama list                       # liste modÃ¨les installÃ©s
ollama rm <modele>                # supprimer inutilisÃ©
```

### 5.5 Moteurs TTS disponibles

| Moteur | Connexion | QualitÃ© | Config |
|--------|-----------|---------|--------|
| `edge` | En ligne | TrÃ¨s haute | fr-CA-AntoineNeural (**dÃ©faut**) |
| `kokoro` | Hors-ligne | Haute neural | ff_siwis (**fallback auto si internet KO**) |
| `xtts` | Hors-ligne | Studio | 58 voix + voice prints (XTTS v2 coqui-tts) |
| `piper` | Hors-ligne | Haute | fr_FR-upmc-medium.onnx |
| `sapi` | Hors-ligne | Moyenne | Microsoft Hortense FR |

**ChaÃ®ne fallback automatique** : edge â†’ Kokoro â†’ Piper â†’ SAPI5
**Boucle connectivitÃ©** : vÃ©rifie `speech.platform.bing.com:443` toutes les 10s â€” bascule auto Kokoro si internet KO, repasse edge dÃ¨s retour.

Changer via UI (onglet DSP â†’ panneau voix) ou `jarvis_dsp_params.json` â†’ `tts_engine`.

---

## 6. ROUTES API â€” RÃ‰FÃ‰RENCE RAPIDE

| Route | MÃ©thode | Description |
|-------|---------|-------------|
| `/` | GET | UI principale |
| `/api/stats` | GET | CPU / RAM / GPU / disques (polling 2s) |
| `/api/chat` | POST | Chat LLM streaming SSE + tool calling |
| `/api/tts` | POST | Text-to-speech â†’ MP3/WAV |
| `/api/speak` | POST | Lecture vocale directe (DSP stÃ©rÃ©o) |
| `/api/stt` | POST | Transcription audio â†’ texte (Whisper) |
| `/api/stt/status` | GET | Ã‰tat moteur STT |
| `/api/audio/process` | POST | Traitement fichier audio (EQ, denoise, fade, compresseur, stereo, gain) |
| `/api/terminal` | POST | ExÃ©cution commande shell (cd supportÃ©) |
| `/api/terminal/cwd` | GET | Working directory courant |
| `/api/files/drives` | GET | Lecteurs dÃ©tectÃ©s automatiquement |
| `/api/files/ls` | GET | Listing plat 1 niveau |
| `/api/files/tree` | GET | Arborescence dossier |
| `/api/files/read` | GET | Lire un fichier |
| `/api/files/write` | POST | Sauvegarder un fichier |
| `/api/files/mkdir` | POST | CrÃ©er un dossier |
| `/api/llm-params` | GET/POST | ParamÃ¨tres LLM |
| `/api/llm-params/reset-prompt` | GET/POST | Reset prompt systÃ¨me |
| `/api/dsp-params` | GET/POST | ParamÃ¨tres DSP audio |
| `/api/models` | GET/POST | ModÃ¨les Ollama disponibles |
| `/api/voices` | GET/POST | Voix edge-tts |
| `/api/tts/local/voices` | GET | Voix Piper disponibles |
| `/api/tts/local/download` | POST | TÃ©lÃ©charger modÃ¨le Piper |
| `/api/provider` | GET/POST | Provider IA + clÃ©s |
| `/api/tasks` | GET/POST | Liste/crÃ©er tÃ¢ches |
| `/api/tasks/<id>` | DELETE | Supprimer tÃ¢che |
| `/api/tasks/<id>/run` | POST | ExÃ©cuter une tÃ¢che |
| `/api/welcome` | GET/POST | Texte preloader |
| `/api/welcome/reset` | POST | Reset preloader dÃ©faut |
| `/api/welcome/evolve` | POST | IA enrichit le texte d'accueil |
| `/api/memory` | GET/POST/DELETE | MÃ©moire contextuelle |
| `/api/sysdiag` | GET | Diagnostic systÃ¨me complet |
| `/api/web-test` | GET | Test connectivitÃ© + DDG/Wikipedia |
| `/api/prompt-profiles` | GET/POST/DELETE | Profils prompt systÃ¨me |
| `/api/gpu` | GET | Stats GPU RTX 5080 (VRAM, P-state, wattsâ€¦) |
| `/api/ping` | POST | Ping une IP/host distant |
| `/api/security` | GET | Journal blocklist LLM (garde-fou) |
| `/api/security/clear` | POST | Vide le journal blocklist LLM |
| `/api/soc/ban-ip` | POST | Ban une IP via CrowdSec sur srv-nginx |
| `/api/soc/unban-ip` | POST | LÃ¨ve le ban d'une IP CrowdSec |
| `/api/soc/restart-service` | POST | RedÃ©marre un service autorisÃ© (nginx/crowdsec/fail2banâ€¦) |
| `/api/soc/actions` | GET | Journal des opÃ©rations proactives SOC |
| `/api/soc/actions/clear` | POST | Vide le journal proactif |
| `/api/rag/status` | GET | Ã‰tat index RAG (chunks, sources, modÃ¨le) |
| `/api/rag/index-file` | POST | Indexer un fichier dans le RAG |
| `/api/rag/note` | POST | MÃ©moriser une note (RAG) |
| `/api/rag/clear` | DELETE | Vider l'index RAG |
| `/api/xtts/speakers` | GET | Liste voix XTTS v2 (cache + RAM) |
| `/api/xtts/load` | POST | Forcer chargement modÃ¨le XTTS |
| `/api/voice/analyse` | POST | Analyse empreinte vocale (librosa) |
| `/api/voice/prints` | GET | Liste voice prints enregistrÃ©s |
| `/api/memory-summary` | GET/DELETE | RÃ©sumÃ©s mÃ©moire long terme |
| `/api/memory/summarize-session` | POST | RÃ©sumÃ© session en cours (appelÃ© avant arrÃªt) |
| `/api/facts` | GET/POST | Faits persistÃ©s (mÃ©moire JARVIS) |
| `/api/boot-id` | GET | ID de dÃ©marrage (change Ã  chaque restart Flask) |
| `/api/mode` | GET/POST | Mode LLM actif (soc/general/code/code_reasoning) |
| `/api/soc/heartbeat` | POST | Signal dashboard ouvert (TTL 90s) |
| `/api/soc/ip-history` | POST | Historique 30j d'une IP (CrowdSec) |
| `/api/soc/context` | GET | Contexte SOC live (rÃ©sumÃ© monitoring.json) |
| `/api/vram` | GET | VRAM utilisÃ©e + modÃ¨le actif (segment VRAM panel) |

---

## 7. PARAMÃˆTRES LLM â€” PRESETS

Fichier : `scripts/jarvis_llm_params.json`

| Preset | temperature | num_predict | num_ctx | Use case |
|--------|-------------|-------------|---------|----------|
| RAPIDE | 0.5 | 512 | 1024 | RÃ©ponses courtes, faible latence |
| Ã‰QUILIBRÃ‰ | 0.7 | 1024 | 2048 | Usage quotidien (dÃ©faut) |
| QUALITÃ‰ | 0.82 | 2048 | 4096 | RÃ©daction, analyse longue |

---

## 8. DÃ‰PANNAGE

### 8.1 Port 5000 dÃ©jÃ  utilisÃ©

```bat
stop_jarvis.bat
python jarvis.py
```

### 8.2 Ollama ne rÃ©pond pas

```bash
ollama serve          # relancer manuellement
```

### 8.3 RTX 5080 non dÃ©tectÃ©e (Monitor â€” jauges Ã  0)

- VÃ©rifier drivers NVIDIA Ã  jour + CUDA 12.x installÃ©
- `nvidia-smi` doit lister la RTX 5080

### 8.4 TTS muet (mode edge)

- VÃ©rifier connexion internet (edge-tts requiert accÃ¨s Microsoft)
- Basculer sur `sapi` ou `piper` (hors-ligne) via UI DSP

### 8.5 Welcome modal visible partout (bug CSS)

Cause : commentaire CSS imbriquÃ© `/* ... /* ... */ ... */` cassant le parser.
Fix : supprimer tout bloc `/* */` imbriquÃ© dans le CSS de `jarvis.html`.
Contournement : `Ctrl+Shift+R`.

### 8.6 Sliders gradient non synchronisÃ©s (curseur dÃ©tachÃ©)

Cause : `--pct` ou `--f-pct` non mis Ã  jour.
Fix : s'assurer que le listener `DOMContentLoaded` avec `_syncRangeSlider` est prÃ©sent.
Pour les sliders crÃ©Ã©s dynamiquement : appeler `window._syncRangeSlider(el)` manuellement.

### 8.7 EQ Audio Editor sans effet au playback

VÃ©rifier que `_aeInitChain()` est appelÃ© dans `openAudioEditor()` et que `aePlay()` route vers `_aeEqNodes[0]`.

---

## 9. BUGS CONNUS

| # | Composant | Description | PrioritÃ© |
|---|-----------|-------------|----------|
| 1 | Mixer / DSP | Talkover : musique DAT non attÃ©nuÃ©e quand JARVIS parle | ðŸ”´ Fonctionnel |
| 2 | VU-meter | Trait vertical parasite sur fond noir | ðŸŸ¡ Visuel |
| 3 | Audio Editor | Bouton FERMER hors du thÃ¨me JARVIS | ðŸŸ¢ CosmÃ©tique |
| 4 | _compress() | Boucle Python pure O(n) sample-by-sample â€” lent sur longs fichiers audio | ðŸŸ¢ Performance |
| 5 | api_terminal | shell=True intentionnel â€” pas d'injection possible depuis UI (127.0.0.1 seulement depuis 2026-03-28) | â„¹ï¸ Info |

---

## 10. ROADMAP â€” ITEMS OUVERTS

> DÃ©tail complet dans `docs/REFERENCE-TECHNIQUE.md` (section 10).

| PrioritÃ© | Item |
|----------|------|
| ðŸ”µ | Vision active SOC â€” analyse screenshot |
| ðŸ”µ | Wake word â€” activation vocale sans clic |
| ðŸŸ¡ | SSH write ops â€” apt upgrade Â· restart Ã©tendu (validation) |

**Bugs connus (non bloquants)** :

| # | Composant | Description |
|---|-----------|-------------|
| 1 | Mixer / DSP | Talkover : musique DAT non attÃ©nuÃ©e quand JARVIS parle |
| 2 | VU-meter | Trait vertical parasite sur fond noir |
| 3 | Audio Editor | Bouton FERMER hors thÃ¨me JARVIS |

---

## 11. ROADMAP VERSIONING

```
v3.0  (livrÃ©)   â€” UI holographique unifiÃ©e, Monitor RTX 5080, preloader, TTS DSP stÃ©rÃ©o
v3.1  (livrÃ©)   â€” DSP Haas stÃ©rÃ©o, AI AUDIO RACK hardware, Audio Editor, EQ 5 bandes, STT Whisper, TTS local Piper/SAPI
v3.2  (livrÃ©)   â€” ChaÃ®ne Web Audio rÃ©elle (EQ+Compresseur live), Voice Lab redesign, fond global unifiÃ©, audit HTML propre
v3.3  (en cours)
  âœ… Routing 3 branches SOC (phi4:14b) / GÃ‰NÃ‰RAL+VOCAL (gemma4) / CODE (qwen2.5-coder) + switch manuel
  âœ… SSH outils lecture seule (4 hÃ´tes) + _BLOCKED_SSH
  âœ… VM multi-stop/start (bypass LLM direct SSH Proxmox)
  âœ… MCP 8 outils (Claude Code â†” JARVIS bridge) + RAG auto-refresh 6h
  âœ… RAG Live SOC (logs SSH temps rÃ©el dans contexte LLM)
  âœ… Vision gemma4 multimodal (remplace llava-phi3 â€” appel unique)
  âœ… XTTS v2 58 voix + voice prints
  âœ… STT large-v3-turbo + initial_prompt vocabulaire SOC
  âœ… NDT 100/100 â€” dette zÃ©ro absolue script auto Â· session 26 (CRITIQUE+MOYEN+FAIBLE rÃ©solus)
  âœ… ThreatScore 30j historique â€” sparkline SVG + modal Canvas
  âœ… Rapport quotidien vocal + corrÃ©lation temporelle campagnes /24
  âœ… Proxmox API directe â€” _pve_fetch_state() Â· ticket+token auth Â· cache 30s
  âœ… Terminal CODE xterm.js + WebSocket PTY SSH srv-dev-1
  âœ… Phase 3 split monolithe Python â€” 30 modules Â· session 33b (2026-05-13)
  âœ… Session 33c split JS partiel â€” recorder.js + voice_print.js extraits Â· jarvis_main.js -14.4%
  âœ… Chantier dette technique 2026-05-14/15 â€” Ruff 98â†’0 + git local + pre-commit/pre-push hooks + ruff.toml + CSS 8 fichiers + audio_dsp.py + suite pytest + refactor JS terminÃ© (âˆ’98,1%) + fix perf IPv6 (-97% latence interne) + **circuit breaker Ollama 8 call-sites** + **prÃ©-warm Kokoro CUDA au boot** + **profiling TTS dÃ©taillÃ©**
  âœ… Audit dette complet 2026-05-22 â€” score/lignes/tests/coverage â†’ BILAN-TECHNIQUE.md Â§0
  â¬œ SSH write ops partielles â€” apt upgrade Â· restart service
  âœ… Refactor JS terminÃ© (jarvis_main.js âˆ’98,1% Â· 18 modules)
  âœ… Tests unitaires Python (suite pytest) Â· profiling performance (`profile_perf.py` + `profile_tts.py`)
v3.4  (moyen)   â€” WebSocket Monitor, historique chat SQLite, graphiques Chart.js, alerte GPU
v4.0  (long)    â€” Service Windows NSSM, Docker Compose, HTTPS mkcert, SSH write ops matures
```

---

## 12. Ã‰TAT DES FICHIERS (mis Ã  jour 2026-05-22)

> Tailles de fichiers et coverage â†’ source unique [`../BILAN-TECHNIQUE.md` Â§0](../BILAN-TECHNIQUE.md).

| Fichier | RÃ´le |
|---------|------|
| `scripts/jarvis.py` | Orchestrateur Flask Â· ~150 routes Â· routing 4 branches SOC/GÃ‰NÃ‰RAL/CODE/CR Â· 33 modules extraits |
| **31 modules Python extraits** | Phase 3 + `audio_dsp.py` â€” voir [`ROUTING-JARVIS.md`](ROUTING-JARVIS.md) |
| `scripts/blueprints/soc.py` | Blueprint SOC Â· rsyslog v1.6.1 Â· SSH 4 hÃ´tes Â· cache 30s + fallback SSH |
| `scripts/jarvis_mcp_server.py` | 12 outils MCP Â· `jarvis_soc_ask` historique IP 30j Â· streamable-HTTP port 5010 |
| `scripts/templates/jarvis.html` | Shell Jinja2 Â· 0 handler inline Â· 8 onglets |
| `scripts/static/jarvis_main.js` | Point d'entrÃ©e JS Â· refactor terminÃ© Â· 18 modules extraits |
| `scripts/static/js/` | 18 modules JS â€” voir [`ROUTING-JARVIS.md`](ROUTING-JARVIS.md) |
| `scripts/static/css/` | 8 fichiers CSS par secteur |
| `scripts/static/css/` | 8 fichiers | âœ… ex-`jarvis.css` 5270L â†’ core/chat/dsp/terminal-taches/hud-welcome/rack/settings-soc/voicelab (chantier 2026-05-14) |
| `ruff.toml` Â· `.pre-commit-config.yaml` Â· `.gitignore` | â€” | âœ… chantier dette 2026-05-14 â€” git initialisÃ© (16 commits, 100% local) |
| `scripts/static/css/` (8 fichiers) | ex-5270 | âœ… dÃ©coupÃ© par secteur (chantier 2026-05-14) Â· NDT-CSS 0 |
| `scripts/jarvis_llm_params.json` | â€” | âœ… phi4:14b Â· num_ctx:8192 (SOC 16384â†’8192 le 2026-05-20, optim VRAM) Â· num_predict:4096 Â· temp:0.5 Â· top_k:40 |
| `scripts/jarvis_dsp_params.json` | â€” | âœ… tts_engine:edge Â· tts_default_engine:edge |
| `scripts/jarvis_model.json` | â€” | âœ… phi4:14b |
| `scripts/jarvis_prompt_profiles.json` | â€” | âœ… 7 profils Â· 3 RÃˆGLES ABSOLUES (Qwen2.5/DeepSeek/LLaVA/SOC-Rapide/Infra supprimÃ©s) |
| `scripts/jarvis_rag/meta.json` | â€” 599 chunks | âœ… MEMORY.mdÃ—2 (535) + CIRCUIT_SOC_JARVIS (49) + RUNBOOK (15) â€” seuil 0.35 |
| `scripts/jarvis_rag/embeddings.npy` | â€” | âœ… mxbai-embed-large float32 Â· 1024 dims |
| `scripts/voices/fr_FR-upmc-medium.onnx` | â€” 74 MB | âœ… Piper TTS |
| `models/tts_models/.../xtts_v2/` | â€” | âœ… XTTS v2 Â· 58 voix |

---

## 13. CONTACTS & RÃ‰FÃ‰RENCES

- Projet : `c:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\`
- Logs : `logs\jarvis.log`
- UI : `http://localhost:5000`
- Ollama API : `http://localhost:11434`
- Memory Claude : `C:\Users\mmsab\.claude\projects\c--Users-mmsab-Documents-JARVIS\memory\`
- CrÃ©ateur interface : **0xcyberlitech**

---

*Document mis Ã  jour le 2026-05-14 â€” v3.3*

