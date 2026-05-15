# JARVIS — Référence Technique
<!-- 2026-05-15 — v1.8 — routing 4 branches · phi4:14b + qwen3:8b CR · mxbai-embed-large · NDT script auto 100/100 · score honnête global 92/100 (recalibré depuis 62 réel · +30 via chantier dette 2026-05-14/15 : Ruff 98→0 + git + hooks + ruff.toml + CSS 8 fichiers + audio_dsp.py + refactor JS jarvis_main.js 7828→148L (-98,1%) + 705 tests pytest sur 33/34 modules coverage 39% lignes + fix perf IPv6 + hook pre-push) -->

Assistant IA personnel 0xCyberLiTech · Windows 11 Pro · RTX 5080 Blackwell · Python 3.11

---

## 1. Identité & état

| Attribut | Valeur |
|---|---|
| Version | 3.3 (production) · chantier dette technique 2026-05-14/15 |
| Audit sécurité | **8/10** honnête (v2.7 — 2026-05-13 · audit ciblé + 1 fix race condition) |
| Dette technique (NDT script auto) | **100/100** · D1/D2/D6/D13 zéro violation (session 17 — 2026-05-08) |
| **Score honnête global** | **92/100** (recalibré post-audit pytest --cov : départ réel 62/100, +30 via chantier dette 2026-05-14/15 — git + hooks pre-commit/pre-push + ruff.toml + CSS 8 fichiers + audio_dsp.py + refactor JS jarvis_main.js 7828→148L (−98,1%) + 705 tests pytest sur 33/34 modules avec coverage 39% lignes + fix perf IPv6 −97% latence interne · MAIS pas de CI cloud — alternative locale pre-push) |
| Machine | Windows 11 Pro · RTX 5080 16 GB GDDR7 · CUDA 12 · Python 3.11 |
| LLM | Ollama local uniquement — zéro cloud |

---

## 2. Architecture technique

### 2.1 Stack

| Couche | Technologie |
|---|---|
| Backend | Python 3.11 · Flask :5000 (loopback 127.0.0.1) |
| LLM SOC / raisonnement | phi4:14b · 9.1 GB · keep_alive 24h |
| LLM GÉNÉRAL + VOCAL + vision | gemma4:latest · ~9.6 GB · multimodal · switch manuel ↔ SOC |
| LLM CODE | qwen2.5-coder:14b · 9.0 GB · dev srv-dev-1 · switch manuel ↔ CODE |
| LLM CODE REASONING | qwen3:8b · ~5 GB · single-pass thinking `<think>` masqué · switch manuel ↔ C·R |
| Embeddings RAG | mxbai-embed-large · ~0.7 GB · 1024 dims |
| RAG | mxbai-embed-large · 599 chunks · seuil 0.35 · TTL 300s |
| STT | faster-whisper large-v3-turbo · CUDA · FR · initial_prompt SOC |
| TTS défaut | edge-tts fr-CA-AntoineNeural (HTTPS) |
| TTS fallback | Kokoro ff_siwis (CUDA) → XTTS v2 58 voix → Piper (onnx) → SAPI5 |
| DSP | numpy · scipy · DeepFilterNet GPU sm_120 Blackwell |
| MCP | jarvis_mcp_server.py · 10 outils · stdio pythonw |

### 2.2 Métriques fichiers (2026-05-14 · post-chantier dette technique)

| Fichier | Lignes | État |
|---|---|---|
| `scripts/jarvis.py` | **4 633** | 75 routes · NDT 100/100 · routing **4 branches** SOC/GÉNÉRAL/CODE/CR · réduit via Phase 3 (30 modules) + audio_dsp.py (chantier 2026-05-14) |
| `scripts/blueprints/soc.py` | 1 689 | Blueprint SOC · auto-engine · SSH 4 hôtes · `/api/soc/ip-history` · fix race condition `_soc_actions_save` (2026-05-13) |
| `scripts/jarvis_mcp_server.py` | ~430 | **10 outils** · `_TOOLS_DEFS` · streamable-HTTP port 5010 · 0 fonction >80L |
| `scripts/static/jarvis_main.js` | **4 013** | 🟡 refactor JS 2026-05-14 soir : 7828→4013 (−49%) · 11 modules extraits · reste à finir |
| `scripts/static/js/` (11 modules) | ~5 000 | terminal_code·voice_lab·stt + tasks_tab·welcome·eq_parametric·eq_music·audio_mire·audio_viz·settings_llm·dsp_audio (refactor JS 2026-05-14) |
| **31 modules Python extraits** | **~3 540** | Phase 3 : Audio/Voice 5 + Bypass 8 + Infra/RAG 2 + Chat/LLM core 15 + `audio_dsp.py` 508L (chantier 2026-05-14) — voir [`ROUTING-JARVIS.md`](ROUTING-JARVIS.md) |
| `scripts/static/css/` | 8 fichiers | ex-`jarvis.css` 5270L → core/chat/dsp/terminal-taches/hud-welcome/rack/settings-soc/voicelab (chantier 2026-05-14) |
| `scripts/templates/jarvis.html` | ~215 | Shell Jinja2 · 0 handler inline · charge 8 `<link>` CSS + 15 `<script>` JS |
| RAG `jarvis_rag/meta.json` | 599 chunks | MEMORY.md×2 + CIRCUIT_SOC (49) + RUNBOOK (15) |
| `jarvis_prompt_profiles.json` | — | 7 profils · Généraliste Gemma4 · 3 RÈGLES ABSOLUES (Qwen2.5/DeepSeek/LLaVA supprimés) |

---

## 3. Routage LLM automatique — 4 branches + bypass ⚡

```
Message utilisateur
  │
  ├─ 1. ⚡ Bypass direct (sans LLM, instantané)
  │        VM stop/start → SSH Proxmox qm stop/start
  │        Service restart → SSH systemctl restart + is-active
  │        Backup JARVIS → PowerShell streaming backup-jarvis.ps1
  │        Backup Proxmox → PowerShell streaming proxmox-backup-auto.ps1
  │        Lecture fichier → SSH cat / ls -la
  │
  ├─ 2. 🤖 Branche SOC — mot-clé (_CHAT_SOC_KW) → phi4:14b
  │        + contexte monitoring.json live (SSH srv-ngix)
  │        + temp=0.2 · num_ctx=16384
  │
  ├─ 3. 🤖 Branche CODE — _jarvis_mode == 'code' → qwen2.5-coder:14b
  │        + _CODE_SYSTEM_SUFFIX injecté · SSH dev srv-dev-1
  │
  ├─ 4. 🤖 Branche CODE REASONING — _jarvis_mode == 'code_reasoning' → qwen3:8b
  │        + single-pass thinking masqué <think>…</think> · zéro injection SOC/PVE
  │
  └─ 5. 🤖 Branche GÉNÉRAL — tout le reste → gemma4:latest
           + profil "◎ Généraliste — Gemma4" · [NO_SOC]
           + infra · quotidien · vision (multimodal)
           + sans contexte sécurité
```

**Priorité** : Bypass > CODE REASONING > SOC > CODE > GÉNÉRAL  
**Règle** : `soc_trigger=True` force phi4:14b. Switch manuel via boutons `SOC / GÉNÉRAL / CODE / C·R` dans l'UI.  
⚠ Supprimés : phi4-reasoning:plus · qwen2.5:14b · deepseek-r1:14b · llava-phi3:latest (2026-05-08) · nomic-embed-text (2026-05-10)

### 3.1 Mots-clés SOC — liste exacte

**Outils** : `soc` · `monitoring` · `crowdsec` · `fail2ban` · `suricata` · `ufw` · `waf` · `bouncer`  
**IPs** : `bannir` · `débannir` · `ip suspecte` · `ip bloquée` · `ip malveillante`  
**Événements** : `menace` · `attaque` · `hacker` · `intrusion` · `incident` · `exploit` · `cve` · `rce` · `ddos` · `brute force` · `injection` · `scan de port` · `comportement suspect`  
**Kill chain** : `kill chain` · `recon`  
**Phrases composées** : `analyse la situation` · `état soc` · `rapport soc` · `score menace` · `niveau de menace` · `sécurité réseau` · `trafic réseau` · `trafic suspect` · `anomalie réseau` · `tentative de connexion` · `journal sécurité` · `défense réseau`

> Mots seuls trop génériques **exclus** : `sécurité`, `trafic`, `score`, `tentative`, `anomalie`, `reconnaissance`, `défense` → remplacés par des phrases composées.

### 3.2 Continuations GÉNÉRAL reconnues

Après une réponse infra/GÉNÉRAL, les confirmations courtes restent sur la branche GÉNÉRAL (gemma4) :
```python
_INFRA_CONFIRM_RE = re.compile(
    r'^\s*(oui|non|ok|vas-y|go|confirme|yes|allez|d.accord|lance|fais.le|applique)\s*[!.]?\s*$', re.I)
```

---

## 4. Sécurité — Audit 10/10

### 4.1 Points verts (0 gap — 2026-05-06 v2.6)

| Domaine | Mesure |
|---|---|
| Exposition réseau | `host=127.0.0.1` · `debug=False` · Windows Firewall bloque LAN |
| CORS | Whitelist stricte : localhost + 192.168.1.50 uniquement |
| Headers HTTP | `X-Frame-Options:DENY` · `nosniff` · `Server` header supprimé |
| Terminal intégré | IP check 127.0.0.1/192.168.1.x · `shell=False` · blacklist destructive |
| SSH tools | 4 hôtes · 29 patterns bloqués `_BLOCKED_SSH` · lecture seule + write whitelist |
| Rate limiting | 8 routes générales + SOC Blueprint 5–120/min |
| LLM | Ollama localhost:11434 — zéro cloud |
| RFC1918 | IPs LAN intouchables — code ET tous les profils LLM |
| Logs | `tts.log` rotation 50 KB×3 · `_SEC_EVENTS` journal sécurité interne |

### 4.2 Garde-fous non négociables

- **RFC1918 intouchable** : aucun LLM ni outil ne peut bannir 192.168.x / 10.x / 172.16-31.x
- **`_ALLOWED_SERVICES`** : restart autorisé uniquement nginx / crowdsec / fail2ban / apache2
- **Données** : zéro logs bruts, zéro IPs vers Anthropic — résumés structurés uniquement

### 4.3 _BLOCKED_SSH — 29 patterns bloqués sur les 4 hôtes

```
Suppression/destruction : rm · rmdir · mkfs · dd if= · truncate
Arrêt système          : shutdown · reboot
Services               : systemctl stop · systemctl disable
Firewall               : iptables -F
Redirections           : > / · | sh · | bash · curl.*sh | · wget.*sh |
Proxmox destructif     : qm destroy · qm suspend · qm migrate · qm set · qm create · qm clone · qm unlock
LXC                    : pct stop · pct start · pct destroy · pvectl
Fichiers système       : tee · sed -i · chmod · chown · echo > · echo >> · > /etc · > /var · > /opt
Déplacement            : mv · cp
```

### 4.4 Historique passes d'audit

| Date | Score | Points clés |
|---|---|---|
| 2026-03-22 | CONFORME | host 0.0.0.0 → 127.0.0.1 |
| 2026-04-11 | 10/10 | Rate limiters SOC · Blueprint · STT/Vision |
| 2026-04-15 | 10/10 | CSRF · `shlex.quote` · XSS mixing/main |
| 2026-04-17 | 10/10 | `'use strict'` IIFE · `_esc()` · `except Exception` typés |
| 2026-04-18 | 10/10 | 288 onclick → data-action · 86 dispatchers |
| 2026-05-03 | 10/10 | NDT 100/100 · dette zéro absolue |
| 2026-05-04 | 10/10 | SSH tools 4 hôtes · `_BLOCKED_SSH` · fix 500 Ollama |
| 2026-05-05 | 10/10 | STT large-v3-turbo · num_ctx adaptatif · RAG 599 chunks |
| 2026-05-05 v2.2 | 10/10 | NDT-CSS `_stColor()` · `/api/soc/ip-history` · historique IP MCP |
| 2026-05-06 v2.5 | 10/10 | NDT-LONG jarvis_mcp_server.py — 0 fonction >80L |
| 2026-05-06 v2.6 | 10/10 | NDT-CSS `_vpSetInfo` 2 IIFEs · `except OSError` · audit complet |
| 2026-05-08 s17  | 10/10 | NDT-MAGIC 14 constantes timeout · NDT-ERR 8 catch→warn · NDT-CSS impact-bar classList |
| 2026-05-10 s26  | NDT 100/100 | NDT-DUP SSH `_tool_commande_ssh_run()` · NDT-HTML-MAGIC Jinja2 `{{ dev_ip }}` · NDT-ERR~15 blocs documentés · NDT-DEAD 5 imports/consts supprimés |
| 2026-05-13 s33  | **89/100** (valeur d'époque) | Phase 3 split monolithe Python complète (30 modules · -31% jarvis.py) · 25 tests E2E Playwright · ESLint 0 errors · audit sécurité 8/10 |
| 2026-05-13 s33c | **92/100** (valeur d'époque) | Split JS partiel : `recorder.js` + `voice_print.js` extraits · `jarvis_main.js` 10507→8994L (-14.4%) |
| 2026-05-14       | **78/100 honnête** (recalibré) | ⚠ Audit strict : le 91 était optimiste, départ réel **62/100**. Chantier dette 2026-05-14 (**62→78, +16**) : Ruff 98→0 (2 bugs F821 réels corrigés) + `ruff.toml` · **git initialisé** (100% local) · **pre-commit hooks bloquants** · `jarvis.css` → 8 fichiers CSS · `audio_dsp.py` extrait · 2 smoke tests LLM · **refactor JS partiel** (3 modules : terminal_code/voice_lab/stt) |
| 2026-05-14 soir  | **~82/100 honnête** | **Refactor JS massif** : `jarvis_main.js` 7828→**4013 L** (−49%) · **11 modules** extraits dans `static/js/` · méthode byte-identique vérifiée (node --check · eslint 0 · validation E2E prod) · 1 régression d'ordre détectée+corrigée |
| 2026-05-15       | **~92/100 honnête** | **Refactor JS terminé** + **Phase 4 tests massifs étendus** : `jarvis_main.js` 4013→**148 L** (−98,1% cumul depuis 7828) · 21 modules JS · **705 tests pytest** sur 33/34 modules (94%) avec coverage **39% lignes** (proxmox_api 93%, bypass_backup 96%, voice_lab 71%, deepfilter 84%, ssh_terminal 100%, stt 98%, rag_live 92%, soc.py 33%, jarvis.py 26%, audio_dsp 25%) · **fix perf systémique IPv6** (-97% latence interne via `OLLAMA_URL`/`JARVIS_BASE` → `127.0.0.1`) · **hook pre-push pytest** · 3 bugs prod détectés+fixés · outil `tools/profile_perf.py` |

---

## 5. Qualité logicielle — 2 scores distincts

⚠ **Distinction critique** :
- **NDT 100/100** = score script automatisé maison (D1/D2/D6/D13 dans le code Python). Mesure fonction longue, silent pass, magic numbers, params >6. Reste vrai au 2026-05-15.
- **Score honnête global ~92/100** = ce que mesure JARVIS dans son ensemble (Python + JS + tests + CI + perf). Recalibré honnêtement le 2026-05-15 post-audit pytest --cov : le 92/100 affiché en session 33c était optimiste (départ réel 62), chantier 2026-05-14/15 a fait +29 (→91) via : git+hooks+CSS, refactor JS jarvis_main.js sous 150 L (−98,1%), 705 tests pytest sur 33/34 modules avec coverage 39% lignes, fix perf IPv6, hook pre-push. Reste pour 95+ : tester tts_engines (199 stmts, 4 engines async/CUDA) + jarvis_mcp_server (211 stmts, FastMCP) · profiling TTS détaillé · circuit breaker Ollama · CI cloud (impossible « rien sur le web »).

### NDT (script automatisé) — 100/100

| Catégorie NDT | Violations | Résolution |
|---|---|---|
| NDT-CSS (style inline extractable) | 0 | `_stColor()` · 7 classes st-* · classList partout · périmètre 3 fichiers JS |
| NDT-LONG (fonction >80 lignes) | 0 | `_sse_tok()` · `_ssh_base()` · `list_tools` 2L · `call_tool` 13L |
| NDT-ERR (bare except:) | 0 | Tous `except: pass` documentés (raison commentée) · catégories : fallback légitime · API throws by design · network poll resilience |
| NDT-DUP (blocs dupliqués) | 0 | `_sse_tok()` · `_tool_commande_ssh_run()` · `_clearAfter()` · `_TOOLS_DEFS` · `_TOOL_HANDLERS` |
| NDT-MAGIC (nombres magiques) | 0 | 14 constantes timeout nommées `_*_TIMEOUT_S` · `_NUM_CTX_*` · `_SOC_TEMPERATURE` · etc. |
| NDT-DEAD (code mort) | 0 | 74 MB nettoyés (Piper mort · WAV dev · logs stale) |
| NDT-LOG (console.log prod) | 0 | |
| NDT-HTML (handler inline) | 0 | data-action · data-oninput · data-onchange dispatchers |

Périmètre : `jarvis.py` · `soc.py` · `jarvis_mcp_server.py` · `audio_dsp.py` + 30 modules · `jarvis_main.js` · `static/css/` (8 fichiers)

---

## 6. Architecture multi-agent — JARVIS + Claude

### 6.1 Philosophie

```
┌──────────────────────────────────────────────────────┐
│  CLAUDE CODE (Anthropic — cloud)                     │
│  Code · architecture · incidents inconnus            │
│  Règle : ne voit que l'escalade structurée de JARVIS │
└──────────────────────┬───────────────────────────────┘
                       │ résumé structuré (max 5 points)
                       │ jamais de raw data ni IPs brutes
                       ▼
┌──────────────────────────────────────────────────────┐
│  JARVIS (local — RTX 5080)                           │
│  SOC · infra · généraliste · filtrage                │
│  Coût : électricité GPU (quasi zéro)                 │
└──────────────────────────────────────────────────────┘
```

### 6.2 Séparation des rôles

| JARVIS traite seul | Claude intervient |
|---|---|
| Monitoring SOC · bans · alertes vocales | Modifier jarvis.py / soc.py / configs nginx |
| Espace disque · MAJ · état services SSH | Incident inconnu / nouveau pattern |
| Arrêt/démarrage VMs (bypass LLM direct) | Décision architecturale |
| Questions générales (Gemma4 auto) | Bug non résolu après 2 tentatives |

### 6.3 Impact tokens

| Scénario | Avant | Après |
|---|---|---|
| "État de la menace ?" | ~3 000 tokens (logs bruts) | ~200 tokens (résumé JARVIS) |
| Monitoring normal | Claude consulté à chaque poll | 0 token (JARVIS seul) |
| "Espace disque sur pa85 ?" | ~800 tokens | 0 token (gemma4 + SSH tool calling) |
| Question générale | phi4 pollué SOC | Gemma4 direct (0 contexte sécurité) |

---

## 7. MCP — pont Claude Code ↔ JARVIS

### 7.1 Configuration

```json
// .mcp.json — racine workspace VSCode
{
  "mcpServers": {
    "jarvis": {
      "command": "pythonw",
      "args": ["C:/Users/mmsab/Documents/0xCyberLiTech/JARVIS/scripts/jarvis_mcp_server.py"]
    }
  }
}
```

`pythonw` : supprime la fenêtre console Windows, maintient les pipes stdio MCP.

### 7.2 Les 10 outils MCP

| Outil | Endpoint | Rôle |
|---|---|---|
| `jarvis_chat` | POST `/api/chat` SSE | Chat LLM avec routing automatique (4 branches + bypass) |
| `jarvis_soc_status` | GET `/api/soc/context` | État SOC : menace, bans, services |
| `jarvis_stats` | GET `/api/stats` | Uptime, GPU, sessions, TTS/STT |
| `jarvis_soc_ask` | POST `/api/chat` SSE | Question SOC + logs SSH + historique IP 30j |
| `jarvis_infra_status` | POST `/api/chat` SSE | État infra (Proxmox VMs, srv-ngix, clt, pa85) |
| `jarvis_proxmox_vms` | POST `/api/chat` SSE | État VMs Proxmox |
| `jarvis_read_file` | POST `/api/chat` SSE | Lecture fichiers SSH |
| `jarvis_model_switch` | POST `/api/models` | Changement modèle Ollama actif |
| `jarvis_last_response` | GET `/api/conversation/last` | Derniers échanges de la conversation JARVIS |
| `jarvis_code_exec` | bypass `_code_scp_exec_sse` | Écrit + SCP + exécute un fichier sur srv-dev-1 |

> Détail complet des 10 outils : voir [`docs/MCP-SERVER.md`](MCP-SERVER.md).

### 7.3 Injection historique IP dans jarvis_soc_ask

Si IPv4 détectée dans la question → appel `/api/soc/ip-history` (~1.2s) → injection :
```
[HISTORIQUE IP x.x.x.x — 30 jours]
CrowdSec : 5 alertes · actif maintenant : 1
```
Résout le cas "IP récidiviste dont le ban a expiré" — JARVIS recommande le ban plutôt que la surveillance.

### 7.4 Identifiant visuel JARVIS_HEADER

```
╔══════════════════════════╗
║  ◈  JARVIS  —  phi4:14b  ◈  ║
╚══════════════════════════╝
```
Sans ce cadre = réponse Claude directe.

### 7.5 Structure jarvis_mcp_server.py

```
jarvis_mcp_server.py (NDT-LONG refactorisé — 0 fonction >80L)
├── _TOOLS_DEFS        ← 10 outils définis en constante
├── _TOOL_HANDLERS     ← dict nom → handler (dispatch)
├── _RE_IPV4           ← regex détection IPv4
├── _collect_sse_tokens()  ← consomme le stream SSE JARVIS
├── _fetch_ip_history(ip)  ← POST /api/soc/ip-history
├── _fetch_soc_context()   ← GET /api/soc/context
├── 10 × _handle_*()   ← un handler par outil
├── list_tools()       ← 2L
└── call_tool()        ← 13L
```

---

## 8. Outils SSH — périmètre et règles

### 8.1 4 hôtes disponibles

| Outil | Hôte | IP | Port | Clé SSH |
|---|---|---|---|---|
| `commande_ssh_ngix` | srv-ngix (VM 108) | 192.168.1.50 | 2272 | `~/.ssh/id_nginx` |
| `commande_ssh_proxmox` | Proxmox VE | 192.168.1.20 | 2272 | `~/.ssh/id_proxmox` |
| `commande_ssh_clt` | clt (VM 106) | 192.168.1.12 | 2272 | `~/.ssh/id_clt` |
| `commande_ssh_pa85` | pa85 (VM 107) | 192.168.1.13 | 2272 | `~/.ssh/id_pa85` |

### 8.2 RÈGLES ABSOLUES SSH (profil GÉNÉRAL — Gemma4)

| # | Règle |
|---|---|
| N°1 | SSH obligatoire AVANT de répondre — jamais de mémoire, jamais d'estimation |
| N°2 | Valeurs SSH reproduites EXACTES — zéro arrondi, zéro reformulation des chiffres |
| N°3 | UN seul appel outil par question — pas de boucle |
| N°4 | `qm/pvesh/pvesm` exclusifs à l'hôte Proxmox — jamais via ngix/clt/pa85 |
| N°5 | `systemctl restart` autorisé pour apache2/nginx/crowdsec/fail2ban + vérification `is-active` obligatoire après |

### 8.3 Opérations autorisées avec confirmation

```bash
DEBIAN_FRONTEND=noninteractive apt-get update -q && apt-get upgrade -y
# Uniquement après confirmation explicite : "oui", "go", "applique", "vas-y"
```

---

## 9. Intégrations

### 9.1 Dashboard SOC (monitoring-index.html v3.97.157 — 35 tuiles)

| Élément | Description |
|---|---|
| Tuile JARVIS | Grille INFRASTRUCTURE — statut, modèle, compteurs session |
| Auto-engine | Analyse toutes les 60s si JARVIS ONLINE — ban auto si >500 req/h |
| TTS SOC | Lecture vocale via `/api/speak` (edge-tts localhost:5000) |
| Quick prompts | 14 prompts rapides dans le panel bas-droite |
| Alertes vocales | Si niveau ÉLEVÉ ou CRITIQUE → TTS automatique |

JARVIS reste **optionnel** — le SOC dashboard fonctionne à 100% sans lui.

### 9.2 Infrastructure réseau couverte

| Hôte | IP | Rôle |
|---|---|---|
| srv-ngix (VM 108) | 192.168.1.50 | nginx + CrowdSec WAF + Suricata + fail2ban |
| clt (VM 106) | 192.168.1.12 | Apache · site cybersécurité CLT |
| pa85 (VM 107) | 192.168.1.13 | Apache · site associatif PA85 |
| Proxmox VE | 192.168.1.20 | Hyperviseur · ZFS 3.5 To |

---

## 10. Roadmap

### Items ouverts (v3.3)

| Priorité | Item | Gain |
|---|---|---|
| 🔵 | **3.1 Vision active SOC** — analyse screenshot SOC | Analyse visuelle |
| 🔵 | **1.2 Wake word** — activation vocale sans clic | Vocal hands-free |
| 🟡 | **SSH write ops** — apt upgrade · restart étendu (validation) | Maintenance automatisée |

### Items fermés (ne pas ré-ouvrir)

```
✅ Routing 3 branches SOC/GÉNÉRAL/CODE + switch  ✅ SSH tools 4 hôtes · _BLOCKED_SSH
✅ VM multi-stop/start bypass LLM                 ✅ MCP 8 outils · JARVIS_HEADER
✅ RAG 599 chunks · seuil 0.35 · mxbai-embed      ✅ RAG Live SOC (logs SSH temps réel)
✅ Vision gemma4 multimodal (remplace llava-phi3) ✅ STT large-v3-turbo + initial_prompt
✅ ThreatScore 30j historique + tendance           ✅ /api/soc/ip-history + MCP injection
✅ Mémoire inter-sessions + session-end summary    ✅ SSH write ops (RÈGLE N°5)
✅ NDT 10/10 session 17 (MAGIC·ERR·CSS résolus)   ✅ Audit 10/10 (0 gap)
✅ Mots-clés SOC affinés (génériques exclus)      ✅ Sauvegarde JARVIS via chat
✅ 4 LLM supprimés (phi4-reasoning:plus/qwen2.5:14b/deepseek-r1:14b/llava-phi3) · gemma4 couvre GÉNÉRAL+vision
✅ nomic-embed-text supprimé (2026-05-10) · mxbai-embed-large seul embed actif
```

### Ce qui ne sera pas ajouté

| Fonctionnalité | Raison |
|---|---|
| Accès LAN (0.0.0.0) | Décision sécurité — loopback strict conservé |
| WebSocket (remplacement poll) | Refonte trop lourde pour le gain |
| Cloud LLM (OpenAI, Groq) | Principe zéro dépendance externe |
| Base de données SQL | JSON files suffisent |

---

*REFERENCE-TECHNIQUE.md · JARVIS 0xCyberLiTech · 2026-05-14 v1.6*
