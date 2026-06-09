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
# J.A.R.V.I.S

> **Assistant IA local · 100 % privé · Interface holographique · SOC cybersécurité**

JARVIS est un assistant IA personnel de type Iron Man construit sur Python/Flask + Ollama.
Tout tourne en local — aucune donnée ne quitte la machine.

<div align="center">
  <img src="Images/Jarvis.png" alt="JARVIS — interface holographique principale" width="900"/>
</div>

---

## Hermès — L'agent persistant

<div align="center">
  <img src="Images/hermes.png" alt="Hermès — synoptique 6 couches actives" width="820"/>
</div>

<br/>

> **Hermès transforme un assistant en agent.**
> Là où un assistant répond à des questions, un agent **observe, mémorise, apprend et agit** — sans être re-briefé à chaque session.

<div align="center">

| Brique | Rôle |
|--------|------|
| **Synoptique temps réel** | 6 couches moteur visibles dans l'interface : LLM actif, RAG, STT/TTS, auto-engine SOC, état mémoire |
| **Tuile Mémoire** | Mémoire vectorielle persistante — échanges, résumés, leçons apprises — rechargeable sans redémarrage |
| **Bypass déterministe** | Commandes critiques interceptées avant le LLM : exécution instantanée < 100 ms, 0 hallucination |
| **Boucle d'apprentissage** | `"Souviens-toi que X"` → leçon persistée, indexée, réinjectée automatiquement dans les futures réponses |
| **Briefing matinal** | `"Bonjour JARVIS"` → niveau de menace SOC, état des machines, alertes des 24 dernières heures |

</div>

<div align="center">

| Avant Hermès | Après Hermès |
|--------------|--------------|
| Chaque session recommence à zéro | Contexte conservé entre les sessions |
| Le contexte disparaît au redémarrage | Leçons et conventions indexées dans le RAG |
| L'assistant répond seulement | L'agent surveille, alerte et agit |
| Toutes les commandes passent par le LLM | Bypass déterministe pour les commandes critiques |

</div>

---

## À propos & Objectifs

<div align="center">

| Objectif | Description |
|----------|-------------|
| **100 % local** | LLM, STT, TTS, RAG, données — tout sur le poste de travail (GPU NVIDIA CUDA) |
| **Agentification** | Hermès — mémoire longue durée, apprentissage inter-sessions, briefing automatique |
| **SOC cybersécurité** | Auto-engine de détection, ban automatique, alertes vocales, injection contexte sécurité live |
| **Accessibilité** | Interface haute lisibilité, alertes vocales TTS, commandes vocales à bypass déterministe |
| **Qualité** | 1 465 tests · 79 % coverage · ruff 0 · eslint 0 · hooks bloquants |

</div>

---

## Sommaire

<div align="center">

| # | Document | Description | Statut | |
|---|----------|-------------|--------|---|
| 01 | [Hermès — Agent persistant](DOCUMENTATION/01-HERMES.md) | 5 briques · bypass déterministe · boucle apprentissage · briefing matinal | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/01-HERMES.md) |
| 02 | [Intégration SOC](DOCUMENTATION/02-SOC-INTEGRATION.md) | Auto-engine · ban/unban · alertes vocales · injection contexte sécurité | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/02-SOC-INTEGRATION.md) |
| 03 | [Architecture globale](DOCUMENTATION/03-ARCHITECTURE.md) | 5 zones · Flask · Blueprints · modules · polling | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/03-ARCHITECTURE.md) |
| 04 | [Audio DSP](DOCUMENTATION/04-AUDIO-DSP.md) | Chaîne broadcast · TTS 4 moteurs · STT faster-whisper · DSP 3 étages | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/04-AUDIO-DSP.md) |
| 05 | [Installation](DOCUMENTATION/05-INSTALLATION.md) | Pré-requis matériel · Python · Ollama · lancement · vérification | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/05-INSTALLATION.md) |
| 06 | [MCP Server](DOCUMENTATION/06-MCP-SERVER.md) | 12 outils · Claude Desktop · watchdog · principe de séparation | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/06-MCP-SERVER.md) |

</div>

---

## Stack technique

<div align="center">

| Couche | Technologie |
|--------|-------------|
| **Backend** | Python 3.11 · Flask · Blueprints autoportants · DI pur |
| **LLM local** | Ollama · phi4:14b (SOC) · gemma4:latest (GÉNÉRAL + vision) · qwen2.5-coder:14b (CODE) |
| **RAG** | mxbai-embed-large · BM25 hybride · ~600 chunks · TTL 5 min |
| **TTS** | edge-tts fr-CA Antoine → Kokoro CUDA → SAPI5 (cascade automatique) |
| **STT** | faster-whisper large-v3-turbo CUDA · vocabulaire SOC |
| **Frontend** | Vanilla JS · 21 modules · Web Audio API · xterm.js · Monaco Editor |
| **Agent Hermès** | 5 briques · bypass regex · scheduler daemon · DI pur · indépendant du LLM |
| **MCP** | 12 outils exposés à Claude Desktop · streamable-HTTP · watchdog |
| **Qualité** | 1 465 pytest · 79 % coverage · ruff 0 · eslint 0 · hooks pré-commit/pré-push |

</div>

---

## Sécurité

<div align="center">

| Principe | Implémentation |
|----------|----------------|
| **100 % local** | JARVIS filtre et agrège localement — rien ne part vers un LLM cloud |
| **RFC1918 immuable** | Les plages IP privées ne peuvent jamais être bannies |
| **SSH lecture seule** | 29 patterns dangereux bloqués · whitelist explicite pour l'écriture |
| **SOC side-channel** | Le contexte sécurité n'entre jamais dans l'historique chat |
| **Audit forensique** | Toute opération SSH d'écriture tracée dans un journal JSONL |

</div>

---

**Commencer →** [01 — Hermès, l'agent persistant](DOCUMENTATION/01-HERMES.md)

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
