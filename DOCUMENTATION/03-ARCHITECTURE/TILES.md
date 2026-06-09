# Tuiles & Blueprints autoportants

> Architecture modulaire de JARVIS : chaque fonctionnalité est un Blueprint Flask
> avec injection de dépendances (DI) pure — zéro couplage direct entre tuiles.

---

## Principe des tuiles autoportantes

Une **tuile** est un Blueprint Flask qui :
1. Déclare ses dépendances via `init_routes(**kwargs)` (DI pur)
2. N'importe aucun autre module JARVIS directement
3. Est testable de façon isolée avec des mocks

```python
# Pattern standard
def init_routes(
    get_model_fn,
    set_model_fn,
    get_prompt_fn,
    ...
):
    bp = Blueprint("settings", __name__)

    @bp.route("/api/llm-params", methods=["GET"])
    def get_llm_params():
        ...
    return bp
```

---

## Liste des Blueprints (8 tuiles)

| Blueprint | Fichier | Routes principales |
|-----------|---------|-------------------|
| **SOC** | `blueprints/soc.py` | `/api/soc/*` — auto-engine, ban/unban, journal |
| **Settings** | `settings/routes.py` | `/api/llm-params`, `/api/prompt-profiles`, `/welcome` |
| **Voice** | `voice/routes.py` | `/api/speak`, `/api/tts`, `/api/stt`, `/api/voices` |
| **Dev** | `dev/routes.py` | `/api/dev/exec`, `/api/dev/stats`, `/api/save-code` |
| **Memory** | `memory/routes.py` | `/api/memory`, `/api/memory-summary`, `/api/memory/stats` |
| **RAG** | `rag/routes.py` | `/api/rag/status`, `/api/rag/refresh`, `/api/rag/note` |
| **Tasks** | `tasks/routes.py` | `/api/tasks`, `/api/cr-poll`, `/api/run` |
| **Vision** | `vision/routes.py` | `/api/vision` |

---

## Injection de dépendances — jarvis.py

`jarvis.py` instancie tous les modules et injecte les dépendances dans chaque Blueprint :

```python
# Dans jarvis.py
from settings.routes import init_routes as sr_init

settings_bp = sr_init(
    get_llm_params_fn=_get_llm_params,
    set_llm_params_fn=_set_llm_params,
    get_system_prompt_fn=_get_system_prompt,
    set_system_prompt_fn=_set_system_prompt,
    ...  # 28 paramètres DI
)
app.register_blueprint(settings_bp)
```

**Avantage** : chaque Blueprint est testable avec `Flask test_client()` + mocks injectés directement.

---

## Modules centralisés

| Module | Centralise | Fichier |
|--------|-----------|---------|
| `_buildChatPayload()` | 6/6 appels LLM — injection contexte SOC | `jarvis_main.js` |
| `_jarvisInit()` | 1/1 DOMContentLoaded — init complète | `jarvis_main.js` |
| `compute_threat_score()` | Score officiel — jamais recalculé ailleurs | `monitoring_gen.py` |
| `_soc_monitor_loop()` | Auto-engine Python quand dashboard fermé | `soc.py` |
| `_SSH_LOCK` | Toutes les connexions SSH | `soc.py` |
| `_TTS_LOCK` | Séquencement TTS — évite doublons vocaux | `jarvis.py` |

---

## Architecture frontend — 21 modules JS

| Module | Rôle |
|--------|------|
| `jarvis_main.js` | Point d'entrée unique — `_jarvisInit()` |
| `boot_init.js` | Initialisation au démarrage |
| `chat_core.js` | Pipeline chat + SSE |
| `soc_engine.js` | Auto-engine SOC côté navigateur |
| `canvas_kc.js` | Kill Chain visualisation canvas |
| `canvas_leaflet.js` | Carte géo des IPs |
| `audio_dsp.js` | Contrôles DSP audio |
| `voice_lab.js` | Voice Lab — TTS/STT interface |
| `monitor_core.js` | Métriques système temps réel |
| `terminal.js` | xterm.js — terminal SSH |
| `editor.js` | Monaco Editor — éditeur code |
| `memory_ui.js` | Interface mémoire Hermès |
| ... | 9 modules supplémentaires |

---

## Tests — couverture par Blueprint

| Blueprint | Coverage pytest | Tests |
|-----------|----------------|-------|
| `soc.py` | 72 % | 85 tests |
| `settings/routes.py` | 59 % | 15 tests |
| `voice/routes.py` | 50 % | 17 tests |
| `dev/routes.py` | 93 % | 16 tests |
| `memory/routes.py` | 87 % | 18 tests |
| `rag/routes.py` | 90 % | 15 tests |
| `tasks/routes.py` | 99 % | 14 tests |
| `vision/routes.py` | 100 % | 11 tests |

---

*TILES.md · 0xCyberLiTech · 2026-06-09*
