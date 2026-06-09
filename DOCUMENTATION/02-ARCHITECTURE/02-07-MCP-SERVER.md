---
title: "MCP server â€” 12 outils + Claude Desktop"
code: "JARVIS-DOC-02-07"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "Architecture"
mots_cles: ["mcp", "claude", "desktop", "outils", "integration"]
---

# JARVIS MCP Server â€” Pont Claude â†” JARVIS

Le serveur MCP (Model Context Protocol) expose JARVIS comme un set d'**outils** consommables par Claude Desktop, Claude Code et tout client compatible MCP. Permet Ã  Claude (cloud) d'interroger JARVIS (local) sans passer raw data sensible vers Anthropic.

**Architecture clÃ© :** JARVIS filtre/agrÃ¨ge/dÃ©tecte localement â†’ Claude voit uniquement l'escalade ou la synthÃ¨se.

> **HiÃ©rarchie des appels et autonomie** : pour le dÃ©tail de qui appelle qui (Claude â†’ MCP â†’ JARVIS â†’ srv-nginx), qui tombe si X est Ã©teint, et pourquoi le MCP reste autonome de Claude, voir la section dÃ©diÃ©e [`CIRCUIT_SOC_JARVIS.md#hiÃ©rarchie-des-appels-et-autonomie`](../CIRCUIT_SOC_JARVIS.md#hi%C3%A9rarchie-des-appels-et-autonomie). En rÃ©sumÃ© : **MCP est un proxy autonome qui sert tout client MCP** (Claude n'est qu'un consommateur parmi d'autres possibles) Â· **JARVIS pilote le process MCP** (subprocess + watchdog) mais ne dÃ©pend jamais ni de Claude ni du MCP pour fonctionner.

> **Split monolithe â€” Phase 3 (session 33) + chantier dette (2026-05-14/15) + chantier coverage (2026-05-17)** : le serveur MCP `jarvis_mcp_server.py` n'a **PAS changÃ© fonctionnellement** â€” il consomme toujours les routes HTTP de `jarvis.py`. Les outils MCP fonctionnent identiquement aprÃ¨s extraction de **32 modules** Python (Phase 3 + ajouts ultÃ©rieurs `audio_dsp.py` et `ollama_circuit.py`). `jarvis.py` a Ã©tÃ© allÃ©gÃ© (ex-monolithe 6592 lignes), les routes Flask consommÃ©es par MCP restent dans jarvis.py via wrappers DI vers les modules. Score dette, tests et coverage â†’ source unique [`../BILAN-TECHNIQUE.md` Â§0](../BILAN-TECHNIQUE.md) (audit dette complet 2026-05-22 Â· refactor JS terminÃ© (âˆ’98,1%) Â· fix perf IPv6 -97 % latence interne Â· circuit breaker Ollama Ã©tendu 8 call-sites Â· prÃ©-warm Kokoro CUDA Â· hook pre-push pytest Â· SSH write ops 4 couches + audit log forensic (2026-05-17) Â· Ollama 0.24.0 Â· pas de CI cloud â€” alternative locale OK).

---

## Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  Claude Desktop / Claude Code  (cloud Anthropic)                â”‚
â”‚                                                                  â”‚
â”‚         â”‚ MCP protocol (JSON-RPC over HTTP streamable)           â”‚
â”‚         â–¼                                                        â”‚
â”‚  â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—               â”‚
â”‚  â•‘  jarvis_mcp_server.py   (Windows Â· port 5010) â•‘               â”‚
â”‚  â•‘  Starlette + uvicorn + MCP SDK                â•‘               â”‚
â”‚  â•‘  12 outils @app.list_tools()                  â•‘               â”‚
â”‚  â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•               â”‚
â”‚         â”‚ HTTP REST + SSE                                        â”‚
â”‚         â–¼                                                        â”‚
â”‚  â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—               â”‚
â”‚  â•‘  jarvis.py   (Windows Â· port 5000)            â•‘               â”‚
â”‚  â•‘  Flask + Ollama (11434) + SOC blueprint       â•‘               â”‚
â”‚  â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•               â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

| Composant | DÃ©tail |
|-----------|--------|
| **Fichier** | [`scripts/jarvis_mcp_server.py`](../scripts/jarvis_mcp_server.py) (~430 lignes) |
| **Port** | `5010` (modifiable via `--port`) |
| **Lib MCP** | `mcp.server.lowlevel` + `mcp.server.streamable_http_manager` |
| **HTTP framework** | Starlette + uvicorn |
| **Mode** | StreamableHTTPSessionManager Â· stateless |
| **Endpoints HTTP** | `/health`, `/sse`, `/mcp` (GET/POST/DELETE) |
| **JARVIS_BASE** | `http://127.0.0.1:5000` (IPv4 explicite Â· loopback only â€” Ã©vite timeout IPv6 ~2s sur Windows) |
| **Timeouts** | 120s pour `/api/chat` (LLM lourd) Â· 10s pour status/stats/health |

---

## Les 12 outils MCP

Tous les outils retournent du `TextContent` prÃ©fixÃ© par `JARVIS_HEADER` (cartouche ASCII identifiant la source).

### 1. `jarvis_chat`
**Description :** Envoie un message Ã  JARVIS (Ollama local) et retourne sa rÃ©ponse complÃ¨te.
**Params :** `message: string` (requis)
**Usage :** questions gÃ©nÃ©rales, analyses, code, cybersÃ©curitÃ© â€” l'avis du LLM local sans contexte SOC injectÃ©.
**Endpoint sous-jacent :** `POST /api/chat` (SSE accumulÃ©)

### 2. `jarvis_soc_status`
**Description :** Ã‰tat SOC temps rÃ©el â€” niveau de menace, IPs bannies CrowdSec/fail2ban, services actifs, auto-engine.
**Params :** aucun
**Usage :** "donne-moi un Ã©tat rapide du SOC" sans dÃ©clencher un appel LLM
**Endpoint :** `GET /api/soc/context` (`monitoring.json` parsÃ©) â†’ fallback `/api/status`

### 3. `jarvis_soc_ask`
**Description :** Pose une question SOC Ã  JARVIS avec **injection automatique** du contexte live (monitoring.json complet + historique IP 30j).
**Params :** `question: string` (requis)
**Usage :** analyse d'attaque, interprÃ©tation d'alertes, dÃ©cision de ban, comprÃ©hension d'incident â€” donnÃ©es SOC rÃ©elles, pas de RAG statique.
**Endpoint :** `POST /api/soc/ip-history` + `POST /api/chat` (contexte injectÃ© cÃ´tÃ© MCP)

### 4. `jarvis_stats`
**Description :** Statistiques JARVIS â€” uptime, sessions chat, appels TTS/STT, modÃ¨le actif, Ã©tat RAG.
**Params :** aucun
**Endpoint :** `GET /api/stats`

### 5. `jarvis_infra_status`
**Description :** Ã‰tat rapide de toute l'infrastructure â€” Proxmox VMs, srv-nginx (nginx/CrowdSec), clt (Apache), pa85 (Apache).
**Params :** `focus: string` (optionnel â€” `'proxmox'`, `'nginx'`, `'clt'`, `'pa85'`, ou vide pour tout)
**Endpoint :** `POST /api/chat` (LLM avec contexte infra)

### 6. `jarvis_proxmox_vms`
**Description :** Liste les VMs Proxmox avec leur Ã©tat (running/stopped), RAM, CPU, uptime.
**Params :** aucun
**Endpoint :** `POST /api/chat` (LLM avec contexte PVE) Â· bypass Python dÃ©tectÃ© â†’ rÃ©ponse directe sans LLM

### 7. `jarvis_read_file`
**Description :** Lit le contenu d'un fichier distant sur une VM via SSH JARVIS.
**Params :** `vm: string` (requis Â· `'nginx'|'clt'|'pa85'|'proxmox'|'srv-dev-1'`) Â· `path: string` (requis Â· chemin absolu)
**Usage :** lire `nginx.conf`, `jail.conf`, scripts, logs depuis VSCode sans quitter.
**SÃ©curitÃ© :** hÃ©ritÃ©e de `_BLOCKED_SSH` JARVIS (fichiers `/etc/passwd`, `/etc/shadow`, etc. bloquÃ©s) Â· lecture seule

### 8. `jarvis_model_switch`
**Description :** Change le modÃ¨le Ollama actif dans JARVIS.
**Params :** `model: string` (requis Â· ex: `phi4:14b`, `qwen2.5-coder:14b`, `gemma4:latest`, `qwen3:8b`)
**Endpoint :** `POST /api/models`
**Note :** voir [ROUTING-JARVIS.md](ROUTING-JARVIS.md) pour le mapping mode â†” modÃ¨le

### 9. `jarvis_last_response`
**Description :** Retourne le ou les derniers Ã©changes de la conversation JARVIS (user + jarvis).
**Params :** `n: integer` (optionnel Â· 1-5, dÃ©faut 1)
**Usage :** vÃ©rifier ce que JARVIS vient de rÃ©pondre sans voir l'interface web
**Endpoint :** `GET /api/conversation/last?n=N`

### 10. `jarvis_code_exec`
**Description :** Ã‰crit un fichier sur le serveur JARVIS â†’ transfÃ¨re sur srv-dev-1 via SCP â†’ exÃ©cute â†’ retourne la sortie.
**Params :** `filename: string` (requis) Â· `code: string` (requis Â· contenu complet)
**Extensions supportÃ©es :** `.py .sh .js .ts .html .css .json .yml .rb .go .php .sql`
**SÃ©curitÃ© :** uniquement srv-dev-1 (`192.168.1.21`) Â· hÃ©ritage `_BLOCKED_SSH` (rm, mkfs, dd, shutdown, etc.)
**Endpoint :** bypass Python `_detect_code_command` â†’ `_code_scp_exec_sse`

### 11. `jarvis_defense_24h`
**Description :** RÃ©sumÃ© compact des actions dÃ©fensives 24h sur srv-nginx â€” KPI agrÃ©gÃ©s (bans CrowdSec, blocks WAF CLT/PA85, alertes Suricata sev1/sev2, GeoBlock, fail2ban actifs, UFW), heatmap horaire, top pays/AS/scÃ©narios, timeline rÃ©trochrono. Source prÃ©-calculÃ©e par `defense_aggregator.py` cÃ´tÃ© SOC (cron 60 s) â†’ `defense_24h.json` (16 Ko, **13Ã— plus compact** que monitoring.json).
**Params :** aucun
**Usage :** Â« combien de bans aujourd'hui ? quel pays attaque le plus ? quelle heure de pointe ? Â» sans avoir Ã  parser le brut.
**Endpoint :** `GET /api/soc/defense` (cache 30s cÃ´tÃ© JARVIS Â· proxy vers `http://192.168.1.50:8080/defense_24h.json`)
**Pattern :** Single Source of Truth â€” mÃªme fichier consommÃ© par la page web `/defense.html`, le bloc d'injection phi4 mode SOC, et cet outil MCP.

### 12. `jarvis_ioc_status` *(Sprint 18d â€” 2026-05-16)*
**Description :** Score IoC POST-COMPROMISSION 0-100 + 6 signaux prÃ©-calculÃ©s (AIDE drift, C2 outbound Suricata, SSH anomaly, webshells nginx, AppArmor denials, sudo events). DÃ©tecte si un attaquant est **DÃ‰JÃ€ ENTRÃ‰** dans le SOC homelab (vs dÃ©tecter les tentatives â€” couvert par KC). Niveau **OK / WARN / CRIT**. Source prÃ©-calculÃ©e par `ioc_collect.py` sur srv-nginx (cron 60s, 95% cov).
**Params :** aucun
**Usage :** Â« quel est le score IoC ? Â», Â« y a-t-il une compromission ? Â», Â« JARVIS surveille quoi en post-compro ? Â»
**Endpoint :** `GET /api/soc/ioc` (cache 30s cÃ´tÃ© JARVIS Â· extraction clÃ© `ioc` de `monitoring.json`)
**Format rÃ©ponse :** bloc texte compact LLM-friendly â€” header JARVIS + score + 6 compteurs (AIDE/C2/SSH/Webshells/AppArmor/Sudo) + dÃ©tails âš  si levelâ‰ OK avec exemple par signal.

---

## Configuration Claude Desktop

Ajoute Ã  `%APPDATA%\Claude\claude_desktop_config.json` :

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

Puis redÃ©marre Claude Desktop. Les 12 outils apparaissent sous "jarvis" dans le menu MCP de Claude.

**VÃ©rification :**
- `http://localhost:5010/health` â†’ devrait retourner `{"status": "ok"}`
- Dans Claude Desktop, demander : "list les outils MCP disponibles" â€” les 12 outils `jarvis_*` doivent apparaÃ®tre

---

## DÃ©marrage / arrÃªt

### Manuel

```bash
cd C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\scripts
python jarvis_mcp_server.py --port 5010
```

### TÃ¢che planifiÃ©e Windows + Watchdog

JARVIS MCP est censÃ© tourner H24 en background. Le watchdog [`jarvis_watchdog.ps1`](../scripts/jarvis_watchdog.ps1) (lancÃ© par tÃ¢che planifiÃ©e toutes les 5 min) vÃ©rifie que les 2 processus tournent :
- `jarvis.py` (port 5000)
- `jarvis_mcp_server.py` (port 5010)

Si l'un des deux est down, le watchdog le relance automatiquement et log dans `jarvis_watchdog.log` (rotation Ã  512 KB).

**Installation watchdog** : voir [`jarvis_watchdog_install.ps1`](../scripts/jarvis_watchdog_install.ps1) (crÃ©ation de la tÃ¢che planifiÃ©e).

---

## JARVIS_HEADER â€” signature des rÃ©ponses MCP

Toutes les rÃ©ponses MCP sont prÃ©fixÃ©es par un cartouche ASCII pour identifier la source :

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘  â—ˆ  JARVIS  â€”  phi4:14b  â—ˆ  â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

â†’ Claude voit clairement quelles infos viennent de JARVIS local vs sa propre gÃ©nÃ©ration.

---

## SÃ©curitÃ©

| Couche | DÃ©tail |
|--------|--------|
| **Loopback only** | MCP Ã©coute sur `localhost:5010` (pas exposÃ© en LAN) Â· JARVIS lui-mÃªme sur `localhost:5000` |
| **Pas d'auth** | Pas de token (rÃ©seau local fiable) â€” Ã  durcir si exposition LAN un jour |
| **RFC1918 immuable** | HÃ©rite de JARVIS â€” JAMAIS ban d'IP RFC1918 (cf. [ROUTING-JARVIS.md](ROUTING-JARVIS.md)) |
| **_BLOCKED_SSH** | HÃ©rite â€” `jarvis_read_file` ne peut pas lire `/etc/shadow`, `jarvis_code_exec` ne peut pas exÃ©cuter `rm`/`mkfs`/`dd`/`shutdown` |
| **`jarvis_code_exec`** | Cible exclusivement `srv-dev-1` (192.168.1.21) â€” pas d'autre hÃ´te atteignable |
| **Timeouts** | 120s max sur `/api/chat`, 10s sur status â€” pas de blocage long terme |

---

## Architecture des fonctions

| Symbole | `jarvis_mcp_server.py:ligne` | RÃ´le |
|---------|------------------------------|------|
| `_TOOLS_DEFS` | 143 | Liste des 12 outils MCP (Tool objects) |
| `@app.list_tools()` | 213 | Handler MCP qui expose `_TOOLS_DEFS` au client |
| `@app.call_tool()` | 369 | Dispatcher qui route le nom d'outil â†’ fonction Python |
| `_collect_sse_tokens()` | 53 | Helper async : appelle endpoint SSE JARVIS et accumule les tokens |
| `_fetch_ip_history()` | 88 | `jarvis_soc_ask` injection IP 30j |
| `_fetch_soc_context()` | 115 | `jarvis_soc_status` parse monitoring.json |
| `_sanitize()` | 318 | Tronque les rÃ©ponses longues Ã  `max_chars=3000` |
| `_build_starlette_app()` | 385 | Construit l'app Starlette (3 routes : /health, /sse, /mcp) |

---

## RÃ©fÃ©rences

- MÃ©moire dÃ©taillÃ©e : [`~/.claude/.../memory/project_jarvis_mcp.md`](../../../.claude/projects/c--Users-mmsab-Documents-0xCyberLiTech/memory/project_jarvis_mcp.md)
- Architecture globale : [`JARVIS_SOC_PLATFORM.md`](../JARVIS_SOC_PLATFORM.md)
- Routing modes : [`ROUTING-JARVIS.md`](ROUTING-JARVIS.md)
- Watchdog : [`scripts/jarvis_watchdog.ps1`](../scripts/jarvis_watchdog.ps1)

