---
title: "Architecture par tuiles (24 tuiles, post Ã©tape 37)"
code: "JARVIS-DOC-02-02"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "Architecture"
mots_cles: ["jarvis", "tuiles", "refactor", "blueprint", "di"]
---

# JARVIS â€” Architecture par tuiles (2026-05-23 post Ã©tape 37)

> SchÃ©ma de la structure modulaire JARVIS aprÃ¨s le refactor 27-37 du
> 2026-05-23. **24 tuiles autoportantes** + `blueprints/soc.py` (existant
> prÃ©-refactor). `jarvis.py` rÃ©duit Ã  **1821 lignes** (vs 4814 au dÃ©part,
> âˆ’62%) â€” il reste l'ossature : Flask app, config, CORS, registration des
> tuiles, bloc `__main__` (MCP subprocess + app.run).

## Vue d'ensemble

```
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚            BROWSER (Marc Â· F12)             â”‚
                    â”‚   xterm.js Â· Web Audio Â· jarvis_main.js     â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                      â”‚  HTTP/WS/SSE :5000
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                       scripts/jarvis.py (1819 L)                         â”‚
â”‚                       â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€                          â”‚
â”‚   Flask app Â· CORS Â· config Â· 23 register_blueprint + 23 init()          â”‚
â”‚   Globals mutables : MODEL, SYSTEM_PROMPT, _vram_model, _jarvis_mode     â”‚
â”‚   Setters lambda lazy injectÃ©s en DI aux tuiles consommatrices           â”‚
â”‚   Routes restantes : / Â· /favicon.ico Â· /api/debug/* Â· /api/mode         â”‚
â”‚   __main__ : kill MCP orphan port 5010 + Popen jarvis_mcp_server.py      â”‚
â”‚              + app.run(threaded=True)                                    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
       â”‚                                                              â”‚
       â”‚ register_blueprint (HTTP routes)         init() (helpers DI) â”‚
       â–¼                                                              â–¼
```

## Les 23 tuiles + blueprints/soc

### Tuiles HTTP (avec Blueprint Flask) â€” 15

| Tuile | Routes principales | RÃ´le |
|---|---|---|
| **system/** | `/api/sysdiag` | Diagnostics matÃ©riel/OS/LLM agrÃ©gÃ©s |
| **memory/** | `/api/memory*`, `/api/memory-summary*` | Historique conv + rÃ©sumÃ©s long terme |
| **rag/** | `/api/rag/*` | RAG mxbai-embed-large (599 chunks) |
| **health/** | `/api/boot-id`, `/api/health`, `/api/stats`, `/api/status`, `/api/ollama-status`, `/api/vram`, `/api/security*`, `/api/ping` | SantÃ© runtime + ping IP |
| **settings/** | `/api/llm-params*`, `/api/dsp-params*`, `/api/models*`, `/api/prompt-profiles*`, `/api/welcome*` | Config persistante 16 routes |
| **voice/** | `/api/stt*`, `/api/tts*`, `/api/speak*`, `/api/voices*`, `/api/voice/*` | STT/TTS + speak family + voice prints |
| **vision/** | `/api/vision` | LLaVA multimodal |
| **tasks/** | `/api/tasks*`, `/api/cr-poll` | TÃ¢ches planifiÃ©es + Code Reasoning poll |
| **dev/** | `/api/dev/exec`, `/api/dev/stats`, `/api/code/exec`, `/api/code/save` | Exec code srv-dev-1 + stats |
| **web/** | `/api/web-test` (+ helper `search.web_search`) | DuckDuckGo HTML search |
| **facts/** | `/api/facts` (GET/POST) + `inject.py` helper | Faits persistants + injection prompt |
| **terminal/** | `/ws/ssh/<host>`, `/ws/dev` (WebSocket PTY SSH) | Terminal interactif xterm.js |
| **chat/** | `/api/chat`, `/api/history/last` | **Carrefour LLM** â€” voir dÃ©tail ci-dessous |
| **commands/** | (pas de routes â€” SSE generators consommÃ©s par chat) | 6 SSE VM/reboot/update/service |
| **mode/** â­ | `/api/mode` (GET/POST) | SÃ©lection mode JARVIS (soc/general/code/CR) + swap VRAM |

â­ = crÃ©Ã© Ã©tape 37 (2026-05-23)

### Tuiles helpers (sans routes HTTP) â€” 9

| Tuile | Contenu | ConsommÃ©e par |
|---|---|---|
| **files/** | `_tool_lire_fichier`, `_tool_ecrire_fichier`, `_tool_modifier_fichier`, `_tool_lister_dossier`, `_tool_arborescence_projet`, `_tool_lire_plusieurs_fichiers`, `_tool_rechercher_dans_fichiers` | tools/dispatch |
| **ssh/** | `_tool_commande_ssh_run` + 4 wrappers (`nginx`, `proxmox`, `clt`, `pa85`) + `_ssh_timeout` | tools/dispatch + chat orchestrator |
| **tools/** | `local.py` (3 outils : executer_code, soc_status, executer_script_windows) + `dispatch.py` (build dict _TOOL_DISPATCH) | chat orchestrator |
| **bypass/** | `proxmox.py`, `code.py`, `backup.py`, `filesystem.py`, `simple.py`, `wrappers.py` (11 wrappers DI couplÃ©s jarvis) | chat dispatcher |
| **proxmox/** | `api.py` (fetch_state + ticket+token + cache 30s) | bootstrap + chat |
| **runtime/** | `gpu_stats.py` (3 fns NVML + state local) + `speak.py` (queue TTS + dedup) | health + voice + bootstrap |
| **bootstrap/** | `threads.py` (10 threads daemon : kokoro_preload, vram_cleanup, soc/kokoro prewarm, vram_sync, tts_connectivity, gpu_temp, rag_embed/auto_refresh) + idempotence anti-double-import | jarvis.py boot |
| **llm/** â­ | `vram.py` (ensure_vram + ollama_swap) + `stream.py` (stream_llm + think_filter) | api_mode + chat orchestrator |

â­ = crÃ©Ã© Ã©tape 35 (2026-05-23)

### Tuile composite : **chat/** (14 sous-modules)

Le carrefour LLM le plus dense â€” agrÃ©gÃ© en un seul module pour cohÃ©rence :

```
chat/
â”œâ”€â”€ dispatcher.py   â† route /api/chat + chat_try_bypass + detect_file_corrections
â”‚                    + /api/history/last (Ã©tape 32)
â”œâ”€â”€ orchestrator.py â† cÅ“ur orchestration LLM (_chat_generate, _chat_resolve_model,
â”‚                    _chat_build_system_prompt, _capture_gen, _LAST_EXCHANGES,
â”‚                    LlmCtx namedtuple, execute_tool, call_llm_with_tools)
â”œâ”€â”€ routing.py      â† logique routing 4 modes (soc/general/code/code_reasoning)
â”œâ”€â”€ messages.py     â† build payload messages (modes, ctx, vocal, overrides)
â”œâ”€â”€ stream.py       â† streaming SSE Ollama â†’ client (4 BiquadFilter audio side)
â”œâ”€â”€ generate.py     â† wrapper Ollama /api/generate (one-shot)
â”œâ”€â”€ system_prompt.pyâ† assemblage prompt final (profil + facts + RAG)
â”œâ”€â”€ capture.py      â† SSE generator capture pour _LAST_EXCHANGES
â”œâ”€â”€ pending_bypass.pyâ† rÃ©solution bypass diffÃ©rÃ©s (confirmation 'oui')
â”œâ”€â”€ soc_inject.py   â† injection bloc SOC compact dans system prompt phi4
â”œâ”€â”€ soc_context.py  â† formatage contexte SOC (_INFRA_IPS, build_monitoring_context)
â”œâ”€â”€ tool_calls.py   â† dispatch tool_calls LLM (file/ssh/code/...)
â”œâ”€â”€ tool_schemas.py â† 14 schÃ©mas TOOLS JSON pour Ollama
â””â”€â”€ file_correct.py â† validate_protect_directives + 3 SSE corrections fichier
```

### blueprints/soc.py (1500 L, prÃ©-refactor)

Le seul gros module non-tuile encore prÃ©sent. Contient :
- Clusters extraits Ã©tapes prÃ©-tuile : `soc_ip_deep`, `soc_suricata_ban`,
  `soc_threat_score`, `soc_reqhour` (4 modules Ã  plat dans scripts/)
- `_soc_llm_call` (thread analyse auto-engine) + `from jarvis import` dans 4
  fonctions (lignes 1149/1153/1154/1463) â€” **source du bug double-import** fixÃ©
  par `8e3d518` (idempotence boot_id via `os.environ` cache)
- 24 routes `/api/soc/*` (ban, unban, restart, autoban, heartbeat, monitor,
  ip-deep, ip-history, context, â€¦)

Ã€ faire long terme : passer les 4 `from jarvis import` en DI explicite via
`init_soc()` pour Ã©liminer le re-import au lieu de juste neutraliser le
symptÃ´me.

## Flux d'une requÃªte utilisateur typique

### Cas 1 â€” Chat normal en mode SOC

```
Browser POST /api/chat {history, model_override, ...}
    â”‚
    â–¼
chat/dispatcher.api_chat()
    â”œâ”€ chat_try_bypass()  â†’ bypass (VM, reboot, backup...) si match â†’ SSE direct
    â”œâ”€ detect_file_corrections() â†’ file_correct si "lis+corrige"
    â”œâ”€ chat/system_prompt.build() â†’ facts/inject.inject() + RAG + SOC live
    â”œâ”€ chat/routing.resolve_model() â†’ llm/vram.ensure_vram(MODEL)
    â”‚                               (decharge ancien modÃ¨le, preload nouveau)
    â””â”€ chat/generate.chat_generate()
            â”‚
            â–¼
        llm/stream.stream_llm(messages)
            â”‚ (Ollama /api/chat streaming)
            â–¼
        chat/stream.stream_tokens_tts() â†’ tokens â†’ SSE â†’ Browser
```

### Cas 2 â€” Switch de mode (UI)

```
Browser POST /api/mode {mode: "code"}
    â”‚
    â–¼
jarvis.py api_mode()
    â””â”€ llm/vram.ensure_vram(_CODE_MODEL)
            â””â”€ llm/vram.ollama_swap(unload=phi4, load=qwen2.5-coder)
                    â”œâ”€ unload SYNC (8s timeout)
                    â””â”€ preload BACKGROUND (thread daemon, 180s timeout)
```

### Cas 3 â€” Auto-engine SOC dÃ©clenche alerte vocale

```
[Thread bootstrap/threads.gpu_temp_monitor_loop ou alerte SOC]
    â”‚
    â–¼
blueprints/soc._soc_llm_call(prompt)
    â”œâ”€ from jarvis import _CODE_REASONING_MODE, _jarvis_mode âš  re-import dÃ©clenchÃ©
    â”‚   â†’ top-level jarvis.py rÃ©-exÃ©cutÃ© UNE FOIS (cache sys.modules aprÃ¨s)
    â”‚   â†’ _JARVIS_BOOT_ID stable grÃ¢ce au cache os.environ (fix 8e3d518)
    â”‚   â†’ _log handler protÃ©gÃ© par idempotence (fix 06e4297)
    â”‚   â†’ start_all() shuntÃ© par flag _threads_started
    â”‚
    â””â”€ runtime/speak.speak("Alerte XYZ")
            â””â”€ _speak_queue â†’ browser polling /api/speak/queue
                    â†’ Web Audio joue le TTS
```

## Garde-fous d'observabilitÃ© (toujours actifs)

| MÃ©canisme | Fichier | Volume max |
|---|---|---|
| `scripts/jarvis.log` (RotatingFileHandler) | `jarvis.py:31-50` (idempotent) | 5 MB Ã— 7 = 35 MB |
| `scripts/tts.log` | `jarvis.py:55-65` (_tts_logger) | 2 MB Ã— 7 = 14 MB |
| `scripts/tts_perf.log` (filtre `[TTS-PERF]`) | `jarvis.py:67-80` | 1 MB Ã— 3 = 3 MB |
| JS-DIAG v2 (`window.error`, `unhandledrejection`, `beforeunload`, `visibility`) | `boot_init.js:18-78` + `jarvis.py:1147-1166` route `/api/_diag/jslog` | inclus dans `jarvis.log` |
| Try/except global `/api/tts` enrichi | `voice/routes.py:294-314` | inclus dans `tts.log` (tag `[GLOBAL-CRASH]`) |
| `JARVIS_SKIP_BOOT_THREADS=1` env flag | `bootstrap/threads.py:start_all()` | â€” |
| Idempotence handler + start_all + boot_id | `jarvis.py`, `bootstrap/threads.py` | â€” |

**VolumÃ©trie totale plafonnÃ©e Ã  52 MB max sur disque** (rotation auto, jamais
de saturation possible). Voir
`~/.claude/.../memory/jarvis_diag_tools_active.md` pour le dÃ©tail.

## Chiffres post Ã©tape 37 + ruff strict cleanup (2026-05-23 17:55)

| MÃ©trique | Valeur |
|---|---|
| jarvis.py | 1821 L |
| Cumul refactor depuis monolithe | **4814 â†’ 1821 = âˆ’62 %** |
| Tuiles autoportantes | **24** (+ blueprints/soc) |
| Sous-modules chat | 14 |
| Tests pytest | **1294 pass Â· 0 skip Â· 0 fail** |
| Coverage globale | **76 %** (7394 stmts Â· 1806 miss) |
| ruff | 0 erreur (audit strict B/C4/SIM/UP/RUF passÃ©) |
| eslint | 0 erreur |
| Pre-commit/pre-push hooks | actifs |
| Bug UI reload | **rÃ©solu cause racine** (DI explicite soc.py Ã©tape 36b) + validÃ© end-to-end |
| TODO/FIXME ouverts | **0** dans le code Marc |
| Dette restante connue | aliases backward-compat (~80 L), dÃ©cision archi assumÃ©e |

