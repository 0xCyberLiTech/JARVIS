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
# MCP Server — 12 outils Claude Desktop

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
Données SOC · Infrastructure · LLM qwen3:8b
```

**Transport réel = streamable-HTTP** (MCP 1.6+). Le serveur expose, via uvicorn/Starlette
sur `127.0.0.1:5010` :

| Route | Méthodes | Rôle |
|-------|----------|------|
| `/mcp` | GET · POST · DELETE | Transport principal streamable-HTTP (session stateless) |
| `/sse` | GET | Transport SSE legacy (rétrocompat) |
| `/messages/` | POST | Canal POST associé au SSE legacy |
| `/health` | GET | Sonde de vie `{ok, service, port, auth}` — toujours ouverte |

> Le serveur ne fait **pas** de stdio/JSON-RPC : tout passe par HTTP sur le port 5010.

**Principe fondamental** : JARVIS filtre et agrège localement.
Claude ne voit que **l'escalade** — jamais les données brutes (logs, IPs, configurations).
Garde-fou de sortie unique : toute réponse renvoyée à Claude est masquée (IPv4 → `[IP]`)
et bornée en taille avant émission.

---

## Les 12 outils

| Outil | Description |
|-------|-------------|
| `jarvis_chat` | Envoyer un message à JARVIS (chat complet avec contexte LLM) |
| `jarvis_soc_status` | État temps réel : bans actifs, ThreatScore, alertes récentes |
| `jarvis_soc_ask` | Question SOC enrichie — injecte l'historique 30j si une IPv4 est détectée |
| `jarvis_stats` | Stats JARVIS : uptime, sessions de chat, appels TTS/STT, modèle actif, état RAG |
| `jarvis_infra_status` | État des serveurs SSH (nginx, clt, pa85, Proxmox) |
| `jarvis_proxmox_vms` | État des VMs Proxmox (`qm list` live) |
| `jarvis_read_file` | Lire un fichier sur un serveur via SSH (lecture seule) |
| `jarvis_model_switch` | Changer le modèle Ollama actif (SOC/GÉNÉRAL/CODE) |
| `jarvis_last_response` | Derniers échanges de la conversation JARVIS en cours |
| `jarvis_code_exec` | Écrire + SCP + exécuter un fichier sur le serveur de dev |
| `jarvis_defense_24h` | Résumé défense SOC 24 h : bans, Kill Chain, IDS, WAF |
| `jarvis_ioc_status` | Score IoC **post-compromission** (0-100, niveau OK/WARN/CRIT) + 6 signaux : AIDE drift, C2 alerts, SSH anomaly, webshells, AppArmor denials, sudo events |

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

## Configuration

Fichier `.mcp.json` à la racine du workspace VSCode (`0xCyberLiTech/.mcp.json`) — transport HTTP :

```json
{
  "mcpServers": {
    "jarvis": {
      "type": "http",
      "url": "http://127.0.0.1:5010/mcp"
    }
  }
}
```

> Le client se connecte au transport streamable-HTTP sur le port 5010. Le serveur est
> lancé séparément (`python jarvis_mcp_server.py` — ou relancé par le watchdog) ; il n'est
> **pas** démarré par le client MCP via stdio.

---

## Authentification (Bearer — opt-in)

Le port 5010 bind `127.0.0.1` (jamais exposé au LAN). En défense en profondeur, un token
Bearer **optionnel** protège `/mcp`, `/sse` et `/messages/` (`/health` reste toujours ouvert).

- **Source unique du token** : fichier local `scripts/jarvis_mcp_token.txt` (gitignoré),
  **ou** variable d'environnement `JARVIS_MCP_TOKEN` (prioritaire sur le fichier).
- **Comportement** : si aucun token n'est configuré → middleware **no-op** (le bind localhost
  reste la seule barrière, aucune connexion existante n'est cassée). Si un token existe → toute
  requête sur les routes protégées doit porter `Authorization: Bearer <token>` (sinon `401`).
  Comparaison en temps constant (anti timing-attack).

**Activer l'auth (2 étapes)** :

1. Créer le fichier token : écrire le secret dans `scripts/jarvis_mcp_token.txt` (ou exporter
   `JARVIS_MCP_TOKEN`), puis relancer le serveur MCP.
2. Ajouter l'en-tête dans `.mcp.json` :

```json
{
  "mcpServers": {
    "jarvis": {
      "type": "http",
      "url": "http://127.0.0.1:5010/mcp",
      "headers": { "Authorization": "Bearer <token>" }
    }
  }
}
```

---

## Identifiant visuel dans VSCode

Chaque réponse JARVIS est encadrée pour la différencier de Claude :

```
╔══════════════════════════════╗
║  ◈  JARVIS  —  qwen3:8b  ◈  ║
╚══════════════════════════════╝
[réponse de JARVIS]
```

Différence visuelle immédiate : une réponse de JARVIS se distingue d'un coup d'œil d'une réponse de Claude.

---

## Watchdog

Le watchdog (`jarvis_watchdog.ps1`) sonde JARVIS (`localhost:5000/api/health`) **et**, depuis
l'audit 2026-06-22, le MCP via `http://127.0.0.1:5010/health`. Si JARVIS tourne mais que le MCP
ne répond pas, le watchdog relance `jarvis_mcp_server.py --port 5010`.

---

## Observabilité — log applicatif

Le serveur écrit un log applicatif borné `scripts/jarvis_mcp.log`
(`RotatingFileHandler`, 512 Ko × 3 fichiers). Il trace le démarrage (port + état de l'auth),
les erreurs d'outil et les cas où JARVIS:5000 est injoignable.
Avant l'audit 2026-06-22 le MCP n'avait aucun log (uvicorn `log_level=error`, sortie redirigée
vers `DEVNULL`) — toute panne était invisible.

---

**Précédent ←** [05 — Installation](05-INSTALLATION.md) &nbsp;&nbsp; **Retour →** [README](../README.md)

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
