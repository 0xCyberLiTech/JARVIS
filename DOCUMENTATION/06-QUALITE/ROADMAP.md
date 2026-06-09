---
title: "Roadmap — prochaines étapes prévues"
code: "JARVIS-DOC-07-01"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "Roadmap"
mots_cles: ["roadmap", "futur", "evolutions", "v3.4", "feature"]
---

# Roadmap JARVIS

> Document vivant — mis à jour à chaque session de planification.
> Date dernière revue : **2026-06-09**.

## Fait — historique

### ✅ Fait (2026-05-23)

- ✅ Refactor monolithe `jarvis.py` 4814 L → 1834 L (−62 %)
- ✅ 24 tuiles autoportantes avec pattern Blueprint+DI
- ✅ Bug UI reload résolu cause racine (DI explicite `blueprints/soc.py`)
- ✅ Couverture 62 % → 77 % (1360 tests · score 96/100)
- ✅ Observabilité complète (jarvis.log + JS-DIAG v2 + try/except enrich)
- ✅ Base documentaire `DOCUMENTATION/` créée (26 docs, 8 catégories)

### ✅ Fait (2026-06-05 — 2026-06-09)

- ✅ **Hermès Brique 1 — Synoptique** : 6 couches moteur temps réel
  (LLM actif, RAG chunks, STT/TTS état, SOC auto-engine, mémoire)
- ✅ **Hermès Brique 2 — Tuile Mémoire** : état vectorielle depuis l'UI
- ✅ **Hermès Brique 3 — Commandes vocales** : bypass LLM déterministe
  (*"recharge le RAG"*, *"vide la mémoire"*) — indépendant du modèle actif
- ✅ **Hermès Brique 4 — Boucle d'apprentissage** : *"souviens-toi que X"*
  → persisté dans `jarvis_corrections.md`, indexé RAG, réinjecté
- ✅ **Hermès Brique 5 — Briefing matinal** : *"bonjour JARVIS"* →
  brief vocal SOC + Proxmox. Scheduler daemon à heure fixe configurable
- ✅ **RAG warmup au boot** : `engine.warmup()` — fin de l'état "non chargé"
  après redémarrage JARVIS
- ✅ **Fix RAG timestamp monotonic** : `get_status()` utilisait `time.time()`
  (unix timestamp ~1,78 milliard) alors que `_rag_load()` stockait via
  `time.monotonic()` → affichage "1780970605s" corrigé
- ✅ **proc_guard.py** : MCP lifecycle fix — Job Object Windows
  `KILL_ON_JOB_CLOSE`, fin des orphelins port 5010 à chaque démarrage

### 🔄 Court terme (à venir)

| Priorité | Tâche | Effort | Gain |
|---|---|---|---|
| Moyen | Tests E2E Playwright nettoyés (cover Blueprints HTTP voice/settings/dev/web routes) | 2-3 h | +1 pt dette |
| Bas | Documentation auto-générée à partir des docstrings Python (Sphinx ?) | 1 h | +0.5 pt |
| Bas | Réduction des aliases backward-compat (~80 L jarvis.py) — *risqué : modif 30+ tests* | 1-2 h | +0.5 pt |

## Moyen terme (mois)

### Features fonctionnelles

| Feature | Description | Effort estimé |
|---|---|---|
| **Mode multi-utilisateurs** | ACL granulaires (admin / opérateur / lecture seule) | 1 semaine |
| **Plugin marketplace tuiles** | Tuile communautaire installable (Grafana, Wazuh, Zabbix) | 2 semaines |
| **Mode voix continue** | Active listening sans wake-word (mode "Iron Man") | 3 jours |
| **Historique chat persistant DB** | SQLite remplaçant `jarvis_memory.json` simple | 2 jours |
| **Notifications push mobile** | Alerte SOC critique vers téléphone Marc (Telegram bot ? ntfy.sh ?) | 1 jour |
| **Dashboard SOC enrichi** | Tile "JARVIS recommandations" sur dashboard srv-nginx | 1 jour |
| **MCP plus de tools** | Au-delà des 12 actuels (read_logs_remote, ssh_diagnose_perf, etc.) | 1 jour par tool |

### Amélioration architecture

| Amélioration | Effort | Gain |
|---|---|---|
| Containerisation Docker (Dockerfile + docker-compose) | 1 jour | Portabilité homelab |
| CI/CD GitHub Actions (lint + pytest) | 2 h | Validation auto |
| Coverage 76 % → 90 %+ | 1 semaine | Confiance refactor |

## Long terme (mois / année)

### Vision

> **JARVIS comme produit open source réutilisable** par d'autres homelabs
> cybersécurité.

| Étape | Description |
|---|---|
| 1. **Generalisation pattern par tuiles** | Documenter le pattern Blueprint+DI pour qu'un tiers puisse créer ses propres tuiles |
| 2. **Anonymisation** | Retirer les références spécifiques homelab Marc (IPs, hostnames) → config externalisée `jarvis.toml` |
| 3. **Tests E2E complets** | Validation cross-platform Linux/Windows |
| 4. **License + README public** | Choix MIT/Apache-2.0 (à valider avec Marc) |
| 5. **Publication GitHub** | Repo public + démo + screencast |
| 6. **Community building** | Discord / forum / contributors guide |

## Décisions différées (parking)

Ces idées ont été évoquées mais reportées à plus tard ou non décidées :

- **Mode "agent autonome" complet** (décisions sans validation) : Hermès
  implémente les 5 briques d'agentification — l'autonomie complète
  (décisions critiques infra sans confirmation) reste différée.
- **Intégration Claude API cloud directe depuis JARVIS** : violerait le
  principe "100 % local" sauf si stricte escalade vers Anthropic.
- **Interface mobile native** : webapp responsive suffit actuellement.

## Risques techniques connus

| Risque | Mitigation actuelle | Action future |
|---|---|---|
| Aliases backward-compat (~80 L) | Documenté + tests les couvrent | Refactor progressif si maintenance pénible |
| 5 globals mutables (MODEL, _vram_model, etc.) | Setters lambda + DI accesseurs | Refonte state object au niveau app Flask |
| Blueprints HTTP < 80 % coverage (voice, settings, dev, web) | Tests E2E Playwright (existants partiels) | Nettoyage suite Playwright |
| Dépendance Edge-TTS (Internet) | Fallback Kokoro/Piper/SAPI5 local | RAS |
| Dépendance Ollama (process séparé) | Circuit breaker 8 call-sites (refus 1ms) | RAS |

## Comment proposer une nouvelle évolution

1. Créer un fichier `07-02b-PROPOSITION-NOMFEATURE.md` (statut : Brouillon)
2. Décrire : besoin, alternatives, impact archi, effort estimé
3. Validation Marc → statut passe à Validé
4. Implémentation → entrée dans cette roadmap
