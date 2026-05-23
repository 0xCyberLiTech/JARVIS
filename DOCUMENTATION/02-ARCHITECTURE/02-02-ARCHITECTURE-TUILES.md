---
title: "Architecture par tuiles (24 tuiles, post étape 37)"
code: "JARVIS-DOC-02-02"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "Architecture"
mots_cles: ["jarvis", "tuiles", "refactor", "blueprint", "di"]
---

# JARVIS — Architecture par tuiles (2026-05-23 post étape 37)

> Schéma de la structure modulaire JARVIS après le refactor 27-37 du
> 2026-05-23. **24 tuiles autoportantes** + `blueprints/soc.py` (existant
> pré-refactor). `jarvis.py` réduit à **1821 lignes** (vs 4814 au départ,
> −62%) — il reste l'ossature : Flask app, config, CORS, registration des
> tuiles, bloc `__main__` (MCP subprocess + app.run).

## Vue d'ensemble

```
                    ┌─────────────────────────────────────────────┐
                    │            BROWSER (Marc · F12)             │
                    │   xterm.js · Web Audio · jarvis_main.js     │
                    └─────────────────┬───────────────────────────┘
                                      │  HTTP/WS/SSE :5000
┌─────────────────────────────────────▼────────────────────────────────────┐
│                       scripts/jarvis.py (1819 L)                         │
│                       ─────────────────────────                          │
│   Flask app · CORS · config · 23 register_blueprint + 23 init()          │
│   Globals mutables : MODEL, SYSTEM_PROMPT, _vram_model, _jarvis_mode     │
│   Setters lambda lazy injectés en DI aux tuiles consommatrices           │
│   Routes restantes : / · /favicon.ico · /api/debug/* · /api/mode         │
│   __main__ : kill MCP orphan port 5010 + Popen jarvis_mcp_server.py      │
│              + app.run(threaded=True)                                    │
└──────────────────────────────────────────────────────────────────────────┘
       │                                                              │
       │ register_blueprint (HTTP routes)         init() (helpers DI) │
       ▼                                                              ▼
```

## Les 23 tuiles + blueprints/soc

### Tuiles HTTP (avec Blueprint Flask) — 15

| Tuile | Routes principales | Rôle |
|---|---|---|
| **system/** | `/api/sysdiag` | Diagnostics matériel/OS/LLM agrégés |
| **memory/** | `/api/memory*`, `/api/memory-summary*` | Historique conv + résumés long terme |
| **rag/** | `/api/rag/*` | RAG mxbai-embed-large (599 chunks) |
| **health/** | `/api/boot-id`, `/api/health`, `/api/stats`, `/api/status`, `/api/ollama-status`, `/api/vram`, `/api/security*`, `/api/ping` | Santé runtime + ping IP |
| **settings/** | `/api/llm-params*`, `/api/dsp-params*`, `/api/models*`, `/api/prompt-profiles*`, `/api/welcome*` | Config persistante 16 routes |
| **voice/** | `/api/stt*`, `/api/tts*`, `/api/speak*`, `/api/voices*`, `/api/voice/*` | STT/TTS + speak family + voice prints |
| **vision/** | `/api/vision` | LLaVA multimodal |
| **tasks/** | `/api/tasks*`, `/api/cr-poll` | Tâches planifiées + Code Reasoning poll |
| **dev/** | `/api/dev/exec`, `/api/dev/stats`, `/api/code/exec`, `/api/code/save` | Exec code srv-dev-1 + stats |
| **web/** | `/api/web-test` (+ helper `search.web_search`) | DuckDuckGo HTML search |
| **facts/** | `/api/facts` (GET/POST) + `inject.py` helper | Faits persistants + injection prompt |
| **terminal/** | `/ws/ssh/<host>`, `/ws/dev` (WebSocket PTY SSH) | Terminal interactif xterm.js |
| **chat/** | `/api/chat`, `/api/history/last` | **Carrefour LLM** — voir détail ci-dessous |
| **commands/** | (pas de routes — SSE generators consommés par chat) | 6 SSE VM/reboot/update/service |
| **mode/** ⭐ | `/api/mode` (GET/POST) | Sélection mode JARVIS (soc/general/code/CR) + swap VRAM |

⭐ = créé étape 37 (2026-05-23)

### Tuiles helpers (sans routes HTTP) — 9

| Tuile | Contenu | Consommée par |
|---|---|---|
| **files/** | `_tool_lire_fichier`, `_tool_ecrire_fichier`, `_tool_modifier_fichier`, `_tool_lister_dossier`, `_tool_arborescence_projet`, `_tool_lire_plusieurs_fichiers`, `_tool_rechercher_dans_fichiers` | tools/dispatch |
| **ssh/** | `_tool_commande_ssh_run` + 4 wrappers (`ngix`, `proxmox`, `clt`, `pa85`) + `_ssh_timeout` | tools/dispatch + chat orchestrator |
| **tools/** | `local.py` (3 outils : executer_code, soc_status, executer_script_windows) + `dispatch.py` (build dict _TOOL_DISPATCH) | chat orchestrator |
| **bypass/** | `proxmox.py`, `code.py`, `backup.py`, `filesystem.py`, `simple.py`, `wrappers.py` (11 wrappers DI couplés jarvis) | chat dispatcher |
| **proxmox/** | `api.py` (fetch_state + ticket+token + cache 30s) | bootstrap + chat |
| **runtime/** | `gpu_stats.py` (3 fns NVML + state local) + `speak.py` (queue TTS + dedup) | health + voice + bootstrap |
| **bootstrap/** | `threads.py` (10 threads daemon : kokoro_preload, vram_cleanup, soc/kokoro prewarm, vram_sync, tts_connectivity, gpu_temp, rag_embed/auto_refresh) + idempotence anti-double-import | jarvis.py boot |
| **llm/** ⭐ | `vram.py` (ensure_vram + ollama_swap) + `stream.py` (stream_llm + think_filter) | api_mode + chat orchestrator |

⭐ = créé étape 35 (2026-05-23)

### Tuile composite : **chat/** (14 sous-modules)

Le carrefour LLM le plus dense — agrégé en un seul module pour cohérence :

```
chat/
├── dispatcher.py   ← route /api/chat + chat_try_bypass + detect_file_corrections
│                    + /api/history/last (étape 32)
├── orchestrator.py ← cœur orchestration LLM (_chat_generate, _chat_resolve_model,
│                    _chat_build_system_prompt, _capture_gen, _LAST_EXCHANGES,
│                    LlmCtx namedtuple, execute_tool, call_llm_with_tools)
├── routing.py      ← logique routing 4 modes (soc/general/code/code_reasoning)
├── messages.py     ← build payload messages (modes, ctx, vocal, overrides)
├── stream.py       ← streaming SSE Ollama → client (4 BiquadFilter audio side)
├── generate.py     ← wrapper Ollama /api/generate (one-shot)
├── system_prompt.py← assemblage prompt final (profil + facts + RAG)
├── capture.py      ← SSE generator capture pour _LAST_EXCHANGES
├── pending_bypass.py← résolution bypass différés (confirmation 'oui')
├── soc_inject.py   ← injection bloc SOC compact dans system prompt phi4
├── soc_context.py  ← formatage contexte SOC (_INFRA_IPS, build_monitoring_context)
├── tool_calls.py   ← dispatch tool_calls LLM (file/ssh/code/...)
├── tool_schemas.py ← 14 schémas TOOLS JSON pour Ollama
└── file_correct.py ← validate_protect_directives + 3 SSE corrections fichier
```

### blueprints/soc.py (1500 L, pré-refactor)

Le seul gros module non-tuile encore présent. Contient :
- Clusters extraits étapes pré-tuile : `soc_ip_deep`, `soc_suricata_ban`,
  `soc_threat_score`, `soc_reqhour` (4 modules à plat dans scripts/)
- `_soc_llm_call` (thread analyse auto-engine) + `from jarvis import` dans 4
  fonctions (lignes 1149/1153/1154/1463) — **source du bug double-import** fixé
  par `8e3d518` (idempotence boot_id via `os.environ` cache)
- 24 routes `/api/soc/*` (ban, unban, restart, autoban, heartbeat, monitor,
  ip-deep, ip-history, context, …)

À faire long terme : passer les 4 `from jarvis import` en DI explicite via
`init_soc()` pour éliminer le re-import au lieu de juste neutraliser le
symptôme.

## Flux d'une requête utilisateur typique

### Cas 1 — Chat normal en mode SOC

```
Browser POST /api/chat {history, model_override, ...}
    │
    ▼
chat/dispatcher.api_chat()
    ├─ chat_try_bypass()  → bypass (VM, reboot, backup...) si match → SSE direct
    ├─ detect_file_corrections() → file_correct si "lis+corrige"
    ├─ chat/system_prompt.build() → facts/inject.inject() + RAG + SOC live
    ├─ chat/routing.resolve_model() → llm/vram.ensure_vram(MODEL)
    │                               (decharge ancien modèle, preload nouveau)
    └─ chat/generate.chat_generate()
            │
            ▼
        llm/stream.stream_llm(messages)
            │ (Ollama /api/chat streaming)
            ▼
        chat/stream.stream_tokens_tts() → tokens → SSE → Browser
```

### Cas 2 — Switch de mode (UI)

```
Browser POST /api/mode {mode: "code"}
    │
    ▼
jarvis.py api_mode()
    └─ llm/vram.ensure_vram(_CODE_MODEL)
            └─ llm/vram.ollama_swap(unload=phi4, load=qwen2.5-coder)
                    ├─ unload SYNC (8s timeout)
                    └─ preload BACKGROUND (thread daemon, 180s timeout)
```

### Cas 3 — Auto-engine SOC déclenche alerte vocale

```
[Thread bootstrap/threads.gpu_temp_monitor_loop ou alerte SOC]
    │
    ▼
blueprints/soc._soc_llm_call(prompt)
    ├─ from jarvis import _CODE_REASONING_MODE, _jarvis_mode ⚠ re-import déclenché
    │   → top-level jarvis.py ré-exécuté UNE FOIS (cache sys.modules après)
    │   → _JARVIS_BOOT_ID stable grâce au cache os.environ (fix 8e3d518)
    │   → _log handler protégé par idempotence (fix 06e4297)
    │   → start_all() shunté par flag _threads_started
    │
    └─ runtime/speak.speak("Alerte XYZ")
            └─ _speak_queue → browser polling /api/speak/queue
                    → Web Audio joue le TTS
```

## Garde-fous d'observabilité (toujours actifs)

| Mécanisme | Fichier | Volume max |
|---|---|---|
| `scripts/jarvis.log` (RotatingFileHandler) | `jarvis.py:31-50` (idempotent) | 5 MB × 7 = 35 MB |
| `scripts/tts.log` | `jarvis.py:55-65` (_tts_logger) | 2 MB × 7 = 14 MB |
| `scripts/tts_perf.log` (filtre `[TTS-PERF]`) | `jarvis.py:67-80` | 1 MB × 3 = 3 MB |
| JS-DIAG v2 (`window.error`, `unhandledrejection`, `beforeunload`, `visibility`) | `boot_init.js:18-78` + `jarvis.py:1147-1166` route `/api/_diag/jslog` | inclus dans `jarvis.log` |
| Try/except global `/api/tts` enrichi | `voice/routes.py:294-314` | inclus dans `tts.log` (tag `[GLOBAL-CRASH]`) |
| `JARVIS_SKIP_BOOT_THREADS=1` env flag | `bootstrap/threads.py:start_all()` | — |
| Idempotence handler + start_all + boot_id | `jarvis.py`, `bootstrap/threads.py` | — |

**Volumétrie totale plafonnée à 52 MB max sur disque** (rotation auto, jamais
de saturation possible). Voir
`~/.claude/.../memory/jarvis_diag_tools_active.md` pour le détail.

## Chiffres post étape 37 + ruff strict cleanup (2026-05-23 17:55)

| Métrique | Valeur |
|---|---|
| jarvis.py | 1821 L |
| Cumul refactor depuis monolithe | **4814 → 1821 = −62 %** |
| Tuiles autoportantes | **24** (+ blueprints/soc) |
| Sous-modules chat | 14 |
| Tests pytest | **1294 pass · 0 skip · 0 fail** |
| Coverage globale | **76 %** (7394 stmts · 1806 miss) |
| ruff | 0 erreur (audit strict B/C4/SIM/UP/RUF passé) |
| eslint | 0 erreur |
| Pre-commit/pre-push hooks | actifs |
| Bug UI reload | **résolu cause racine** (DI explicite soc.py étape 36b) + validé end-to-end |
| TODO/FIXME ouverts | **0** dans le code Marc |
| Dette restante connue | aliases backward-compat (~80 L), décision archi assumée |
