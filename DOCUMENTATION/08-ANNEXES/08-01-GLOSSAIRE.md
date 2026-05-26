---
title: "Glossaire — SOC, JARVIS, termes techniques"
code: "JARVIS-DOC-08-01"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "Annexes"
mots_cles: ["glossaire", "terminologie", "soc", "jarvis", "definitions"]
---

# Glossaire

> Recueil des termes techniques et acronymes utilisés dans le projet JARVIS,
> avec définitions courtes et liens vers les docs détaillées.

## A

| Terme | Définition |
|---|---|
| **AppSec** | Application Security — protection couche applicative (WAF, vpatch CVE) |
| **API** | Interface de programmation applicative (REST HTTP dans JARVIS) |
| **Auto-engine SOC** | Thread `_soc_monitor_loop` dans `blueprints/soc.py` qui détecte menaces et déclenche alertes vocales JARVIS. **Actif uniquement en mode soc**. |

## B

| Terme | Définition |
|---|---|
| **BiquadFilter** | Filtre audio second ordre Web Audio API (4 utilisés dans JARVIS pour EQ) |
| **Blueprint** | Pattern Flask pour modulariser les routes HTTP en sous-applications |
| **Bypass LLM** | Court-circuit du LLM pour commandes déterministes (VM start/stop, reboot, restart service). Pas d'hallucination, exécution 200 ms vs 8 s via LLM. |
| **boot_id** | Identifiant unique de session JARVIS (timestamp). Consommé par `_pollBootId` côté JS pour détecter un redémarrage serveur. |

## C

| Terme | Définition |
|---|---|
| **CR / CODE-REASONING** | 4e mode JARVIS, modèle `qwen3:8b` raisonnement natif streaming |
| **CrowdSec** | IDS communautaire installé sur srv-nginx — bans coordonnés via consensus |
| **CSRF** | Cross-Site Request Forgery — token de protection sur les routes POST sensibles |
| **CUDA** | API NVIDIA pour calcul GPU (12.x sur RTX 5080) |

## D

| Terme | Définition |
|---|---|
| **DeepFilterNet** | Modèle de réduction de bruit audio CUDA, pré-warmé au boot |
| **DI** | Dependency Injection — pattern d'injection de dépendances explicite (utilisé partout dans JARVIS via `init(...)`) |
| **DSP** | Digital Signal Processing — chaîne EQ + comp + stereo + reverb appliquée au TTS |

## E

| Terme | Définition |
|---|---|
| **Edge-TTS** | Service Microsoft Edge TTS cloud (voix `fr-CA-AntoineNeural` défaut) |
| **EXPLOIT** | Stade 4 de la Kill Chain (utilisation active d'une vulnérabilité) — priorité absolue ban |
| **E2E** | End-to-End — tests qui couvrent le navigateur jusqu'au backend (Playwright dans JARVIS) |

## F

| Terme | Définition |
|---|---|
| **fail2ban** | Outil de ban dynamique basé sur les logs (auth, nginx, ssh) — sur srv-nginx |
| **FCrDNS** | Forward-Confirmed reverse DNS — méthode de vérification des crawlers légitimes (Googlebot, etc.) |
| **Flask** | Framework web Python (backend JARVIS) |
| **Flask-Sock** | Extension Flask pour WebSocket (terminal SSH xterm.js) |
| **Frontmatter** | Métadonnées YAML en tête de fichier markdown (titre, auteur, date, statut) |

## G

| Terme | Définition |
|---|---|
| **gemma4** | Modèle Google 9.6 GB — mode GENERAL JARVIS + vision multimodale |
| **GeoIP** | Géolocalisation IP — module exploitable pour ban par pays |

## H

| Terme | Définition |
|---|---|
| **Homelab** | Infrastructure personnelle d'expérimentation (Marc = 0xCyberLiTech) |
| **HUD** | Heads-Up Display — l'interface holographique JARVIS v3.3 |

## I

| Terme | Définition |
|---|---|
| **Idempotence** | Propriété d'une opération qu'on peut appeler N fois avec le même résultat (utilisé pour les fix anti-cascade) |
| **IDS** | Intrusion Detection System — Suricata sur srv-nginx |

## J

| Terme | Définition |
|---|---|
| **JARVIS** | Just A Rather Very Intelligent System — nom inspiré du film Iron Man |
| **Jinja2** | Moteur de templates Python (10 templates HTML dans `scripts/templates/`) |
| **JS-DIAG** | Instrumentation JS posée 2026-05-23 pour capturer les erreurs frontend (window.error, unhandledrejection, beforeunload) |

## K

| Terme | Définition |
|---|---|
| **Kill Chain** | Modèle d'attaque cyber (5 stades : RECON → SCAN → EXPLOIT → BRUTE → NEUTRALISÉ) |
| **Kokoro** | Moteur TTS local CUDA — fallback si Edge-TTS indisponible. Voix `ff_siwis`. |

## L

| Terme | Définition |
|---|---|
| **LLM** | Large Language Model — phi4, gemma4, qwen2.5-coder, qwen3 dans JARVIS |
| **LLaVA** | Modèle vision multimodal (capacité image dans gemma4) |

## M

| Terme | Définition |
|---|---|
| **MCP** | Model Context Protocol — protocole Anthropic pour intégrer Claude Desktop à JARVIS via 12 outils |
| **ModSec** | ModSecurity — WAF Apache pour les sites CLT/PA85 |
| **mxbai-embed-large** | Modèle d'embeddings 1024-dim utilisé pour le RAG |

## N

| Terme | Définition |
|---|---|
| **NDT** | "Note de Dette" — convention Marc pour classer les findings d'audit (CRITIQUE/MOYEN/FAIBLE) |
| **NVML** | NVIDIA Management Library — API Python `pynvml` pour stats GPU |

## O

| Terme | Définition |
|---|---|
| **Ollama** | Runtime LLM local on-premise (port `:11434`). Backend tous les modèles JARVIS. |
| **OpenVAS** | Scanner vulnérabilités (passé sur sites CLT/PA85, archivé) |

## P

| Terme | Définition |
|---|---|
| **Paramiko** | Lib Python SSH client (terminal xterm.js + bypass infra) |
| **phi4:14b** | Modèle Microsoft 9.1 GB — mode SOC JARVIS (défaut) |
| **Piper** | Moteur TTS local CPU — 3e fallback après Edge et Kokoro |
| **PTY** | Pseudo-terminal — terminal interactif via WebSocket (paramiko `invoke_shell()`) |
| **PVE / Proxmox VE** | Hyperviseur sur 192.168.1.20 — héberge srv-nginx + clt + pa85 + srv-dev-1 |
| **pre-warm** | Préchargement d'un modèle (Kokoro CUDA, phi4 Ollama) au boot pour éviter cold start |

## Q

| Terme | Définition |
|---|---|
| **qwen2.5-coder:14b** | Modèle Alibaba 9 GB — mode CODE JARVIS |
| **qwen3:8b** | Modèle Alibaba 5.2 GB raisonnement — mode CODE-REASONING JARVIS |

## R

| Terme | Définition |
|---|---|
| **RAG** | Retrieval-Augmented Generation — JARVIS injecte 599 chunks indexés dans le prompt LLM |
| **RECON** | Stade 1 Kill Chain (reconnaissance passive) |
| **RFC1918** | Plages IP privées (10./172.16-31./192.168./127.) — **JAMAIS bannies** par règle ABSOLUE |
| **ruff** | Linter Python ultra-rapide (remplace flake8 + isort) — 0 erreur dans JARVIS |

## S

| Terme | Définition |
|---|---|
| **SAPI5** | Speech API Windows natif — ultime fallback TTS |
| **SCP** | Secure Copy — déploiement fichiers via SSH (bypass CODE → srv-dev-1) |
| **SOC** | Security Operations Center — dashboard sur srv-nginx v3.107.3 + intégration JARVIS |
| **SSE** | Server-Sent Events — streaming HTTP unidirectionnel (utilisé pour le chat JARVIS) |
| **STT** | Speech-to-Text — `faster-whisper large-v3-turbo` CUDA dans JARVIS |
| **Suricata** | IDS réseau — alerte sur signatures malveillantes (port scan, EXPLOIT, etc.) |
| **srv-dev-1 / clt / pa85 / ngix** | Hôtes du homelab (VM Proxmox) |

## T

| Terme | Définition |
|---|---|
| **TTS** | Text-to-Speech — chaîne Edge → Kokoro → Piper → SAPI5 dans JARVIS |
| **Tuile** | Module autoportant JARVIS (Blueprint + DI init). 24 tuiles au 2026-05-23. |

## U

| Terme | Définition |
|---|---|
| **UFW** | Uncomplicated Firewall — pare-feu Debian sur srv-nginx |

## V

| Terme | Définition |
|---|---|
| **VRAM** | Mémoire vidéo GPU (16 GB sur RTX 5080) — modèles Ollama y sont chargés |
| **vpatch** | Patch virtuel WAF (CrowdSec AppSec ~150 règles CVE) |

## W

| Terme | Définition |
|---|---|
| **WAF** | Web Application Firewall — CrowdSec AppSec + ModSec sur srv-nginx |
| **Web Audio API** | API navigateur pour traitement audio temps réel (graph DSP JARVIS) |
| **whisper** | Modèle OpenAI STT (variante `faster-whisper` CTranslate2 dans JARVIS) |

## X

| Terme | Définition |
|---|---|
| **XDR** | Extended Detection and Response — fusion multi-sources SOC (Suricata + ModSec + rsyslog + ...) |
| **xterm.js** | Émulateur de terminal JavaScript (frontend terminaux SSH JARVIS) |

## Acronymes JARVIS spécifiques

| Code | Signification |
|---|---|
| **JARVIS-DOC-NN-MM** | Code unique de chaque document de cette base documentaire |
| **`_BLOCKED_SSH`** | Whitelist Python 29 patterns SSH bloqués (immutable sans validation Marc) |
| **`_ALLOWED_SOC_RESTART_SVCS`** | Whitelist services restart SOC (source unique) |
| **`_pollBootId`** | Fonction JS qui détecte un redémarrage serveur (boot_init.js:870) |
| **`_chat_stream_active`** | `threading.Event` signalant un chat SSE en cours |
| **`_VRAM_LOCK`** | `threading.Lock` sérialisant l'accès VRAM Ollama |
