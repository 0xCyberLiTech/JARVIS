# Pré-requis

> Configuration matérielle et logicielle nécessaire pour faire tourner JARVIS.

---

## Matériel minimum recommandé

| Composant | Minimum | Configuration de référence |
|-----------|---------|---------------------------|
| **GPU** | NVIDIA 8 GB VRAM | RTX 5080 — 16 GB GDDR7 CUDA |
| **RAM** | 16 GB | 32 GB DDR5 |
| **Stockage** | 50 GB SSD | NVMe (modèles Ollama ~29 GB) |
| **CPU** | 8 cœurs | AMD/Intel moderne |

> **Note** : avec 8 GB VRAM, seul un modèle 7B peut tourner sans swap.
> Pour phi4:14b (9.1 GB) + mxbai-embed (0.7 GB), il faut minimum **12 GB VRAM**.
> La configuration de référence (16 GB) laisse de la marge pour gemma4:latest (~9.6 GB).

---

## Système d'exploitation

| Élément | Requis |
|---------|--------|
| **OS** | Windows 11 Pro (recommandé) ou Windows 10 |
| **Architecture** | x86-64 |

---

## Python

| Élément | Version |
|---------|---------|
| **Python** | 3.11.x (strictement — certains paquets CUDA sont incompatibles 3.12) |
| **pip** | Dernière version (`python -m pip install --upgrade pip`) |
| **venv** | Inclus avec Python 3.11 |

---

## NVIDIA / CUDA

| Élément | Version |
|---------|---------|
| **Pilotes NVIDIA** | 570+ (CUDA 12) |
| **CUDA Toolkit** | 12.x |
| **PyTorch** | 2.7.1+cu128 (inclus dans requirements.txt) |
| **cuDNN** | Inclus avec PyTorch CUDA |

Vérification CUDA :
```bash
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"
```

---

## Ollama

| Élément | Détail |
|---------|--------|
| **Ollama** | Dernière version stable (https://ollama.com) |
| **Port** | 11434 (défaut, localhost uniquement) |
| **Modèles requis** | phi4:14b · gemma4:latest · qwen2.5-coder:14b · mxbai-embed-large |

---

## Dépendances Python clés

| Paquet | Rôle |
|--------|------|
| `flask` | Serveur web |
| `faster-whisper` | STT (CUDA) |
| `edge-tts` | TTS défaut |
| `kokoro` | TTS local CUDA |
| `pynvml` | Stats GPU NVIDIA |
| `paramiko` | SSH |
| `chromadb` | Base vectorielle RAG |
| `rank-bm25` | Recherche BM25 hybride |
| `sentence-transformers` | Embeddings RAG |

Liste complète dans `scripts/requirements.txt`.

---

## Réseau

JARVIS est conçu pour un usage en réseau local (LAN).
Il écoute uniquement sur `localhost:5000` par défaut.

Pour une intégration SOC, un serveur nginx sur le LAN est nécessaire
avec le script `monitoring_gen.py` qui génère `monitoring.json`.

---

*PRE-REQUIS.md · 0xCyberLiTech · 2026-06-09*
