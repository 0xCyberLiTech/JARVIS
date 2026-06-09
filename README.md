# J.A.R.V.I.S — Assistant IA Local & SOC Cybersécurité

> **Agent persistant · 100 % local · SOC cybersécurité · Voix · Mémoire vectorielle**

**Créateur** : Marc Sabater — [0xCyberLiTech](https://github.com/0xCyberLiTech) &nbsp;·&nbsp; RTX 5080 &nbsp;·&nbsp; Ollama local

![Tests](https://img.shields.io/badge/tests-1465%20pass-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-79%25-green)
![Score](https://img.shields.io/badge/score%20qualit%C3%A9-97%2F100-blue)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Licence](https://img.shields.io/badge/licence-usage%20personnel-lightgrey)

---

## Sommaire

- [Qu'est-ce que JARVIS ?](#quest-ce-que-jarvis-)
- [Hermès — Agent persistant](#hermès--agent-persistant)
- [SOC Cybersécurité](#soc-cybersécurité)
- [Lancement rapide](#-lancement-rapide)
- [Stack technique](#-stack-technique)
- [Documentation](#-documentation)
- [Structure du projet](#-structure-du-projet)
- [Sécurité](#-sécurité)
- [Qualité](#-qualité)
- [Licence](#-licence)

---

## Qu'est-ce que JARVIS ?

JARVIS est une interface web locale type **Iron Man** construite sur Python/Flask + Ollama.  
Elle intègre un chat IA multi-modèles, un terminal SSH, un monitoring GPU/système en temps réel,
un Voice Lab complet (STT + TTS CUDA), un éditeur audio DSP et une intégration SOC cybersécurité.

Tout tourne **entièrement en local** — aucune donnée ne quitte la machine.

---

## Hermès — Agent persistant

![Hermès — synoptique 6 couches actives : LLM, RAG, STT, TTS, SOC, MÉMOIRE](Images/hermes.png)

Hermès est la couche d'**agentification persistante** de JARVIS.  
Là où un assistant répond à des questions, un agent **observe, mémorise, apprend et agit** de façon autonome.

| Brique | Rôle |
|--------|------|
| **Synoptique** | 6 couches moteur visibles en temps réel : LLM actif, chunks RAG chargés, STT/TTS, auto-engine SOC, mémoire |
| **Tuile Mémoire** | État de la mémoire vectorielle — échanges, résumés, leçons apprises — rechargement RAG depuis l'interface |
| **Commandes vocales** | Bypass LLM déterministe — *"recharge le RAG"*, *"vide la mémoire"* — exécution instantanée, sans LLM |
| **Boucle d'apprentissage** | *"Souviens-toi que X"* → leçon persistée, indexée dans le RAG, réinjectée automatiquement dans les futures réponses |
| **Briefing matinal** | *"Bonjour JARVIS"* → briefing vocal complet : niveau de menace SOC, état des machines, alertes 24 h |

**Avant Hermès** — chaque session recommençait à zéro. Le contexte était perdu au redémarrage.  
**Après Hermès** — JARVIS accumule les leçons, les indexe dans sa base vectorielle et les réinjecte.
Il connaît les règles d'infra, les conventions de code, les préférences utilisateur — sans être re-briefé.

---

## SOC Cybersécurité

JARVIS s'intègre avec un dashboard SOC homelab (CrowdSec · fail2ban · Suricata · ModSec)
et expose des capacités de **réponse automatisée** :

| Capacité | Description |
|----------|-------------|
| **Auto-engine SOC** | Analyse le niveau de menace en continu — ban automatique si seuil dépassé, restart automatique si service down |
| **Injection contexte** | Le contexte sécurité (IPs actives, menaces 24 h, Kill Chain) est injecté côté serveur dans chaque réponse LLM en mode SOC |
| **Routes SOC sécurisées** | ban-ip · unban-ip · restart-service — opérations protégées par whitelist RFC1918 et liste de services explicite |
| **MCP Claude Desktop** | 12 outils exposés : `jarvis_soc_status`, `jarvis_soc_ask`, `jarvis_ioc_status`, `jarvis_proxmox_vms`... |
| **Alertes vocales** | TTS déclenché automatiquement si niveau de menace ÉLEVÉ ou CRITIQUE |

Intégration détaillée → [03-01 Circuit SOC ↔ JARVIS](DOCUMENTATION/03-INTEGRATION-SOC/03-01-CIRCUIT-SOC-JARVIS.md)

---

## 🚀 Lancement rapide

```bat
start_dashboard.bat
```

Lance l'environnement virtuel Python, démarre Ollama et ouvre l'interface dans le navigateur.

**Arrêt** : `stop_jarvis.bat`

Pré-requis → [04-03 Pré-requis](DOCUMENTATION/04-DEPLOIEMENT/04-03-PRE-REQUIS.md)  
Installation complète → [04-01 Déploiement](DOCUMENTATION/04-DEPLOIEMENT/04-01-DEPLOIEMENT.md)

---

## 🧠 Stack technique

| Couche | Technologie |
|--------|-------------|
| **Backend** | Python 3.11 · Flask · 33 modules · Blueprints autoportants |
| **LLM local** | Ollama · phi4:14b (SOC/raisonnement) · gemma4 (GÉNÉRAL + vision) · qwen2.5-coder:14b (CODE) · mxbai-embed-large (RAG) |
| **RAG** | mxbai-embed-large · BM25 hybride · ~600 chunks · seuil 0.35 · TTL 5 min · warmup au boot |
| **TTS** | edge-tts fr-CA Antoine (défaut) → Kokoro CUDA → SAPI5 (fallback auto) |
| **STT** | faster-whisper large-v3-turbo CUDA · vocabulaire SOC |
| **Frontend** | Vanilla JS · 21 modules · Web Audio API · xterm.js · Monaco Editor |
| **Agent Hermès** | 5 briques · bypass regex déterministe · scheduler daemon · DI pur · indépendant du LLM |
| **MCP** | 12 outils exposés à Claude Desktop · port 5010 streamable-HTTP · watchdog |
| **Tests** | 1 465 pytest · 0 fail · 79 % coverage · ruff 0 · eslint 0 · hooks pre-commit/pre-push bloquants |

Architecture détaillée → [02-ARCHITECTURE/](DOCUMENTATION/02-ARCHITECTURE/)

---

## 📚 Documentation

> 26 fichiers · 8 catégories · Index complet → [DOCUMENTATION/00-INDEX.md](DOCUMENTATION/00-INDEX.md)

### 01 — Présentation

| Document | Description |
|----------|-------------|
| [01-01 Vision projet](DOCUMENTATION/01-PRESENTATION/01-01-VISION-PROJET.md) | Philosophie · objectifs · positionnement |
| [01-02 Présentation JARVIS](DOCUMENTATION/01-PRESENTATION/01-02-PRESENTATION-JARVIS.md) | Vue d'ensemble fonctionnelle |
| [01-03 Équipe & contexte](DOCUMENTATION/01-PRESENTATION/01-03-EQUIPE-ET-CONTEXTE.md) | Contexte homelab · environnement matériel |

### 02 — Architecture

| Document | Description |
|----------|-------------|
| [02-01 Architecture globale](DOCUMENTATION/02-ARCHITECTURE/02-01-ARCHITECTURE-GLOBALE.md) | Vue d'ensemble des composants |
| [02-02 Architecture tuiles](DOCUMENTATION/02-ARCHITECTURE/02-02-ARCHITECTURE-TUILES.md) | Modèle des tuiles autoportantes |
| [02-03 Référence technique](DOCUMENTATION/02-ARCHITECTURE/02-03-REFERENCE-TECHNIQUE.md) | API routes · structures de données |
| [02-04 Schéma IA local](DOCUMENTATION/02-ARCHITECTURE/02-04-SCHEMA-IA-LOCAL.md) | Pipeline LLM · RAG · STT · TTS |
| [02-05 Routing JARVIS](DOCUMENTATION/02-ARCHITECTURE/02-05-ROUTING-JARVIS.md) | 4 modes · bypasses déterministes · règles de sécurité |
| [02-06 Audio DSP](DOCUMENTATION/02-ARCHITECTURE/02-06-AUDIO-DSP.md) | Web Audio graph · BiquadFilter · Compresseur · Convolver |
| [02-07 MCP Server](DOCUMENTATION/02-ARCHITECTURE/02-07-MCP-SERVER.md) | 12 outils · config Claude Desktop · watchdog |

### 03 — Intégration SOC

| Document | Description |
|----------|-------------|
| [03-01 Circuit SOC ↔ JARVIS](DOCUMENTATION/03-INTEGRATION-SOC/03-01-CIRCUIT-SOC-JARVIS.md) | Auto-engine · ban/unban · injection contexte sécurité |

### 04 — Déploiement

| Document | Description |
|----------|-------------|
| [04-01 Déploiement](DOCUMENTATION/04-DEPLOIEMENT/04-01-DEPLOIEMENT.md) | Installation pas à pas |
| [04-02 Réinstallation](DOCUMENTATION/04-DEPLOIEMENT/04-02-REINSTALLATION.md) | Procédure disaster recovery |
| [04-03 Pré-requis](DOCUMENTATION/04-DEPLOIEMENT/04-03-PRE-REQUIS.md) | Dépendances · versions · matériel minimum |

### 05 — Exploitation

| Document | Description |
|----------|-------------|
| [05-01 Runbook](DOCUMENTATION/05-EXPLOITATION/05-01-RUNBOOK.md) | Procédures opérationnelles courantes |
| [05-02 Support & infogérance](DOCUMENTATION/05-EXPLOITATION/05-02-SUPPORT-INFOGERANCE.md) | Dépannage · cas fréquents |
| [05-03 Observabilité & logs](DOCUMENTATION/05-EXPLOITATION/05-03-OBSERVABILITE-LOGS.md) | jarvis.log · rotation · diagnostics |

### 06 — Bilan & Historique

| Document | Description |
|----------|-------------|
| [06-01 Bilan technique](DOCUMENTATION/06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md) | Score qualité · métriques · décisions (source unique) |
| [06-02 Mémoire projet](DOCUMENTATION/06-BILAN-ET-HISTORIQUE/06-02-MEMORY-PROJET.md) | Décisions architecturales clés |
| [06-03 Historique incidents](DOCUMENTATION/06-BILAN-ET-HISTORIQUE/06-03-HISTORIQUE-INCIDENTS.md) | Bugs majeurs résolus · leçons apprises |

### 07 — Roadmap

| Document | Description |
|----------|-------------|
| [07-01 Roadmap](DOCUMENTATION/07-ROADMAP/07-01-ROADMAP.md) | Évolutions prévues · priorités |
| [07-02 Dette technique](DOCUMENTATION/07-ROADMAP/07-02-DETTE-TECHNIQUE.md) | Inventaire dette · décisions de gel |

### 08 — Annexes

| Document | Description |
|----------|-------------|
| [08-01 Glossaire](DOCUMENTATION/08-ANNEXES/08-01-GLOSSAIRE.md) | Termes techniques · acronymes |
| [08-02 Conventions code](DOCUMENTATION/08-ANNEXES/08-02-CONVENTIONS-CODE.md) | Style Python/JS/Git · règles de contribution |

---

## 📁 Structure du projet

```
JARVIS/
├── DOCUMENTATION/              ← Base documentaire (26 docs, 8 catégories)
│   ├── 00-INDEX.md             ← Index complet
│   ├── 01-PRESENTATION/        ← Vision, présentation, contexte
│   ├── 02-ARCHITECTURE/        ← 7 docs techniques
│   ├── 03-INTEGRATION-SOC/     ← Circuit SOC ↔ JARVIS
│   ├── 04-DEPLOIEMENT/         ← Installation, pré-requis, recovery
│   ├── 05-EXPLOITATION/        ← Runbook, support, observabilité
│   ├── 06-BILAN-ET-HISTORIQUE/ ← Bilan technique, incidents
│   ├── 07-ROADMAP/             ← Évolutions, dette
│   └── 08-ANNEXES/             ← Glossaire, conventions
├── Images/
│   └── hermes.png              ← Synoptique Hermès
├── scripts/                    ← Code source
│   ├── jarvis.py               ← Orchestrateur Flask (33 Blueprints)
│   ├── bypass/                 ← Agent Hermès (morning_brief, learn, sysctrl...)
│   ├── blueprints/soc.py       ← Blueprint SOC — auto-engine + routes
│   ├── chat/                   ← Dispatcher · routing · contexte sécurité
│   ├── rag/                    ← Moteur RAG hybride (BM25 + vecteur)
│   ├── voice/                  ← STT · TTS · DSP audio
│   ├── jarvis_mcp_server.py    ← MCP bridge (12 outils)
│   ├── static/                 ← JS (21 modules) · CSS
│   └── templates/              ← HTML
├── tests/                      ← pytest · 1 465 tests · 79 % coverage
├── tools/                      ← Outils dev (profiling, diagnostics)
├── CLAUDE.md                   ← Briefing IA (collaboration développement)
└── README.md
```

---

## 🛡️ Sécurité

Principes non négociables intégrés dans le code :

| Principe | Implémentation |
|----------|----------------|
| **IPs privées immuables** | Plages RFC1918 jamais bannies, quelle que soit la situation |
| **SSH lecture seule** | 29 patterns bloqués par défaut · whitelist explicite pour les opérations d'écriture |
| **Injection SOC côté serveur** | Le contexte sécurité n'entre jamais dans l'historique chat |
| **Auto-engine isolé** | Actif uniquement en mode `soc` — jamais en mode général ou code |
| **100 % local** | JARVIS filtre et agrège en local — rien ne quitte la machine vers un LLM cloud |

Détails → [02-05 Routing JARVIS](DOCUMENTATION/02-ARCHITECTURE/02-05-ROUTING-JARVIS.md)

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

Source unique des métriques → [06-01 Bilan technique](DOCUMENTATION/06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md)

---

## 📜 Licence

Usage personnel — Marc Sabater (0xCyberLiTech).  
Candidat MIT pour publication future.
