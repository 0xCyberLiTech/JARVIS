# JARVIS — Procédure de Déploiement, Exploitation & Améliorations

> Version 3.3 — Mai 2026 (mise à jour 2026-05-14 — chantier dette technique)
> Machine cible : Windows 11 Pro · RTX 5080 (Blackwell 16 GB GDDR7, sm_120) · Python 3.11

---

## 1. PRÉREQUIS

### 1.1 Logiciels obligatoires

| Logiciel | Version min | Rôle |
|----------|-------------|------|
| Python | 3.11 | Runtime backend Flask |
| Ollama | Dernière | Serveur LLM local |
| CUDA Toolkit | 12.x | Accélération GPU |
| Edge-TTS | auto-install | Voix Microsoft neurale (en ligne) |

### 1.2 Vérification de l'environnement

```powershell
python --version          # doit afficher 3.11.x
ollama --version          # doit répondre
nvidia-smi                # RTX 5080 visible
```

### 1.3 Modèles Ollama installés

```bash
ollama pull phi4:14b              # mode SOC défaut (keep_alive 24h · 9.1 GB)
ollama pull gemma4:latest         # mode GÉNÉRAL + VOCAL + vision (multimodal · ~9.6 GB)
ollama pull qwen2.5-coder:14b     # mode CODE · dev srv-dev-1 (9.0 GB)
ollama pull mxbai-embed-large     # embeddings RAG (obligatoire · 1024 dims · 0.7 GB)
```

> ⚠ Supprimés : phi4-reasoning:plus · qwen2.5:14b · deepseek-r1:14b · llava-phi3:latest (2026-05-08) · nomic-embed-text (2026-05-10)

---

## 2. INSTALLATION INITIALE

### 2.1 Structure du projet

```
JARVIS/
├── scripts/
│   ├── jarvis.py                  ← serveur Flask principal (~4850 lignes · 72 routes · NDT 10/10)
│   ├── blueprints/
│   │   └── soc.py                 ← Blueprint SOC (1555 lignes) · SSH 4 hôtes
│   ├── jarvis_mcp_server.py       ← MCP bridge Claude Code ↔ JARVIS (8 outils)
│   ├── templates/
│   │   ├── jarvis.html            ← shell Jinja2 (204 lignes · 0 handler inline)
│   │   ├── tabs/                  ← 8 onglets modulaires
│   │   └── partials/modals.html
│   ├── static/
│   │   ├── jarvis_main.js         ← JS principal (7893 lignes · ⚠ reste majoritairement monolithique)
│   │   ├── jarvis_mixing.js       ← DSP mixer (1375 lignes)
│   │   ├── recorder.js            ← DAT RECORDER R-1 IIFE (660 lignes)
│   │   ├── voice_print.js         ← Voice Print v2 IIFE (852 lignes)
│   │   ├── js/                    ← modules extraits : terminal_code.js · voice_lab.js · stt.js (refactor 2026-05-14)
│   │   └── css/                   ← 8 fichiers CSS par secteur (ex-jarvis.css 5270L · chantier 2026-05-14)
│   ├── jarvis_llm_params.json     ← paramètres LLM persistés
│   ├── jarvis_prompt_profiles.json ← 7 profils (Qwen2.5/DeepSeek/LLaVA/SOC-Rapide/Infra supprimés)
│   ├── jarvis_dsp_params.json     ← paramètres DSP audio
│   ├── jarvis_model.json          ← modèle actif Ollama
│   ├── jarvis_memory.json         ← mémoire contextuelle JARVIS
│   ├── jarvis_welcome.json        ← texte preloader d'accueil
│   ├── voices/                    ← modèles Piper TTS local
│   │   └── fr_FR-upmc-medium.onnx
│   └── stop_jarvis.bat            ← arrêt forcé du serveur
├── logs/
│   └── tts.log                    ← logs TTS rotation 50KB×3
├── models/
│   └── tts_models/                ← XTTS v2 (coqui-tts)
├── docs/                          ← documentation technique
├── README.md
└── MEMORY.md
```

### 2.2 Dépendances Python

Les packages s'installent automatiquement au premier démarrage via `install()`.
Pour un environnement isolé (recommandé) :

```bash
python -m venv .venv
.venv\Scripts\activate
pip install flask pynvml psutil requests edge-tts playsound==1.2.2 pydub numpy scipy
pip install faster-whisper pyttsx3        # STT local + TTS SAPI5
# Piper TTS : télécharger via l'UI (onglet DSP → moteur voix)
```

### 2.3 Provider IA

JARVIS utilise **Ollama local uniquement**.

```json
{ "base_url": "http://localhost:11434", "model": "phi4:14b" }
```

Le modèle actif est persisté dans `jarvis_model.json`.

---

## 3. DÉMARRAGE

### 3.1 Démarrage standard

```bat
cd c:\Users\mmsab\Documents\JARVIS\scripts
python jarvis.py
```

Le navigateur s'ouvre automatiquement sur `http://localhost:5000`.

### 3.2 Démarrage Ollama (si non lancé en service)

```bat
ollama serve
```

Ollama doit écouter sur `http://localhost:11434` avant de lancer JARVIS.

### 3.3 Vérification démarrage

```powershell
curl http://localhost:5000          # Flask actif ?
curl http://localhost:11434/api/tags  # Ollama actif ?
```

Dans l'UI → onglet Monitor → toutes les jauges GPU vertes = RTX 5080 détectée.

---

## 4. ARRÊT

### 4.1 Arrêt propre

`Ctrl+C` dans le terminal Python.

### 4.2 Arrêt forcé (port bloqué)

```bat
c:\Users\mmsab\Documents\JARVIS\scripts\stop_jarvis.bat
```

---

## 5. EXPLOITATION QUOTIDIENNE

### 5.1 Cycle de vie normal

```
Matin    → python jarvis.py            (preloader JARVIS animé)
Usage    → Chat IA / DSP / Audio Editor / Terminal / Monitor
Soir     → Ctrl+C  ou  stop_jarvis.bat
```

### 5.2 Logs et historique

```
logs/jarvis.log          ← toutes les conversations horodatées
```

Rotation manuelle :
```bat
copy logs\jarvis.log logs\jarvis_%date:~-4%%date:~3,2%%date:~0,2%.log
echo. > logs\jarvis.log
```

### 5.3 Backup des JSON de configuration

| Fichier | Contenu critique |
|---------|-----------------|
| `jarvis_memory.json` | Mémoire contextuelle IA |
| `jarvis_welcome.json` | Texte preloader personnalisé |
| `jarvis_llm_params.json` | Préréglages LLM choisis |
| `jarvis_dsp_params.json` | Préréglages DSP audio |
| `jarvis_model.json` | Modèle actif Ollama |

Backup rapide :
```bat
xcopy scripts\*.json backup\%date:~-4%%date:~3,2%%date:~0,2%\ /Y
```

### 5.4 Mise à jour des modèles Ollama

```bash
ollama pull phi4:14b              # met à jour
ollama pull gemma4:latest         # met à jour
ollama pull qwen2.5-coder:14b     # met à jour
ollama pull mxbai-embed-large     # met à jour
ollama list                       # liste modèles installés
ollama rm <modele>                # supprimer inutilisé
```

### 5.5 Moteurs TTS disponibles

| Moteur | Connexion | Qualité | Config |
|--------|-----------|---------|--------|
| `edge` | En ligne | Très haute | fr-CA-AntoineNeural (**défaut**) |
| `kokoro` | Hors-ligne | Haute neural | ff_siwis (**fallback auto si internet KO**) |
| `xtts` | Hors-ligne | Studio | 58 voix + voice prints (XTTS v2 coqui-tts) |
| `piper` | Hors-ligne | Haute | fr_FR-upmc-medium.onnx |
| `sapi` | Hors-ligne | Moyenne | Microsoft Hortense FR |

**Chaîne fallback automatique** : edge → Kokoro → Piper → SAPI5
**Boucle connectivité** : vérifie `speech.platform.bing.com:443` toutes les 10s — bascule auto Kokoro si internet KO, repasse edge dès retour.

Changer via UI (onglet DSP → panneau voix) ou `jarvis_dsp_params.json` → `tts_engine`.

---

## 6. ROUTES API — RÉFÉRENCE RAPIDE

| Route | Méthode | Description |
|-------|---------|-------------|
| `/` | GET | UI principale |
| `/api/stats` | GET | CPU / RAM / GPU / disques (polling 2s) |
| `/api/chat` | POST | Chat LLM streaming SSE + tool calling |
| `/api/tts` | POST | Text-to-speech → MP3/WAV |
| `/api/speak` | POST | Lecture vocale directe (DSP stéréo) |
| `/api/stt` | POST | Transcription audio → texte (Whisper) |
| `/api/stt/status` | GET | État moteur STT |
| `/api/audio/process` | POST | Traitement fichier audio (EQ, denoise, fade, compresseur, stereo, gain) |
| `/api/terminal` | POST | Exécution commande shell (cd supporté) |
| `/api/terminal/cwd` | GET | Working directory courant |
| `/api/files/drives` | GET | Lecteurs détectés automatiquement |
| `/api/files/ls` | GET | Listing plat 1 niveau |
| `/api/files/tree` | GET | Arborescence dossier |
| `/api/files/read` | GET | Lire un fichier |
| `/api/files/write` | POST | Sauvegarder un fichier |
| `/api/files/mkdir` | POST | Créer un dossier |
| `/api/llm-params` | GET/POST | Paramètres LLM |
| `/api/llm-params/reset-prompt` | GET/POST | Reset prompt système |
| `/api/dsp-params` | GET/POST | Paramètres DSP audio |
| `/api/models` | GET/POST | Modèles Ollama disponibles |
| `/api/voices` | GET/POST | Voix edge-tts |
| `/api/tts/local/voices` | GET | Voix Piper disponibles |
| `/api/tts/local/download` | POST | Télécharger modèle Piper |
| `/api/provider` | GET/POST | Provider IA + clés |
| `/api/tasks` | GET/POST | Liste/créer tâches |
| `/api/tasks/<id>` | DELETE | Supprimer tâche |
| `/api/tasks/<id>/run` | POST | Exécuter une tâche |
| `/api/welcome` | GET/POST | Texte preloader |
| `/api/welcome/reset` | POST | Reset preloader défaut |
| `/api/welcome/evolve` | POST | IA enrichit le texte d'accueil |
| `/api/memory` | GET/POST/DELETE | Mémoire contextuelle |
| `/api/sysdiag` | GET | Diagnostic système complet |
| `/api/web-test` | GET | Test connectivité + DDG/Wikipedia |
| `/api/prompt-profiles` | GET/POST/DELETE | Profils prompt système |
| `/api/gpu` | GET | Stats GPU RTX 5080 (VRAM, P-state, watts…) |
| `/api/ping` | POST | Ping une IP/host distant |
| `/api/security` | GET | Journal blocklist LLM (garde-fou) |
| `/api/security/clear` | POST | Vide le journal blocklist LLM |
| `/api/soc/ban-ip` | POST | Ban une IP via CrowdSec sur srv-ngix |
| `/api/soc/unban-ip` | POST | Lève le ban d'une IP CrowdSec |
| `/api/soc/restart-service` | POST | Redémarre un service autorisé (nginx/crowdsec/fail2ban…) |
| `/api/soc/actions` | GET | Journal des opérations proactives SOC |
| `/api/soc/actions/clear` | POST | Vide le journal proactif |
| `/api/rag/status` | GET | État index RAG (chunks, sources, modèle) |
| `/api/rag/index-file` | POST | Indexer un fichier dans le RAG |
| `/api/rag/note` | POST | Mémoriser une note (RAG) |
| `/api/rag/clear` | DELETE | Vider l'index RAG |
| `/api/xtts/speakers` | GET | Liste voix XTTS v2 (cache + RAM) |
| `/api/xtts/load` | POST | Forcer chargement modèle XTTS |
| `/api/voice/analyse` | POST | Analyse empreinte vocale (librosa) |
| `/api/voice/prints` | GET | Liste voice prints enregistrés |
| `/api/memory-summary` | GET/DELETE | Résumés mémoire long terme |
| `/api/memory/summarize-session` | POST | Résumé session en cours (appelé avant arrêt) |
| `/api/facts` | GET/POST | Faits persistés (mémoire JARVIS) |
| `/api/boot-id` | GET | ID de démarrage (change à chaque restart Flask) |
| `/api/mode` | GET/POST | Mode LLM actif (soc/general/code) |
| `/api/soc/heartbeat` | POST | Signal dashboard ouvert (TTL 90s) |
| `/api/soc/ip-history` | POST | Historique 30j d'une IP (CrowdSec) |
| `/api/soc/context` | GET | Contexte SOC live (résumé monitoring.json) |
| `/api/vram` | GET | VRAM utilisée + modèle actif (segment VRAM panel) |

---

## 7. PARAMÈTRES LLM — PRESETS

Fichier : `scripts/jarvis_llm_params.json`

| Preset | temperature | num_predict | num_ctx | Use case |
|--------|-------------|-------------|---------|----------|
| RAPIDE | 0.5 | 512 | 1024 | Réponses courtes, faible latence |
| ÉQUILIBRÉ | 0.7 | 1024 | 2048 | Usage quotidien (défaut) |
| QUALITÉ | 0.82 | 2048 | 4096 | Rédaction, analyse longue |

---

## 8. DÉPANNAGE

### 8.1 Port 5000 déjà utilisé

```bat
stop_jarvis.bat
python jarvis.py
```

### 8.2 Ollama ne répond pas

```bash
ollama serve          # relancer manuellement
```

### 8.3 RTX 5080 non détectée (Monitor — jauges à 0)

- Vérifier drivers NVIDIA à jour + CUDA 12.x installé
- `nvidia-smi` doit lister la RTX 5080

### 8.4 TTS muet (mode edge)

- Vérifier connexion internet (edge-tts requiert accès Microsoft)
- Basculer sur `sapi` ou `piper` (hors-ligne) via UI DSP

### 8.5 Welcome modal visible partout (bug CSS)

Cause : commentaire CSS imbriqué `/* ... /* ... */ ... */` cassant le parser.
Fix : supprimer tout bloc `/* */` imbriqué dans le CSS de `jarvis.html`.
Contournement : `Ctrl+Shift+R`.

### 8.6 Sliders gradient non synchronisés (curseur détaché)

Cause : `--pct` ou `--f-pct` non mis à jour.
Fix : s'assurer que le listener `DOMContentLoaded` avec `_syncRangeSlider` est présent.
Pour les sliders créés dynamiquement : appeler `window._syncRangeSlider(el)` manuellement.

### 8.7 EQ Audio Editor sans effet au playback

Vérifier que `_aeInitChain()` est appelé dans `openAudioEditor()` et que `aePlay()` route vers `_aeEqNodes[0]`.

---

## 9. BUGS CONNUS

| # | Composant | Description | Priorité |
|---|-----------|-------------|----------|
| 1 | Mixer / DSP | Talkover : musique DAT non atténuée quand JARVIS parle | 🔴 Fonctionnel |
| 2 | VU-meter | Trait vertical parasite sur fond noir | 🟡 Visuel |
| 3 | Audio Editor | Bouton FERMER hors du thème JARVIS | 🟢 Cosmétique |
| 4 | _compress() | Boucle Python pure O(n) sample-by-sample — lent sur longs fichiers audio | 🟢 Performance |
| 5 | api_terminal | shell=True intentionnel — pas d'injection possible depuis UI (127.0.0.1 seulement depuis 2026-03-28) | ℹ️ Info |

---

## 10. ROADMAP — ITEMS OUVERTS

> Détail complet dans `docs/REFERENCE-TECHNIQUE.md` (section 10).

| Priorité | Item |
|----------|------|
| 🔵 | Vision active SOC — analyse screenshot |
| 🔵 | Wake word — activation vocale sans clic |
| 🟡 | SSH write ops — apt upgrade · restart étendu (validation) |

**Bugs connus (non bloquants)** :

| # | Composant | Description |
|---|-----------|-------------|
| 1 | Mixer / DSP | Talkover : musique DAT non atténuée quand JARVIS parle |
| 2 | VU-meter | Trait vertical parasite sur fond noir |
| 3 | Audio Editor | Bouton FERMER hors thème JARVIS |

---

## 11. ROADMAP VERSIONING

```
v3.0  (livré)   — UI holographique unifiée, Monitor RTX 5080, preloader, TTS DSP stéréo
v3.1  (livré)   — DSP Haas stéréo, AI AUDIO RACK hardware, Audio Editor, EQ 5 bandes, STT Whisper, TTS local Piper/SAPI
v3.2  (livré)   — Chaîne Web Audio réelle (EQ+Compresseur live), Voice Lab redesign, fond global unifié, audit HTML propre
v3.3  (en cours)
  ✅ Routing 3 branches SOC (phi4:14b) / GÉNÉRAL+VOCAL (gemma4) / CODE (qwen2.5-coder) + switch manuel
  ✅ SSH outils lecture seule (4 hôtes) + _BLOCKED_SSH
  ✅ VM multi-stop/start (bypass LLM direct SSH Proxmox)
  ✅ MCP 8 outils (Claude Code ↔ JARVIS bridge) + RAG auto-refresh 6h
  ✅ RAG Live SOC (logs SSH temps réel dans contexte LLM)
  ✅ Vision gemma4 multimodal (remplace llava-phi3 — appel unique)
  ✅ XTTS v2 58 voix + voice prints
  ✅ STT large-v3-turbo + initial_prompt vocabulaire SOC
  ✅ NDT 100/100 — dette zéro absolue script auto · session 26 (CRITIQUE+MOYEN+FAIBLE résolus)
  ✅ ThreatScore 30j historique — sparkline SVG + modal Canvas
  ✅ Rapport quotidien vocal + corrélation temporelle campagnes /24
  ✅ Proxmox API directe — _pve_fetch_state() · ticket+token auth · cache 30s
  ✅ Terminal CODE xterm.js + WebSocket PTY SSH srv-dev-1
  ✅ Phase 3 split monolithe Python — 30 modules · session 33b (2026-05-13)
  ✅ Session 33c split JS partiel — recorder.js + voice_print.js extraits · jarvis_main.js -14.4%
  ✅ Chantier dette technique 2026-05-14 — Ruff 98→0 + git initialisé (17 commits) + pre-commit hooks + ruff.toml + CSS 8 fichiers + audio_dsp.py + 2 smoke tests LLM + refactor JS partiel (3 modules) · score honnête global 78/100 (recalibré depuis 62 réel · +16)
  ⬜ SSH write ops partielles — apt upgrade · restart service
  🟡 Refactor JS — suite incrémentale (3/N modules faits · jarvis_main.js 8994→7893L · méthode validée)
  ⬜ Tests unitaires Python · profiling performance
v3.4  (moyen)   — WebSocket Monitor, historique chat SQLite, graphiques Chart.js, alerte GPU
v4.0  (long)    — Service Windows NSSM, Docker Compose, HTTPS mkcert, SSH write ops matures
```

---

## 12. ÉTAT DES FICHIERS (mis à jour 2026-05-14 · post-chantier dette technique)

| Fichier | Lignes | État |
|---------|--------|------|
| `scripts/jarvis.py` | **4633** | ✅ 75 routes · NDT 100/100 · routing **4 branches** SOC/GÉNÉRAL/CODE/CR · réduit via 31 modules extraits |
| **31 modules Python extraits** | **~3540** | ✅ Phase 3 (30 modules) + `audio_dsp.py` 508L (chantier 2026-05-14) — voir [`ROUTING-JARVIS.md`](ROUTING-JARVIS.md) |
| `scripts/blueprints/soc.py` | 1689 | ✅ rsyslog v1.6.1 · SSH 4 hôtes · `_ssh_base()` générique · fix race condition `_soc_actions_save` |
| `scripts/jarvis_mcp_server.py` | ~430 | ✅ **10 outils MCP** · JARVIS_HEADER · `jarvis_soc_ask` historique IP 30j · streamable-HTTP port 5010 |
| `scripts/templates/jarvis.html` | 211 | ✅ 0 handler inline · charge 8 `<link>` CSS + 4 `<script>` JS |
| `scripts/static/jarvis_main.js` | **7893** | ⚠ **reste majoritairement monolithique** · refactor JS partiel (8994→7893 · -12%) |
| `scripts/static/jarvis_mixing.js` | 1375 | ✅ DSP mixer stéréo |
| `scripts/static/js/` (3 modules) | 1138 | ✅ terminal_code.js 445L + voice_lab.js 580L + stt.js 113L (refactor 2026-05-14) |
| `scripts/static/recorder.js` | **660** | ✅ DAT RECORDER R-1 IIFE |
| `scripts/static/voice_print.js` | **852** | ✅ Voice Print v2 IIFE |
| `scripts/static/css/` | 8 fichiers | ✅ ex-`jarvis.css` 5270L → core/chat/dsp/terminal-taches/hud-welcome/rack/settings-soc/voicelab (chantier 2026-05-14) |
| `ruff.toml` · `.pre-commit-config.yaml` · `.gitignore` | — | ✅ chantier dette 2026-05-14 — git initialisé (5 commits, 100% local) |
| `scripts/static/css/` (8 fichiers) | ex-5270 | ✅ découpé par secteur (chantier 2026-05-14) · NDT-CSS 0 |
| `scripts/jarvis_llm_params.json` | — | ✅ phi4:14b · num_ctx:16384 · num_predict:4096 · temp:0.5 · top_k:40 |
| `scripts/jarvis_dsp_params.json` | — | ✅ tts_engine:edge · tts_default_engine:edge |
| `scripts/jarvis_model.json` | — | ✅ phi4:14b |
| `scripts/jarvis_prompt_profiles.json` | — | ✅ 7 profils · 3 RÈGLES ABSOLUES (Qwen2.5/DeepSeek/LLaVA/SOC-Rapide/Infra supprimés) |
| `scripts/jarvis_rag/meta.json` | — 599 chunks | ✅ MEMORY.md×2 (535) + CIRCUIT_SOC_JARVIS (49) + RUNBOOK (15) — seuil 0.35 |
| `scripts/jarvis_rag/embeddings.npy` | — | ✅ mxbai-embed-large float32 · 1024 dims |
| `scripts/voices/fr_FR-upmc-medium.onnx` | — 74 MB | ✅ Piper TTS |
| `models/tts_models/.../xtts_v2/` | — | ✅ XTTS v2 · 58 voix |

---

## 13. CONTACTS & RÉFÉRENCES

- Projet : `c:\Users\mmsab\Documents\JARVIS\`
- Logs : `logs\jarvis.log`
- UI : `http://localhost:5000`
- Ollama API : `http://localhost:11434`
- Memory Claude : `C:\Users\mmsab\.claude\projects\c--Users-mmsab-Documents-JARVIS\memory\`
- Créateur interface : **0xcyberlitech**

---

*Document mis à jour le 2026-05-10 — v3.3*
