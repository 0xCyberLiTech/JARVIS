---
title: "Dette technique restante (décisions architecturales assumées)"
code: "JARVIS-DOC-07-02"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "Roadmap"
mots_cles: ["dette-technique", "assumée", "decisions", "audit", "optimisations"]
---

# Dette technique restante

> Audit dette honnête re-mesuré au **2026-06-09** (audit complet, demande Marc).
> **Score honnête actuel : 97/100** (marbre tenu) — preuves : pytest **1465**/0 fail · coverage **79%** ·
> ruff défaut **0** · ruff strict **0 B-bugbear** (63 cosmétiques) · eslint **0/0** · **0 secret** · logs bornés.
> Améliorations sans franchir de seuil, dette gelée persiste honnêtement, **0 nouvelle dette** — détaillé dans
> [`../06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md`](../06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md) §0.
>
> Cette page liste les éléments qui pourraient être améliorés mais qui sont
> **assumés comme décisions architecturales** ou **non prioritaires** après
> évaluation ROI/risque.

## Légende

| Statut | Signification |
|---|---|
| 🟢 **Décision archi assumée** | Choix délibéré documenté — pas vraiment de la "dette" |
| 🟡 **Optimisation possible** | Améliorable, mais ROI/risque non favorable |
| 🔴 **Vraie dette à traiter** | À planifier dans la roadmap |

## Inventaire

### 🟢 Aliases backward-compat dans `jarvis.py` (~80 L, 120 aliases)

```python
_LAST_EXCHANGES         = _chat_orch._LAST_EXCHANGES
_facts_inject           = _facts_inject_mod.inject
_gpu_cuda_procs         = _runtime_stats._gpu_cuda_procs
_speak_queue            = _runtime_speak._speak_queue
# ... × 120
```

**Pourquoi conservés** : les tests pytest existants consomment `jm._X`
(120 références dans `tests/python/test_*.py`). Les supprimer nécessiterait
de modifier 30+ tests pour pointer directement vers les modules source.

**Décision** : laisser. ROI/risque défavorable. Pattern délibéré documenté.

**À reconsidérer** : si la maintenance des aliases devient pénible (>1h
de bruit dans une revue de code).

### 🟢 5 globals mutables avec setters lambda

```python
MODEL = _load_model()              # mutable via _set_model_global
SYSTEM_PROMPT = _load_system_prompt()  # mutable via _set_system_prompt_global
_vram_model: str | None = None     # mutable via _set_vram_model_global
_welcome_data = ...                # mutable via _reset_welcome_global
_AUTO_PROFILE_MODEL = ...          # mutable via _set_auto_profile_model_global
```

**Pourquoi** : Flask + état global = pattern legacy assumé. Les setters
sont passés en DI lambda aux tuiles consommatrices, pas de couplage direct.

**Décision** : laisser. Sortir vers un objet `AppState` au niveau application
Flask serait un refactor lourd pour gain limité.

**À reconsidérer** : si Marc veut un mode multi-utilisateurs (alors AppState
devient nécessaire pour isoler par utilisateur).

### 🟢 Blueprints HTTP sous-couverts en pytest — **couverts par Playwright (2026-05-23 nuit)**

| Module | Coverage pytest | Statut |
|---|---|---|
| `voice/routes.py` | 36 % | ✅ **7 tests Playwright** dans `tests/e2e/api-coverage.spec.js` (stt/status, speak/status, speak/queue, tts/status, voices, tts/local/voices, voice/prints) |
| `settings/routes.py` | 44 % | ✅ **5 tests Playwright** (llm-params, prompt-profiles, welcome, dsp-params, models) |
| `dev/routes.py` | 27 % | ✅ **1 test Playwright** (dev/stats — disk/ram/uptime srv-dev-1) |
| `web/routes.py` | 26 % | ✅ **1 test Playwright** (web-test — DDG + Wikipedia connectivity) |

**Décision** : couverture pytest faible **assumée** car Playwright valide
bout-en-bout les routes critiques avec JARVIS up. Mocker Flask test_client
sur téléchargements + audio + Ollama + SSH coûterait beaucoup pour un
bénéfice faible. La suite Playwright tourne en 2.2 min, 39 tests, 100 % pass,
0 flaky.

**À reconsidérer** : si Playwright devient lent (>5 min) ou flaky → bascule
vers mocking pytest des routes les plus appelées.

### 🟡 2 lambdas E731 dans `chat/soc_inject.py`

```python
top = lambda lst, n=5: " ".join(...)        # ligne 110
kvd = lambda key: _kpi_with_delta(k, dlt, key)  # ligne 113
```

**Décision** : noms expressifs (`top`, `kvd`), usage local strict.
Conversion en `def` alourdirait sans gain de lisibilité.

### 🟡 13 try/except: pass (SIM105)

```python
try:
    channel.close()
except Exception:
    pass  # channel may already be closed — ignore
```

**Décision** : non convertis en `contextlib.suppress(Exception)`. Le
`try/except: pass` reste plus lisible quand on veut explicitement marquer
"on ignore cette erreur précise et c'est OK".

### 🟡 8 patterns `arr + [x]` (RUF005)

```python
ssh_arr + [remote_cmd]   # au lieu de [*ssh_arr, remote_cmd]
```

**Décision** : refactor mécanique sans gain de performance ni de lisibilité.
Le pattern legacy reste correct.

### 🟡 ~135 inline styles JS (HUD temps réel)

```javascript
element.style.color = '#00cfff';
element.style.opacity = 0.6;
```

**Pourquoi** : HUD holographique avec animations temps réel (curseur,
oscilloscope, EQ). Migrer vers classes CSS dynamiques = surcouche +
moins fluide.

**Décision** : accepté. Refactor non engagé.

### 🟡 Monaco Editor via CDN (seule dép. réseau externe)

```html
<script src="https://cdn.jsdelivr.net/npm/monaco-editor@.../min/vs/loader.js">
```

**Pourquoi** : Monaco Editor pèse 2 MB+ minifié. Servir local = augmente
le bundle. Dégradation gracieuse hors ligne déjà en place (textarea
fallback).

**Décision** : assumé. Documenté dans `CLAUDE.md`.

## Pour atteindre **95/100**

### (a) Tests E2E Playwright nettoyés (~2-3 h, +1 pt)

- Suite Playwright existe partiellement
- Nettoyer les flaky tests, couvrir les Blueprints HTTP sous-couverts
- Run en CI locale (pre-push hook ou cron)

### (b) Documentation auto-générée des docstrings (~1 h, +0.5 pt)

- Sphinx ou pdoc3 sur les 24 tuiles
- Sortie HTML statique servie par nginx srv-nginx ou dans `DOCUMENTATION/`
- Auto-régénérée à chaque commit (CI ou hook)

### (c) Réduction des aliases backward-compat (~1-2 h, +0.5 pt)

- Modifier 30+ tests pour `from chat import orchestrator; orchestrator._LAST_EXCHANGES`
  au lieu de `jm._LAST_EXCHANGES`
- Supprimer ~80 L d'aliases jarvis.py
- **⚠ Risque** : si tests pas exhaustifs, une régression silencieuse

## Décisions de NON-action (audit 2026-05-23)

| Item | Décision | Raison |
|---|---|---|
| Sortir `stream_llm` dans tuile dédiée | NON pour l'instant | Reste dans jarvis.py par cohérence ossature LLM |
| Convertir try/except: pass en contextlib.suppress | NON | Moins lisible, pas plus correct |
| Moderniser `arr + [x]` en `[*arr, x]` | NON | Refactor mécanique sans gain |
| Convertir lambdas en def dans soc_inject | NON | Noms expressifs locaux |
| Refonte Inline styles JS | NON | HUD animation temps réel |

## Bilan honnête

JARVIS est dans un **état très propre**. Les éléments listés ici ne sont
**pas de la "dette" au sens strict** mais des **décisions architecturales
documentées**. Le projet est prêt pour reprise par un tiers ou production
sur le long terme.
