---
title: "INDEX — Documentation projet JARVIS"
code: "JARVIS-DOC-00-00"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "Index"
mots_cles: ["index", "navigation", "table-matieres", "jarvis"]
---

# DOCUMENTATION JARVIS — Index général

> **Base documentaire officielle du projet JARVIS** — assistant IA personnel
> local de Marc Sabater (homelab 0xCyberLiTech). Tous les documents projet
> sont regroupés ici, organisés thématiquement et numérotés pour faciliter
> la navigation, la maintenance et la reprise du projet par un tiers.

## Convention de nommage

- **Dossiers** : `NN-CATEGORIE/` (numérotés, MAJUSCULES, kebab-case)
- **Fichiers** : `NN-MM-TITRE.md` où `NN` = numéro catégorie, `MM` = numéro doc
- **Frontmatter YAML** obligatoire en tête de chaque document :
  - `title` (humain), `code` (machine `JARVIS-DOC-NN-MM`), `version`, `date_creation`,
    `date_revision`, `auteur`, `statut` (Brouillon/Revue/Validé/Obsolète), `categorie`,
    `mots_cles`
- **Encodage** : UTF-8, fin de ligne LF, Markdown CommonMark

## Statuts des documents

| Statut | Signification |
|---|---|
| **Brouillon** | Document en cours de rédaction, contenu incomplet |
| **Revue** | Document complet, en attente de validation par Marc |
| **Validé** | Document validé, à jour, source de vérité |
| **Obsolète** | Document conservé pour traçabilité, ne plus consommer |

## Table des matières

### 01 — Présentation projet

| Code | Document | Statut |
|---|---|---|
| [01-01](01-PRESENTATION/01-01-VISION-PROJET.md) | Vision et objectifs du projet JARVIS | Validé |
| [01-02](01-PRESENTATION/01-02-PRESENTATION-JARVIS.md) | Présentation détaillée — JARVIS SOC Platform | Validé |
| [01-03](01-PRESENTATION/01-03-EQUIPE-ET-CONTEXTE.md) | Équipe, contexte homelab, environnement | Validé |

### 02 — Architecture technique

| Code | Document | Statut |
|---|---|---|
| [02-01](02-ARCHITECTURE/02-01-ARCHITECTURE-GLOBALE.md) | Architecture globale JARVIS | Validé |
| [02-02](02-ARCHITECTURE/02-02-ARCHITECTURE-TUILES.md) | Architecture par tuiles (24 tuiles, post étape 37) | Validé |
| [02-03](02-ARCHITECTURE/02-03-REFERENCE-TECHNIQUE.md) | Référence technique — stack, composants | Validé |
| [02-04](02-ARCHITECTURE/02-04-SCHEMA-IA-LOCAL.md) | Schéma IA locale (Ollama + modèles + RAG) | Validé |
| [02-05](02-ARCHITECTURE/02-05-ROUTING-JARVIS.md) | Routing — 4 modes + bypass Python + sécurité | Validé |
| [02-06](02-ARCHITECTURE/02-06-AUDIO-DSP.md) | Pipeline audio — Web Audio + TTS chain + DSP | Validé |
| [02-07](02-ARCHITECTURE/02-07-MCP-SERVER.md) | MCP server — 12 outils + Claude Desktop | Validé |

### 03 — Intégration SOC

| Code | Document | Statut |
|---|---|---|
| [03-01](03-INTEGRATION-SOC/03-01-CIRCUIT-SOC-JARVIS.md) | Circuit d'intégration SOC ↔ JARVIS | Validé |

### 04 — Déploiement & installation

| Code | Document | Statut |
|---|---|---|
| [04-01](04-DEPLOIEMENT/04-01-DEPLOIEMENT.md) | Procédure de déploiement (production) | Validé |
| [04-02](04-DEPLOIEMENT/04-02-REINSTALLATION.md) | Procédure de réinstallation / recovery | Validé |
| [04-03](04-DEPLOIEMENT/04-03-PRE-REQUIS.md) | Pré-requis système (OS, Python, Ollama, GPU) | Validé |

### 05 — Exploitation & support

| Code | Document | Statut |
|---|---|---|
| [05-01](05-EXPLOITATION/05-01-RUNBOOK.md) | Runbook — procédures opérationnelles | Validé |
| [05-02](05-EXPLOITATION/05-02-SUPPORT-INFOGERANCE.md) | Support infogérance — SLA et processus | Validé |
| [05-03](05-EXPLOITATION/05-03-OBSERVABILITE-LOGS.md) | Observabilité — logs, JS-DIAG, garde-fous | Validé |

### 06 — Bilan & historique

| Code | Document | Statut |
|---|---|---|
| [06-01](06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md) | Bilan technique — score dette, métriques | Validé |
| [06-02](06-BILAN-ET-HISTORIQUE/06-02-MEMORY-PROJET.md) | Mémoire projet — historique chronologique des sessions | Validé |
| [06-03](06-BILAN-ET-HISTORIQUE/06-03-HISTORIQUE-INCIDENTS.md) | Historique des incidents et résolutions | Validé |

### 07 — Roadmap & dette technique

| Code | Document | Statut |
|---|---|---|
| [07-01](07-ROADMAP/07-01-ROADMAP.md) | Roadmap — prochaines étapes prévues | Validé |
| [07-02](07-ROADMAP/07-02-DETTE-TECHNIQUE.md) | Dette technique restante (décisions architecturales assumées) | Validé |

### 08 — Annexes

| Code | Document | Statut |
|---|---|---|
| [08-01](08-ANNEXES/08-01-GLOSSAIRE.md) | Glossaire (SOC, JARVIS, termes techniques) | Validé |
| [08-02](08-ANNEXES/08-02-CONVENTIONS-CODE.md) | Conventions de code — Python, JS, commits | Validé |

## Documents racine du projet (hors DOCUMENTATION/)

Restent à la racine du projet `JARVIS/` par convention universelle :

- [`README.md`](../README.md) — Présentation projet (entrée GitHub/GitLab)
- [`CLAUDE.md`](../CLAUDE.md) — Briefing IA Claude pour collaboration

## Comment contribuer

1. Toute modification respecte le frontmatter (date_revision à mettre à jour)
2. Tout nouveau document suit le nommage `NN-MM-TITRE.md`
3. Statut passe à `Revue` après modification substantielle, repasse `Validé` après validation
4. L'index `00-INDEX.md` (ce fichier) est mis à jour à chaque ajout/déplacement

## Recherche transverse

```bash
# Lister tous les documents
find DOCUMENTATION/ -name "*.md" -type f | sort

# Trouver un mot-clé
grep -rni "kill chain" DOCUMENTATION/

# Voir les documents en Brouillon
grep -rl 'statut: "Brouillon"' DOCUMENTATION/
```

---

*Cette base documentaire a remplacé l'ancien dossier `docs/` + les fichiers
markdown éparpillés à la racine. Date de la refonte : 2026-05-23.*
