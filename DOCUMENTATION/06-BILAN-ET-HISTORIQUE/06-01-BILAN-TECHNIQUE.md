---
title: "Bilan technique — score dette, métriques, décisions"
code: "JARVIS-DOC-06-01"
version: "1.2"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "Bilan"
mots_cles: ["bilan", "dette", "metriques", "score", "coverage"]
---

# BILAN TECHNIQUE — JARVIS 0xCyberLiTech
## Assistant IA local v3.3 — 2026-05-23 nuit (refonte documentaire complète + extension Playwright sur 4 Blueprints HTTP sous-couverts · score 95/100 = plafond pratique atteint)

---

## 0. État actuel (audit dette honnête 2026-05-23 nuit — post refonte doc + extension Playwright api-coverage)

> 📊 **SOURCE UNIQUE des métriques courantes du projet** — score dette, lignes
> `jarvis.py` / `soc.py` / `jarvis_main.js`, nombre de tests pytest, coverage.
> Les autres docs JARVIS pointent ici au lieu de recopier ces chiffres : un seul
> endroit à mettre à jour, plus de dérive entre documents.

**Score honnête : 95/100** (+1 vs 94 du soir grâce à l'extension Playwright `tests/e2e/api-coverage.spec.js` : 14 nouveaux tests E2E ciblés sur les 4 Blueprints HTTP précédemment sous-couverts en pytest — `voice/routes` · `settings/routes` · `dev/routes` · `web/routes`. Le critère « Blueprints HTTP testés indirectement par E2E » est désormais **testé directement et explicitement** sur les vraies routes HTTP avec JARVIS up). **Plafond pratique atteint** — voir §0septies pour les actions résiduelles à ROI très défavorable. Décomposition :

| Critère | Score | Justification |
|---|---|---|
| Architecture | **24/25** | **24 tuiles autoportantes** (étape 35 → `llm/`, étape 36b → DI explicite soc.py élimine les 4 `from jarvis import` lazy = cause racine bug UI reload, étape 37 → `mode/`). `jarvis.py` **4814 → 1821 L (−62%)**, devenu ossature qui register 24 Blueprints. Pattern Blueprint+DI validé partout. **−1 honnête** : 5 globals mutables conservés (MODEL, _vram_model, SYSTEM_PROMPT, _welcome_data, _AUTO_PROFILE_MODEL) avec setters lambda — pattern legacy assumé · ~80 L d'aliases backward-compat dans jarvis.py (bruit mais nécessaire pour tests existants — décision documentée commit `98c9e0c` après audit). |
| Tests | **23/25** | **1294 tests pytest · 0 skip · 0 fail · 0 régression** (+282 tests sur la journée) · coverage globale **75%** (7394 stmts · 1827 miss) · **39 tests Playwright E2E · 100% pass · 0 flaky** (25 historiques + **14 nouveaux** dans `tests/e2e/api-coverage.spec.js` ciblés sur les 4 Blueprints HTTP sous-couverts en pytest — voice/settings/dev/web routes désormais testés bout-en-bout avec JARVIS up). **Gains pytest ciblés** : `tools/local.py` 49→**95%**, `runtime/speak.py` 41→**89%**, `bypass/wrappers.py` 65→**97%**, `terminal/ssh_ws.py` 15→**82%**, `commands/sse.py` 12→**92%**, `llm/vram.py` 40→**100%**, `chat/file_correct.py` 22→**97%**, `mode/routes.py` 0→**100%**. **Fix critique conftest** : `JARVIS_SKIP_BOOT_THREADS=1` auto-set avant tout import. **−2 honnêtes** : la coverage pytest des Blueprints HTTP reste basse (36-44%) car Playwright ne génère pas de coverage Python ; le mocking Flask test_client de ces routes (téléchargements + audio + Ollama + SSH) coûterait beaucoup pour un bénéfice faible vu l'extension Playwright. |
| Documentation | **15/15** | **Refonte documentaire complète 2026-05-23 fin de journée** : `DOCUMENTATION/` (25 docs, 8 catégories numérotées 01-PRESENTATION → 08-ANNEXES) avec **frontmatter YAML universel** (title, code `JARVIS-DOC-NN-MM`, version, dates, auteur, statut, mots-clés). `00-INDEX.md` central. 15 docs migrés (renames git détectés à 94-99%) + 9 nouveaux (vision, contexte, pré-requis, observabilité-logs, historique-incidents, roadmap, dette-technique, glossaire, conventions-code). Suppression `docs/` + 8 `.md` racine éparpillés. Racine assainie : seuls `README.md` (réécrit, pointe vers INDEX) + `CLAUDE.md` (sources de vérité réalignées). Source unique des métriques préservée (§0). |
| Lisibilité/Conventions | 24/25 | ruff **0** (2 noqa F401 documentés sur `psutil` + `TOOLS` après extraction runtime/gpu_stats et chat/tool_schemas) · eslint **0** · pre-commit/pre-push hooks bloquants · **audit ruff strict `--select=B,C4,SIM,UP,RUF`** (commit `98c9e0c`) : 84 suggestions évaluées dont 42 noqa légitimes (refusés), 2 modernisations f-string `repr(x) → {x!r}` conservées. −1 : ~135 inline styles JS (HUD temps réel) accepté · aliases backward-compat ajoutent du bruit dans jarvis.py (~80 L, décision archi assumée). |
| Performance | 10/10 | Circuit breaker Ollama · cache SOC 30s · fix IPv6 systémique · pré-warm Kokoro CUDA + phi4 SOC · pipeline voix invariant AudioContext + découpage TTS · optimisation VRAM · **`JARVIS_SKIP_BOOT_THREADS=1`** (conftest auto-set) · **indicateur visuel `mode-loading`** (étape 36) → pulse cyan + ⏳ sur le bouton mode pendant le swap VRAM (1-3s) → UX explicite quand le LLM est vraiment prêt. |
| Sécurité | 24/25 | Whitelist SSH stricte 29 patterns bloqués · profil SOC anti-double-ban · règle anti-hallucination phi4 · injection SOC 100% serveur · IPs hardcodées en `.gitignore` · **try/except global sur `/api/tts`** + contexte voix+moteur+texte au crash · **RotatingFileHandler `_log` → `scripts/jarvis.log`** persistant 5MB×7 · **fix idempotence × 3** (handler + threads + boot_id) · **DI explicite soc.py** (étape 36b commit `709049f` : élimine la cause racine du bug UI reload) · **instrumentation JS-DIAG v2** (commit `da7384d`) → `beforeunload` + stack trace capture toute navigation sortante. **−1 honnête** : Marc accepte que l'auto-engine SOC reste silencieux en mode CODE/CR/GENERAL (règle ABSOLUE `feedback_jarvis_no_regression`). |

**Chiffres clés (2026-05-23 fin de journée — post refonte documentaire)** :

| Métrique | Valeur |
|---|---|
| **Tests pytest** | **1294 pass · 0 skip · 0 fail** (mesure re-vérifiée fin de journée) |
| **Tests Playwright E2E** | **39 pass · 0 flaky · 100%** en 2.2 min (25 historiques + **14 nouveaux** `api-coverage.spec.js` ciblant voice/settings/dev/web routes bout-en-bout) |
| **Coverage globale pytest** | **75%** (7394 stmts · 1827 miss — Playwright ne génère pas de coverage Python) |
| **TODOs/FIXMEs codebase** | **0** (Python + JS — codebase propre, zéro marqueur de dette inline) |
| **Tuiles autoportantes** | **24** : `system` `memory` `rag` `files` `ssh` `bypass` `proxmox` `chat` `voice` `vision` `settings` `tasks` `health` `commands` `dev` `web` `bootstrap` `terminal` `runtime` `facts` (+ `inject.py`) `tools` (+ `dispatch.py`) `llm` (+ `vram.py` + `stream.py`) `mode` + `blueprints/soc` (existant) |
| **Sous-modules chat** | 14 : `capture` · `dispatcher` · `file_correct` · `generate` · `messages` · `orchestrator` · `pending_bypass` · `routing` · `soc_context` · `soc_inject` · `stream` · `system_prompt` · `tool_calls` · `tool_schemas` |
| **Couverture clés (≥80%)** | `jarvis.py` 80% · `tools/local.py` 95% · `runtime/speak.py` 89% · `bypass/wrappers.py` **97%** · `terminal/ssh_ws.py` 82% · `commands/sse.py` **92%** · `llm/vram.py` **100%** · `chat/file_correct.py` **97%** · `mode/routes.py` **100%** · `facts/routes.py` 87% · `voice/audio_dsp.py` 93% · `voice/voice_lab.py` **100%** · `voice/stt.py` 98% · `proxmox/api.py` 93% |
| **`jarvis.py`** | **1822 L** — ossature qui register 24 Blueprints + glue DI + carrefour boot + 5 setters globaux + `index/favicon/api_debug` |
| **`blueprints/soc.py`** | **1548 L** (DI explicite 36b) |
| **`jarvis_mcp_server.py`** | 554 L · MCP bridge 12 outils Claude Desktop |
| **Total Python `scripts/`** | **14973 L** |
| **`jarvis_main.js`** | 148 L (post-refactor −98,1% depuis 7828L) |
| **Modules JS métier** | 22 (18 `static/js/` + 4 `static/` hors vendored) · 3 fichiers JS tiers vendored (highlight, xterm + addon) |
| **CSS** | 8 fichiers métier (`static/css/`) + 2 vendored (atom-one-dark + xterm) |
| **Templates HTML** | 10 fichiers (`templates/jarvis.html` + `partials/modals.html` + 8 `tabs/`) |
| **MCP outils** | 12 |
| **Modèles LLM** | 5 (phi4:14b SOC · gemma4 GÉNÉRAL · qwen2.5-coder CODE · qwen3:8b CR · mxbai-embed-large RAG) |
| **TTS moteurs** | 4 (edge-tts · Kokoro CUDA · Piper · SAPI5) avec fallback chain |
| **ESLint** | **0 erreur · 0 warning** |
| **ruff (config projet)** | **0 erreur** (2 `noqa F401` documentés : `psutil` + `TOOLS`) |
| **ruff strict (`--select=B,C4,SIM,UP,RUF`)** | **40 items**, tous **décisions architecturales assumées documentées** : 13 SIM105 try/except: pass (lisibilité), 8 RUF005 `arr + [x]` (refactor sans gain), 26 RUF100 unused-noqa en mode strict = noqa **légitimes** pour la config par défaut F401/E402 (ne pas retirer), 10 items unicode/SIM/UP/C416 mineurs |
| **Documentation** | **25 docs** dans `DOCUMENTATION/` (8 catégories numérotées, frontmatter YAML universel, INDEX central) · racine assainie (`README.md` + `CLAUDE.md` uniquement) |
| **Pre-commit hooks** | ruff + eslint (commit) · pytest 1294 tests (pre-push) |
| **Env flags runtime** | `JARVIS_SKIP_BOOT_THREADS=1` → smoke imports sans threads boot (auto-set par conftest.py) |
| **Logs persistants** | `scripts/jarvis.log` (5MB×7, _log JARVIS principal) · `scripts/tts.log` (2MB×7, JARVIS.TTS) · `scripts/tts_perf.log` (1MB×3, filtre `[TTS-PERF]`) — total **~52 MB max** plafonnés |
| **Bug UI reload (15+ jours)** | **résolu cause racine** (étape 36b — DI explicite soc.py) + palliatif `os.environ` boot_id cache + instrumentation JS-DIAG v2 active en permanence |

---

## 0septies. Session 2026-05-23 soir — refonte documentaire complète + audit final honnête

### Refonte documentaire (`DOCUMENTATION/` — 25 docs, 8 catégories)

À la demande de Marc : sortir du modèle « docs/ + 8 fichiers .md éparpillés à
la racine » pour une vraie base documentaire de suivi de projet, structurée,
numérotée, datée, frontmatter YAML universel, capable d'être reprise à froid
par un tiers.

**Structure mise en place** :

```
DOCUMENTATION/
├── 00-INDEX.md
├── 01-PRESENTATION/    ← vision projet, présentation JARVIS, équipe/contexte
├── 02-ARCHITECTURE/    ← 7 docs (globale, tuiles, ref technique, schéma IA, routing, audio DSP, MCP)
├── 03-INTEGRATION-SOC/ ← circuit SOC ↔ JARVIS
├── 04-DEPLOIEMENT/     ← déploiement, réinstallation, pré-requis
├── 05-EXPLOITATION/    ← runbook DR, support infogérance, observabilité-logs
├── 06-BILAN-ET-HISTORIQUE/ ← bilan technique (ce doc), mémoire projet, historique incidents
├── 07-ROADMAP/         ← roadmap, dette technique
└── 08-ANNEXES/         ← glossaire, conventions code
```

**Frontmatter YAML obligatoire** sur chaque doc (déclinaison sur les 25 fichiers) :

```yaml
title: "..."
code: "JARVIS-DOC-NN-MM"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "..."
mots_cles: ["...", "..."]
```

**Migration** : 15 docs existants déplacés et enrichis avec frontmatter (renames
git détectés à 94-99% — l'historique git reste lisible) + 9 nouveaux docs créés
pour combler les manques (vision, contexte, pré-requis, observabilité-logs,
historique-incidents, roadmap, dette-technique, glossaire, conventions-code).

**Suppression** : `docs/` (7 fichiers) + 8 `.md` racine éparpillés
(`ARCHITECTURE-JARVIS`, `ARCHITECTURE-TUILES`, `BILAN-TECHNIQUE`,
`CIRCUIT_SOC_JARVIS`, `JARVIS_SOC_PLATFORM`, `MEMORY`, `RUNBOOK`,
`SCHEMA-IA-LOCAL`). Racine assainie : seuls `README.md` (réécrit, concis,
pointe vers `DOCUMENTATION/00-INDEX.md`) + `CLAUDE.md` (sources de vérité
réalignées sur les nouveaux chemins) restent.

**Référence code MAJ** : `scripts/chat/routing.py` pointait sur l'ancien
`docs/ROUTING-JARVIS.md` → MAJ vers `DOCUMENTATION/02-ARCHITECTURE/02-05-ROUTING-JARVIS.md`.

**Verification post-refonte** :
- `ruff check scripts/ tests/` → **All checks passed**
- `pytest tests/python/` → **1294 passed** (zéro régression)

Commit : `23be34d — docs(jarvis): refonte documentaire complete - DOCUMENTATION/ (25 docs, 8 categories numerotees)`.

### Audit honnête fin de journée (calibration du score)

**Mesures réelles re-vérifiées** (vs ce qui était annoncé le matin) :

| Item | Annoncé matin | Mesure réelle soir | Écart |
|---|---|---|---|
| Tests pytest | 1294 pass | 1294 pass | ✓ |
| Coverage globale | 76% (7394 / 1806 miss) | **75%** (7394 / 1827 miss) | **−1 pt honnête** (drift normal du code) |
| `jarvis.py` | 1821 L | **1822 L** | ✓ (±1) |
| `blueprints/soc.py` | 894 stmts | **1548 L** (LOC brute, ≠ stmts) | unité différente, pas un écart |
| Tuiles | 24 | 24 | ✓ |
| Sous-modules chat | 14 listés | 14 vérifiés | ✓ |
| ESLint | 0 erreur · 0 warning | 0 erreur · 0 warning | ✓ |
| ruff (config projet) | 0 erreur | 0 erreur | ✓ |
| TODOs/FIXMEs codebase | (non mesuré) | **0** Python + JS | bonus honnête |

**Ruff strict revérifié** (`--select=B,C4,SIM,UP,RUF`) : 40 items, **tous
décisions architecturales assumées** déjà documentées dans `07-02-DETTE-TECHNIQUE.md` :
- 13 SIM105 (try/except: pass — plus lisible que `contextlib.suppress`)
- 8 RUF005 (`arr + [x]` patterns — refactor mécanique sans gain)
- 26 RUF100 (unused noqa **en mode strict**) — les noqa sont en réalité
  **légitimes pour la config par défaut F401/E402** : tentative d'autofix
  vérifiée → casse 57 erreurs F401 sur les `__init__.py` des tuiles → restauré
- 10 items mineurs (RUF001/002/003 unicode, SIM114, C416, RUF046, SIM102/110/115/117, UP017)

### Extension Playwright `api-coverage.spec.js` (commit nuit — 14 nouveaux tests)

Constat fait après mesure réelle de la suite Playwright existante : elle est
**déjà 100% verte (25/25 pass, 0 flaky)**. L'hypothèse « Playwright flaky à
nettoyer » du matin était fausse — la suite est saine. Le vrai gain n'est
pas le nettoyage, c'est **l'extension de couverture** sur les routes
non testées en pytest.

`tests/e2e/api-coverage.spec.js` ajoute **14 tests E2E ciblés** sur les 4
Blueprints HTTP précédemment sous-couverts :

| Blueprint | Coverage pytest | Tests Playwright ajoutés |
|---|---|---|
| `voice/routes` | 36 % | 7 (stt/status, speak/status, speak/queue, tts/status, voices, tts/local/voices, voice/prints) |
| `settings/routes` | 44 % | 5 (llm-params, prompt-profiles, welcome, dsp-params, models) |
| `dev/routes` | 27 % | 1 (dev/stats — disk/ram/uptime srv-dev-1) |
| `web/routes` | 26 % | 1 (web-test — DDG + Wikipedia connectivity) |

Stratégie : routes **GET read-only uniquement** → zéro effet de bord serveur,
run rapide (6.7 s pour les 14 tests), validation **bout-en-bout réelle** sur
JARVIS up (Playwright fait l'aller-retour HTTP vs pytest qui mock le
test_client). C'est exactement la complémentarité recherchée.

Suite Playwright totale : 25 → **39 tests · 100 % pass · 2.2 min · 0 flaky**.

### Verdict honnête final : **95/100** (+2 vs 93 du matin · plafond pratique atteint)

| Critère | Matin | Nuit | Justification du delta |
|---|---|---|---|
| Architecture | 24/25 | 24/25 | inchangé (décisions documentées) |
| **Tests** | **22/25** | **23/25** | **+1 honnête** : extension Playwright `api-coverage.spec.js` couvre désormais les 4 Blueprints HTTP précédemment sous-couverts par des tests **bout-en-bout réels** sur JARVIS up — le « −3 honnête » du matin descend à « −2 honnête » (la couverture pytest reste basse mais c'est désormais couvert par Playwright, plus une décision archi assumée que de la dette) |
| **Documentation** | **14/15** | **15/15** | **+1 honnête** : refonte structurée 25 docs / 8 catégories / frontmatter YAML, INDEX central, suppression éparpillement |
| Lisibilité/Conventions | 24/25 | 24/25 | inchangé (40 items ruff strict = décisions assumées) |
| Performance | 10/10 | 10/10 | inchangé |
| Sécurité | 24/25 | 24/25 | inchangé (règles ABSOLUES respectées) |
| **TOTAL** | **93/100** | **95/100** | **+2** |

### Plafond pratique 95/100 — pourquoi pas plus

Les ~5 pts manquants pour atteindre 100 sont **tous des décisions
architecturales assumées documentées** dans `07-02-DETTE-TECHNIQUE.md`, avec
un ROI très défavorable :

- **Architecture (−1)** : ~80 L d'aliases backward-compat dans `jarvis.py`
  (120 aliases consommés par 30+ tests existants) + 5 globals mutables avec
  setters lambda. Sortir ces patterns nécessiterait de modifier 30+ tests
  pour gain marginal (≤0.5 pt mesuré, risque régression silencieuse).
- **Tests (−2)** : la coverage pytest des Blueprints HTTP reste basse car
  Playwright ne génère pas de coverage Python. Faire monter ces lignes
  demanderait soit un système hybride pytest+coverage avec serveur live (lourd),
  soit du mocking Flask test_client (téléchargements + audio + Ollama + SSH —
  coût ≫ bénéfice vu que Playwright valide déjà bout-en-bout).
- **Lisibilité (−1)** : 13 SIM105 try/except: pass (lisibilité), 8 RUF005
  `arr + [x]`, ~135 inline styles JS HUD (animations temps réel), Monaco
  Editor CDN (2 MB+ minifié, dégradation gracieuse OK), 2 lambdas E731
  dans `chat/soc_inject.py` (noms expressifs locaux).
- **Sécurité (−1)** : Marc accepte que l'auto-engine SOC reste silencieux en
  mode CODE/CR/GENERAL (règle ABSOLUE `feedback_jarvis_no_regression`).

**95/100 est le plafond pratique honnête** pour ce projet sans engager des
refactors lourds dont le coût dépasserait largement le gain mesurable.

### Commits de la soirée + nuit (chronologique)

- `23be34d` — `docs(jarvis): refonte documentaire complete - DOCUMENTATION/ (25 docs, 8 categories numerotees)`
- `f62f072` — `docs(jarvis): MAJ bilan technique post refonte doc (score 94/100, audit honnete fin de journee)`
- `<next>` — `test(jarvis): extension Playwright api-coverage.spec.js (14 tests E2E sur 4 Blueprints HTTP sous-couverts en pytest) + score 95/100`

---

## 0sexies. Session 2026-05-23 fin d'après-midi — étapes 35-36 + bug UI reload RÉSOLU cause racine + couverture finale

Suite directe de §0quinquies. 8 commits supplémentaires en fin de session :

### Étape 35 — Tuile `llm/` (commit `3bcbea3`)

23ème tuile : extraction du cœur runtime LLM de jarvis.py :
- `llm/vram.py` (98 L) : `ensure_vram` + `ollama_swap` (unload SYNC + preload
  thread daemon), DI via getters/setter `_vram_model`
- `llm/stream.py` (158 L) : `stream_llm` (generator SSE Ollama /api/chat) +
  `think_filter_step` (filtre `<think>...</think>` modèles raisonnement)

jarvis.py : 1866 → 1819 L (−47).

### Étape 36 — Indicateur visuel `mode-loading` (commit `6506199`)

Suite à diagnostic latence fantôme au switch mode (1-3s côté Marc, RTX 5080) :
- CSS `.mode-loading` : pulse cyan + suffixe ⏳ sur les 4 boutons mode
- JS `_pollModeReady(mode)` : poll `/api/vram` toutes les 500ms (max 30s)
  jusqu'à voir le modèle target dans la liste loaded, puis retire la classe
- Mapping `_MODE_TARGET_MODEL` : general→gemma4, code→qwen2.5-coder,
  code_reasoning→qwen3 (SOC = MODEL résolu via GET /api/mode)

### Étape 36b — DI explicite `soc.py` = FIX RACINE bug UI reload (commit `709049f`)

**Le fix LONG TERME du bug UI reload signalé par Marc depuis des semaines**.

Remplace les 4 `from jarvis import` dans `blueprints/soc.py` (lignes 1149/
1153/1154/1463 — pattern lazy import dans fonctions thread) par DI explicite
via `init_soc()` étendu avec 4 kwargs optionnels : `get_jarvis_mode`,
`code_reasoning_mode`, `get_model`, `ollama_url`.

**Mécanisme du bug enfin compris** : Python ne voyait pas `jarvis` dans
`sys.modules` (qui tournait en `__main__`), donc à chaque appel de
`_soc_llm_call` ou similaire, **import jarvis.py UNE 2ème fois** comme
module → tout le top-level ré-exécuté → `_JARVIS_BOOT_ID` régénéré → côté
JS `_pollBootId` détectait nouveau boot_id → `location.reload()`. **UNE
fois par session** (après c'est en cache sys.modules) — d'où le caractère
aléatoire et non corrélé aux actions utilisateur.

Diagnostic n'a été possible que grâce à l'instrumentation JS-DIAG v2
(commit `da7384d`) qui a capturé la stack exacte `boot_init.js:870`.

Fix `8e3d518` (palliatif `os.environ` boot_id cache) reste en place par
sécurité mais n'est plus nécessaire. Marc a validé end-to-end : « l'ui
ne bronche pas top ».

### Étape couverture B + finale (commits `a8a9c5a` + `9a2c23b`)

+69 tests sur 4 modules les plus sous-couverts restants :
- `test_terminal_ssh_ws.py` (15 tests) : 15% → **82%** (mock paramiko + WS)
- `test_commands_sse.py` (23 tests) : 12% → **92%** (mock Proxmox API + SSH)
- `test_llm_vram.py` (10 tests) : 40% → **100%** (mock urllib + threads)
- `test_chat_file_correct.py` (21 tests) : 22% → **97%** (mock SSH + LLM
  stream + validate_protect_directives nginx)

### Score honnête recalibré (post étapes 35-36 + couverture finale)

| | Après §0quinquies | Post étapes 35-36 + couverture |
|---|---|---|
| jarvis.py | 1866 L | **1819 L** (−47) |
| Tuiles | 22 | **23** (+ `llm/`) |
| Tests | 1214 | **1283** (+69) |
| Coverage globale | 71% | **75%** (+4 pts ciblés) |
| Bug UI reload | palliatif + JS-DIAG en surveillance | **résolu cause racine** (DI explicite soc.py) + validé end-to-end Marc |
| Score | 91/100 | **93/100** |

### Commits de la fin d'après-midi (chronologique)

- `3bcbea3` — `refactor(jarvis): llm/vram + llm/stream - VRAM swap + stream Ollama (etape 35)`
- `7972eb5` — `docs(jarvis): ARCHITECTURE-TUILES.md - schema structure 23 tuiles post etape 35`
- `6506199` — `feat(jarvis): indicateur visuel mode-loading pendant swap VRAM (etape 36)`
- `8e3d518` — `fix(jarvis): _JARVIS_BOOT_ID idempotent via os.environ cache (RACINE bug UI reload)`
- `9a8162c` — `docs(jarvis): MEMORY trace finale bug UI reload (race + fix racine + validation Marc)`
- `709049f` — `refactor(jarvis): DI explicite soc.py - elimine les 4 from jarvis import (etape 36b)`
- `a8a9c5a` — `test(jarvis): +38 tests terminal/ssh_ws + commands/sse (etape B couverture)`
- `9a2c23b` — `test(jarvis): +31 tests llm/vram (100%) + chat/file_correct (97%) — couverture`
- `016b058` — `docs(jarvis): MAJ finale session 2026-05-23 (etapes 35-36 + bug UI reload resolu + couverture)`
- `5215547` — `refactor(jarvis): mode/ - route /api/mode + DI explicite (etape 37)`
- `b2cd4c4` — `test(jarvis): +11 tests mode/routes (100% coverage)`
- `98c9e0c` — `chore(jarvis): cleanup ruff strict — f-string modernisation + noqa documentes`

### Décisions architecturales documentées (audit final commit `98c9e0c`)

- **Aliases backward-compat dans jarvis.py (~80 L, 120 aliases)** : conservés. Pattern délibéré (les tests pytest existants consomment `jm._X`). Décision après audit explicite — la réduction est risquée (modifie 30+ tests) pour un gain marginal (≤0.5 pt). À reconsidérer si la maintenance devient pénible.
- **5 globals mutables avec setters lambda** : pattern legacy assumé (MODEL, _vram_model, SYSTEM_PROMPT, _welcome_data, _AUTO_PROFILE_MODEL). Sortir nécessiterait un refactor au niveau d'application Flask (state object au lieu de globals).
- **Blueprints HTTP sous-couverts (voice/routes 36%, settings/routes 44%, dev/routes 27%, web/routes 26%)** : décision archi — testés indirectement par E2E Playwright. Mocking Flask route ↔ téléchargements + audio + Ollama coûteux pour bénéfice limité.
- **Lambdas E731 dans `chat/soc_inject.py` (2)** : noms expressifs (`top`, `kvd`) + usage local strict, conversion en `def` alourdirait sans gain.
- **Try/except: pass (13 SIM105)** : non convertis en `contextlib.suppress` (plus verbeux, pas plus lisible).
- **`arr + [x]` patterns (8 RUF005)** : non modernisés en `[*arr, x]` (refactor risqué pour gain nul).

⚠ **Pour atteindre 95+/100** : (a) tests E2E Playwright nettoyés (~2-3 h, +1 pt) · (b) doc auto-générée à partir des docstrings (~1 h, +0.5 pt) · (c) réduction des aliases backward-compat (~1-2 h risqué, +0.5 pt — décidé NON aujourd'hui).

---

## 0quinquies. Session 2026-05-23 après-midi — étapes 34a/b + couverture +50 tests + fix conftest critique + log persistant

Suite directe de §0quater (étapes 27-33 du matin). 5 commits supplémentaires
l'après-midi : 2 refactors finaux (`tools/dispatch` + `facts/inject`), 1 batch
de tests ciblés (+50, couverture des modules récents), 2 fix infrastructure
(`jarvis.log` persistant + enrich `/api/tts` + **fix critique conftest.py**).

### Étape 34a — `tools/dispatch.py` (commit `569500b`)

Extraction du dict `_TOOL_DISPATCH` (14 outils LLM) vers `tools/dispatch.py`.
Fabrique `build(**handlers)` reçoit les 14 callables en DI explicite et
renvoie le dict prêt pour `chat/orchestrator.execute_tool`. Suppression de
14 lambdas thunk (`lambda args: _tool_X(args)`) qui ne faisaient que ré-appeler
la fonction. Avantage : le mapping `tool_name → handler` vit dans la tuile
`tools/` (sa place logique), plus hardcodé dans jarvis.py.
jarvis.py : 1860 → 1879 L (+19 net, lisibilité > compacité).

### Étape 34b — `facts/inject.py` (commit `36e8f17`)

Extraction de `_facts_inject` + `_load_facts` + `_now_fr` + constantes
`_MOIS_FR`/`_JOURS_FR` vers `facts/inject.py`. L'injection du system prompt
(date/heure live + faits persistants + résumés mémoire) vit maintenant dans
la tuile `facts/` où elle a sa place logique (les routes `/api/facts` y
sont déjà). DI via `init(get_facts_file, load_memory_summary, log)` — le
**callable getter** (vs Path figé) permet aux tests de monkeypatch
`jm.FACTS_FILE` sans casser. jarvis.py : 1879 → 1866 L (−13).

### Étape 34c — +50 tests ciblés sur modules sous-couverts (commits `d3eb0b0` + `7ffbcec`)

`tests/python/test_tools_local.py` (16) + `test_runtime_speak.py` (14) +
`test_bypass_wrappers.py` (20). Tous les modules récents (étapes 27-33) qui
étaient sous-couverts à 41-65% passent à **89-97%** :

| Module | Coverage avant | Coverage après |
|---|---|---|
| `tools/local.py` | 49% | **95%** |
| `runtime/speak.py` | 41% | **89%** |
| `bypass/wrappers.py` | 65% | **97%** |
| `facts/routes.py` | (juste créé) | **87%** |

Tests couvrent : sécurité executer_code (blocked_hard, blocked_args, timeout) ·
soc_status (fetch OK/KO/JSON invalide) · executer_script_windows (whitelist,
Popen mock, returncode) · speak() dedup intra/global + drop-oldest queue
pleine + routage stream actif/inactif · wrappers Proxmox/code/backup avec
DI réinitialisé et **restauration de l'état initial en teardown** (évite la
contamination des tests `test_jarvis_functions::_detect_service_restart_*`).

### Étape 34d — Fix infra critique : `conftest.py` + `jarvis.log` + enrich crash (commits `d3eb0b0` + `be4dc8b`)

**Bug remonté par Marc 14:07** : « UI qui se relance pendant lecture audio +
slider EQ » sur le dashboard SOC. Diagnostic post-mortem :

1. **Aucun crash backend** dans logs (`jarvis.log` + `tts.log`) — pas
   d'exception `/api/tts`. Le wrapper try/except était bien posé mais rien
   à capturer.
2. **Cause racine identifiée** : les **6 commandes `pytest tests/python/`**
   lancées pendant cette session ont chacune importé `jarvis` dans leur
   process Python (5 fichiers `test_jarvis_*` ont `import jarvis`), ce qui
   démarrait les **10 threads boot** (kokoro_preload, boot_vram_cleanup,
   soc_model_prewarm, kokoro_prewarm, ...) **sans** le flag
   `JARVIS_SKIP_BOOT_THREADS`. Pendant les 5-15 s de vie de chaque pytest,
   l'instance JARVIS de Marc voyait sa **VRAM swap, Ollama décharger des
   modèles, et Kokoro synthétiser "JARVIS opérationnel." sur les enceintes**.
3. **Doublons dans `jarvis.log`** à partir de 14:07:11 = signature exacte du
   process pytest parallèle écrivant dans le même fichier que l'instance
   JARVIS. Doublons stoppent à 14:08:11 = pytest terminé.

**Fix appliqué** : `tests/python/conftest.py` fait
`os.environ.setdefault("JARVIS_SKIP_BOOT_THREADS", "1")` **AVANT** le
`sys.path.insert` (donc avant que pytest collecte les modules).
`bootstrap/threads.start_all()` retourne alors immédiatement avec un log
`[BOOTSTRAP] ... SHUNTÉS`. Plus jamais d'interférence pytest ↔ JARVIS prod.

**Améliorations connexes** (commit `d3eb0b0`) :
- `_log` JARVIS reçoit un `RotatingFileHandler` → `scripts/jarvis.log`
  persistant (5 MB × 7 backups) avec format ISO datetime + niveau + name
  + traceback complet sur ERROR. Avant : `basicConfig` stdout uniquement,
  perdu si scrollback console ou close.
- Wrapper `/api/tts` enrichi : au crash, snapshot du contexte
  `{voice, engine, len, preview}` construit via getters `_get_voice` +
  `_get_dsp_params`. Diagnostic ciblé : révèle instantanément la voix Edge
  problématique à la prochaine occurrence du bug.

### Étape 34e — Fix idempotence anti-double-import (commit `06e4297`)

**Bug reproduit par Marc à 14:30** (lecture audio + slider EQ) puis **encore
à 14:33** (changement de mode dans le chat) — UI qui « saute / reboot ».

Diagnostic complet :

1. Logs `jarvis.log` montrent toutes les lignes écrites **2 fois** depuis le
   redémarrage à 14:29:02. Pas mes pytests cette fois (le fix conftest était
   actif), un seul process Python sur port 5000 (vérifié `Get-Process`).
2. Le coupable : `blueprints/soc.py` contient 4 `from jarvis import ...` à
   l'intérieur de fonctions thread (lignes 1149, 1153, 1154, 1463) — pattern
   lazy import pour éviter le cycle d'import au top-level.
3. Quand ces fonctions s'exécutent, Python ne voit pas `jarvis` dans
   `sys.modules` (le vrai jarvis tourne en `__main__`), donc il **importe
   `jarvis.py` UNE SECONDE FOIS** comme module `jarvis` → tout le top-level
   ré-exécuté → `_log.addHandler` ajoute le handler 2 fois (logs 2×) +
   `bootstrap.threads.start_all()` **relance les 10 threads boot**
   (kokoro_preload synthétise, boot_vram_cleanup décharge, prewarm phi4
   force la VRAM) → **interférence directe avec la session utilisateur**
   → UI qui semble se relancer.

Fix d'idempotence à 2 endroits :

- `scripts/jarvis.py` : `_log.addHandler(_jarvis_log_handler)` enveloppé
  dans `if not any(handler avec même baseFilename in _log.handlers)`. Le
  nom de fichier `RotatingFileHandler` sert d'identifiant unique.
- `scripts/bootstrap/threads.py` : flag module-level `_threads_started`
  vérifié au début de `start_all()`. Si True, log info
  `[BOOTSTRAP] start_all() déjà appelé — threads boot SHUNTÉS
  (anti-double-import)` et retour immédiat.

⚠ **Fix long terme préférable** : remplacer les 4 `from jarvis import`
dans `blueprints/soc.py` par des accesseurs DI passés à `init_soc()` —
plus invasif (modifie init_soc signature + jarvis.py qui l'appelle + 4
références soc.py). Le fix d'idempotence ci-dessus **étouffe les symptômes
sans changer le contrat de blueprints/soc** (zéro risque de régression).

**Validation** : log `jarvis.log` de Marc post-redémarrage 14:34:53 → 0
doublon depuis (vs systématique avant fix). 1214 tests OK.

### Étape 34f — Instrumentation JS-DIAG anti-bug UI reload (commits `30462b1` v1 + `da7384d` v2)

Posée par anticipation pour capturer la prochaine occurrence du bug UI
reload si le fix d'idempotence n'a pas tout couvert (hypothèse frontend
pur encore ouverte). **Bug reproduit chez Marc à 14:51:37 — preuve
dans le log** : 2 lignes `[JS-DIAG] jsdiag.ready` espacées de 93s = la
page a fait un **VRAI reload** (rechargement complet des scripts JS).
**Aucun `window.error` ni `unhandledrejection` capturé entre les deux**
→ c'est un `location.reload()` appelé directement par JS, pas une
exception non gérée. → confirme que le bug est côté frontend pur (pas
backend).

Contrat serveur (`scripts/jarvis.py`) :
- Route `POST /api/_diag/jslog` (60/min) — ingère `{kind, msg, src, url}`
  et logue dans `scripts/jarvis.log` sous le tag `[JS-DIAG]` avec
  troncatures (kind 32, msg 1000, src/url 300). Try/except enveloppe.

**v1 (`30462b1`)** : 3 hooks JS — `window.error`, `unhandledrejection`,
monkey-patch `location.reload` via `Object.defineProperty`.

⚠ **Échec monkey-patch reload v1** observé immédiatement après
déploiement : `[JS-DIAG] kind=jsdiag.setup | msg=reload monkey-patch
failed: Cannot redefine property: reload`. Les navigateurs modernes
(2026) refusent de redéfinir `location.reload` (property
non-configurable depuis longtemps).

**v2 (`da7384d`)** : remplace le monkey-patch par
`window.addEventListener('beforeunload', ...)` qui capte TOUTE
navigation sortante (reload, F5, close-tab, `location.href`). On perd
la distinction reload pur vs close-tab, mais on **gagne la stack trace
de l'exécution JS en cours au moment du unload** — suffit pour
identifier le caller. Bonus : `visibilitychange` ajouté.

Envoi : `navigator.sendBeacon` (préférentiel, survit à un reload) avec
fallback `fetch keepalive`. Send-and-forget, jamais throw.

**Au prochain bug UI (post-`da7384d`)** : `grep '\[JS-DIAG\]'
scripts/jarvis.log` listera tous les évents capturés. La ligne
`[JS-DIAG] kind=beforeunload | msg=UNLOAD/RELOAD | src=<stack 800
chars>` révélera quelle fonction JS a déclenché le reload (frame
identifiable dans la stack `at <function>:<line>:<col>`).

### Score honnête recalibré 2026-05-23 (post étape 34)

| | Matin (post-33) | Après-midi (post-34a/b/c/d/e/f) |
|---|---|---|
| jarvis.py | 1860 L | **1866 L** (+6 net) |
| Tuiles | 21 | **22** |
| Tests | 1164 | **1214** (+50 cibles couverture modules récents → 41-65% → 89-97%) |
| Coverage globale | 70% | **71%** |
| Bug intermittent UI reload | observé non diagnostiqué | **cause racine identifiée** (from jarvis import → double-init) **+ fix posé + instrumentation JS-DIAG en cas de récurrence** |
| Logs persistants | tts.log uniquement | + **scripts/jarvis.log** (5 MB × 7) + **JS-DIAG** dans le même flux |
| Score | 87/100 | **91/100** |

⚠ **Pour atteindre 93+/100** : (a) sortir `_ensure_vram` + `_ollama_swap` +
`stream_llm` + `_think_filter_step` dans une nouvelle tuile `llm/` (~140 L,
étape 35 envisagée) → +1 pt · (b) remplacer les 4 `from jarvis import`
dans `blueprints/soc.py` par DI explicite via init_soc() (fix long terme
vs palliatif idempotence) → +1 pt · (c) couvrir `terminal/ssh_ws.py`
(15%) et `commands/sse.py` (12%) — gros effort mocking paramiko + Proxmox
API → +2 pts.

---

## 0quater. Session 2026-05-23 — refactor architecture par tuiles complet (étapes 27-33 + 2 fixes)

Poursuite directe du refactor jarvis.py démarré 2026-05-22 (étapes 3-26 dans
commit `62ac692`). 7 nouvelles étapes commitées dans la journée + 2 hot-fixes
révélés en cours de session. Aucune régression cumulée : **1164 tests pytest
pass** à chaque commit.

### Étapes (cumul jarvis.py : 2556 → 1860 L, −696 L sur la session)

- **Étape 27 — `bypass/wrappers.py`** (commit `a329f3c`) : 11 wrappers DI
  couplés jarvis (3 détecteurs Proxmox + 2 wrappers code + 4 wrappers backup
  + `apt_upgrade_bypass_sse`) + constantes `VM_START_SSH_MAP`,
  `UPDATE_REBOOT_HOSTS`, `SVC_RESTART_RE` calculées dans `init()`.
  jarvis.py 2556→2477 L (−79).

- **Étape 28 — `chat/dispatcher.py`** (commit `ef97d17`) : carrefour chat
  complet extrait — route `/api/chat` + `chat_try_bypass` + `detect_file_corrections`.
  Blueprint `chat_dispatcher` (14ème tuile). DI massive ~30 deps injectée
  tardivement après `_chat_orch.init()`. Le rate-limit Flask-Limiter
  appliqué dans `init()` avant `register_blueprint`. jarvis.py 2477→2386 L (−91).

- **Étape 29 — `bootstrap/threads.py`** (commit `1497604`) : 9 threads daemon
  de démarrage + `rag_live_prewarm_start` regroupés derrière `init()` + `start_all()`
  unique. Threads : `kokoro_preload`, `tts_connectivity_loop`,
  `gpu_temp_monitor_loop`, `rag_embed_prewarm`, `boot_vram_cleanup`,
  `soc_model_prewarm`, `kokoro_prewarm`, `rag_auto_refresh_loop`, `vram_sync_loop`.
  `_vram_model` muté via getter/setter lambda (zéro couplage global).
  jarvis.py 2386→2210 L (−176).

- **Étape 30 — `terminal/ssh_ws.py`** (commit `9964c4e`) : 2 routes WebSocket
  PTY SSH (`/ws/ssh/<host>` et `/ws/dev`) + 3 helpers paramiko (`_ssh_reader`,
  `_ssh_connect`, `_ssh_handler`). DI légère `init(sock, ssh_terminal_map)`.
  jarvis.py 2210→2105 L (−105).

- **Étape 31 — `runtime/gpu_stats.py` + `runtime/speak.py`** (commit `af62370`) :
  helpers d'exécution partagés. `gpu_stats.py` (169L) = 3 fonctions GPU + état
  local `_net_prev`/`_disk_prev` sous `_STATS_LOCK`. `speak.py` (103L) = file
  TTS Python→browser avec dedup intra-source 3s + dedup global cross-source.
  jarvis.py 2105→**1954 L** (−151) — **première fois sous les 2000 lignes**.

- **Étape 32 — `facts/` + dispatch routes API dispersées** (commit `617e480`) :
  nouvelle tuile `facts/` (Blueprint `/api/facts` GET+POST). 3 routes éclatées
  vers Blueprints existants : `api_status` → `health/`, `api_history_last`
  → `chat/dispatcher`, `api_soc_context` → `blueprints/soc.py`.
  jarvis.py 1954→1898 L (−56).

- **Étape 33 — `tools/local.py`** (commit `6103358`) : 3 outils LLM exécutés
  localement Windows. `executer_code` (subprocess Python + whitelist hard+args)
  · `soc_status` (snapshot SOC pour phi4) · `executer_script_windows`
  (PowerShell whitelist stricte). DI propre via `init()`.
  jarvis.py 1898→**1860 L** (−38).

### Hot-fixes session (2 commits non-refactor)

- **`f4ad131` — `fix(jarvis): try/except global sur /api/tts`** : wrapper
  `api_tts` dans un try/except qui capture toute exception non gérée, log
  traceback complet (`_log.error` + `_tts_logger.error 'GLOBAL-CRASH'`) et
  retourne 500 JSON propre. Le corps réel est extrait dans `_api_tts_impl()`.
  Posé pour diagnostiquer le bug intermittent « UI qui se relance au switch
  voix Edge » signalé par Marc — la prochaine occurrence laissera une trace
  exploitable dans `logs/jarvis.log` + `logs/tts.log`.

- **`b03f23f` — `feat(jarvis): JARVIS_SKIP_BOOT_THREADS env flag`** : garde-fou
  dans `bootstrap/threads.start_all()` — si la variable d'env est définie,
  aucun thread n'est démarré (log info `[BOOTSTRAP] ... SHUNTÉS`). Suite
  d'une boulette de mes smoke tests qui avaient déclenché `kokoro_preload`
  (synthèse audio en parallèle de la lecture utilisateur) + `boot_vram_cleanup`
  (déchargement de modèles Ollama partagés). Usage : `JARVIS_SKIP_BOOT_THREADS=1
  python -c "import jarvis"` → 0 thread lancé, 0 interférence avec instance
  JARVIS en service.

### Score honnête recalibré 2026-05-23

| | Avant session | Après session (post-doc) |
|---|---|---|
| jarvis.py | 2556 L | **1860 L** (−61% cumul depuis 4814 L) |
| Tuiles | 16 | **21** (+`bootstrap`, `terminal`, `runtime`, `facts`, `tools`) |
| Tests | 1164 | 1164 (0 régression) |
| Coverage globale | 69% | **70%** (+1 pt, marginal — refactor pas suivi de tests directs sur les nouveaux modules) |
| Score | 95/100 (auto-affiché, surévalué) | **87/100 honnête** |

⚠ **Recalibrage honnête** : le 95/100 affiché par §0bis était trop indulgent.
Avec 5 nouveaux modules sous-couverts (terminal/ssh_ws 15%, commands/sse 12%,
runtime/speak 41%, bootstrap/threads 54%, chat/dispatcher 46%, tools/local 49%)
et 9 commits de retard sur la doc, le score réel avant MAJ doc était **82/100**.
La mise à jour doc (cette section) remonte à **87/100**. Pour atteindre 90+ :
ajouter ~50 tests directs sur les modules récents (+3-4 pts) et résoudre le
bug switch voix Edge quand il se reproduit (+2 pts).

---

## 0bis. Session 2026-05-22 — audit dette complet honnête + 7 correctifs

Audit dette technique complet du projet JARVIS (3 agents d'audit + vérification
personnelle de chaque finding sérieux). Score recalibré honnêtement : le
**92/100** auto-affiché était inflaté — consolidé **84/100** avant correctifs,
**88/100** après. Les 9 findings ont été traités le jour même :

- **E2** — deux whitelists de services divergentes (`_ALLOWED_SERVICES` soc.py
  vs `ALLOWED_RESTART_SVCS` security_whitelists.py) → consolidées dans
  `security_whitelists.py` (nouvelle `ALLOWED_SOC_RESTART_SVCS`, source unique ;
  `soc._ALLOWED_SERVICES` devient un alias). Divergence `php*-fpm` **résolue le
  jour même par vérification SSH** : aucun hôte ne tourne php-fpm (srv-nginx sans
  PHP, clt/pa85 en mod_php `libapache2-mod-php8.4`) — entrées `php*-fpm` mortes
  retirées des deux whitelists. `suricata` ajouté à `ALLOWED_SOC_RESTART_SVCS` :
  l'auto-engine SOC (`_check_services`, déclencheur #10) devait pouvoir le
  redémarrer mais son absence de la whitelist bloquait l'action.
- **M1** — `_SSH_DEV1` hardcodé alors que les 4 autres hôtes passaient par
  `soc_config.json` → `dev1_*` ajouté aux défauts, `_SSH_DEV1` dérivé de la config.
- **M2** — bloc `[tool.ruff]` mort dans `pyproject.toml` (ruff lit `ruff.toml`
  en priorité) → supprimé ; `pyproject.toml` ne porte plus que la config pytest.
- **M3** — éditeur Monaco chargé depuis CDN jsdelivr (seule dépendance réseau
  externe) → documenté dans `chat_ui.js` + `CLAUDE.md`, dégradation gracieuse OK.
- **M4** — `json.loads` non gardé dans `stream_llm` → `try/except` : une ligne
  Ollama malformée est sautée sans casser le flux SSE.
- **F1** — `.gitignore` ne couvrait pas `*.bak.<timestamp>.json` → pattern
  `*.bak.*` ajouté.
- **F4** — code mort retiré : `_vpEncodeWav` (voice_print.js), `handle_mcp`
  (jarvis_mcp_server.py) ; chemin obsolète `Documents\JARVIS` corrigé (DEPLOIEMENT.md).
- **F3** — doc drift corrigé (`CLAUDE.md`, ce document : compteurs
  lignes/tests/coverage réalignés sur la mesure réelle).
- **E1** *(partiel)* — couverture du cœur sécurité : +26 tests
  (`test_jarvis_soc_context.py`) sur `_build_monitoring_context`, `_kc_ban_signal`,
  `_pve_context_lines` — fonctions pures portant l'injection de contexte SOC dans
  phi4, jusque-là à 0%. `jarvis.py` 26→30%. ⚠ Reste ouvert : la couverture
  agrégée de `jarvis.py` (~150 routes Flask) demande un chantier de tests dédié —
  flaggé, non forcé (`feedback_no_big_refactor`).

Vérifications : **983 pytest pass · 0 skip · 0 fail**, ruff **0**, eslint **0 erreur**.
Travaux complémentaires le même jour : dé-duplication documentaire (source unique
§0) + **campagne couverture étape 1** (+158 tests → `jarvis.py` 26→40%, `soc.py`
31→59%, total 62%) + correctif crash `/api/facts` sur corps non-dict → score
**88 → 91/100**. ⚠ Refactor des monolithes : décidé avec Marc = couverture
d'abord, refactor ensuite, par extraction incrémentale validée à chaque étape.

**Refactor incrémental — étape 1** (2026-05-22) : cluster investigation IP
(`_b64py`, `_ssh_json_exec`, `_deep_geoip/crowdsec/fail2ban/autoban/nginx/rsyslog`)
extrait de `soc.py` vers le module dédié **`soc_ip_deep.py`** (DI : `_ssh_nginx`
injecté). `soc.py` 1872→**1729 L** (−143). `soc_ip_deep.py` 78% cov. soc.py garde
des alias légers → routes `ip-history`/`ip-deep` inchangées. 1091 tests, 0 régression.

**Refactor incrémental — étape 2** (2026-05-22) : cluster ban Suricata
(`_sur_ban_sev1`, `_sur_ban_scans`, `_sur_ban_sev2_surge`) extrait vers
**`soc_suricata_ban.py`** (DI : 6 fonctions du cœur ban/whitelist injectées).
`soc.py` 1729→**1687 L**. `soc_suricata_ban.py` 96% cov. `_soc_suricata_check`
appelle les `_sur_ban_*` via alias, inchangé.

**Refactor incrémental — étape 3** (2026-05-22) : cluster scoring menace
(`_threat_score_from_json`, `_check_threat_level`, `_check_escalation`) extrait
vers **`soc_threat_score.py`** (DI : `_soc_cooldown_ok` + `_ip_to_tts` injectés).
`soc.py` 1687→**1548 L**. `soc_threat_score.py` 74% cov. La route
`/api/soc/threat-score` et `_soc_monitor_loop` appellent les fonctions via alias,
inchangés.

**Refactor incrémental — étape 4** (2026-05-22) : cluster pic de trafic req/h
(`_reqhour_candidates`, `_reqhour_inject_suricata`, `_soc_reqhour_check`) extrait
vers **`soc_reqhour.py`** (équivalent Python de `checkReqPerHour()` JS).
`soc.py` 1548→**1500 L**. `soc_reqhour.py` 97% cov (+3 tests sur l'orchestrateur,
jusque-là non couvert). Cumul refactor : `soc.py` 1872→1500 (−372 L), 4 modules
cohérents extraits, 1094 tests, 0 régression. ⚠ Honnêteté : ce cluster est plus
couplé au cœur ban que les étapes 1-3 — DI à 12 dépendances, dont `_speak` et le
dict `_SOC_AUTO_BANNED` (réassignés après chargement du module) injectés via
lambdas résolues à l'appel. Les clusters restants (autoban, rsyslog/LLM, checks
auto-engine) sont enchevêtrés dans le cœur ban : les extraire relèverait du
déplacement plus que du découplage → **refactor par extraction suspendu ici**,
priorité remise sur la couverture de `jarvis.py`.

**Campagne couverture `jarvis.py`** (2026-05-22) : +26 tests sur les fonctions
pures et semi-pures de l'orchestrateur jusque-là non couvertes — politique CORS
(`_cors_origin`), détection restart service (`_detect_service_restart`), garde
des directives nginx protégées (`_validate_protect_directives`), profils de
prompt (`_get_model_profile`), persistance modèle/tâches/mémoire/résumés
(`_load_model`, `_load_tasks`, `load_memory`, `_load_memory_summary`, …).
`jarvis.py` 40→**43%**, coverage globale 63→**64%**. Plafond pragmatique : le
reste des ~1700 lignes non couvertes est constitué de handlers de routes Flask
et de générateurs SSE qui exigent un mock lourd d'Ollama/SSH/TTS — ROI
décroissant, traités au fil de l'eau plutôt qu'en chantier dédié.

**Refactor incrémental jarvis.py — étape 1** (2026-05-23) : cluster diagnostics
système (`_diag_gpu` + `_diag_ollama` + `_diag_cpu_temp` + `_diag_memory_count` +
`_diag_cpu_ram_disk`) extrait vers **`sys_diag.py`** (115 L · 80% cov). État
`_ollama_prev_ok` déplacé dans le module (son unique consommateur était
`_diag_ollama`). DI : `speak` injecté via lambda + `OLLAMA_URL` + `MEMORY_FILE`.
`jarvis.py` 4814→**4758 L** (−56 L, −55 stmts). La route `/api/sysdiag` reste
inchangée via les alias légers. **1164 tests, 0 régression.**

**Conversion complète en architecture par tuiles — étapes 3-26** (2026-05-23) :
sur demande de Marc (« je veux un JARVIS sans monolithique, que du modularisé »
+ « on poursuit jusqu'au bout »), conversion de tout JARVIS en 16 tuiles
autoportantes en 24 étapes / 24 commits, **0 régression** sur toute la série.

| Étape | Tuile / cluster | Effet sur `jarvis.py` |
|---|---|---|
| 3  | `system/` (sys_diag → tuile) | 4814→4758 (−56) |
| 4  | `memory/` (Blueprint + 6 routes) | 4758→4663 |
| 5  | `rag/` (Blueprint + 5 routes) | 4663→4419 |
| 6  | `files/` (outils LLM, pas de routes) | 4419→4316 |
| 7  | `ssh/` (outils LLM) | 4316→4281 |
| 8  | `bypass/` (regroupement 5 modules) | 4281→4281 (visuel) |
| 9  | `proxmox/` (api PVE) | 4281→4274 |
| 10 | `chat/` phase A (9 modules `chat_*` regroupés) | 4274→4256 |
| 11 | `voice/` phase A (8 modules tts/audio regroupés) | 4256→4256 (visuel) |
| 12 | `chat/orchestrator.py` (12 wrappers `_chat_*` extraits) | 4256→4211 |
| VRAM lock + sync `/api/ps` (post-checkpoint) | — | maintien 4211 |
| 13 | `voice/` Phase B1 (routes STT) | 4211→4217 |
| 14 | `voice/` Phase B2 (9 routes TTS/speak) | 4217→3994 |
| 15 | `voice/` Phase B3 (7 routes voice_lab) | 3994→3883 |
| 16 | `vision/` tuile | 3883→3867 |
| 17 | `settings/` tuile (16 routes config) | 3867→3694 |
| 18 | `tasks/` tuile (5 routes) | 3694→3612 |
| 19 | `health/` tuile (8 routes santé/stats) | 3612→3501 |
| 20 | `commands/` (6 générateurs SSE infra) | 3501→3292 |
| 21 | `chat/file_correct.py` (3 SSE + validate directives) | 3292→3150 |
| 22 | `dev/` tuile (4 routes + dev_exec_sse, sans WS) | 3150→3023 |
| 23 | `web/` tuile (recherche + /api/web-test) | 3023→2920 |
| 24 | `chat/tool_schemas.py` (210 L de schémas LLM) | 2920→2714 |
| 25 | `chat/orchestrator` reçoit `execute_tool` + `call_llm_with_tools` | 2714→2694 |
| 26 | `chat/soc_context.py` (`_build_monitoring_context` + helpers) | 2694→**2556** |

**Pattern** : chaque tuile = dossier `scripts/<tuile>/` + `__init__.py` (Blueprint
si routes + `init(...)` qui injecte les deps) + sous-modules métier. DI typique
20-30 paramètres injectés depuis `jarvis.py` au démarrage, jamais d'import
inverse `from jarvis import …`. Aliases backward-compat conservés dans
`jarvis.py` pour les tests existants et les consommateurs internes.

**VRAM lock + sync** (parenthèse non comptée comme étape) : `_VRAM_LOCK`
(threading.Lock) sérialise `_ensure_vram`/`_ollama_swap` ; `_vram_sync_loop`
thread daemon (60s) synchronise `_vram_model` avec l'état réel d'Ollama via
`/api/ps` — élimine les cold starts surprise quand Ollama décharge un modèle
(TTL embed 10m, pression mémoire). Pré-requis multi-user/productisation posés.

**Bilan cumulé** : `jarvis.py` **4814→2556 L (−47%, −2258 L)** · **16 tuiles
autoportantes** · **13 Blueprints register** · **1164 pytest pass · 0 régression**
sur les 24 commits enchaînés · coverage globale **64→69%** (+5pts).

**Plancher pratique atteint** : ~2500 L est l'ossature résiduelle légitime
(Flask app + imports + constants + glue DI/aliases + boot threads + api_chat
carrefour + WS terminal). La cible initiale « 700-1000 L ossature pure » était
trop optimiste — la glue DI/aliases pour 16 tuiles est incompressible à ~500 L.

**Restart obligatoire** entre la session précédente (étape 12 chat orchestrator)
et celle-ci pour valider le boot avec les 14 nouvelles tuiles. JARVIS confirmé
**fonctionnel** par Marc après restart (étape 13).

**Push Lisibilité + Tests** (2026-05-23) — 92 → **94/100** :

- **Lisibilité 13 → 14/15** : eslint **154 → 0 warnings**. Diagnostic des 154
  warnings : *tous* `no-unused-vars` sur des fonctions top-level consommées par
  HTML via le dispatcher `data-action` de `jarvis.html` (`window[fn]` lookup
  dynamique) que ESLint, sans bundler ni introspection HTML, ne peut pas tracer
  — faux positifs structurels. Correctif honnête en 2 temps : (1) config
  `eslint.config.js` alignée sur la politique du projet — `vars: 'local'`
  neutralise le scope global tout en gardant le signal sur les vrais locals
  (cohérent avec `ruff.toml` qui ignore E701/E702 pour les one-liners
  délibérés) ; (2) 12 vrais locals préfixés `_` (args/destructure inutilisés).
  Pas de `eslint-disable` épars, pas de gaming.
- **Tests 22 → 23/25** : +24 tests sur les helpers cœur de `blueprints/soc.py`
  (`_dur_to_tts`, `_ip_to_tts`, `_is_whitelisted`, `_ip_skip`, `_load_soc_config`,
  wrappers SSH par hôte, `_ssh_host`, `_ban_ip_ssh`, `_load_whitelist`,
  `_soc_log`). **`soc.py` 56→60% (seuil franchi)**, 1120→**1144 tests**. Le
  −2 restant = `jarvis.py` (43%) — handlers Flask/SSE comme exposé ci-dessus.

---

## 0ter. Session 2026-05-20 — correctif structurel pipeline voix + optimisation VRAM + instrumentation TTS

Diagnostic d'une latence voix intermittente au démarrage (parfois ~15-24 s, parfois gel total). Instrumentation AVANT correction (règle `feedback_instrument_first`).

### Correctif structurel du pipeline de lecture voix (`audio_viz.js`, `boot_init.js`)

Cause racine : la file de lecture (`processQueue`/`playSentence`) pouvait **(a)** geler définitivement (`playSentence` ne se résolvait que sur `source.onended`, jamais émis si la source joue sur un `AudioContext` suspendu) ou **(b)** provoquer un chevauchement (`source.start()` sur contexte suspendu planifie une source « gelée » qui ressurgit au `resume` suivant). Fix = invariant unique : **jamais de source TTS démarrée sur un AudioContext suspendu** — `processQueue` resume-ou-abandonne avant `playSentence`, verrou `isPlaying` pris avant tout `await`, ancien « timeout filet » supprimé. `boot_init.js` : déverrouillage audio armé tôt dans `_jarvisInit`, multi-gestes, flag `_userGestured` découplé du timing `/api/boot-id`.

### Découpage TTS des textes longs (`_splitForTts`)

`_splitForTts` découpe les textes > 280 caractères aux frontières de phrase (edge-tts a un temps de synthèse proportionnel à la longueur) → la voix démarre en ~1 s au lieu de ~15-24 s sur les longues analyses SOC.

### Optimisation VRAM (`jarvis.py`, `llm_opts.py`, `JARVIS-menu.ps1`)

- `_SOC_NUM_CTX` / `DEFAULT_SOC_NUM_CTX` : **16384 → 8192** → phi4 passe de ~12.4 Go à ~11.56 Go en VRAM (KV cache réduit).
- `mxbai-embed-large` dé-épinglé : `keep_alive` `-1` → `"10m"` (décharge après 10 min d'inactivité au lieu d'être épinglé à vie).
- `_soc_model_prewarm` précharge phi4 directement en `num_ctx 8192` (évite un reload au 1er chat SOC) · `_rag_embed_prewarm` délai 20 s → 5 s.
- Résultat mesuré : VRAM libre ~1.3 Go → **~2.0-2.8 Go**.
- **Décision actée** : phi4:14b conservé comme modèle SOC (pas de passage à qwen3:8b) — meilleur raisonneur analytique par Go de VRAM, VRAM suffisante après optimisation, zéro re-calibration du prompt anti-hallucination.

### Instrumentation TTS

Sondes `[TTS-PERF]` (`jarvis.py`, `tts_engines.py`, `deepfilter.py`) : décomposition `/api/tts` (edge_gen / dsp / total), timing edge-tts par tentative, chargement DeepFilterNet, threads de préchauffage boot. Log persistant `scripts/tts_perf.log` (RotatingFileHandler · filtre `[TTS-PERF]`).

### Tuile VRAM — tri d'affichage stable (`gpu_monitor.js`)

Les modèles d'embedding (RAG) sont toujours affichés en dernier → le segment RAG ne « saute » plus de gauche à droite quand phi4 charge.

---

## 0quater. Session 2026-05-16 nuit — Sprint 18d + refactor `_SOC_BAN_CONFIG` + intégrations defense_24h

### Sprint 18d — MCP `jarvis_ioc_status` (12ème outil)

Côté SOC : Sprint 18a a livré `ioc_collect.py` qui agrège 6 signaux POST-COMPROMISSION (AIDE drift / C2 Suricata / SSH anomaly NIGHT / webshells xdr nginx_drop / AppArmor denials / sudo events). Score 0-100 pondéré + level OK/WARN/CRIT exposé dans `monitoring.json` clé `ioc`.

Côté JARVIS (commit `ab80df5`) :
- **Endpoint `GET /api/soc/ioc`** dans `blueprints/soc.py` — lit `monitoring.json` via `_fetch_monitoring()` (cache TTL 30s + fallback SSH existant), extrait clé `ioc`.
- **12ème MCP tool `jarvis_ioc_status`** — handler async httpx → format compact LLM (header JARVIS + score/level + 6 compteurs + détails ⚠ si level≠OK).
- **Tests JARVIS** : 800 → **801 pass** (compte `test_jarvis_mcp_server` adapté 11→12).
- Smoke test live OK : `curl /api/soc/ioc` retourne `{"ok": true, "ioc": {...}}`. MCP écoute 127.0.0.1:5010.

### Refactor `_SOC_BAN_CONFIG` (commit `16469b6`)

Centralisation des 4 seuils `_SOC_BAN_MIN_*` + `_STAGE_PRIORITY` dans un dict structuré `_SOC_BAN_CONFIG` documentant les 4 stages OFFENSIFS auto-banables (EXPLOIT/BRUTE/SCAN/RECON) avec `(min_hits, source_lbl, duration, priority)` ; NEUTRALISÉ (IP déjà bloquée) jamais un candidat ban — PROBE/WAF ne sont pas des maillons KC (couches défensives séparées). Profils transverses `_SOC_BAN_HONEYPOT` / `_SOC_BAN_SURICATA` extraits. Backwards-compat : alias `_SOC_BAN_MIN_*` dérivés.

### Intégration `/api/soc/defense` (commit `ed8f3a8`)

Pattern « Single Source of Truth » : 1 JSON SOC (`defense_aggregator.py` cron 60s) → 3 consommateurs JARVIS :
- **Route HTTP `/api/soc/defense`** (cache 30s) — `blueprints/soc.py:_fetch_defense()`
- **Injection bloc compact phi4 mode SOC** — `chat_soc_inject.py:_format_defense_block()` (~400 chars : KPI + pic horaire + top 5 pays/AS/scénarios). Phi4 répond direct aux questions « combien de bans / quel pays attaque le plus / quelle heure de pointe » sans recalculer depuis monitoring.json brut (210 Ko → 0,4 Ko de contexte LLM).
- **Outil MCP `jarvis_defense_24h`** (11ème outil, devenu 12 avec IoC) — `jarvis_mcp_server.py:_handle_jarvis_defense_24h()`.

### Adaptation granularité heatmap 15 min (commit `0d7de9c`)

Suite au passage SOC à 96 buckets 15 min, les 2 consommateurs JARVIS du JSON adaptés : lecture `heatmap_bucket_min` du JSON (15 v1.2, fallback 60 si len(heat)≤24). Label peak adaptable : « tranche courante » / « il y a Xmin » / « h-X » / « h-X Ymin ».

### Quick wins dette ESLint (commit `9c904c2`)

QW4 — Hook ESLint pre-commit JARVIS aligné cohérence cross-projet :
- `files:` élargi de 4 fichiers historiques à **tous les modules JS** (4 + 18 extraits dans `scripts/static/js/`)
- `varsIgnorePattern: '^_'` → `'^(_|[A-Z][A-Z0-9_])'` (capture aussi SCREAMING_SNAKE_CASE comme `BS`, `DSP_PROFILES`)
- Résultat : **161 → 155 warnings** (80% restants = fonctions camelCase partagées impossibles à détecter sans bundler — acceptable). 0 erreur.
- Tests : 801/801 PASS, aucune régression.

---

## 1. Vue d'ensemble

JARVIS est un **assistant IA local** (type Iron Man) tournant sur la **station Windows 11** de Marc (RTX 5080, 16 GB VRAM). Interface web holographique v3.2, serveur Flask sur `localhost:5000`.

**Caractéristiques techniques** :
- Backend Python — **32 modules** (`jarvis.py` 4814L + 31 modules satellites), Flask + Ollama
- Frontend JS — **21 modules** (`jarvis_main.js` 148L + 18 modules `static/js/` + 3 modules `static/`)
- LLM local : **5 modèles Ollama** routés par mode (SOC/GENERAL/CODE/CR/RAG)
- TTS chain : **4 moteurs** avec fallback (edge → Kokoro CUDA → Piper → SAPI5)
- STT : **faster-whisper large-v3-turbo** + vocabulaire SOC initial_prompt
- RAG : **599 chunks** · mxbai-embed-large · seuil 0.35 · TTL 300s · auto-refresh 6h
- MCP server : **12 outils** exposés à Claude Desktop / Cursor sur port 5010 streamable-HTTP
- Routing automatique : 3 branches + bypass Python (VM/service/backup → sans LLM)
- Tests : **959 pytest pass** · coverage 52% · 22 modules à 100% cov
- Sécurité : whitelist SSH 29 patterns bloqués · profil SOC anti-double-ban · injection 100% serveur

**Architecture moteur IA local** :
```
Windows 11 (localhost:5000)
├── jarvis.py (Flask) + blueprints/soc.py + 30 modules satellites
├── Ollama (:11434)
│   ├── phi4:14b             9.1 GB  ← SOC/raisonnement (défaut)
│   ├── qwen2.5-coder:14b    9.0 GB  ← CODE · multi-fichiers
│   ├── gemma4:latest        9.6 GB  ← GÉNÉRAL + vision
│   ├── qwen3:8b             5.2 GB  ← CODE REASONING
│   └── mxbai-embed-large    0.7 GB  ← RAG embeddings · keep_alive 10m
├── Routing automatique — 3 branches + bypass
│   ├── VM/service/backup → bypass Python (sans LLM)
│   ├── mode CODE → qwen2.5-coder:14b
│   ├── mode CR (code reasoning) → qwen3:8b
│   ├── mode GÉNÉRAL/VOCAL → gemma4:latest
│   └── mode SOC (défaut) → phi4:14b + monitoring.json live
├── RAG local : 599 chunks · mxbai-embed-large · seuil 0.35 · TTL 300s · refresh 6h
├── STT : faster-whisper large-v3-turbo (CUDA) · vocabulaire SOC initial_prompt
├── TTS : edge-tts Antoine fr-CA → Kokoro ff_siwis (CUDA) → Piper → SAPI5
└── MCP : jarvis_mcp_server.py — 12 outils · port 5010
```

---

## 2. Architecture Python (32 modules)

### Cœur Flask

| Module | Taille | Coverage | Contenu |
|---|---|---|---|
| `jarvis.py` | 4814 L (2957 stmts) | 30% | Serveur Flask · ~150 endpoints · routing 4 modes · auto-engine SOC proactif · pré-warm phi4/Kokoro · circuit breaker imports · 8 call-sites Ollama wrappés |
| `blueprints/soc.py` | 1001 stmts (1687 L) | 57% | Endpoints SOC (`/api/soc/*`) · cache monitoring.json TTL 30s · fallback SSH · IP history 30j · ban/unban CrowdSec · defense_24h · ioc |
| `soc_ip_deep.py` | 69 stmts (180 L) | 78% | Investigation IP — GeoIP/CrowdSec/Fail2ban/autoban/nginx/rsyslog · extrait de soc.py (refactor incrémental étape 1, 2026-05-22) · DI `_ssh_nginx` |
| `soc_suricata_ban.py` | 57 stmts (82 L) | 96% | Ban auto Suricata — sév.1 / port scans / surge C2 · extrait de soc.py (refactor incrémental étape 2, 2026-05-22) · DI 6 fonctions |

### Modules satellites — Chat & LLM

| Module | Coverage | Contenu |
|---|---|---|
| `chat_system_prompt.py` | 100% | Assemblage system prompt par mode (SOC/GENERAL/CODE/CR) · injection profils prompt |
| `chat_soc_inject.py` | 38% | Injection bloc SOC compact dans system prompt phi4 (monitoring + defense_24h) — 100% serveur · `_build_monitoring_context` |
| `chat_routing.py` | 100% | Routing 3 branches + bypass Python (VM/service/backup détecté par mots-clés) |
| `chat_stream.py` | 100% | SSE streaming tokens Ollama → frontend |
| `chat_capture.py` | 100% | Capture réponse stream pour TTS deferred + history |
| `chat_generate.py` | 100% | Génération non-streamée (RAG embedding, tool detection, summarize) |
| `chat_messages.py` | 100% | Construction messages Ollama (history + system + user) |
| `chat_tool_calls.py` | 100% | Parsing tool calls Ollama format (function_call structure) |
| `chat_pending_bypass.py` | 100% | Bypass Python en attente — exécutés avant appel LLM |
| `llm_opts.py` | 100% | Params LLM (temperature, num_ctx adaptatif, num_predict, seed) |
| `stream_tokens.py` | 100% | Helpers SSE format `data: {...}\n\n` |

### Modules satellites — Audio & TTS/STT

| Module | Coverage | Contenu |
|---|---|---|
| `tts_engines.py` | 83% | 4 moteurs TTS · cache pipeline Kokoro/Piper · fallback chain · cold start mesuré |
| `tts_cleaner.py` | 100% | Pré-processing texte avant TTS (regex emojis, ponctuation, abréviations) |
| `tts_dedup.py` | 100% | Dédup phrases consécutives (anti-bégaiement TTS) |
| `deferred_speak.py` | 100% | Speak après fin stream (anti-coupure mid-phrase) |
| `audio_dsp.py` | 25% | Calculs DSP audio Web Audio API (EQ paramétrique, compresseur, limiteur, convolution IR) |
| `deepfilter.py` | 84% | DeepFilterNet CUDA · denoising audio temps réel |
| `stt.py` | 98% | faster-whisper large-v3-turbo · vocabulaire SOC initial_prompt |
| `voice_lab.py` | 71% | XTTS v2 voice prints (58 voix) + UI Voice Lab |
| `vision.py` | 92% | Vision gemma4 (multimodal images) |

### Modules satellites — Infrastructure & sécurité

| Module | Coverage | Contenu |
|---|---|---|
| `ollama_circuit.py` | 100% | Circuit breaker Ollama (state machine 3 états CLOSED/HALF_OPEN/OPEN · backoff exponentiel ×2 plafonné 5min · thread-safe singleton) |
| `security_whitelists.py` | 100% | `_BLOCKED_SSH` 29 patterns · `_ALLOWED_SERVICES` immuables sans validation |
| `ssh_terminal.py` | 100% | SSH read-only 4 hôtes (srv-nginx · clt · pa85 · proxmox) · clés `~/.ssh/id_*` |
| `bypass_filesystem.py` | 100% | Bypass fichiers (read/list/stat) · sandboxé par hôte |
| `bypass_proxmox.py` | 100% | Bypass Proxmox (API ticket + token · qm list · pct list) |
| `bypass_backup.py` | 96% | Bypass backup Proxmox + Windows + GPU + disque |
| `proxmox_api.py` | 93% | API Proxmox VE directe (ticket+token auth · cache 30s) · `_pve_fetch_state` + `_pve_context_summary` |
| `rag_live.py` | 92% | RAG live · 599 chunks · auto-refresh 6h · embed `keep_alive "10m"` (dé-épinglé 2026-05-20) |
| `code_reasoning.py` | 44% | Mode CODE REASONING · qwen3:8b · contexte étendu |

### Modules satellites — MCP server

| Module | Coverage | Contenu |
|---|---|---|
| `jarvis_mcp_server.py` | 91% | Serveur MCP streamable-HTTP port 5010 · 12 outils · sanitize IP → [IP] · JARVIS_HEADER format · watchdog |

---

## 3. Architecture Frontend (21 modules JS)

### Refactor JS terminé (2026-05-14 → 2026-05-15)

`jarvis_main.js` **7828 → 148 L (−98,1%)** en **13 extractions** dans `static/js/` :

| # | Commit | Module | Lignes | Contenu |
|---|---|---|---|---|
| 1 | `a118772` | `tasks_tab.js` + `welcome.js` | 129 + 244 | Onglet tâches · message bienvenue |
| 2 | `fe1be24` | `eq_parametric.js` | 502 | EQ voix paramétrique |
| 3 | `3f37189` | `eq_music.js` + `audio_mire.js` | 701 + 383 | EQ musique · mire audio |
| 4 | `0c5d110` + `c83f57f` | `audio_viz.js` | 1138 | Toute la viz audio · ⚠ régression load-order `_SAMPLE_RATE` |
| 5 | `5f57018` | `settings_llm.js` | 477 | Params LLM · profils prompt · system prompt · faits · mémoire LT · RAG |
| 6 | `496ffc7` | `dsp_audio.js` | 291 | Chaîne DSP UI · gain/comp/lim/EQ bandes · push backend |
| 7 | `99b920c` | `boot_init.js` | 792 | BOOT SEQUENCE · message intro vocal · rack FX UI · INIT `_jarvisInit` |
| 8 | `6fa224d` | `audio_rack.js` | 693 | AI AUDIO RACK · faders/comp/EQ/stereo/Haas/DeepFilter/master/VU · presets EQ |
| 9 | `b1c8188` + `f8725b5` | `chat_core.js` | 512 | `sendMessage` · SSE chat streaming · 4 modes setters · vision · diagnostic · ⚠ régression `_LS_PROMPT_PROFILE` |
| 10 | `(commit)` + sed off-by-one fix | `chat_ui.js` | (extracted) | UI chat · `const history` perdu puis restauré |
| 11 | `(commit)` | `gpu_monitor.js` | (extracted) | Monitoring GPU temps réel |
| 12-13 | finals | (autres) | (extracted) | Voice Lab · STT · Terminal Code |

**Validation par étape** : bodies byte-identiques · `node --check` · eslint 0 erreur · validation E2E prod F12=0 sur tous onglets.

### Modules JS finaux dans `static/js/` (18 fichiers) et `static/` (3 fichiers)

Top tailles :
- `jarvis_mixing.js` (1375 L) — UI mixing audio
- `audio_viz.js` (1138 L) — viz spectre + waterfall + VU
- `voice_print.js` (852 L) — empreintes vocales XTTS
- `boot_init.js` (792 L) — boot sequence + rack FX
- `eq_music.js` (701 L) — EQ musique
- `audio_rack.js` (693 L) — AI audio rack
- `recorder.js` (660 L) — recording audio + analyse
- `soc_tab.js` (593 L) — onglet SOC dashboard
- `chat_core.js` (512 L) — chat core SSE
- `eq_parametric.js` (502 L) — EQ paramétrique
- `settings_llm.js` (477 L) — params LLM
- `audio_mire.js` (383 L) — mire audio test
- `dsp_audio.js` (291 L) — chaîne DSP
- `welcome.js` (244 L) — message bienvenue
- `jarvis_main.js` (148 L) — POINT D'ENTRÉE FINAL après refactor

### Reste dans `jarvis_main.js` (148 L)

ONGLET SOC · SOC GRAPHIQUES · MODELE/VOICE SWITCHER · SETTINGS GPU HEALTH · CHAT HUD EXTRAS — 4-5 modules potentiels mais **rendement décroissant**. Refactor **officiellement clos** (cf. `feedback_no_big_refactor`).

### CSS (8 fichiers · 5087 L total)

- `chat.css` 1489L · `voicelab.css` 1349L · `jarvis.css` (base) · `boot.css` · `dsp.css` · `eq.css` · `audio.css` · `soc.css` (intégration tuile SOC)

### Templates HTML (10 fichiers · 3371 L total)

`jarvis.html` (204 L · split tabs/ + modals.html) + templates partiels pour chaque onglet/modal.

---

## 4. Circuit breaker Ollama (commit `8ebbbad` + extensions)

**Module** : `scripts/ollama_circuit.py` (110 L · 100% cov · 23 tests)

**Pattern** : state machine 3 états thread-safe singleton.

| État | Comportement | Transition |
|---|---|---|
| **CLOSED** (vert) | Requêtes passent normalement | → OPEN après 3 erreurs consécutives |
| **OPEN** (rouge) | Refus immédiat (`OllamaUnavailable` 1ms) au lieu de timeout 30s | → HALF_OPEN après backoff (30s × 2^N · max 5min) |
| **HALF_OPEN** (orange) | Test 1 requête | → CLOSED si succès · → OPEN si échec |

**8 call-sites wrappés dans `jarvis.py`** :
1. Chat stream L1791 (principal)
2. Chat models test L4296
3. Summarize L774
4. RAG embed L821
5. Tool detect L1733
6. Welcome refresh L2519
7. RAG embed prewarm L4565
8. SOC model prewarm L4601

**4 endpoints intentionnellement NON wrappés** (ping/health) : L674 health, L2560 sysdiag, L4575 vram cleanup, L4585 unload urllib direct.

**UX** :
- **Indicateur HUD** `● OLLAMA` (vert CLOSED · orange HALF_OPEN · rouge OPEN clignotant)
- **Endpoint `/api/ollama-status`** : `{running, state, retry_in_s, current_timeout_s}`
- **Bouton SOC dashboard PING JARVIS** (commit SOC `3d73448`) : toast + badge `cb-closed/cb-half_open/cb-open` + animation blink si OPEN

**Bénéfice mesuré** : refus 1ms vs timeout 30s = JARVIS reste réactif quand Ollama crash · diagnostic instantané pour user.

---

## 5. TTS chain & profiling (commits `efac7f9` + `2cc98e9`)

### 4 moteurs avec fallback chain

`edge-tts → Kokoro CUDA → Piper → SAPI5`

| Moteur | TTFB médian (chaud) | Cold start | Backend |
|---|---|---|---|
| **edge-tts** | 1453 ms | 765-1344 ms (DNS+retry) | API Microsoft cloud (fr-CA-AntoineNeural défaut) |
| **Kokoro** | **203 ms** ⚡ | **42.8 s** (chargement VRAM CUDA) | Local CUDA · pipeline ff_siwis |
| **Piper** | 219 ms | 1.6 s (ONNX CPU) | Local CPU · ONNX |
| **SAPI5** | 563 ms | (Windows natif) | SAPI Hortense FR · fallback ultime |

**Outil profiling** : `tools/profile_tts.py` — mesure TTFB+total+taille pour 4 moteurs × 7 textes. Restaure engine d'origine en `try/finally`.

### Pré-warm Kokoro CUDA au boot (commit `2cc98e9`)

**Problème** : cold start Kokoro = 42.8s → 1re alerte vocale SOC arrivait avec ~43s de latence.

**Fix** : thread daemon `_kokoro_prewarm` lancé 60s après boot (après `_soc_model_prewarm` + marge GPU). Charge le pipeline Kokoro CUDA en VRAM avant la 1re alerte vocale.

**Validation post-redémarrage** : `/api/tts/status` retourne Kokoro = `EN SERVICE` immédiatement (au lieu de `CHARGEMENT`). TTS instantané dès la 1re alerte SOC (~200 ms TTFB).

**Recommandation** : Kokoro/Piper 7-10× plus rapides qu'edge en chaud — défaut pour temps-réel SOC.

---

## 6. MCP server — 12 outils

**Module** : `scripts/jarvis_mcp_server.py` (269 stmts · 91% cov · 52 tests)

**Configuration** : streamable-HTTP port 5010 · accessible Claude Desktop / Cursor.

### Sanitize sortant
- IPv4 → `[IP]` (anti-leak credentials)
- Troncature 3000 chars

### Liste des 12 outils

| # | Outil | Fonction |
|---|---|---|
| 1 | `jarvis_chat` | Chat libre avec JARVIS (mode actif) |
| 2 | `jarvis_soc_ask` | Question SOC avec injection historique IP 30j (via `/api/soc/ip-history`) |
| 3 | `jarvis_soc_status` | État SOC live (monitoring.json compact) |
| 4 | `jarvis_stats` | Stats JARVIS (Ollama state, modèle actif, RAG chunks) |
| 5 | `jarvis_read_file` | Lecture fichier sandbox (read-only) |
| 6 | `jarvis_model_switch` | Changement modèle Ollama actif |
| 7 | `jarvis_last_response` | Récupère la dernière réponse JARVIS |
| 8 | `jarvis_code_exec` | Exécution code Python sandbox restrictif |
| 9 | `jarvis_ssh_file` | SSH read-only fichier sur 4 hôtes whitelistés |
| 10 | `jarvis_ip_history` | Historique IP 30 jours (depuis `/api/soc/ip-history`) |
| 11 | `jarvis_defense_24h` | Résumé compact actions défensives 24h (Sprint defense_aggregator) |
| 12 | `jarvis_ioc_status` | Score IoC POST-COMPROMISSION (Sprint 18d 2026-05-16) — 6 signaux (AIDE/C2/SSH/Webshells/AppArmor/Sudo) + level OK/WARN/CRIT |

---

## 7. Intégrations SOC (cross-projet)

JARVIS consomme `monitoring.json` (cron srv-nginx 1min) via 3 patterns :

### 7.1. Cache + fallback SSH
- `/api/soc/*` endpoints utilisent `_fetch_monitoring()` (cache TTL 30s)
- Si HTTP `:8080` échoue → fallback SSH `scp` depuis srv-nginx
- Garde JARVIS opérationnel même si srv-nginx HTTP down

### 7.2. Injection contexte phi4 mode SOC (100% serveur)
- `chat_soc_inject.py` injecte un bloc compact dans le system prompt phi4
- **JAMAIS persisté dans l'historique chat** (sinon hallucinations multi-tours)
- Profil SOC : règles ABSOLUES (IPs déjà bannies + crawlers légitimes + reco ban proportionnée signal FORT/faible)
- Auto-engine SOC actif **UNIQUEMENT en mode soc**

### 7.3. MCP outils SOC
- 6 outils MCP exposent SOC à Claude Desktop : `jarvis_soc_ask`, `jarvis_soc_status`, `jarvis_ip_history`, `jarvis_defense_24h`, `jarvis_ioc_status`, `jarvis_ssh_file`

### Données consommées de SOC

- **`monitoring.json`** v3.7.0 (cron 1min srv-nginx) — 59 clés validées jsonschema
- **`defense_24h.json`** (cron 60s `defense_aggregator.py`) — KPI + heatmap 96 buckets + delta + top + timeline
- ~~`router.json`~~ retiré 2026-05-17 ( — routeur débranché)
- **clé `ioc`** dans monitoring.json (Sprint 18a `ioc_collect.py`) — 6 signaux POST-COMPROMISSION

---

## 8. Sécurité & règles absolues

### 8.1. Whitelist SSH stricte (`security_whitelists.py` 100% cov · 41 tests)

**`BLOCKED_SSH_PATTERNS`** : **33 patterns** regex bloqués (rm/dd/mkfs/shutdown/qm destroy/sed -i/chmod/`apt install`/`apt upgrade`/`apt-get install`/`apt-get upgrade`/etc.) — ajout 2026-05-17 des 4 patterns apt pour fermer faille défense-en-profondeur.
**`ALLOWED_RESTART_SVCS`** : 8 services restartables whitelistés (`nginx`, `fail2ban`, `crowdsec`, `crowdsec-firewall-bouncer`, `suricata`, `apache2`, `php7.4-fpm`, `php8.2-fpm`)
**`ALLOWED_APT_PKGS`** : 12 paquets `apt install/upgrade` whitelistés (5 services ci-dessus + `suricata-update`, `libssl3`, `openssl`, `python3`, `python3-pip`, `certbot`, `python3-certbot-nginx`)
**`is_known_write_op(cmd)`** (ajout 2026-05-17) : gardien sécurité — retourne `True` ssi la commande est de forme reconnue par `check_write_op` (systemctl restart `<svc>` OU apt[-get] install/upgrade `<pkg>`). Source unique regex `_RE_SYSTEMCTL_RESTART` + `_RE_APT_WRITE` extraites en constantes module.
**`check_write_op()`** : valide ops write sur whitelist stricte. Retourne `None` si OK ou hors scope, message d'erreur sinon. ⚠ Doit toujours être précédé de `is_known_write_op` dans le caller — sinon `None` pour `rm -rf /` autoriserait à tort.

**Logique 4 couches corrigée 2026-05-17** dans `_tool_commande_ssh_run` ([jarvis.py:1652](scripts/jarvis.py#L1652)) :

| Couche | Condition | Décision | Audit |
|---|---|---|---|
| 1 | Aucun pattern BLOCKED matche | Exec direct (lecture/diagnostic) | Pas d'audit (hors scope write) |
| 2 | Pattern BLOCKED matche + `is_known_write_op=True` + `check_write_op=None` (whitelistée) | Exec | `allowed=true` |
| 3 | Pattern BLOCKED matche + `is_known_write_op=False` (rm/mkfs/dd/shutdown/qm destroy/...) | **REFUS PAR DÉFAUT** | `allowed=false` |
| 4 | Pattern BLOCKED matche + `is_known_write_op=True` + `check_write_op` retourne str (svc/pkg non whitelisté) | REFUS explicite | `allowed=false` |

**⚠ Fix critique 2026-05-17** : avant la correction, la couche 3 n'existait pas. `rm -rf /` matchait pattern `"rm "`, `check_write_op` retournait `None` (pas son rôle), `err is not None` était False → **commande exécutée**. Faille colmatée par ajout `is_known_write_op` comme gardien préalable.

### 8.2. Audit log write ops (ajouté 2026-05-17)

**Fichier** : `JARVIS/logs/audit_writeops.jsonl` (gitignored — `logs/` exclu)

**Fonction** : `audit_writeop(host, cmd, allowed, output, *, log_path, ts)` dans `security_whitelists.py` — best-effort (un échec d'I/O ne bloque JAMAIS l'exécution de la commande SSH).

**Format JSONL** (1 ligne par appel) :
```json
{"ts":"2026-05-17T07:13:27Z","host":"ngix","cmd":"systemctl restart nginx","allowed":true,"out_len":27}
{"ts":"2026-05-17T07:13:28Z","host":"clt","cmd":"systemctl restart evilsvc","allowed":false,"out_len":51}
```

**Trace TOUTES les write ops détectées** : autorisations ET refus (forensic). Commande tronquée à 500 chars (limite taille log). Sortie commande non loggée (seulement sa longueur, pour confidentialité).

**Tests pytest** : 7 nouveaux tests (`test_audit_writeop_*`) — append JSONL · refus tracé · multiple append · troncature 500 chars · création répertoire parent · best-effort I/O errors · format timestamp UTC ISO8601.

**Total tests pytest** : 801 → **808 pass** (+7 audit_writeop).

### 8.3. SSH read-only par défaut (`ssh_terminal.py` 100% cov)

4 hôtes terminal interactif xterm.js : srv-dev-1 · srv-nginx · clt · pa85. Mode interactif WebSocket PTY (paramiko).

**Hôtes write ops via `_tool_commande_ssh_*`** : 4 wrappers (ngix · proxmox · clt · pa85). Toute commande qui matche un `BLOCKED_SSH_PATTERN` doit passer `check_write_op` → si whitelistée, exécution + audit log.

### 8.3. Profil SOC anti-double-ban (`_SOC_BAN_CONFIG`)

Source unique seuils ban dans `blueprints/soc.py` (refactor commit `16469b6`) :
- **4 stages OFFENSIFS** auto-banables : EXPLOIT · BRUTE · SCAN · RECON (chacun avec min_hits, source_lbl, duration, priority)
- **NEUTRALISÉ** jamais banni (règle absolue) : IP déjà bloquée par CrowdSec/fail2ban
- KC v4 = 5 maillons offensifs purs ; PROBE (UFW) / WAF (ModSec) ne sont PAS des maillons KC — couches défensives séparées (ligne de défense)

Profils transverses : `_SOC_BAN_HONEYPOT` · `_SOC_BAN_SURICATA`.

### 8.4. Anti-hallucination phi4 (commits `d9b1656` + `ff217ba`)

- `shown[:25]` → `[:100]` dans `_build_monitoring_context_soc` (+contexte)
- Règle anti-double-ban explicite dans SYSTEM_PROMPT
- Description KC 5 maillons (RECON→SCAN→EXPLOIT→BRUTE→NEUTRALISÉ) — PROBE/WAF hors KC (réaligné 2026-05-20)
- Injection 100% serveur (jamais l'historique chat)

### 8.5. RFC1918 immuable

Adresses RFC1918 (10./172.16-31./192.168./127.) **JAMAIS** :
- Recommandées au ban
- Traitées comme menace externe
- Exposées en clair dans le MCP (sanitize → `[IP]`)

---

## 9. Performance

### 9.1. Fix IPv6 systémique (Phase 3 perf)

**Problème** : `localhost` résout `::1` (IPv6) en premier sur Windows → Flask n'écoute pas IPv6 → timeout ~2s par requête interne.

**Fix** : forcer `127.0.0.1` partout dans les clients internes.

| Variable | Avant | Après | Localisation |
|---|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | `http://127.0.0.1:11434` | `jarvis.py:544` (source unique) |
| `JARVIS_BASE` (MCP) | `localhost:5000` | `127.0.0.1:5000` | `jarvis_mcp_server.py` |
| Clients internes | divers `localhost` | `127.0.0.1` partout | tous modules |

**Gain mesuré** : −97% latence clients internes.

**Outil profiling** : `tools/profile_perf.py`.

### 9.2. Cache SOC 30s + fallback SSH

`_fetch_monitoring()` dans `blueprints/soc.py` :
- Cache TTL 30s (évite hammering srv-nginx `:8080`)
- Fallback SSH `scp` automatique si HTTP fail (garde MCP fonctionnel)

### 9.3. Pré-warm modèles au boot

- **phi4:14b SOC** (`_soc_model_prewarm`) — thread daemon · préchauffe directement en `num_ctx 8192` (évite un reload au 1er chat SOC)
- **Kokoro CUDA TTS** (`_kokoro_prewarm`) — thread daemon 60s après boot
- **RAG embed prewarm** (`_rag_embed_prewarm`) — mxbai-embed-large · délai 5s (le RAG se charge avant phi4) · `keep_alive "10m"` (dé-épinglé 2026-05-20 : se décharge après 10 min d'inactivité)

### 9.4. Optimisation VRAM (2026-05-20)

- `_SOC_NUM_CTX` (jarvis.py) / `DEFAULT_SOC_NUM_CTX` (llm_opts.py) : **16384 → 8192** → KV cache réduit, phi4 passe de ~12.4 Go à **~11.56 Go** en VRAM.
- `mxbai-embed-large` dé-épinglé : `keep_alive` `-1` → `"10m"` (dans `_rag_embed` et `_rag_embed_prewarm`).
- **Résultat mesuré** : VRAM libre **~1.3 Go → ~2.0-2.8 Go**.
- phi4:14b conservé comme modèle SOC (décision actée — pas de passage à qwen3:8b).

### 9.5. Pipeline de lecture voix — invariant AudioContext (2026-05-20)

- File de lecture `processQueue`/`playSentence` (`audio_viz.js`) : invariant « jamais de source TTS sur AudioContext suspendu » — supprime le gel définitif et le chevauchement.
- `_splitForTts` découpe les textes > 280 caractères aux frontières de phrase → voix en ~1 s vs ~15-24 s sur les longues analyses SOC (edge-tts a un temps de synthèse proportionnel à la longueur).

### 9.6. Debounce DSP audio

Push backend params DSP → debouncé 100ms (évite spam HTTP sur drag slider EQ).

---

## 10. Tests & qualité

### Coverage par catégorie

**Modules à 100% cov** (21) — logique pure isolée :
`ollama_circuit · chat_tool_calls · tts_cleaner · stream_tokens · security_whitelists · chat_pending_bypass · llm_opts · chat_capture · chat_generate · chat_messages · chat_routing · chat_stream · chat_system_prompt · deferred_speak · bypass_filesystem · stt · ssh_terminal · tts_dedup · vision · bypass_proxmox · deepfilter`

**Modules ≥83%** (additionnel) :
`tts_engines 83% · jarvis_mcp_server 91% · rag_live 92% · vision 92% · proxmox_api 93% · bot_verify 95% · bypass_backup 96% · stt 98%`

**Modules <50%** (5) — surface monolithique I/O :
`jarvis.py 30% · audio_dsp.py 25% · blueprints/soc.py 31% · chat_soc_inject.py 38% · code_reasoning.py 44%`

### Tests E2E

**25 tests E2E Playwright** (`tests/e2e/`) :
- 23 UI (boot, modes, chat, SOC tab, voice lab, settings)
- 2 smoke LLM (chat round-trip phi4/gemma)

### Pre-commit hooks

- **Commit** : ruff + eslint bloquants (0 erreur required)
- **Pre-push** : pytest 959 tests bloquants (CI cloud impossible « rien sur le web »)

### ESLint config (`eslint.config.js`)

- `varsIgnorePattern: '^(_|[A-Z][A-Z0-9_])'` — capture `_` et SCREAMING_SNAKE_CASE
- Globals cross-file déclarés pour modules JS sans bundler
- **155 warnings · 0 erreur** (camelCase exports inter-modules, acceptés)

---

## 11. Roadmap résiduelle

### Tâches ouvertes (CLAUDE.md racine `## Roadmap JARVIS`)

- [ ] **SSH write ops** — levée partielle (`apt upgrade` / `restart`) après stabilisation routing — **SEULE tâche encore ouverte**

### Tâches terminées (toutes `[x]` validées)

- [x] Triggers auto-engine SOC (ban >500 req/h · restart si service down)
- [x] Onglet `◈ SOC` jarvis.html + journal proactif + analyse LLM
- [x] Alertes vocales TTS niveau ÉLEVÉ/CRITIQUE
- [x] Routing automatique phi4/qwen2.5 + 3 RÈGLES ABSOLUES
- [x] SSH tools 4 hôtes lecture seule + 29 patterns bloqués
- [x] STT large-v3-turbo + initial_prompt vocabulaire SOC
- [x] RAG 599 chunks · seuil 0.45 · TTL 300s
- [x] NDT 100/100 dette zéro absolue CSS/JS/HTML/Python
- [x] MCP `jarvis_soc_ask` injection historique IP 30j
- [x] 3.3 ThreatScore 30j historique (sparkline + modal Canvas)
- [x] 4.2 Rapport quotidien (email cron srv-nginx + vocal `_check_daily_report()`)
- [x] 3.2 Corrélation temporelle 14j (campagnes lentes /24 + alerte vocale)
- [x] 4.1 Proxmox API directe (`_pve_fetch_state` cache 30s · ticket+token)
- [x] Circuit breaker Ollama 8 call-sites + indicateur HUD
- [x] Pré-warm Kokoro CUDA au boot
- [x] Profiling TTS détaillé (`tools/profile_tts.py`)
- [x] Refactor JS terminé `jarvis_main.js` 7828 → 148L (−98,1%)
- [x] Sprint 18d MCP `jarvis_ioc_status` (12ème outil)
- [x] Refactor `_SOC_BAN_CONFIG` source unique seuils ban

### ⚠ Rappel : ce ne sont PAS des dettes actionnables

Le projet JARVIS est **post-modularisation** des 2 côtés :
- **Côté Python** : 33 modules satellites extraits de `jarvis.py`. Ce qui reste dans `jarvis.py` (4814L) est un **orchestrateur Flask** : endpoints HTTP + routing + auto-engine SOC + glue code. Logique métier déjà extraite.
- **Côté JS** : refactor officiellement TERMINÉ. `jarvis_main.js` 7828→148L (−98,1%). 13 modules extraits dans `static/js/`.

**Les chiffres ci-dessous sont des observations honnêtes, pas des dettes à attaquer** :

| Item | Réalité opérationnelle | Action |
|---|---|---|
| `jarvis.py` 30% cov (2957 stmts) | Coverage pytest unit normale pour orchestrateur HTTP · couvert indirectement par **25 tests E2E Playwright** + tests pytest sur modules satellites · +26 tests cœur sécurité 2026-05-22 | IGNORER |
| `blueprints/soc.py` 31% cov (1095 stmts) | Idem orchestrateur SOC · endpoints cache + fallback SSH · testé indirectement via MCP | IGNORER |
| 155 warnings ESLint | Exports camelCase inter-modules sans bundler → **faux positifs lint**, pas une dette | IGNORER |
| 135 inline styles JS | Pattern HUD temps réel acceptable · refactor CSS-in-JS = anti-ROI | IGNORER |

### Roadmap clôturée 2026-05-17

- [x] **SSH write ops** — la levée partielle (apt upgrade / restart) était DÉJÀ livrée via `security_whitelists.py` Phase 3 module 6b (BLOCKED_SSH_PATTERNS + check_write_op + 8 services + 12 paquets · 28 tests). La roadmap était obsolète (TODO non actualisé). **Cochée 2026-05-17 + audit log forensic ajouté** (`logs/audit_writeops.jsonl` · best-effort · 7 tests → 808 pass).

---

## 12. Bilan santé — 2026-05-22

| Indicateur | Valeur |
|---|---|
| Version JARVIS | **v3.3** (interface holographique) |
| Score dette honnête | **91/100** (audit dette complet 2026-05-22 + lot tests routes + dé-duplication doc) |
| Tests pytest | **1091 pass · 0 skip · 0 fail** |
| Coverage globale | **62%** (6217 stmts) |
| Modules ≥100% cov | **22 modules** |
| ESLint | **0 erreur** (warnings camelCase cross-modules acceptés) |
| ruff | **0 erreur** |
| Pre-push hook | **pytest 1091 tests** bloquants |
| Refactor JS | **terminé** (`jarvis_main.js` 148 L) |
| MCP outils | **12** |
| Circuit breaker | **8 call-sites Ollama** wrappés |
| TTS chain | **4 moteurs** + pré-warm Kokoro |
| Modèles LLM | **5** (phi4/gemma4/qwen2.5-coder/qwen3/mxbai-embed) |
| Bypass infra | **5** (filesystem/proxmox/backup/SSH read-only) |
| Intégrations SOC | **`/api/soc/defense` + `/api/soc/ioc` + 6 outils MCP** |
| Dépôt git | **local 100%** (aucun remote) |
| Tâches roadmap ouvertes | **1** (SSH write ops) |

**Verdict** : JARVIS est en **zone d'équilibre saine**, score plafond atteint pour un projet vivant. Refactor JS officiellement clos. Dette résiduelle structurelle (monolithe Flask + cov asymétrique cœur/satellites) acceptée par design.

---

*Document mis à jour le 2026-05-22 (audit dette complet honnête + correctifs + campagne couverture étape 1 + dé-duplication doc) — JARVIS 0xCyberLiTech v3.3 — 1091 tests pass · 0 skip · coverage 62% · 22 modules à 100% cov · score dette 91/100 honnête*
