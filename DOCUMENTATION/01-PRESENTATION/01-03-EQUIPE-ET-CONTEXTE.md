---
title: "Équipe, contexte homelab, environnement"
code: "JARVIS-DOC-01-03"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "Présentation"
mots_cles: ["equipe", "contexte", "homelab", "infrastructure", "marc"]
---

# Équipe, contexte homelab, environnement

## Équipe

| Rôle | Personne | Contact |
|---|---|---|
| **Owner / Lead Developer** | Marc Sabater | `mm.sab8572@outlook.fr` |
| **Organisation** | 0xCyberLiTech (homelab personnel) | — |
| **Collaboration IA** | Claude (Anthropic) — Opus 4.x via Claude Code | — |

Marc est l'architecte, développeur et opérateur unique du projet. Claude
intervient comme **assistant de développement et de cybersécurité** via
l'outil Claude Code (CLI Anthropic dans VS Code) et Claude Desktop (MCP).

## Contexte homelab 0xCyberLiTech

### Infrastructure réseau (2 segments)

| Segment | CIDR | Gateway | Rôle |
|---|---|---|---|
| LAN serveur Freebox | `192.168.1.0/24` | Freebox `.254` | Toute l'infra serveur (Proxmox + VMs) |
| LAN ASUS | `192.168.50.0/24` | Routeur ASUS `.1` (WAN `.1.110`) | Poste Windows / JARVIS |

### Machines & rôles

| Hôte | IP | Rôle | Accès SSH |
|---|---|---|---|
| Proxmox VE | 192.168.1.20 | Hyperviseur (srv-nginx + clt + pa85 + srv-dev-1) | port 2272, `~/.ssh/id_proxmox` |
| srv-nginx (VM 108) | 192.168.1.50 | nginx + CrowdSec + dashboard SOC | port 2272, `~/.ssh/id_nginx` |
| clt (VM 106) | 192.168.1.12 | Apache + site CLT cybersécurité | port 2272, `~/.ssh/id_clt` |
| pa85 (VM 107) | 192.168.1.13 | Apache + site PA85 associatif | port 2272, `~/.ssh/id_pa85` |
| srv-dev-1 (VM 101) | 192.168.1.21 | VM Debian 13 dev/test (mode CODE) | port 2272, `~/.ssh/id_dev` |
| Routeur ASUS GT-BE19000-AI | LAN `.50.1` / WAN `.1.110` | Passerelle + Docker natif | port 2272, `~/.ssh/id_router` user `admin-clt` |
| Windows / JARVIS | 192.168.50.90 (LAN ASUS, NAT vers `.1.110`) | Poste de travail Marc · JARVIS Flask | localhost:5000 |
| Dashboard SOC | http://192.168.1.50:8080/ | Monitoring CrowdSec + fail2ban + Suricata | HTTP |

### Configuration matérielle (poste Windows)

| Composant | Détail |
|---|---|
| OS | Windows 11 Pro |
| CPU | (variable selon machine Marc) |
| GPU | NVIDIA RTX 5080 Blackwell — 16 GB GDDR7, CUDA 12 |
| RAM | 32 GB+ |
| Stockage | NVMe SSD (modèles Ollama 25+ GB) |
| Python | 3.11 |
| Shell scripts | PowerShell 5.1 + Git Bash (requis pour ssh/scp dans `.bat`/`.ps1`) |

## Stack technique JARVIS

### Backend

| Couche | Composant | Version |
|---|---|---|
| Application | Flask (Python) | 3.x |
| Serveur ASGI/WSGI | Werkzeug threaded | Built-in Flask |
| WebSocket | Flask-Sock (sock) | 0.x |
| Rate limiting | Flask-Limiter (memory storage) | 3.x |
| LLM local | Ollama (`:11434`) | 0.24+ |
| RAG embed | mxbai-embed-large (Ollama) | local |

### LLM models actifs

| Modèle | Taille | Mode JARVIS | Rôle |
|---|---|---|---|
| phi4:14b | 9.1 GB | SOC (défaut) | Raisonnement analyse cybersec |
| qwen2.5-coder:14b | 9.0 GB | CODE | Génération code multi-fichiers |
| gemma4:latest | 9.6 GB | GENERAL | Conversation fluide + vision |
| qwen3:8b | 5.2 GB | CODE-REASONING | Raisonnement code natif |
| mxbai-embed-large | 0.7 GB | RAG (transverse) | Embeddings 1024-dim |

### TTS chain (chaîne de fallback)

1. **edge-tts** (Microsoft Edge TTS cloud, défaut) — voix `fr-CA-AntoineNeural`
2. **Kokoro CUDA** (local, fallback Internet KO) — voix `ff_siwis`
3. **Piper** (local, fallback Kokoro KO)
4. **SAPI5** (Windows natif, ultime fallback)

### STT

- **faster-whisper** `large-v3-turbo` (CUDA)
- Initial prompt avec vocabulaire SOC pour améliorer la reconnaissance

### Frontend

| Couche | Composant |
|---|---|
| Framework | Vanilla JS (aucun NPM sauf tests E2E) |
| Modules JS | 21 modules (`scripts/static/js/` + 3 `scripts/static/`) |
| Audio | Web Audio API + 4 BiquadFilter + 2 Compressor + Convolver |
| Terminal | xterm.js + xterm-addon-fit |
| Éditeur code | Monaco Editor via CDN (seule dép. réseau externe — dégradation gracieuse offline) |
| Highlight | highlight.js (local) |
| Templates | Jinja2 (10 templates HTML) |
| CSS | 8 fichiers (~5100 lignes) |

## Outils de développement

| Outil | Usage |
|---|---|
| **Claude Code** (CLI) | Pair programming Claude + Marc |
| **Claude Desktop** | Conversations Claude via MCP (12 outils JARVIS exposés) |
| **VS Code** | Éditeur principal (extension Claude Code) |
| **Git** (local) | Versioning — pas de remote pushé pour l'instant |
| **pytest** | Tests unitaires (1294 tests, 76 % coverage) |
| **ruff** | Linter Python (0 erreur) |
| **eslint** | Linter JS (0 erreur, config alignée 2026-05-23) |
| **Pre-commit hooks** | ruff + eslint (commit) · pytest 1294 tests (pre-push) |

## Modes de travail Marc + Claude

### Sessions de développement infogérance

Sessions explicites avec « feu vert » de Marc (`feedback_infogerance_feux_verts.md`) :
Claude agit sans confirmation par étape, sauf actions destructives/push/VMs où
Claude pause systématiquement.

### Règles ABSOLUES non négociables

Documentées dans la mémoire centrale Claude (`feedback_jarvis_no_regression.md`,
`feedback_data_security.md`) :

1. **RFC1918 immuable** — 10./172.16-31./192.168./127. JAMAIS bannies
2. **`_BLOCKED_SSH` 29 patterns** — whitelist SSH read-only intouchable sans validation Marc
3. **`_ALLOWED_SOC_RESTART_SVCS`** — liste blanche services, source unique immutable
4. **Injection SOC = 100 % serveur** — JAMAIS dans l'historique chat
5. **Auto-engine SOC** — actif UNIQUEMENT en mode soc
6. **Zéro raw data vers cloud LLM** — JARVIS filtre/agrège/détecte en local

## Workflow git typique

```
1. Édition locale dans VS Code (poste Windows)
2. Pre-commit hook : ruff + eslint → bloque si erreur
3. git commit → message conventionnel `type(scope): description`
4. Pre-push hook : pytest 1294 tests → bloque si fail
5. git push → (pas de remote pour l'instant)
6. Redémarrer JARVIS (stop_jarvis.bat → python jarvis.py)
```

## Liens vers autres projets 0xCyberLiTech

| Projet | Dossier | Rôle |
|---|---|---|
| SOC | `../SOC/` | Dashboard monitoring sur srv-nginx |
| PROXMOX | `../PROXMOX/` | Scripts backup VMs Proxmox |
| CLT | `../CLT/` | Site cybersécurité |
| PA85 | `../PA85/` | Site associatif |
| NGINX | `../NGINX/` | Configs nginx srv-nginx |
| ASUS_ROG_19000_AI | `../ASUS_ROG_19000_AI/` | Routeur ASUS (sauvegarde + intégration SOC) |
