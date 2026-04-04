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
