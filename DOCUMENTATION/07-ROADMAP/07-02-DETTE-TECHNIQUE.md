---
title: "Dette technique restante (décisions architecturales assumées)"
code: "JARVIS-DOC-07-02"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "Roadmap"
mots_cles: ["dette-technique", "assumée", "decisions", "audit", "optimisations"]
---

# Dette technique restante

> Audit dette honnête au **2026-05-23** après les 30 commits de la journée.
> **Score honnête actuel : 93/100** — détaillé dans
> [`../06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md`](../06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md).
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

### 🟡 Blueprints HTTP sous-couverts en pytest

| Module | Coverage | Pourquoi |
|---|---|---|
| `voice/routes.py` | 36 % | Routes Flask téléchargements + audio + Ollama → mock lourd |
| `settings/routes.py` | 44 % | 16 routes config (16 fichiers DSP_PARAMS, LLM_PARAMS, etc.) |
| `dev/routes.py` | 27 % | Routes SCP + exec srv-dev-1 → mock SSH complet |
| `web/routes.py` | 26 % | Routes DuckDuckGo search → mock HTTP fastidieux |

**Décision** : testés indirectement par **Playwright E2E** (suite existante
partielle). Refonte E2E pour cover ces routes = 2-3h roadmap.

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
- Sortie HTML statique servie par nginx srv-ngix ou dans `DOCUMENTATION/`
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
