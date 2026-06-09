---
title: "Glossaire â€” SOC, JARVIS, termes techniques"
code: "JARVIS-DOC-08-01"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "ValidÃ©"
categorie: "Annexes"
mots_cles: ["glossaire", "terminologie", "soc", "jarvis", "definitions"]
---

# Glossaire

> Recueil des termes techniques et acronymes utilisÃ©s dans le projet JARVIS,
> avec dÃ©finitions courtes et liens vers les docs dÃ©taillÃ©es.

## A

| Terme | DÃ©finition |
|---|---|
| **AppSec** | Application Security â€” protection couche applicative (WAF, vpatch CVE) |
| **API** | Interface de programmation applicative (REST HTTP dans JARVIS) |
| **Auto-engine SOC** | Thread `_soc_monitor_loop` dans `blueprints/soc.py` qui dÃ©tecte menaces et dÃ©clenche alertes vocales JARVIS. **Actif uniquement en mode soc**. |

## B

| Terme | DÃ©finition |
|---|---|
| **BiquadFilter** | Filtre audio second ordre Web Audio API (4 utilisÃ©s dans JARVIS pour EQ) |
| **Blueprint** | Pattern Flask pour modulariser les routes HTTP en sous-applications |
| **Bypass LLM** | Court-circuit du LLM pour commandes dÃ©terministes (VM start/stop, reboot, restart service). Pas d'hallucination, exÃ©cution 200 ms vs 8 s via LLM. |
| **boot_id** | Identifiant unique de session JARVIS (timestamp). ConsommÃ© par `_pollBootId` cÃ´tÃ© JS pour dÃ©tecter un redÃ©marrage serveur. |

## C

| Terme | DÃ©finition |
|---|---|
| **CR / CODE-REASONING** | 4e mode JARVIS, modÃ¨le `qwen3:8b` raisonnement natif streaming |
| **CrowdSec** | IDS communautaire installÃ© sur srv-nginx â€” bans coordonnÃ©s via consensus |
| **CSRF** | Cross-Site Request Forgery â€” token de protection sur les routes POST sensibles |
| **CUDA** | API NVIDIA pour calcul GPU (12.x sur RTX 5080) |

## D

| Terme | DÃ©finition |
|---|---|
| **DeepFilterNet** | ModÃ¨le de rÃ©duction de bruit audio CUDA, prÃ©-warmÃ© au boot |
| **DI** | Dependency Injection â€” pattern d'injection de dÃ©pendances explicite (utilisÃ© partout dans JARVIS via `init(...)`) |
| **DSP** | Digital Signal Processing â€” chaÃ®ne EQ + comp + stereo + reverb appliquÃ©e au TTS |

## E

| Terme | DÃ©finition |
|---|---|
| **Edge-TTS** | Service Microsoft Edge TTS cloud (voix `fr-CA-AntoineNeural` dÃ©faut) |
| **EXPLOIT** | Stade 4 de la Kill Chain (utilisation active d'une vulnÃ©rabilitÃ©) â€” prioritÃ© absolue ban |
| **E2E** | End-to-End â€” tests qui couvrent le navigateur jusqu'au backend (Playwright dans JARVIS) |

## F

| Terme | DÃ©finition |
|---|---|
| **fail2ban** | Outil de ban dynamique basÃ© sur les logs (auth, nginx, ssh) â€” sur srv-nginx |
| **FCrDNS** | Forward-Confirmed reverse DNS â€” mÃ©thode de vÃ©rification des crawlers lÃ©gitimes (Googlebot, etc.) |
| **Flask** | Framework web Python (backend JARVIS) |
| **Flask-Sock** | Extension Flask pour WebSocket (terminal SSH xterm.js) |
| **Frontmatter** | MÃ©tadonnÃ©es YAML en tÃªte de fichier markdown (titre, auteur, date, statut) |

## G

| Terme | DÃ©finition |
|---|---|
| **gemma4** | ModÃ¨le Google 9.6 GB â€” mode GENERAL JARVIS + vision multimodale |
| **GeoIP** | GÃ©olocalisation IP â€” module exploitable pour ban par pays |

## H

| Terme | DÃ©finition |
|---|---|
| **Homelab** | Infrastructure personnelle d'expÃ©rimentation (Marc = 0xCyberLiTech) |
| **HUD** | Heads-Up Display â€” l'interface holographique JARVIS v3.3 |

## I

| Terme | DÃ©finition |
|---|---|
| **Idempotence** | PropriÃ©tÃ© d'une opÃ©ration qu'on peut appeler N fois avec le mÃªme rÃ©sultat (utilisÃ© pour les fix anti-cascade) |
| **IDS** | Intrusion Detection System â€” Suricata sur srv-nginx |

## J

| Terme | DÃ©finition |
|---|---|
| **JARVIS** | Just A Rather Very Intelligent System â€” nom inspirÃ© du film Iron Man |
| **Jinja2** | Moteur de templates Python (10 templates HTML dans `scripts/templates/`) |
| **JS-DIAG** | Instrumentation JS posÃ©e 2026-05-23 pour capturer les erreurs frontend (window.error, unhandledrejection, beforeunload) |

## K

| Terme | DÃ©finition |
|---|---|
| **Kill Chain** | ModÃ¨le d'attaque cyber (5 stades : RECON â†’ SCAN â†’ EXPLOIT â†’ BRUTE â†’ NEUTRALISÃ‰) |
| **Kokoro** | Moteur TTS local CUDA â€” fallback si Edge-TTS indisponible. Voix `ff_siwis`. |

## L

| Terme | DÃ©finition |
|---|---|
| **LLM** | Large Language Model â€” phi4, gemma4, qwen2.5-coder, qwen3 dans JARVIS |
| **LLaVA** | ModÃ¨le vision multimodal (capacitÃ© image dans gemma4) |

## M

| Terme | DÃ©finition |
|---|---|
| **MCP** | Model Context Protocol â€” protocole Anthropic pour intÃ©grer Claude Desktop Ã  JARVIS via 12 outils |
| **ModSec** | ModSecurity â€” WAF Apache pour les sites CLT/PA85 |
| **mxbai-embed-large** | ModÃ¨le d'embeddings 1024-dim utilisÃ© pour le RAG |

## N

| Terme | DÃ©finition |
|---|---|
| **NDT** | "Note de Dette" â€” convention Marc pour classer les findings d'audit (CRITIQUE/MOYEN/FAIBLE) |
| **NVML** | NVIDIA Management Library â€” API Python `pynvml` pour stats GPU |

## O

| Terme | DÃ©finition |
|---|---|
| **Ollama** | Runtime LLM local on-premise (port `:11434`). Backend tous les modÃ¨les JARVIS. |
| **OpenVAS** | Scanner vulnÃ©rabilitÃ©s (passÃ© sur sites CLT/PA85, archivÃ©) |

## P

| Terme | DÃ©finition |
|---|---|
| **Paramiko** | Lib Python SSH client (terminal xterm.js + bypass infra) |
| **phi4:14b** | ModÃ¨le Microsoft 9.1 GB â€” mode SOC JARVIS (dÃ©faut) |
| **Piper** | Moteur TTS local CPU â€” 3e fallback aprÃ¨s Edge et Kokoro |
| **PTY** | Pseudo-terminal â€” terminal interactif via WebSocket (paramiko `invoke_shell()`) |
| **PVE / Proxmox VE** | Hyperviseur sur 192.168.1.20 â€” hÃ©berge srv-nginx + clt + pa85 + srv-dev-1 |
| **pre-warm** | PrÃ©chargement d'un modÃ¨le (Kokoro CUDA, phi4 Ollama) au boot pour Ã©viter cold start |

## Q

| Terme | DÃ©finition |
|---|---|
| **qwen2.5-coder:14b** | ModÃ¨le Alibaba 9 GB â€” mode CODE JARVIS |
| **qwen3:8b** | ModÃ¨le Alibaba 5.2 GB raisonnement â€” mode CODE-REASONING JARVIS |

## R

| Terme | DÃ©finition |
|---|---|
| **RAG** | Retrieval-Augmented Generation â€” JARVIS injecte 599 chunks indexÃ©s dans le prompt LLM |
| **RECON** | Stade 1 Kill Chain (reconnaissance passive) |
| **RFC1918** | Plages IP privÃ©es (10./172.16-31./192.168./127.) â€” **JAMAIS bannies** par rÃ¨gle ABSOLUE |
| **ruff** | Linter Python ultra-rapide (remplace flake8 + isort) â€” 0 erreur dans JARVIS |

## S

| Terme | DÃ©finition |
|---|---|
| **SAPI5** | Speech API Windows natif â€” ultime fallback TTS |
| **SCP** | Secure Copy â€” dÃ©ploiement fichiers via SSH (bypass CODE â†’ srv-dev-1) |
| **SOC** | Security Operations Center â€” dashboard sur srv-nginx v3.107.3 + intÃ©gration JARVIS |
| **SSE** | Server-Sent Events â€” streaming HTTP unidirectionnel (utilisÃ© pour le chat JARVIS) |
| **STT** | Speech-to-Text â€” `faster-whisper large-v3-turbo` CUDA dans JARVIS |
| **Suricata** | IDS rÃ©seau â€” alerte sur signatures malveillantes (port scan, EXPLOIT, etc.) |
| **srv-dev-1 / clt / pa85 / nginx** | HÃ´tes du homelab (VM Proxmox) |

## T

| Terme | DÃ©finition |
|---|---|
| **TTS** | Text-to-Speech â€” chaÃ®ne Edge â†’ Kokoro â†’ Piper â†’ SAPI5 dans JARVIS |
| **Tuile** | Module autoportant JARVIS (Blueprint + DI init). 24 tuiles au 2026-05-23. |

## U

| Terme | DÃ©finition |
|---|---|
| **UFW** | Uncomplicated Firewall â€” pare-feu Debian sur srv-nginx |

## V

| Terme | DÃ©finition |
|---|---|
| **VRAM** | MÃ©moire vidÃ©o GPU (16 GB sur RTX 5080) â€” modÃ¨les Ollama y sont chargÃ©s |
| **vpatch** | Patch virtuel WAF (CrowdSec AppSec ~150 rÃ¨gles CVE) |

## W

| Terme | DÃ©finition |
|---|---|
| **WAF** | Web Application Firewall â€” CrowdSec AppSec + ModSec sur srv-nginx |
| **Web Audio API** | API navigateur pour traitement audio temps rÃ©el (graph DSP JARVIS) |
| **whisper** | ModÃ¨le OpenAI STT (variante `faster-whisper` CTranslate2 dans JARVIS) |

## X

| Terme | DÃ©finition |
|---|---|
| **XDR** | Extended Detection and Response â€” fusion multi-sources SOC (Suricata + ModSec + rsyslog + ...) |
| **xterm.js** | Ã‰mulateur de terminal JavaScript (frontend terminaux SSH JARVIS) |

## Acronymes JARVIS spÃ©cifiques

| Code | Signification |
|---|---|
| **JARVIS-DOC-NN-MM** | Code unique de chaque document de cette base documentaire |
| **`_BLOCKED_SSH`** | Whitelist Python 29 patterns SSH bloquÃ©s (immutable sans validation Marc) |
| **`_ALLOWED_SOC_RESTART_SVCS`** | Whitelist services restart SOC (source unique) |
| **`_pollBootId`** | Fonction JS qui dÃ©tecte un redÃ©marrage serveur (boot_init.js:870) |
| **`_chat_stream_active`** | `threading.Event` signalant un chat SSE en cours |
| **`_VRAM_LOCK`** | `threading.Lock` sÃ©rialisant l'accÃ¨s VRAM Ollama |

