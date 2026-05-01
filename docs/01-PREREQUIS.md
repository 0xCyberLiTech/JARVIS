<div align="center">

  <br></br>

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=50&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS_" alt="Titre dynamique JARVIS" />
  </a>

  <br></br>

  <h2>Assistant IA local · voix · interface holographique · automatisation SOC 24/7</h2>

  <p align="center">
    <a href="https://0xcyberlitech.github.io/">
      <img src="https://img.shields.io/badge/Portfolio-0xCyberLiTech-181717?logo=github&style=flat-square" alt="Portfolio" />
    </a>
    <a href="https://github.com/0xCyberLiTech">
      <img src="https://img.shields.io/badge/Profil-GitHub-181717?logo=github&style=flat-square" alt="Profil GitHub" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/releases/latest">
      <img src="https://img.shields.io/github/v/release/0xCyberLiTech/JARVIS?label=version&style=flat-square&color=blue" alt="Dernière version" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/blob/main/CHANGELOG.md">
      <img src="https://img.shields.io/badge/📄%20Changelog-JARVIS-blue?style=flat-square" alt="Changelog" />
    </a>
    <a href="https://github.com/0xCyberLiTech?tab=repositories">
      <img src="https://img.shields.io/badge/Dépôts-publics-blue?style=flat-square" alt="Dépôts publics" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/graphs/contributors">
      <img src="https://img.shields.io/badge/👥%20Contributeurs-cliquez%20ici-007ec6?style=flat-square" alt="Contributeurs" />
    </a>
  </p>

</div>

<div align="center">
  <img src="https://img.icons8.com/fluency/96/000000/cyber-security.png" alt="CyberSec" width="80"/>
</div>

<div align="center">
  <p>
    <strong>IA 100% locale</strong> <img src="https://img.icons8.com/color/24/000000/lock--v1.png"/> &nbsp;•&nbsp; <strong>Voix naturelle · STT · TTS</strong> <img src="https://img.icons8.com/color/24/000000/linux.png"/> &nbsp;•&nbsp; <strong>Automatisation SOC</strong> <img src="https://img.icons8.com/color/24/000000/shield-security.png"/>
  </p>
</div>

---

# Étape 1 — Prérequis JARVIS

## Objectif
Mettre en place l'environnement Python, Ollama et les dépendances audio  
avant d'installer JARVIS.

---

## Environnement testé

| Composant | Version | Notes |
|-----------|---------|-------|
| OS | Windows 11 / Linux | Fonctionne sur les deux |
| Python | 3.11 | 3.10+ requis |
| GPU | NVIDIA (CUDA 12) | Optionnel — accélère STT et NR |
| RAM | 8 Go minimum | 16 Go recommandé pour LLM 14B |
| Stockage | 30 Go libres | Pour les modèles Ollama |

---

## Étape 1.1 — Python 3.11

### Windows
```powershell
# Télécharger depuis python.org (version officielle, pas Microsoft Store)
# Cocher "Add Python to PATH" à l'installation

python --version  # Vérification
```

### Linux (Debian)
```bash
apt install -y python3.11 python3.11-venv python3-pip
python3.11 --version
```

---

## Étape 1.2 — Ollama (LLM local)

Ollama est le moteur qui fait tourner les modèles de langage en local.

```bash
# Linux / macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Télécharger l'installateur depuis https://ollama.com

# Vérification
ollama --version
```

### Télécharger un modèle

```bash
# Modèle recommandé : phi4 (14B, bon rapport qualité/performance)
ollama pull phi4

# Alternative légère (moins de RAM)
ollama pull mistral:7b

# Alternative puissante (nécessite 16 Go+ RAM)
ollama pull phi4-reasoning

# Lister les modèles disponibles
ollama list
```

---

## Étape 1.3 — Dépendances Python

```bash
pip install flask flask-cors requests

# Text-to-Speech
pip install edge-tts

# Speech-to-Text (reconnaissance vocale)
pip install faster-whisper

# Réduction de bruit audio (optionnel — nécessite CUDA pour GPU)
pip install deepfilternet

# Utilitaires audio
pip install sounddevice soundfile numpy

# SSH (pour intégration SOC)
pip install paramiko
```

### requirements.txt complet

```
flask>=2.3.0
flask-cors>=4.0.0
requests>=2.31.0
edge-tts>=6.1.9
faster-whisper>=0.10.0
deepfilternet>=0.5.6
sounddevice>=0.4.6
soundfile>=0.12.1
numpy>=1.24.0
paramiko>=3.3.0
psutil>=5.9.0
```

---

## Étape 1.4 — Vérification GPU (optionnel)

```python
# Vérifier si CUDA est disponible pour accélérer STT et DeepFilter
import torch
print("CUDA disponible :", torch.cuda.is_available())
print("GPU :", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU uniquement")
```

> Sans GPU : JARVIS fonctionne mais la transcription vocale sera plus lente.  
> Avec GPU NVIDIA : inférence STT en temps réel.

---

## Étape 1.5 — Structure des dossiers

```
JARVIS/
├── scripts/
│   ├── jarvis.py              # Serveur Flask principal
│   ├── templates/
│   │   └── jarvis.html        # Interface web
│   ├── static/
│   │   ├── audio/             # Fichiers TTS générés
│   │   └── img/               # Assets visuels
│   ├── jarvis_model.json      # Modèle Ollama actif
│   ├── jarvis_llm_params.json # Paramètres LLM
│   └── jarvis_dsp_params.json # Paramètres audio DSP
└── logs/
    └── jarvis.log
```

---

**Étape suivante →** [02 — LLM et Ollama](./02-LLM-OLLAMA.md)

---

<div align="center">

<table>
<tr>
<td align="center"><b>🖥️ Infrastructure &amp; Sécurité</b></td>
<td align="center"><b>💻 Développement &amp; Web</b></td>
<td align="center"><b>🤖 Intelligence Artificielle</b></td>
</tr>
<tr>
<td align="center">
  <a href="https://www.kernel.org/"><img src="https://skillicons.dev/icons?i=linux" width="48" title="Linux" /></a>
  <a href="https://www.debian.org"><img src="https://skillicons.dev/icons?i=debian" width="48" title="Debian" /></a>
  <a href="https://www.gnu.org/software/bash/"><img src="https://skillicons.dev/icons?i=bash" width="48" title="Bash" /></a>
  <br/>
  <a href="https://nginx.org"><img src="https://skillicons.dev/icons?i=nginx" width="48" title="Nginx" /></a>
  <a href="https://git-scm.com"><img src="https://skillicons.dev/icons?i=git" width="48" title="Git" /></a>
</td>
<td align="center">
  <a href="https://www.python.org"><img src="https://skillicons.dev/icons?i=python" width="48" title="Python" /></a>
  <a href="https://flask.palletsprojects.com"><img src="https://skillicons.dev/icons?i=flask" width="48" title="Flask" /></a>
  <a href="https://developer.mozilla.org/docs/Web/HTML"><img src="https://skillicons.dev/icons?i=html" width="48" title="HTML5" /></a>
  <br/>
  <a href="https://developer.mozilla.org/docs/Web/CSS"><img src="https://skillicons.dev/icons?i=css" width="48" title="CSS3" /></a>
  <a href="https://developer.mozilla.org/docs/Web/JavaScript"><img src="https://skillicons.dev/icons?i=js" width="48" title="JavaScript" /></a>
  <a href="https://code.visualstudio.com"><img src="https://skillicons.dev/icons?i=vscode" width="48" title="VS Code" /></a>
</td>
<td align="center">
  <a href="https://ollama.com"><img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" /></a>
  <br/><br/>
  <a href="https://anthropic.com"><img src="https://img.shields.io/badge/Anthropic-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic" /></a>
</td>
</tr>
</table>

<br/>

<sub>🔒 Projets proposés par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · Développés en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🔒</sub>

</div>
