# JARVIS — Guide de réinstallation Windows

> Document critique — à conserver dans les sauvegardes.
> Dernière mise à jour : 2026-05-14 — Chantier dette : git local + pre-commit hooks + ruff.toml + CSS 8 fichiers + audio_dsp.py · 31 modules Python · jarvis.py 4633L · refactor JS soir : jarvis_main.js 7828→4013 L, 11 modules static/js/

---

## Scripts automatiques

| Script | Rôle | Emplacement |
|--------|------|-------------|
| `backup-jarvis.ps1` | **Sauvegarde complète** → `D:\BACKUP-WINDOWS\` | `JARVIS\doc\` et `D:\BACKUP-WINDOWS\JARVIS\` |
| `install-jarvis.ps1` | **Réinstallation automatique** depuis backup | `JARVIS\doc\` et `D:\BACKUP-WINDOWS\JARVIS\` |

### backup-jarvis.ps1 — Ce qu'il sauvegarde

1. Fichiers JARVIS complets (scripts, html, configs, voices, start/stop scripts)
2. Clés SSH (`~/.ssh/` — id_nginx, id_clt, id_pa85, id_proxmox)
3. Mémoire Claude Code (`~/.claude/`)
4. **Modèles Ollama** (`~/.ollama/models/` → `D:\BACKUP-WINDOWS\OLLAMA-MODELS\models\`) — copie automatique ~47 GB
5. Auto-copie de backup-jarvis.ps1 et install-jarvis.ps1 dans le backup

> Lancer régulièrement et **obligatoirement** avant toute réinstallation Windows.

### install-jarvis.ps1 — Ce qu'il installe (8 étapes)

1. Python 3.11.9 (téléchargement + install silencieuse + PATH)
2. Ollama (téléchargement + install)
3. **Modèles LLM** — restauration depuis `D:\BACKUP-WINDOWS\OLLAMA-MODELS\models\` → `~/.ollama/models/`
   - Ollama est arrêté pendant la copie (évite les verrous fichiers)
   - Redémarré automatiquement après
   - Si pas de backup : `ollama pull` des 5 modèles (~47 GB)
4. Packages Python (Flask, edge-tts, Whisper, DeepFilterNet, scipy...)
5. PyTorch CUDA 12.4 (~4 GB)
6. Fichiers JARVIS depuis `D:\BACKUP-WINDOWS\JARVIS\`
7. Clés SSH depuis `D:\BACKUP-WINDOWS\SSH\` + permissions
8. Mémoire Claude depuis `D:\BACKUP-WINDOWS\CLAUDE-MEMORY\`
9. Raccourcis bureau (Démarrage + Arrêt + Dashboard)

### Lancement

```powershell
# Clic droit → Exécuter en tant qu'administrateur
# Ou PowerShell admin :
Set-ExecutionPolicy Bypass -Scope Process -Force
& "D:\BACKUP-WINDOWS\JARVIS\install-jarvis.ps1"
```

---

## Ollama — Démarrage automatique avec Windows

> Configuré le 2026-04-29 — évite le délai de 15-20s à chaque lancement de JARVIS.

Ollama est enregistré dans le registre Windows pour démarrer automatiquement à la session.
Il tourne en fond silencieux — **aucun impact sur les jeux** (0 VRAM au repos, ~200 Mo RAM).

### Entrée registre (déjà configurée)

```
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
Valeur : Ollama
Données : "C:\Users\mmsab\AppData\Local\Programs\Ollama\ollama.exe" serve
```

### Reconfigurer après réinstallation Windows

```powershell
$ollamaPath = "C:\Users\mmsab\AppData\Local\Programs\Ollama\ollama.exe"
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
Set-ItemProperty -Path $regPath -Name "Ollama" -Value "`"$ollamaPath`" serve"
```

### Vérifier que c'est actif

```powershell
Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Ollama"
```

### Supprimer si nécessaire

```powershell
Remove-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "Ollama"
```

### Comportement VRAM — compatibilité jeux

| Situation | VRAM Ollama |
|-----------|------------|
| Ollama actif, aucune requête | **0 Go** — modèle non chargé |
| Pendant une réponse JARVIS | ~9-10 Go (phi4:14b · SOC) ou ~9.6 Go (gemma4 · GÉNÉRAL) |
| En session JARVIS active | **~9 Go** — `keep_alive "24h"` dans jarvis.py maintient le modèle chargé |
| Pendant une session de jeu (JARVIS arrêté) | **0 Go** — RTX 5080 100% disponible |

> ⚠️ JARVIS utilise `keep_alive "24h"` dans `stream_llm()` pour éviter la latence de rechargement. Arrêter JARVIS (`stop_jarvis.bat`) libère la VRAM avant de jouer.

---

## Vue d'ensemble

JARVIS tourne entièrement en local sur Windows 11 Pro.
Aucun serveur distant, aucun service cloud requis — 100% local.

```
Windows 11 Pro
│
├── Python 3.11.9                                   ← moteur d'exécution JARVIS
│   └── C:\Users\mmsab\AppData\Local\Programs\Python\Python311\python.exe
│       └── packages pip (Flask, edge-tts, Whisper, DeepFilterNet, PyTorch...)
│
├── Ollama                                          ← moteur LLM local (service Windows)
│   ├── binaire  : C:\Users\mmsab\AppData\Local\Programs\Ollama\ollama.exe
│   ├── API      : http://localhost:11434
│   └── modèles  : C:\Users\mmsab\.ollama\models\  (~47 GB)
│       ├── phi4:14b              9.1 GB ← mode SOC (défaut · keep_alive 24h)
│       ├── gemma4:latest        ~9.6 GB ← mode GÉNÉRAL + VOCAL + vision
│       ├── qwen2.5-coder:14b    9.0 GB ← mode CODE · dev srv-dev-1
│       └── mxbai-embed-large    0.7 GB ← RAG (obligatoire · 1024 dims)
│
└── JARVIS                                          ← assistant IA local
    ├── racine   : C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\
    ├── backend  : scripts\jarvis.py (orchestrateur Flask — port 5000 — 4633 L + 31 modules Python)
    ├── frontend : scripts\templates\jarvis.html (shell Jinja2) + static\jarvis_main.js (4013 L — refactor JS 2026-05-14, 7828→4013) + static\js\ (11 modules) + static\css\ (8 fichiers)
    └── configs  : jarvis_*.json + jarvis_system_prompt.txt
```

---

## Sauvegardes à préserver

Lancer `backup-jarvis.ps1` avant toute réinstallation Windows.
Résultat dans `D:\BACKUP-WINDOWS\` :

```
D:\BACKUP-WINDOWS\                         ← racine sauvegarde
│
├── JARVIS\                    (148 MB)    ← projet complet
│   ├── install-jarvis.ps1                 ← script réinstallation automatique
│   ├── backup-jarvis.ps1                  ← script sauvegarde (celui-ci)
│   ├── MEMORY.md                          ← mémoire projet JARVIS
│   ├── start_dashboard.bat                ← démarrage JARVIS
│   ├── stop_jarvis.bat                    ← arrêt JARVIS
│   ├── scripts\
│   │   ├── jarvis.py                      ← orchestrateur Flask (4633 lignes · 75 routes · 31 modules extraits)
│   │   ├── templates\
│   │   │   ├── jarvis.html                ← shell Jinja2 (211 lignes)
│   │   │   ├── tabs\                      ← 8 onglets modulaires
│   │   │   └── partials\modals.html
│   │   ├── jarvis_system_prompt.txt       ← prompt SOC enrichi
│   │   ├── jarvis_prompt_profiles.json    ← 7 profils (SOC · phi4 · Gemma4 · JARVIS PERSO…)
│   │   ├── jarvis_model.json              ← modèle actif (phi4:14b)
│   │   ├── jarvis_llm_params.json         ← paramètres LLM
│   │   ├── jarvis_dsp_params.json         ← paramètres DSP audio
│   │   ├── jarvis_welcome.json            ← message accueil
│   │   └── voices\                        ← modèles Piper TTS (.onnx)
│   └── doc\                               ← documentation
│
├── SSH\                                   ← clés SSH (CRITIQUE — copie complète ~/.ssh)
│   ├── id_nginx / id_nginx.pub            ← srv-ngix (VM 108)
│   ├── id_clt   / id_clt.pub             ← VM clt (106)
│   ├── id_pa85  / id_pa85.pub            ← VM pa85 (107)
│   ├── id_proxmox / id_proxmox.pub       ← Proxmox VE
│   ├── id_dev   / id_dev.pub             ← srv-dev-1 (192.168.1.21)
│   ├── id_pi-1  / id_pi-1.pub            ← Raspberry Pi 1
│   ├── id_pi-2  / id_pi-2.pub            ← Raspberry Pi 2
│   ├── id_router / id_router.pub         ← Routeur
│   ├── known_hosts                        ← hôtes connus
│   └── config                             ← aliases SSH
│   ⚠ Vérification dynamique — backup-jarvis.ps1 compare source vs backup
│
├── CLAUDE-MEMORY\                         ← mémoire Claude Code
│   └── projects\...
│
├── OLLAMA-MODELS\             (~28 GB)    ← modèles LLM (optionnel)
│   └── models\
│       ├── phi4\                          ← phi4:14b (SOC · 9.1 GB · actif)
│       ├── gemma4\                        ← gemma4:latest (GÉNÉRAL · ~9.6 GB)
│       ├── qwen2.5-coder\                 ← qwen2.5-coder:14b (CODE · 9.0 GB)
│       └── mxbai-embed-large\             ← embeddings RAG (0.7 GB · obligatoire)
│
├── CLES-API\                              ← clés API en clair (sécurisé)
└── LISEZ-MOI.md                           ← procédure générale
```

| Élément | Chemin source | Critique |
|---------|--------------|---------|
| Dossier JARVIS complet | `C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\` | ✅ OUI |
| Modèles Ollama | `C:\Users\mmsab\.ollama\models\` | ⚠️ 47 GB — optionnel |
| Clés SSH | `C:\Users\mmsab\.ssh\` | ✅ OUI |
| Mémoire Claude | `C:\Users\mmsab\.claude\` | ✅ OUI |

---

## Étape 1 — Python 3.11 (Windows)

### Téléchargement

URL : https://www.python.org/downloads/release/python-3119/
Fichier : `python-3.11.9-amd64.exe`

> ⚠️ **Version 3.11 obligatoire** — pas 3.12, pas 3.13.
> Certaines dépendances (numpy 1.26.4, DeepFilterNet, ctranslate2) ne sont pas compatibles avec Python 3.12+.

### Installation — étapes précises

**Écran 1 — avant de cliquer quoi que ce soit :**

```
┌─────────────────────────────────────────────────┐
│  Install Python 3.11.9 (64-bit)                 │
│                                                 │
│  ○ Install Now          ← choisir celui-ci      │
│  ○ Customize installation                       │
│                                                 │
│  [✅] Use admin privileges when installing...   │
│  [✅] Add python.exe to PATH   ← COCHER AVANT   │
└─────────────────────────────────────────────────┘
```

> ⚠️ Cocher **"Add python.exe to PATH"** **AVANT** de cliquer "Install Now".
> Si oublié : désinstaller et recommencer, ou ajouter manuellement dans les variables d'environnement Windows.

**Cliquer "Install Now"** — installation dans :
```
C:\Users\mmsab\AppData\Local\Programs\Python\Python311\
```

**Écran final :** cliquer **"Disable path length limit"** si proposé (recommandé).

### Vérification

Ouvrir un nouveau cmd (important — pas celui ouvert avant l'install) :

```cmd
python --version
```
→ doit afficher `Python 3.11.9`

```cmd
pip --version
```
→ doit afficher `pip xx.x from ...Python\Python311\...`

### Pip — mise à jour initiale

```cmd
python -m pip install --upgrade pip
```

> JARVIS utilise Python système (pas de venv). Tous les packages sont installés globalement.

---

## Étape 2 — Ollama (moteur LLM local)

### Installation

1. Télécharger depuis https://ollama.com/download/windows
2. Installer — Ollama s'installe comme service Windows, icône dans la barre système
3. Vérifier : ouvrir cmd et taper `ollama list` → doit répondre (liste vide si pas de modèles)

### Configuration

Ollama écoute sur `localhost:11434` par défaut.
Les modèles sont stockés dans `C:\Users\mmsab\.ollama\models\` (~47 GB pour tous les modèles).

### Option A — Restaurer depuis sauvegarde (recommandé — évite le téléchargement)

```cmd
xcopy /E /I "D:\BACKUP-WINDOWS\.ollama" "C:\Users\mmsab\.ollama"
```

### Option B — Re-télécharger les modèles LLM

```cmd
ollama pull phi4:14b              :: ~9.1 GB — modèle actif SOC (défaut · keep_alive 24h)
ollama pull gemma4:latest         :: ~9.6 GB — mode GÉNÉRAL + VOCAL + vision (multimodal)
ollama pull qwen2.5-coder:14b     :: ~9.0 GB — mode CODE · dev srv-dev-1
ollama pull mxbai-embed-large     :: ~0.7 GB — embeddings RAG (obligatoire · 1024 dims)
```

> Total ~28 GB.
> ⚠ Supprimés : phi4-reasoning:plus · qwen2.5:14b · deepseek-r1:14b · llava-phi3:latest (2026-05-08) · nomic-embed-text (2026-05-10)

### Modèle actif par défaut

JARVIS charge le modèle depuis `scripts\jarvis_model.json` :
```json
{"model": "phi4:14b"}
```
Modifiable depuis l'interface JARVIS (onglet Settings) sans redémarrage.

### Provider IA

| Provider | Modèle défaut | Clé API |
|----------|--------------|---------|
| Ollama (local) | phi4:14b | aucune |

---

## Étape 3 — Packages Python

### Commande unique (copier-coller dans cmd)

```cmd
pip install flask flask-cors flask-limiter edge-tts faster-whisper nvidia-ml-py psutil playsound==1.2.2 requests pyttsx3 piper-tts kokoro soundfile DeepFilterNet numpy==1.26.4 scipy ctranslate2 librosa
pip install coqui-tts==0.27.5
```

> `coqui-tts` pour XTTS v2. `librosa` pour l'analyse empreinte vocale (Voice Prints).

> ⚠️ `playsound==1.2.2` — la version doit être exactement 1.2.2, les versions supérieures cassent la lecture WAV sous Windows.
> ⚠️ `numpy==1.26.4` — numpy 2.x est incompatible avec certaines dépendances audio.

### Versions exactes en production (2026-03-25)

| Package | Version | Rôle |
|---------|---------|------|
| Flask | 3.1.3 | Serveur web |
| flask-cors | 6.0.2 | CORS headers |
| Flask-Limiter | 4.1.1 | Rate limiting API |
| edge-tts | 7.2.7 | TTS Microsoft Neural (Antoine FR) |
| faster-whisper | 1.2.1 | STT local (mic → texte) |
| nvidia-ml-py | 13.590.48 | Stats GPU RTX 5080 |
| psutil | 7.2.2 | Stats CPU/RAM/réseau |
| playsound | 1.2.2 | Lecture audio WAV (⚠️ version 1.2.2 obligatoire) |
| requests | 2.32.5 | Appels HTTP (Ollama, WAN ping) |
| pyttsx3 | 2.99 | TTS SAPI5 Windows (fallback) |
| piper-tts | 1.4.1 | TTS neural local hors-ligne |
| kokoro | 0.9.4 | TTS haute qualité 82M params |
| DeepFilterNet | 0.5.6 | Débruitage audio (CPU forcé) |
| DeepFilterLib | 0.5.6 | Dépendance DeepFilterNet |
| numpy | 1.26.4 | Traitement audio DSP |
| scipy | 1.17.1 | Filtres biquad, convolution |
| soundfile | 0.13.1 | Lecture/écriture WAV |
| torch | 2.6.0+cu124 | ML runtime (Whisper GPU) |
| torchaudio | 2.6.0+cu124 | Audio ML |
| torchvision | 0.21.0+cu124 | Dépendance torch |
| ctranslate2 | 4.7.1 | Inférence Whisper optimisée |

### PyTorch CUDA (obligatoire pour Whisper GPU)

```cmd
pip install torch==2.7.1 torchaudio==2.7.1 torchvision --index-url https://download.pytorch.org/whl/cu128
```

> RTX 5080 (Blackwell sm_120) : **PyTorch 2.7.1+cu128** supporte nativement sm_120.
> Kokoro, XTTS v2 et DeepFilterNet tournent sur GPU.
> Whisper STT fonctionne en GPU via ctranslate2.

```cmd
pip install ctranslate2
```

---

## Étape 4 — Restaurer les fichiers JARVIS

Si sauvegarde présente dans `D:\BACKUP-WINDOWS\` :

```cmd
xcopy /E /I "D:\BACKUP-WINDOWS\JARVIS" "C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS"
```

### Fichiers de configuration à vérifier après restauration

| Fichier | Contenu à vérifier |
|---------|-------------------|
| `scripts\jarvis_model.json` | Modèle actif (`phi4:14b`) |
| `scripts\jarvis_prompt_profiles.json` | 7 profils · vérifier cohérence SOC/GÉNÉRAL |
| `scripts\jarvis_dsp_params.json` | Paramètres audio DSP |
| `scripts\jarvis_llm_params.json` | Paramètres LLM |
| `scripts\voices\` | Modèles Piper (.onnx) — fr_FR-upmc-medium |

---

## Étape 5 — Shortcuts bureau

Les raccourcis `.lnk` sont dans `C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\` :

- `JARVIS Dashboard.lnk` → ouvre `http://localhost:5000`
- `JARVIS - Arrêt.lnk` → lance `stop_jarvis.bat`

Si les .lnk ne fonctionnent plus (chemin brisé), recréer :

```cmd
cd "C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\scripts"
python create_shortcut.py
```

---

## Étape 5b — Scripts de démarrage et d'arrêt

Les scripts sont dans deux emplacements (identiques) :

```
JARVIS\start_dashboard.bat       ← raccourci bureau pointe ici
JARVIS\scripts\start_dashboard.bat
JARVIS\stop_jarvis.bat
JARVIS\scripts\stop_jarvis.bat
```

### start_dashboard.bat — Ce qu'il fait

1. Vérifie si JARVIS tourne déjà (port 5000) → ouvre navigateur et quitte si oui
2. Cherche un venv local `.venv\Scripts\python.exe` → sinon utilise Python système
3. Vérifie si Ollama tourne → le démarre avec `ollama serve` si absent
4. Attend Ollama max 12s (poll toutes les 1s sur `localhost:11434`)
5. Lance `python jarvis.py` depuis la racine JARVIS
6. Log tout dans `%USERPROFILE%\Desktop\jarvis-start.log`

### stop_jarvis.bat — Ce qu'il fait

1. Ferme l'onglet navigateur pointant vers `localhost:5000`
2. Lit le PID du process écoutant sur le port 5000 via `netstat`
3. Fait `taskkill /F /PID` sur ce PID
4. Log dans `%USERPROFILE%\Desktop\jarvis-stop.log`
5. Se ferme automatiquement après 2s

> Ollama n'est **pas** arrêté par stop_jarvis.bat — il reste actif en arrière-plan.
> Pour arrêter Ollama : icône système → Quit Ollama.

### Recréer les scripts si perdus

Si les `.bat` sont absents, les copier depuis la sauvegarde ou les recréer manuellement.
Le code complet est dans `JARVIS\scripts\start_dashboard.bat` et `stop_jarvis.bat`.

---

## Étape 6 — Démarrage et test

```cmd
cd "C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS"
start_dashboard.bat
```

Ou double-cliquer sur `start_dashboard.bat`.

JARVIS démarre, Ollama est lancé automatiquement, le navigateur ouvre `http://localhost:5000`.

### Vérifications post-démarrage

```
http://localhost:5000/api/stats     → GPU, RAM, CPU
http://localhost:5000/api/boot-id   → ID de session
http://localhost:5000/api/soc/test  → Connectivité SOC + SSH srv-ngix + TTS
```

---

## Résumé des ports

| Service | Port | Protocole |
|---------|------|-----------|
| JARVIS Flask | 5000 | HTTP local |
| Ollama | 11434 | HTTP local |

---

## En cas de problème

### "Module not found"
```cmd
pip install <module>
```
JARVIS installe automatiquement les dépendances manquantes au démarrage (sauf PyTorch).

### Ollama ne répond pas
```cmd
ollama serve
```

### Port 5000 déjà utilisé
```cmd
netstat -ano | findstr :5000
taskkill /PID <pid> /F
```

### DeepFilterNet erreur CUDA
Normal sur RTX 5080 — forcé CPU dans le code. Aucune action requise.
