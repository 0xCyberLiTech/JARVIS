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
    <a href="https://github.com/0xCyberLiTech/JARVIS/tags">
      <img src="https://img.shields.io/github/v/tag/0xCyberLiTech/JARVIS?sort=semver&label=version&style=flat-square&color=blue" alt="Dernière version" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/blob/main/CHANGELOG.md">
      <img src="https://img.shields.io/badge/%F0%9F%93%84%20Changelog-JARVIS-blue?style=flat-square" alt="Changelog" />
    </a>
    <a href="https://github.com/0xCyberLiTech?tab=repositories">
      <img src="https://img.shields.io/badge/D%C3%A9p%C3%B4ts-publics-blue?style=flat-square" alt="Dépôts publics" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/graphs/contributors">
      <img src="https://img.shields.io/badge/%F0%9F%91%A5%20Contributeurs-cliquez%20ici-007ec6?style=flat-square" alt="Contributeurs" />
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
# MCP Server — outils exposés à Claude Code (VSCode)

## Objectif
Le MCP Server est le pont qui permet à **Claude Code** (dans VSCode) d'interroger JARVIS
et d'accéder aux données SOC en temps réel — sans exposer les données brutes vers le cloud.

---

## Architecture

```
Claude Code (VSCode)
    │  MCP streamable-HTTP — POST/GET/DELETE http://127.0.0.1:5010/mcp
    │  (SSE legacy /sse + /messages/ conservés pour compat)
    ▼
jarvis_mcp_server.py  (uvicorn + Starlette — port 5010)
    │  HTTP 127.0.0.1:5000
    ▼
JARVIS (Flask)
    │  SSH local + Ollama + fichiers
    ▼
Données SOC · Infrastructure · LLM qwen3.5:9b
```

**Transport réel = streamable-HTTP** (MCP 1.6+). Le serveur expose, via uvicorn/Starlette
sur `127.0.0.1:5010` :

| Route | Méthodes | Rôle |
|-------|----------|------|
| `/mcp` | GET · POST · DELETE | Transport principal streamable-HTTP (session stateless) |
| `/sse` | GET | Transport SSE legacy (rétrocompat) |
| `/messages/` | POST | Canal POST associé au SSE legacy |
| `/health` | GET | Sonde de vie `{ok, service, port, auth, uptime_s, calls}` — toujours ouverte |

> Le serveur ne fait **pas** de stdio/JSON-RPC : tout passe par HTTP sur le port 5010.

**Principe fondamental** : JARVIS filtre et agrège localement.
Claude ne voit que **l'escalade** — jamais les données brutes (logs, IPs, configurations).
Garde-fou de sortie unique : toute réponse renvoyée à Claude est masquée (IPv4 → `[IP]`)
et bornée en taille avant émission.

---

## Les outils

| Outil | Description |
|-------|-------------|
| `jarvis_chat` | Envoyer un message à JARVIS (chat complet avec contexte LLM) |
| `jarvis_soc_status` | État temps réel : bans actifs, ThreatScore, alertes récentes |
| `jarvis_soc_ask` | Question SOC enrichie — injecte l'historique 30j si une IPv4 est détectée |
| `jarvis_investigate_ip` | Investigation approfondie d'une IP (géoloc, historique, corrélation) via l'endpoint SOC dédié |
| `jarvis_stats` | Stats JARVIS : uptime, sessions de chat, appels TTS/STT, modèle actif, état RAG |
| `jarvis_infra_status` | État des serveurs SSH (nginx, clt, pa85, Proxmox) |
| `jarvis_proxmox_vms` | État des VMs Proxmox (`qm list` live) |
| `jarvis_read_file` | Lire un fichier sur un serveur via SSH (lecture seule) |
| `jarvis_model_switch` | Changer le modèle Ollama actif — bascule réversible, refusée si le modèle n'est pas installé |
| `jarvis_last_response` | Derniers échanges de la conversation JARVIS en cours |
| `jarvis_code_exec` | Écrire + SCP + exécuter un fichier sur le serveur de dev |
| `jarvis_defense_24h` | Résumé défense SOC 24 h : bans, Kill Chain, IDS, WAF |
| `jarvis_ioc_status` | Score IoC **post-compromission** (0-100, niveau OK/WARN/CRIT) + 6 signaux : AIDE drift, C2 alerts, SSH anomaly, webshells, AppArmor denials, sudo events |
| `jarvis_vision` | Analyser une **image** via le modèle multimodal **LOCAL** (100% privé, sur la GPU du poste) — décrire une capture d'écran, lire un graphique/tableau, extraire du texte. Wrappe `POST /api/vision` (base64 + prompt optionnel ; jpeg/png/gif/webp/bmp) |

> Le catalogue d'outils est **compté LIVE** (dérivé de la source unique, jamais figé dans la prose) —
> un garde-fou refuse tout nombre d'outils codé en dur dans la documentation.

---

## Déterminisme — zéro hallucination sur les faits

Principe : un outil qui renvoie un **fait** (état des VMs, statut serveur, investigation IP) frappe
un **endpoint déterministe** de JARVIS, **jamais** le LLM. Seuls les outils d'**analyse**
(`jarvis_chat`, `jarvis_soc_ask`) passent par le modèle. Ainsi Claude ne peut recevoir une réponse
« inventée » : un état de VM vient de l'API Proxmox, pas d'une génération de texte.

| Nature | Exemples | Source |
|--------|----------|--------|
| **Fait** (déterministe) | `jarvis_infra_status`, `jarvis_proxmox_vms`, `jarvis_investigate_ip`, `jarvis_soc_status` | endpoints JARVIS (API/collecteurs) |
| **Analyse** (LLM) | `jarvis_chat`, `jarvis_soc_ask`, `jarvis_vision` | modèle qwen3.5:9b (multimodal pour la vision) |

Un garde-fou vérifie qu'aucun handler de « fait » n'appelle la route de chat LLM.

---

## Séparation des responsabilités

| JARVIS traite localement | Claude reçoit en escalade |
|--------------------------|--------------------------|
| Logs bruts → résumé structuré | Pattern inconnu de JARVIS |
| Patterns SOC connus → auto-ban | Modification du code source |
| Questions SOC état/compteurs | Décision architecturale |
| Monitoring routine normal → **0 token Claude** | Infra complètement en panne |
| Debugging simple à modéré | Analyse multi-fichiers complexe |

---

## Transport & authentification (conception)

Le serveur ne fait **pas** de stdio/JSON-RPC : tout passe par HTTP sur `127.0.0.1:5010`,
transport streamable-HTTP (MCP 1.6+). Le serveur vit **indépendamment** du client — il est
supervisé par le watchdog, jamais démarré à la demande par le client.

**Authentification fail-closed — toujours active.** Le port bind `127.0.0.1` (jamais exposé au
LAN). En défense en profondeur, un token Bearer protège `/mcp`, `/sse` et `/messages/`
(`/health` reste ouvert) :

- **Source unique du token** : variable d'environnement prioritaire, sinon fichier local gitignoré
  (permissions `600`).
- **Fail-closed** : si **aucun** token n'existe, le serveur en **génère un** (aléatoire, 32 octets)
  et le **persiste** au premier démarrage — l'auth n'est **jamais désactivée**. Pas de mode
  « no-op » : sans le bon `Authorization: Bearer`, la requête reçoit `401`. Comparaison en temps
  constant (anti timing-attack).

### Rotation du token (procédure)

Le serveur **fige le token au démarrage** (`_load_mcp_token()` lu une fois). Une rotation doit donc
**synchroniser 3 choses** puis **redémarrer le MCP** — sinon `.mcp.json` (client) et le serveur en
mémoire divergent (→ `401`). Ordre atomique :

1. Écrire un nouveau token dans `jarvis_mcp_token.txt` (`secrets.token_urlsafe(32)` ; **gitignoré**).
2. Synchroniser le `Authorization: Bearer <token>` dans **`.mcp.json`** (à la **racine du workspace**,
   pas dans `scripts/`).
3. Redémarrer le MCP : **tuer le process** écoutant sur `5010` → le watchdog `_mcp_liveness_watch`
   le **respawn** (< 15 s) en relisant le fichier. (Si `JARVIS_MCP_TOKEN` est défini en env, il
   **prime** sur le fichier → roter l'env à la place.)
4. Vérifier : `curl -X POST -H "Authorization: Bearer <ancien>" http://127.0.0.1:5010/mcp` → **401** ;
   avec le nouveau → **non-401**.

> Rotation effectuée le 2026-07-06 (l'ancien token traînait dans l'historique `scripts/.git`, sans
> remote donc sans fuite publique, mais invalidé par principe).

---

## Identifiant visuel dans VSCode

Chaque réponse JARVIS est encadrée pour la différencier de Claude :

```
╔══════════════════════════════╗
║  ◈  JARVIS — qwen3.5:9b  ◈  ║
╚══════════════════════════════╝
[réponse de JARVIS]
```

Différence visuelle immédiate : une réponse de JARVIS se distingue d'un coup d'œil d'une réponse de Claude.

---

## Autonomie & watchdog — zéro intervention

Deux couches garantissent que le MCP survit sans intervention manuelle :

1. **Liveness interne** — JARVIS lance le MCP dans un *Job Object* (le MCP meurt **avec** JARVIS,
   jamais orphelin) et un thread de surveillance le **relance automatiquement** s'il s'arrête seul
   (compteur de respawns exposé dans `/health` et sur la tuile MCP du dashboard).
2. **Watchdog externe** — `jarvis_watchdog.ps1` sonde JARVIS (`localhost:5000/api/health`) **et**
   le MCP via `http://127.0.0.1:5010/health`. Filet de sécurité : si JARVIS tourne mais que le MCP
   ne répond pas, le watchdog relance `jarvis_mcp_server.py --port 5010`.

La tuile MCP du dashboard affiche la stabilité en direct : uptime, nombre d'appels, respawns.

---

## Observabilité — log applicatif

Le serveur écrit un log applicatif borné `scripts/jarvis_mcp.log`
(`RotatingFileHandler`, 512 Ko × 3 fichiers). Il trace le démarrage (port + état de l'auth),
les erreurs d'outil et les cas où JARVIS:5000 est injoignable.
Avant l'audit 2026-06-22 le MCP n'avait aucun log (uvicorn `log_level=error`, sortie redirigée
vers `DEVNULL`) — toute panne était invisible.

---

**Précédent ←** [04 — Audio DSP](04-AUDIO-DSP.md) &nbsp;&nbsp; **Retour →** [README](../README.md)

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
