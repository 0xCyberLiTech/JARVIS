<div align="center">

  <br/>

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=50&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS_" alt="JARVIS" />
  </a>

  <br/>

  <h2>J.A.R.V.I.S — Assistant IA local · Agent Hermès · SOC cybersécurité</h2>

  <p align="center">
    <a href="https://github.com/0xCyberLiTech">
      <img src="https://img.shields.io/badge/Portfolio-0xCyberLiTech-181717?logo=github&style=flat-square" alt="Portfolio" />
    </a>
    &nbsp;
    <a href="https://github.com/0xCyberLiTech/JARVIS">
      <img src="https://img.shields.io/badge/GitHub-JARVIS-8B5CF6?logo=github&style=flat-square" alt="GitHub JARVIS" />
    </a>
    &nbsp;
    <img src="https://img.shields.io/badge/tests-1465%20pass-22C55E?style=flat-square" alt="Tests" />
    &nbsp;
    <img src="https://img.shields.io/badge/coverage-79%25-22C55E?style=flat-square" alt="Coverage" />
    &nbsp;
    <img src="https://img.shields.io/badge/score-97%2F100-8B5CF6?style=flat-square" alt="Score qualité" />
    &nbsp;
    <img src="https://img.shields.io/badge/Python-3.11-00B4D8?style=flat-square&logo=python&logoColor=white" alt="Python 3.11" />
    &nbsp;
    <img src="https://img.shields.io/badge/Ollama-local-F59E0B?style=flat-square" alt="Ollama" />
    &nbsp;
    <img src="https://img.shields.io/badge/usage-personnel-lightgrey?style=flat-square" alt="Licence" />
  </p>

</div>

---

<div align="center">
  <img src="https://img.icons8.com/fluency/96/000000/artificial-intelligence.png" alt="IA" width="80"/>
</div>

---

## ⚡ Hermès — L'agent persistant au coeur de JARVIS

<div align="center">
  <img src="Images/hermes.png" alt="Hermès — synoptique 6 couches actives" width="800"/>
</div>

<br/>

> **Hermès est ce qui transforme un assistant en agent.**  
> Là où un assistant répond à des questions, un agent **observe, mémorise, apprend et agit** de façon autonome — sans être re-briefé à chaque session.

### Les 5 briques de l'agent

| Brique | Rôle |
|--------|------|
| **Synoptique temps réel** | 6 couches moteur visibles dans l'interface : LLM actif, chunks RAG chargés, STT/TTS, auto-engine SOC, état mémoire |
| **Tuile Mémoire** | État de la mémoire vectorielle — échanges, résumés, leçons apprises — rechargement RAG depuis l'interface sans redémarrage |
| **Bypass déterministe** | Les commandes critiques (`"recharge le RAG"`, `"vide la mémoire"`, `"état des VMs"`) sont interceptées avant le LLM — exécution instantanée < 100 ms |
| **Boucle d'apprentissage** | `"Souviens-toi que X"` → leçon persistée, indexée dans la base vectorielle, réinjectée automatiquement dans toutes les futures réponses |
| **Briefing matinal** | `"Bonjour JARVIS"` → briefing vocal complet : niveau de menace SOC, état des machines, alertes des dernières 24 h |

### Avant / Après Hermès

| Avant | Après |
|-------|-------|
| Chaque session recommence à zéro | JARVIS accumule les leçons à travers les sessions |
| Le contexte est perdu au redémarrage | Les préférences, règles et conventions sont indexées dans le RAG |
| L'assistant répond, il n'agit pas | L'agent surveille, alerte, et agit sur seuil dépassé |
| Les commandes passent toujours par le LLM | Les commandes critiques ont un bypass déterministe (zéro LLM, 0 hallucination) |

---

## 🤖 À propos & Objectifs

**JARVIS** est une interface web holographique locale de type Iron Man, construite sur **Python/Flask + Ollama**.  
Elle intègre un chat IA multi-modèles, un terminal SSH, un monitoring GPU/système en temps réel, un Voice Lab complet (STT + TTS CUDA), un éditeur audio DSP broadcast et une intégration SOC cybersécurité.

Tout tourne **entièrement en local** — aucune donnée ne quitte la machine vers un LLM cloud.

| Objectif | Description |
|----------|-------------|
| **100 % local** | LLM, STT, TTS, RAG, données — tout sur le poste de travail (RTX 5080 CUDA) |
| **Agentification persistante** | Hermès — mémoire longue durée, apprentissage inter-sessions, briefing automatique |
| **SOC cybersécurité** | Auto-engine de détection, ban automatique, alertes vocales, injection contexte sécurité |
| **Accessibilité** | Interface haute lisibilité, alertes vocales TTS, commandes vocales déterministes |
| **Qualité sans compromis** | 1 465 tests · 79 % coverage · ruff 0 · eslint 0 · hooks bloquants pre-commit/pre-push |

---

## 🖼️ Aperçu

<div align="center">

| | |
|:---:|:---:|
| <img src="Images/photo-01.jpg" alt="JARVIS interface" width="400"/> | <img src="Images/photo-02.jpg" alt="SOC dashboard" width="400"/> |
| <img src="Images/photo-03.jpg" alt="Voice Lab" width="400"/> | <img src="Images/photo-04.jpg" alt="DSP Audio" width="400"/> |
| <img src="Images/photo-05.jpg" alt="Monitor GPU" width="400"/> | <img src="Images/photo-06.jpg" alt="Terminal SSH" width="400"/> |

</div>

---

## 📋 Sommaire

| # | Section | Documents |
|---|---------|-----------|
| 01 | [Hermès — Modes & Routing](#01--hermès--modes--routing) | 1 doc |
| 02 | [Intégration SOC](#02--intégration-soc) | 2 docs |
| 03 | [Architecture](#03--architecture) | 5 docs |
| 04 | [Installation](#04--installation) | 3 docs |
| 05 | [Exploitation](#05--exploitation) | 3 docs |
| 06 | [Qualité](#06--qualité) | 3 docs |

---

## 01 — Hermès : Modes & Routing

| Document | Description | |
|----------|-------------|---|
| Routing & Modes | 4 modes (SOC · GÉNÉRAL · CODE · CR) · bypass déterministe · règles de sécurité | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/01-HERMES/ROUTING-MODES.md) |

---

## 02 — Intégration SOC

| Document | Description | |
|----------|-------------|---|
| MCP Server | 12 outils MCP exposés à Claude Desktop · port streamable-HTTP · watchdog | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/02-SOC/MCP-SERVER.md) |
| Circuit SOC ↔ JARVIS | Auto-engine · ban/unban · injection contexte sécurité live | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/02-SOC/SOC-INTEGRATION.md) |

---

## 03 — Architecture

| Document | Description | |
|----------|-------------|---|
| Architecture globale | Vue d'ensemble · 5 zones fonctionnelles · diagrammes ASCII | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/03-ARCHITECTURE/OVERVIEW.md) |
| Schéma IA locale | Pipeline LLM · RAG · STT · TTS · Ollama · routing décisionnel | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/03-ARCHITECTURE/IA-PIPELINE.md) |
| Audio DSP | Web Audio graph broadcast · BiquadFilter · Compresseur · Convolver · DeepFilterNet | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/03-ARCHITECTURE/AUDIO-DSP.md) |
| Référence technique | Routes Flask · API endpoints · structures de données · Blueprints | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/03-ARCHITECTURE/REFERENCE-TECHNIQUE.md) |
| Tuiles & Blueprints | Modèle des tuiles autoportantes · DI pur · 33 modules Python | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/03-ARCHITECTURE/TILES.md) |

---

## 04 — Installation

| Document | Description | |
|----------|-------------|---|
| Installation | Installation pas à pas · virtualenv · Ollama · dépendances CUDA | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/04-INSTALLATION/INSTALLATION.md) |
| Pré-requis | Matériel minimum · versions Python/CUDA · modèles Ollama requis | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/04-INSTALLATION/PRE-REQUIS.md) |
| Réinstallation | Procédure disaster recovery · coffre de sauvegarde · restauration complète | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/04-INSTALLATION/REINSTALLATION.md) |

---

## 05 — Exploitation

| Document | Description | |
|----------|-------------|---|
| Runbook | Procédures opérationnelles · démarrage/arrêt · MAJ Ollama · maintenance | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/05-EXPLOITATION/RUNBOOK.md) |
| Observabilité & Logs | jarvis.log · rotation · diagnostics · métriques runtime | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/05-EXPLOITATION/OBSERVABILITE.md) |
| Support & Infogérance | Dépannage · cas fréquents · reset d'urgence | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/05-EXPLOITATION/SUPPORT.md) |

---

## 06 — Qualité

| Document | Description | |
|----------|-------------|---|
| Bilan technique | Score · métriques · décisions architecturales (source unique) | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/06-QUALITE/BILAN-TECHNIQUE.md) |
| Dette technique | Inventaire dette assumée · décisions de gel documentées | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/06-QUALITE/DETTE-TECHNIQUE.md) |
| Roadmap | Évolutions prévues · fonctionnalités en cours | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white" alt="Explorer">](DOCUMENTATION/06-QUALITE/ROADMAP.md) |

---

## 🧠 Stack technique

| Couche | Technologie |
|--------|-------------|
| **Backend** | Python 3.11 · Flask · 33 modules · Blueprints autoportants avec DI pur |
| **LLM local** | Ollama · phi4:14b (SOC/raisonnement) · gemma4 (GÉNÉRAL + vision) · qwen2.5-coder:14b (CODE) |
| **RAG** | mxbai-embed-large · BM25 hybride · ~600 chunks · TTL 5 min · warmup au démarrage |
| **TTS** | edge-tts fr-CA Antoine (défaut) → Kokoro CUDA → SAPI5 (fallback automatique) |
| **STT** | faster-whisper large-v3-turbo CUDA · vocabulaire spécialisé SOC |
| **Frontend** | Vanilla JS · 21 modules · Web Audio API · xterm.js · Monaco Editor |
| **Agent Hermès** | 5 briques · bypass regex déterministe · scheduler daemon · DI pur |
| **MCP** | 12 outils exposés à Claude Desktop · streamable-HTTP · watchdog |
| **Tests** | 1 465 pytest · 0 fail · 79 % coverage · ruff 0 · eslint 0 · hooks pre-commit/pre-push bloquants |

```
Windows 11 (localhost:5000)
├── jarvis.py (Flask — orchestrateur, 75 routes)
├── blueprints/soc.py (Auto-engine SOC, poll Python 60s)
├── Bypass Hermès (morning_brief · learn · sysctrl · wrappers)
├── Ollama (:11434)
│   ├── phi4:14b             9.1 GB  ← SOC/raisonnement (défaut, toujours chaud)
│   ├── qwen2.5-coder:14b    9.0 GB  ← CODE · dev · SCP
│   ├── gemma4:latest        9.6 GB  ← GÉNÉRAL + vision native
│   └── mxbai-embed-large    0.7 GB  ← RAG embeddings · keep_alive 10m
├── STT : faster-whisper large-v3-turbo (CUDA float16)
├── TTS : edge-tts Antoine → Kokoro (CUDA) → SAPI5
├── RAG : BM25 + vecteur hybride · ~600 chunks · seuil 0.35
└── MCP : jarvis_mcp_server.py — 12 outils · Claude Desktop
```

---

## 🛡️ Sécurité

| Principe | Implémentation |
|----------|----------------|
| **100 % local** | JARVIS filtre et agrège en local — rien ne quitte la machine vers un LLM cloud |
| **IPs privées immuables** | Plages RFC1918 jamais bannies, quelle que soit la situation |
| **SSH lecture seule** | 29 patterns bloqués par défaut · whitelist explicite pour les opérations d'écriture |
| **Injection SOC côté serveur** | Le contexte sécurité n'entre jamais dans l'historique chat — injection side-channel |
| **Auto-engine isolé** | Actif uniquement en mode `soc` — jamais en mode général ou code |
| **Audit forensique** | Toute opération d'écriture SSH journalisée dans `audit_writeops.jsonl` |

---

## 🔧 Qualité

| Indicateur | Valeur |
|------------|--------|
| Tests pytest | **1 465 pass · 0 fail** |
| Coverage | **79 %** |
| Linter Python (ruff) | **0 erreur** |
| Linter JS (eslint) | **0 erreur** |
| Pre-commit hooks | ruff + eslint bloquants |
| Pre-push hook | pytest bloquant |
| Score qualité global | **97 / 100** |

Source unique → [Bilan technique](DOCUMENTATION/06-QUALITE/BILAN-TECHNIQUE.md)

---

## 📁 Structure du projet

```
JARVIS/
├── DOCUMENTATION/
│   ├── 01-HERMES/          ← Modes, routing, agent Hermès
│   ├── 02-SOC/             ← MCP Server, circuit SOC ↔ JARVIS
│   ├── 03-ARCHITECTURE/    ← 5 docs techniques (overview, IA, DSP, API, tuiles)
│   ├── 04-INSTALLATION/    ← Installation, pré-requis, disaster recovery
│   ├── 05-EXPLOITATION/    ← Runbook, observabilité, support
│   └── 06-QUALITE/         ← Bilan, dette, roadmap
├── Images/
│   ├── hermes.png          ← Synoptique Hermès (6 couches)
│   └── Jarvis.png          ← Logo JARVIS
├── scripts/                ← Code source
│   ├── jarvis.py           ← Orchestrateur Flask (75 routes)
│   ├── bypass/             ← Agent Hermès (morning_brief, learn, sysctrl)
│   ├── blueprints/soc.py   ← Blueprint SOC — auto-engine
│   ├── chat/               ← Dispatcher · routing · contexte sécurité
│   ├── rag/                ← Moteur RAG hybride (BM25 + vecteur)
│   ├── voice/              ← STT · TTS · DSP audio
│   ├── jarvis_mcp_server.py← MCP bridge (12 outils)
│   ├── static/             ← JS (21 modules) · CSS
│   └── templates/          ← HTML
├── tests/                  ← pytest · 1 465 tests · 79 % coverage
└── tools/                  ← Outils dev (profiling, diagnostics)
```

---

<div align="center">

<table>
<tr>
<td align="center"><b>🖥️ Infrastructure & Sécurité</b></td>
<td align="center"><b>💻 Développement & Web</b></td>
<td align="center"><b>🤖 Intelligence Artificielle</b></td>
</tr>
<tr>
<td align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=linux,nginx,debian" />
  </a>
</td>
<td align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=python,js,html,css,flask" />
  </a>
</td>
<td align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=pytorch,cuda" />
  </a>
</td>
</tr>
</table>

</div>

---

<div align="center">

<sub>🤖 Projet réalisé par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · Développé en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🤖</sub>

</div>
