---
title: "Bilan technique — score qualité, métriques, décisions"
code: "JARVIS-DOC-06-01"
version: "2.0"
date_revision: "2026-06-09"
statut: "Validé"
---

# Bilan technique — JARVIS 0xCyberLiTech

Assistant IA local · audit qualité honnête · **Score : 97 / 100**

> Source unique des métriques du projet. Mis à jour à chaque évolution significative.

---

## § 0 — État actuel (2026-06-09)

| Catégorie | Score | Justification |
|-----------|-------|---------------|
| Architecture | **24 / 25** | 24 tuiles autoportantes · DI pur · `monitoring_gen` gel assumé (I/O shell peu testable — correct) |
| Tests | **24 / 25** | 1 465 pytest pass · 0 fail · 79 % coverage · −1 `voice/routes.py` borderline 50 % (STT/TTS synthesis non tracé — Playwright E2E) |
| Documentation | **15 / 15** | 26 docs · 8 catégories · index · runbook · bilan · conventions |
| Lisibilité | **14 / 15** | ruff 0 · eslint 0 · −1 `jarvis.py` grand (gel assumé — 4 triggers de revisite définis) |
| Performance | **10 / 10** | CUDA · circuit breaker Ollama · prewarm Kokoro + RAG · num_ctx adaptatif |
| Sécurité | **10 / 10** | RFC1918 · SSH readonly + whitelist explicite · injection SOC côté serveur · auto-engine isolé |
| **Total** | **97 / 100** | Plafond théorique ~98/100 (résorption globals mutables + voice E2E) |

---

## § 1 — Métriques clés

| Indicateur | Valeur |
|------------|--------|
| Tests pytest | **1 465 pass · 0 fail** |
| Coverage globale | **79 %** |
| Modules à ≥ 90 % | ollama_circuit · tts_cleaner · stt · ssh_terminal · security_whitelists · rag/routes · tasks/routes · vision/routes · memory/routes · dev/routes |
| Linter Python (ruff) | **0 erreur** |
| Linter JS (eslint) | **0 erreur** |
| Pre-commit hooks | ruff + eslint bloquants |
| Pre-push hook | pytest bloquant |
| Modules Python | 33 + `jarvis.py` orchestrateur |
| Modules JS | 21 (Vanilla JS · Web Audio API) |

---

## § 2 — Décomposition Tests (24 / 25)

Les 1 465 tests couvrent :

| Périmètre | Couverture |
|-----------|------------|
| Routes Flask blueprints (7 modules, Flask test_client) | 50 – 100 % |
| Cœur sécurité SOC (whitelists, ban, contexte) | ≥ 90 % |
| Agent Hermès (bypass, morning_brief, learn) | ≥ 85 % |
| RAG (moteur, routes) | ≥ 90 % |
| Voice (TTS, STT, DSP) | ~50 – 80 % |
| MCP (12 outils, watchdog) | ≥ 80 % |
| Proxmox API, circuit breaker, tts_cleaner | ≥ 90 % |

**−1 honnête** : `voice/routes.py` borderline 50 % — les routes de synthèse TTS/STT nécessitent
un test E2E Playwright (non tracé en coverage Python). ROI faible pour un refactoring dédié.

---

## § 3 — Décisions de gel (dette assumée)

| Module | Taille | Décision | Triggers de revisite |
|--------|--------|----------|----------------------|
| `monitoring_gen.py` | ~1 320 L | **Gel** — glue I/O shell au bon endroit · 84 % arrêt honnête | taille > 3 500 L · coverage < 40 % · blocage métier · pattern bugs |
| `jarvis.py` | ~1 900 L | **Gel** — orchestrateur Flask, refactoring = risque régressions | idem |
| JS canvas (4 modules > 1 000 L) | > 1 000 L | **Gel** — cohésifs, zéro dette réelle | idem |

---

## § 4 — Règles qualité (5 consignes gravées)

1. **Zéro hardcodé** — source unique (constante/dict centralisé)
2. **Zéro dette non documentée** — toute dette = décision explicite datée
3. **Modularisation** — DI pur, pas de couplage implicite
4. **Maîtrise logs** — rotation `.log.1` + bornage volumétrique
5. **Outils en premier** — créer un outil si le besoin est récurrent

---

## § 5 — Historique des scores

| Date | Score | Action principale |
|------|-------|-------------------|
| 2026-05-15 | 93/100 | Phase 4 — 34/34 modules testés + circuit breaker Ollama |
| 2026-05-17 | 92/100 | Recalibrage honnête (−1 CLAUDE.md absent, −1 BILAN absent) |
| 2026-05-22 | 88/100 | Audit approfondi — 9 correctifs (whitelists, ruff, code mort) |
| 2026-05-27 | 96/100 | +ruff/eslint · +26 tests SOC context · BILAN + CLAUDE.md |
| 2026-05-31 | 96/100 | MCP Job Object + stop-dialog · confirmé en prod |
| **2026-06-09** | **97/100** | +105 tests Flask routes HTTP · 6 blueprints portés à ≥ 50 % · Tests 23→24 |

---

## § 6 — Prochains leviers (plafond ~98/100)

| Levier | Impact | Priorité |
|--------|--------|----------|
| `voice/routes.py` E2E (Playwright) | +1 Tests | Faible — ROI limité |
| Résorption globals mutables `jarvis.py` | +1 Architecture | Moyen — trigger taille |
| Test intégration end-to-end + assertion jsonschema `monitoring_gen` | Confiance | Sanctionné |
