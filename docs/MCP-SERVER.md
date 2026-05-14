# JARVIS MCP Server — Pont Claude ↔ JARVIS

Le serveur MCP (Model Context Protocol) expose JARVIS comme un set d'**outils** consommables par Claude Desktop, Claude Code et tout client compatible MCP. Permet à Claude (cloud) d'interroger JARVIS (local) sans passer raw data sensible vers Anthropic.

**Architecture clé :** JARVIS filtre/agrège/détecte localement → Claude voit uniquement l'escalade ou la synthèse.

> **Phase 3 split monolithe complète (session 33, 2026-05-13)** : le serveur MCP `jarvis_mcp_server.py` n'a **PAS changé** — il consomme toujours les routes HTTP de `jarvis.py`. Les outils MCP fonctionnent identiquement après extraction de **30 modules** Python (audio : stt/voice_lab/tts_engines/deepfilter/vision · bypass : bypass_simple/bypass_filesystem/bypass_proxmox/bypass_backup/bypass_code · sécurité : security_whitelists · SSH/RAG/PVE : ssh_terminal/proxmox_api/rag_live/sse_helpers · chat orchestration : chat_routing/tts_cleaner/chat_messages/tts_dedup/chat_capture/chat_system_prompt/chat_soc_inject/llm_opts/stream_tokens/deferred_speak/chat_pending_bypass/chat_tool_calls/chat_stream/chat_generate · LLM CR : code_reasoning). `jarvis.py` est passé de **6592 → 4520 lignes (-31%)**, les routes Flask consommées par MCP restent dans jarvis.py via wrappers DI vers les modules. Score honnête global : **89/100** (NDT script auto 100/100 mais JS toujours monolithique, pas de CI/CD, pas de profiling perf).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Claude Desktop / Claude Code  (cloud Anthropic)                │
│                                                                  │
│         │ MCP protocol (JSON-RPC over HTTP streamable)           │
│         ▼                                                        │
│  ╔═══════════════════════════════════════════════╗               │
│  ║  jarvis_mcp_server.py   (Windows · port 5010) ║               │
│  ║  Starlette + uvicorn + MCP SDK                ║               │
│  ║  10 outils @app.list_tools()                  ║               │
│  ╚═══════════════════════════════════════════════╝               │
│         │ HTTP REST + SSE                                        │
│         ▼                                                        │
│  ╔═══════════════════════════════════════════════╗               │
│  ║  jarvis.py   (Windows · port 5000)            ║               │
│  ║  Flask + Ollama (11434) + SOC blueprint       ║               │
│  ╚═══════════════════════════════════════════════╝               │
└─────────────────────────────────────────────────────────────────┘
```

| Composant | Détail |
|-----------|--------|
| **Fichier** | [`scripts/jarvis_mcp_server.py`](../scripts/jarvis_mcp_server.py) (~430 lignes) |
| **Port** | `5010` (modifiable via `--port`) |
| **Lib MCP** | `mcp.server.lowlevel` + `mcp.server.streamable_http_manager` |
| **HTTP framework** | Starlette + uvicorn |
| **Mode** | StreamableHTTPSessionManager · stateless |
| **Endpoints HTTP** | `/health`, `/sse`, `/mcp` (GET/POST/DELETE) |
| **JARVIS_BASE** | `http://localhost:5000` (hardcodé · loopback only) |
| **Timeouts** | 120s pour `/api/chat` (LLM lourd) · 10s pour status/stats/health |

---

## Les 10 outils MCP

Tous les outils retournent du `TextContent` préfixé par `JARVIS_HEADER` (cartouche ASCII identifiant la source).

### 1. `jarvis_chat`
**Description :** Envoie un message à JARVIS (Ollama local) et retourne sa réponse complète.
**Params :** `message: string` (requis)
**Usage :** questions générales, analyses, code, cybersécurité — l'avis du LLM local sans contexte SOC injecté.
**Endpoint sous-jacent :** `POST /api/chat` (SSE accumulé)

### 2. `jarvis_soc_status`
**Description :** État SOC temps réel — niveau de menace, IPs bannies CrowdSec/fail2ban, services actifs, auto-engine.
**Params :** aucun
**Usage :** "donne-moi un état rapide du SOC" sans déclencher un appel LLM
**Endpoint :** `GET /api/soc/context` (`monitoring.json` parsé) → fallback `/api/status`

### 3. `jarvis_soc_ask`
**Description :** Pose une question SOC à JARVIS avec **injection automatique** du contexte live (monitoring.json complet + historique IP 30j).
**Params :** `question: string` (requis)
**Usage :** analyse d'attaque, interprétation d'alertes, décision de ban, compréhension d'incident — données SOC réelles, pas de RAG statique.
**Endpoint :** `POST /api/soc/ip-history` + `POST /api/chat` (contexte injecté côté MCP)

### 4. `jarvis_stats`
**Description :** Statistiques JARVIS — uptime, sessions chat, appels TTS/STT, modèle actif, état RAG.
**Params :** aucun
**Endpoint :** `GET /api/stats`

### 5. `jarvis_infra_status`
**Description :** État rapide de toute l'infrastructure — Proxmox VMs, srv-ngix (nginx/CrowdSec), clt (Apache), pa85 (Apache).
**Params :** `focus: string` (optionnel — `'proxmox'`, `'ngix'`, `'clt'`, `'pa85'`, ou vide pour tout)
**Endpoint :** `POST /api/chat` (LLM avec contexte infra)

### 6. `jarvis_proxmox_vms`
**Description :** Liste les VMs Proxmox avec leur état (running/stopped), RAM, CPU, uptime.
**Params :** aucun
**Endpoint :** `POST /api/chat` (LLM avec contexte PVE) · bypass Python détecté → réponse directe sans LLM

### 7. `jarvis_read_file`
**Description :** Lit le contenu d'un fichier distant sur une VM via SSH JARVIS.
**Params :** `vm: string` (requis · `'ngix'|'clt'|'pa85'|'proxmox'|'srv-dev-1'`) · `path: string` (requis · chemin absolu)
**Usage :** lire `nginx.conf`, `jail.conf`, scripts, logs depuis VSCode sans quitter.
**Sécurité :** héritée de `_BLOCKED_SSH` JARVIS (fichiers `/etc/passwd`, `/etc/shadow`, etc. bloqués) · lecture seule

### 8. `jarvis_model_switch`
**Description :** Change le modèle Ollama actif dans JARVIS.
**Params :** `model: string` (requis · ex: `phi4:14b`, `qwen2.5-coder:14b`, `gemma4:latest`, `qwen3:8b`)
**Endpoint :** `POST /api/models`
**Note :** voir [ROUTING-JARVIS.md](ROUTING-JARVIS.md) pour le mapping mode ↔ modèle

### 9. `jarvis_last_response`
**Description :** Retourne le ou les derniers échanges de la conversation JARVIS (user + jarvis).
**Params :** `n: integer` (optionnel · 1-5, défaut 1)
**Usage :** vérifier ce que JARVIS vient de répondre sans voir l'interface web
**Endpoint :** `GET /api/conversation/last?n=N`

### 10. `jarvis_code_exec`
**Description :** Écrit un fichier sur le serveur JARVIS → transfère sur srv-dev-1 via SCP → exécute → retourne la sortie.
**Params :** `filename: string` (requis) · `code: string` (requis · contenu complet)
**Extensions supportées :** `.py .sh .js .ts .html .css .json .yml .rb .go .php .sql`
**Sécurité :** uniquement srv-dev-1 (`192.168.1.21`) · héritage `_BLOCKED_SSH` (rm, mkfs, dd, shutdown, etc.)
**Endpoint :** bypass Python `_detect_code_command` → `_code_scp_exec_sse`

---

## Configuration Claude Desktop

Ajoute à `%APPDATA%\Claude\claude_desktop_config.json` :

```json
{
  "mcpServers": {
    "jarvis": {
      "transport": {
        "type": "http",
        "url": "http://localhost:5010/mcp"
      }
    }
  }
}
```

Puis redémarre Claude Desktop. Les 10 outils apparaissent sous "jarvis" dans le menu MCP de Claude.

**Vérification :**
- `http://localhost:5010/health` → devrait retourner `{"status": "ok"}`
- Dans Claude Desktop, demander : "list les outils MCP disponibles" — les 10 outils `jarvis_*` doivent apparaître

---

## Démarrage / arrêt

### Manuel

```bash
cd C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\scripts
python jarvis_mcp_server.py --port 5010
```

### Tâche planifiée Windows + Watchdog

JARVIS MCP est censé tourner H24 en background. Le watchdog [`jarvis_watchdog.ps1`](../scripts/jarvis_watchdog.ps1) (lancé par tâche planifiée toutes les 5 min) vérifie que les 2 processus tournent :
- `jarvis.py` (port 5000)
- `jarvis_mcp_server.py` (port 5010)

Si l'un des deux est down, le watchdog le relance automatiquement et log dans `jarvis_watchdog.log` (rotation à 512 KB).

**Installation watchdog** : voir [`jarvis_watchdog_install.ps1`](../scripts/jarvis_watchdog_install.ps1) (création de la tâche planifiée).

---

## JARVIS_HEADER — signature des réponses MCP

Toutes les réponses MCP sont préfixées par un cartouche ASCII pour identifier la source :

```
╔══════════════════════════════════╗
║  ◈  JARVIS  —  phi4:14b  ◈  ║
╚══════════════════════════════════╝
```

→ Claude voit clairement quelles infos viennent de JARVIS local vs sa propre génération.

---

## Sécurité

| Couche | Détail |
|--------|--------|
| **Loopback only** | MCP écoute sur `localhost:5010` (pas exposé en LAN) · JARVIS lui-même sur `localhost:5000` |
| **Pas d'auth** | Pas de token (réseau local fiable) — à durcir si exposition LAN un jour |
| **RFC1918 immuable** | Hérite de JARVIS — JAMAIS ban d'IP RFC1918 (cf. [ROUTING-JARVIS.md](ROUTING-JARVIS.md)) |
| **_BLOCKED_SSH** | Hérite — `jarvis_read_file` ne peut pas lire `/etc/shadow`, `jarvis_code_exec` ne peut pas exécuter `rm`/`mkfs`/`dd`/`shutdown` |
| **`jarvis_code_exec`** | Cible exclusivement `srv-dev-1` (192.168.1.21) — pas d'autre hôte atteignable |
| **Timeouts** | 120s max sur `/api/chat`, 10s sur status — pas de blocage long terme |

---

## Architecture des fonctions

| Symbole | `jarvis_mcp_server.py:ligne` | Rôle |
|---------|------------------------------|------|
| `_TOOLS_DEFS` | 143 | Liste des 10 outils MCP (Tool objects) |
| `@app.list_tools()` | 213 | Handler MCP qui expose `_TOOLS_DEFS` au client |
| `@app.call_tool()` | 369 | Dispatcher qui route le nom d'outil → fonction Python |
| `_collect_sse_tokens()` | 53 | Helper async : appelle endpoint SSE JARVIS et accumule les tokens |
| `_fetch_ip_history()` | 88 | `jarvis_soc_ask` injection IP 30j |
| `_fetch_soc_context()` | 115 | `jarvis_soc_status` parse monitoring.json |
| `_sanitize()` | 318 | Tronque les réponses longues à `max_chars=3000` |
| `_build_starlette_app()` | 385 | Construit l'app Starlette (3 routes : /health, /sse, /mcp) |

---

## Références

- Mémoire détaillée : [`~/.claude/.../memory/project_jarvis_mcp.md`](../../../.claude/projects/c--Users-mmsab-Documents-0xCyberLiTech/memory/project_jarvis_mcp.md)
- Architecture globale : [`JARVIS_SOC_PLATFORM.md`](../JARVIS_SOC_PLATFORM.md)
- Routing modes : [`ROUTING-JARVIS.md`](ROUTING-JARVIS.md)
- Watchdog : [`scripts/jarvis_watchdog.ps1`](../scripts/jarvis_watchdog.ps1)
