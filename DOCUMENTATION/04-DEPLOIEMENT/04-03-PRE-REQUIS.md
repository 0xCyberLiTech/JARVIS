---
title: "PrÃ©-requis systÃ¨me (OS, Python, Ollama, GPU)"
code: "JARVIS-DOC-04-03"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "ValidÃ©"
categorie: "DÃ©ploiement"
mots_cles: ["pre-requis", "installation", "windows", "ollama", "cuda", "python"]
---

# PrÃ©-requis systÃ¨me

## MatÃ©riel

| Composant | Minimum | RecommandÃ© (config Marc) |
|---|---|---|
| **CPU** | 4 cÅ“urs / 8 threads | 8+ cÅ“urs / 16+ threads |
| **RAM** | 16 GB | 32 GB |
| **GPU** | NVIDIA CUDA 11+ avec â‰¥ 12 GB VRAM | RTX 5080 16 GB GDDR7 (Blackwell, CUDA 12) |
| **Stockage** | 50 GB libre (modÃ¨les Ollama + RAG + logs) | 100 GB NVMe SSD |
| **RÃ©seau** | LAN privÃ© pour intÃ©gration SOC | 2 segments (Freebox + ASUS GT-BE19000-AI) |

## SystÃ¨me d'exploitation

| OS | Statut | Note |
|---|---|---|
| **Windows 11 Pro** | âœ… TestÃ© production (config Marc) | OS de rÃ©fÃ©rence pour JARVIS |
| Windows 10 | âš  Non testÃ© | Devrait fonctionner (Flask + Python natifs) |
| Linux (Ubuntu 22+) | âš  AdaptÃ© SOC, pas JARVIS | Le SOC est sur Debian, mais JARVIS exploite SAPI5 (Windows-only) en fallback TTS |
| macOS | âŒ Non supportÃ© | SAPI5 indisponible, audio Windows-specific |

## Logiciels essentiels

### Python 3.11

- **Version exacte** : Python 3.11.x (3.11.9 actuellement)
- **Source** : python.org installer officiel (PATH activÃ©)
- **VÃ©rification** :
  ```powershell
  python --version  # Python 3.11.x
  pip --version
  ```

### Ollama

- **Version minimum** : 0.24.0
- **Installation** : https://ollama.ai/download/windows
- **Port** : `11434` (localhost uniquement, jamais exposÃ©)
- **ModÃ¨les Ã  puller** :
  ```powershell
  ollama pull phi4:14b
  ollama pull qwen2.5-coder:14b
  ollama pull gemma4:latest
  ollama pull qwen3:8b
  ollama pull mxbai-embed-large
  ```
- **Espace disque modÃ¨les** : ~25 GB cumul

### CUDA 12 + drivers NVIDIA

- **Drivers NVIDIA** : rÃ©cents (CUDA 12 compatibles, â‰¥ 555.x)
- **VÃ©rification** :
  ```powershell
  nvidia-smi
  ```
  Doit afficher CUDA Version: 12.x

### Git Bash (pour SSH/SCP dans scripts)

- **Installation** : https://git-scm.com/download/win
- Requis pour les scripts `.bat` / `.ps1` qui invoquent `ssh` ou `scp`
- Pas optionnel : le bureau Marc l'utilise pour les sauvegardes Proxmox

## DÃ©pendances Python

Toutes auto-installÃ©es par `jarvis.py` au premier lancement via `pip install -q`
(fonction `install()` ligne 273-275). Mais installation manuelle recommandÃ©e
au premier dÃ©ploiement pour anticipation :

```powershell
pip install -r requirements.txt
```

### Liste principale

| Package | Version | RÃ´le |
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

- [04-01-DEPLOIEMENT.md](04-01-DEPLOIEMENT.md) â€” procÃ©dure d'installation pas Ã  pas
- [04-02-REINSTALLATION.md](04-02-REINSTALLATION.md) â€” recovery aprÃ¨s crash Windows

