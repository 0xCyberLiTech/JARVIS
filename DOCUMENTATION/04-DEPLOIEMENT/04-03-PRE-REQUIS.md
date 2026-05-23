---
title: "Pré-requis système (OS, Python, Ollama, GPU)"
code: "JARVIS-DOC-04-03"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "Déploiement"
mots_cles: ["pre-requis", "installation", "windows", "ollama", "cuda", "python"]
---

# Pré-requis système

## Matériel

| Composant | Minimum | Recommandé (config Marc) |
|---|---|---|
| **CPU** | 4 cœurs / 8 threads | 8+ cœurs / 16+ threads |
| **RAM** | 16 GB | 32 GB |
| **GPU** | NVIDIA CUDA 11+ avec ≥ 12 GB VRAM | RTX 5080 16 GB GDDR7 (Blackwell, CUDA 12) |
| **Stockage** | 50 GB libre (modèles Ollama + RAG + logs) | 100 GB NVMe SSD |
| **Réseau** | LAN privé pour intégration SOC | 2 segments (Freebox + ASUS GT-BE19000-AI) |

## Système d'exploitation

| OS | Statut | Note |
|---|---|---|
| **Windows 11 Pro** | ✅ Testé production (config Marc) | OS de référence pour JARVIS |
| Windows 10 | ⚠ Non testé | Devrait fonctionner (Flask + Python natifs) |
| Linux (Ubuntu 22+) | ⚠ Adapté SOC, pas JARVIS | Le SOC est sur Debian, mais JARVIS exploite SAPI5 (Windows-only) en fallback TTS |
| macOS | ❌ Non supporté | SAPI5 indisponible, audio Windows-specific |

## Logiciels essentiels

### Python 3.11

- **Version exacte** : Python 3.11.x (3.11.9 actuellement)
- **Source** : python.org installer officiel (PATH activé)
- **Vérification** :
  ```powershell
  python --version  # Python 3.11.x
  pip --version
  ```

### Ollama

- **Version minimum** : 0.24.0
- **Installation** : https://ollama.ai/download/windows
- **Port** : `11434` (localhost uniquement, jamais exposé)
- **Modèles à puller** :
  ```powershell
  ollama pull phi4:14b
  ollama pull qwen2.5-coder:14b
  ollama pull gemma4:latest
  ollama pull qwen3:8b
  ollama pull mxbai-embed-large
  ```
- **Espace disque modèles** : ~25 GB cumul

### CUDA 12 + drivers NVIDIA

- **Drivers NVIDIA** : récents (CUDA 12 compatibles, ≥ 555.x)
- **Vérification** :
  ```powershell
  nvidia-smi
  ```
  Doit afficher CUDA Version: 12.x

### Git Bash (pour SSH/SCP dans scripts)

- **Installation** : https://git-scm.com/download/win
- Requis pour les scripts `.bat` / `.ps1` qui invoquent `ssh` ou `scp`
- Pas optionnel : le bureau Marc l'utilise pour les sauvegardes Proxmox

## Dépendances Python

Toutes auto-installées par `jarvis.py` au premier lancement via `pip install -q`
(fonction `install()` ligne 273-275). Mais installation manuelle recommandée
au premier déploiement pour anticipation :

```powershell
pip install -r requirements.txt
```

### Liste principale

| Package | Version | Rôle |
|---|---|---|
| flask | 3.x | Serveur web |
| flask-sock | 0.x | WebSocket |
| flask-limiter | 3.x | Rate limiting |
| edge-tts | latest | TTS cloud |
| kokoro | (custom) | TTS CUDA local |
| faster-whisper | latest | STT |
| nvidia-ml-py (pynvml) | latest | GPU stats |
| psutil | latest | CPU/RAM stats |
| requests | latest | HTTP client |
| paramiko | latest | SSH client |
| pytest, pytest-cov | latest | Tests |
| ruff | latest | Linter Python |
| eslint | latest (Node.js) | Linter JS |

### Voir aussi

- [04-01-DEPLOIEMENT.md](04-01-DEPLOIEMENT.md) — procédure d'installation pas à pas
- [04-02-REINSTALLATION.md](04-02-REINSTALLATION.md) — recovery après crash Windows
