# J.A.R.V.I.S — Agent IA Personnel

> **Pas un chatbot. Un agent persistant** qui tourne entièrement en local, surveille l'infrastructure, mémorise les leçons et parle chaque matin.

**Créateur** : Marc Sabater · [0xCyberLiTech](https://github.com/0xCyberLiTech) · **Version** : v3.3 · **GPU** : RTX 5080 · **LLM** : Ollama local

---

## Sommaire

- [◈ HERMÈS — Agent persistant](#-hermès--agent-persistant)
- [Aperçu](#aperçu)
- [Lancement rapide](#-lancement-rapide)
- [Stack technique](#-stack-technique)
- [Documentation](#-documentation)
  - [01 — Présentation](#01--présentation)
  - [02 — Architecture](#02--architecture)
  - [03 — Intégration SOC](#03--intégration-soc)
  - [04 — Déploiement](#04--déploiement)
  - [05 — Exploitation](#05--exploitation)
  - [06 — Bilan & Historique](#06--bilan--historique)
  - [07 — Roadmap](#07--roadmap)
  - [08 — Annexes](#08--annexes)
- [Structure du projet](#-structure-du-projet)
- [Sécurité](#-sécurité)
- [Qualité](#-qualité)
- [Licence](#-licence)

---

## ◈ HERMÈS — Agent persistant

![Hermès — synoptique 6 couches actives : LLM, RAG, STT, TTS, SOC, MÉMOIRE](Images/hermes.png)

Hermès est la couche d'**agentification persistante** de JARVIS.  
Là où un assistant répond à des questions, un agent **observe, mémorise, apprend et agit** de façon autonome.

| Brique | Ce qu'elle fait |
|--------|----------------|
| **1 — Synoptique** | 6 couches moteur visibles en temps réel : LLM actif, chunks RAG, STT/TTS, auto-engine SOC, mémoire. Tableau de bord vivant de ce que pense JARVIS. |
| **2 — Tuile Mémoire** | État de la mémoire vectorielle : échanges, résumés, leçons apprises. Rechargement RAG et purge accessibles depuis l'interface. |
| **3 — Commandes vocales** | Bypass LLM pour les commandes système : *"recharge le RAG"*, *"vide la mémoire"*. Exécution instantanée, déterministe — indépendant du modèle actif. |
| **4 — Boucle d'apprentissage** | *"Souviens-toi que X"* — la leçon est persistée, indexée dans le RAG et remonte automatiquement dans les réponses futures. |
| **5 — Briefing matinal** | *"Bonjour JARVIS"* → briefing vocal complet : niveau de menace SOC, état des machines, alertes 24h. Automatisable à heure fixe — JARVIS parle seul chaque matin. |

**Avant Hermès** — JARVIS répondait aux questions. Chaque session recommençait à zéro. Le contexte était perdu au redémarrage.

**Après Hermès** — JARVIS accumule les leçons explicites, les indexe dans sa base vectorielle et les réinjecte dans ses réponses futures. Il connaît les règles d'infra, les conventions de code, les préférences de l'utilisateur — sans être re-briefé à chaque session.

---

## Aperçu

JARVIS est une interface web locale type **Iron Man** construite sur Python/Flask + Ollama.  
Elle intègre un chat IA multi-modèles, un terminal, un monitoring GPU/système, un explorateur de fichiers, un gestionnaire de tâches, un Voice Lab complet (STT + TTS CUDA), un éditeur audio IA DSP et une intégration SOC cybersécurité temps réel.

Tout tourne **en local** — aucune donnée ne quitte la machine.

---

## 🚀 Lancement rapide

```bat
start_dashboard.bat
```

Démarre l'environnement virtuel Python, lance Ollama et ouvre l'interface dans le navigateur.

**Arrêt** : `stop_jarvis.bat`

Pré-requis détaillés → [`04-DEPLOIEMENT/04-03-PRE-REQUIS.md`](DOCUMENTATION/04-DEPLOIEMENT/04-03-PRE-REQUIS.md)  
Installation complète → [`04-DEPLOIEMENT/04-01-DEPLOIEMENT.md`](DOCUMENTATION/04-DEPLOIEMENT/04-01-DEPLOIEMENT.md)

---

## 🧠 Stack technique

| Couche | Technologie |
|--------|-------------|
| **Backend** | Python 3.11 · Flask · 24 tuiles autoportantes · `blueprints/soc.py` |
| **LLM local** | Ollama · phi4:14b (SOC) · gemma4 (GÉNÉRAL+vision) · qwen2.5-coder:14b (CODE) · qwen3:8b (CODE-REASONING) · mxbai-embed-large (RAG) |
| **RAG** | mxbai-embed-large · BM25 hybride · ~1700 chunks · TTL 5 min · warmup au boot |
| **TTS** | edge-tts (fr-CA Antoine) → Kokoro CUDA → Piper → SAPI5 (fallback auto) |
| **STT** | faster-whisper `large-v3-turbo` CUDA · vocabulaire SOC |
| **Frontend** | Vanilla JS · 21 modules · Web Audio API · xterm.js · Monaco Editor |
| **Agent Hermès** | 5 briques · bypass regex · scheduler daemon · DI pur · indépendant du LLM |
| **MCP** | 12 outils exposés à Claude Desktop |
| **Tests** | pytest · ruff 0 · eslint 0 · coverage 76 % · hooks pre-commit/pre-push bloquants |

Architecture détaillée → [`02-ARCHITECTURE/`](DOCUMENTATION/02-ARCHITECTURE/)

---

## 📚 Documentation

> La documentation complète vit dans [`DOCUMENTATION/`](DOCUMENTATION/00-INDEX.md) — 26 fichiers, 8 catégories.  
> Index complet → [`DOCUMENTATION/00-INDEX.md`](DOCUMENTATION/00-INDEX.md)

### 01 — Présentation

| Document | Description |
|----------|-------------|
| [01-01 Vision projet](DOCUMENTATION/01-PRESENTATION/01-01-VISION-PROJET.md) | Philosophie, objectifs, positionnement |
| [01-02 Présentation JARVIS](DOCUMENTATION/01-PRESENTATION/01-02-PRESENTATION-JARVIS.md) | Vue d'ensemble fonctionnelle |
| [01-03 Équipe & contexte](DOCUMENTATION/01-PRESENTATION/01-03-EQUIPE-ET-CONTEXTE.md) | Contexte homelab, environnement matériel |

### 02 — Architecture

| Document | Description |
|----------|-------------|
| [02-01 Architecture globale](DOCUMENTATION/02-ARCHITECTURE/02-01-ARCHITECTURE-GLOBALE.md) | Vue d'ensemble des composants |
| [02-02 Architecture tuiles](DOCUMENTATION/02-ARCHITECTURE/02-02-ARCHITECTURE-TUILES.md) | Modèle des 24 tuiles autoportantes |
| [02-03 Référence technique](DOCUMENTATION/02-ARCHITECTURE/02-03-REFERENCE-TECHNIQUE.md) | API routes, structures de données |
| [02-04 Schéma IA local](DOCUMENTATION/02-ARCHITECTURE/02-04-SCHEMA-IA-LOCAL.md) | Pipeline LLM · RAG · STT · TTS |
| [02-05 Routing JARVIS](DOCUMENTATION/02-ARCHITECTURE/02-05-ROUTING-JARVIS.md) | 4 modes · bypasses · règles de sécurité |
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
| [05-03 Observabilité & logs](DOCUMENTATION/05-EXPLOITATION/05-03-OBSERVABILITE-LOGS.md) | jarvis.log · rotation · JS-DIAG v2 |

### 06 — Bilan & Historique

| Document | Description |
|----------|-------------|
| [06-01 Bilan technique](DOCUMENTATION/06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md) | Score qualité · métriques · dette (source unique) |
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
│   ├── jarvis.py               ← Ossature Flask — 24 Blueprints
│   ├── bypass/                 ← Modules Hermès (morning_brief, learn, sysctrl...)
│   ├── blueprints/soc.py       ← Blueprint SOC — auto-engine + routes
│   ├── chat/                   ← Dispatcher · routing · contexte
│   ├── rag/                    ← Moteur RAG hybride (BM25 + vecteur)
│   ├── voice/                  ← STT · TTS · DSP
│   ├── jarvis_mcp_server.py    ← MCP bridge (12 outils)
│   ├── static/                 ← JS (21 modules) · CSS (8 fichiers)
│   ├── templates/              ← HTML (10 templates)
│   ├── jarvis_hermes.json      ← Config Hermès (briefing heure, activation)
│   └── start_dashboard.bat / stop_jarvis.bat
├── tests/                      ← pytest · 1294 tests · 76 % coverage
├── tools/                      ← Outils dev (profile_tts, ...)
├── CLAUDE.md                   ← Briefing IA (collaboration développement)
└── README.md
```

---

## 🛡️ Sécurité

Principes non négociables intégrés dans le code :

- **IPs privées immuables** — plages RFC1918 jamais bannies quelle que soit la situation
- **SSH lecture seule par défaut** — 29 patterns bloqués, whitelist explicite pour les opérations d'écriture
- **Injection SOC côté serveur uniquement** — le contexte de sécurité n'entre jamais dans l'historique chat
- **Auto-engine SOC isolé** — actif uniquement en mode `soc`, jamais en mode général ou code
- **Données traitées localement** — JARVIS filtre et agrège en local, rien ne quitte la machine vers un LLM cloud

Détails → [`02-05 Routing JARVIS`](DOCUMENTATION/02-ARCHITECTURE/02-05-ROUTING-JARVIS.md)

---

## 🔧 Qualité

| Indicateur | Valeur |
|------------|--------|
| Tests pytest | 1294 pass · 0 fail |
| Coverage | 76 % |
| Linter Python (ruff) | 0 erreur |
| Linter JS (eslint) | 0 erreur |
| Pre-commit hooks | ruff + eslint bloquants |
| Pre-push hook | pytest bloquant |
| Score qualité global | **95/100** (plafond pratique atteint) |

Décomposition complète → [`06-01 Bilan technique`](DOCUMENTATION/06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md) §0 (source unique des métriques)

---

## 📜 Licence

Usage personnel — Marc Sabater (0xCyberLiTech).  
Candidat MIT pour publication future.
