---
title: "RÃ©fÃ©rence technique â€” stack, composants"
code: "JARVIS-DOC-02-03"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "Architecture"
mots_cles: ["reference", "stack", "composants", "flask", "python", "ollama"]
---

# JARVIS â€” RÃ©fÃ©rence Technique
<!-- 2026-05-22 â€” v2.1 â€” routing 4 branches Â· phi4:14b + qwen3:8b CR Â· mxbai-embed-large Â· refactor JS terminÃ© Â· fix perf IPv6 Â· circuit breaker Ollama Â· prÃ©-warm Kokoro Â· hook pre-push Â· mÃ©triques courantes (score, lignes, tests, coverage) â†’ ../BILAN-TECHNIQUE.md Â§0 -->

Assistant IA personnel 0xCyberLiTech Â· Windows 11 Pro Â· RTX 5080 Blackwell Â· Python 3.11

---

## 1. IdentitÃ© & Ã©tat

| Attribut | Valeur |
|---|---|
| Version | 3.3 (production) Â· chantier dette technique 2026-05-14/15 |
| Audit sÃ©curitÃ© | **8/10** honnÃªte (v2.7 â€” 2026-05-13 Â· audit ciblÃ© + 1 fix race condition) |
| Dette technique (NDT script auto) | **100/100** Â· D1/D2/D6/D13 zÃ©ro violation (session 17 â€” 2026-05-08) |
| **Score & mÃ©triques** | Source unique â†’ [`BILAN-TECHNIQUE.md` Â§0](../BILAN-TECHNIQUE.md) (score dette, lignes, tests, coverage). Plafond pratique sans CI cloud atteint â€” alternative locale : hook pre-push pytest. |
| Machine | Windows 11 Pro Â· RTX 5080 16 GB GDDR7 Â· CUDA 12 Â· Python 3.11 |
| LLM | Ollama local uniquement â€” zÃ©ro cloud |

---

## 2. Architecture technique

### 2.1 Stack

| Couche | Technologie |
|---|---|
| Backend | Python 3.11 Â· Flask :5000 (loopback 127.0.0.1) |
| LLM SOC / raisonnement | phi4:14b Â· 9.1 GB Â· keep_alive 24h |
| LLM GÃ‰NÃ‰RAL + VOCAL + vision | gemma4:latest Â· ~9.6 GB Â· multimodal Â· switch manuel â†” SOC |
| LLM CODE | qwen2.5-coder:14b Â· 9.0 GB Â· dev srv-dev-1 Â· switch manuel â†” CODE |
| LLM CODE REASONING | qwen3:8b Â· ~5 GB Â· single-pass thinking `<think>` masquÃ© Â· switch manuel â†” CÂ·R |
| Embeddings RAG | mxbai-embed-large Â· ~0.7 GB Â· 1024 dims |
| RAG | mxbai-embed-large Â· 599 chunks Â· seuil 0.35 Â· TTL 300s |
| STT | faster-whisper large-v3-turbo Â· CUDA Â· FR Â· initial_prompt SOC |
| TTS dÃ©faut | edge-tts fr-CA-AntoineNeural (HTTPS) |
| TTS fallback | Kokoro ff_siwis (CUDA) â†’ XTTS v2 58 voix â†’ Piper (onnx) â†’ SAPI5 |
| DSP | numpy Â· scipy Â· DeepFilterNet GPU sm_120 Blackwell |
| MCP | jarvis_mcp_server.py Â· **12 outils** (+`jarvis_defense_24h` 2026-05-16) Â· stdio pythonw |

### 2.2 Fichiers & rÃ´les

> Tailles de fichiers, coverage par module et score dette â†’ source unique
> [`BILAN-TECHNIQUE.md` Â§0 et Â§2](../BILAN-TECHNIQUE.md).

| Fichier | RÃ´le |
|---|---|
| `scripts/jarvis.py` | Orchestrateur Flask Â· ~150 routes Â· routing 4 branches SOC/GÃ‰NÃ‰RAL/CODE/CR Â· 33 modules satellites |
| `scripts/blueprints/soc.py` | Blueprint SOC Â· auto-engine Â· SSH 4 hÃ´tes Â· `/api/soc/ip-history` Â· cache 30s + fallback SSH |
| `scripts/jarvis_mcp_server.py` | MCP â€” 12 outils Â· `_TOOLS_DEFS` Â· streamable-HTTP port 5010 |
| `scripts/static/jarvis_main.js` | Point d'entrÃ©e JS Â· refactor terminÃ© Â· 18 modules extraits |
| `scripts/static/js/` | 18 modules JS (audio_viz, chat_core, chat_ui, boot_init, settings_llm, â€¦) |
| **31 modules Python extraits** | Phase 3 : Audio/Voice + Bypass + Infra/RAG + Chat/LLM core + `audio_dsp.py` â€” voir [`ROUTING-JARVIS.md`](ROUTING-JARVIS.md) |
| `scripts/static/css/` | 8 fichiers (ex-`jarvis.css` Ã©clatÃ© Â· chantier 2026-05-14) |
| `scripts/templates/jarvis.html` | Shell Jinja2 Â· 0 handler inline Â· 8 onglets |
| RAG `jarvis_rag/meta.json` | 599 chunks (MEMORY.mdÃ—2 + CIRCUIT_SOC + RUNBOOK) |
| `jarvis_prompt_profiles.json` | â€” | 7 profils Â· GÃ©nÃ©raliste Gemma4 Â· 3 RÃˆGLES ABSOLUES (Qwen2.5/DeepSeek/LLaVA supprimÃ©s) |

---

## 3. Routage LLM automatique â€” 4 branches + bypass âš¡

```
Message utilisateur
  â”‚
  â”œâ”€ 1. âš¡ Bypass direct (sans LLM, instantanÃ©)
  â”‚        VM stop/start â†’ SSH Proxmox qm stop/start
  â”‚        Service restart â†’ SSH systemctl restart + is-active
  â”‚        Backup JARVIS â†’ PowerShell streaming backup-jarvis.ps1
  â”‚        Backup Proxmox â†’ PowerShell streaming proxmox-backup-auto.ps1
  â”‚        Lecture fichier â†’ SSH cat / ls -la
  â”‚
  â”œâ”€ 2. ðŸ¤– Branche SOC â€” mot-clÃ© (_CHAT_SOC_KW) â†’ phi4:14b
  â”‚        + contexte monitoring.json live (SSH srv-nginx)
  â”‚        + temp=0.2 Â· num_ctx=8192 (16384â†’8192 le 2026-05-20, optim VRAM)
  â”‚
  â”œâ”€ 3. ðŸ¤– Branche CODE â€” _jarvis_mode == 'code' â†’ qwen2.5-coder:14b
  â”‚        + _CODE_SYSTEM_SUFFIX injectÃ© Â· SSH dev srv-dev-1
  â”‚
  â”œâ”€ 4. ðŸ¤– Branche CODE REASONING â€” _jarvis_mode == 'code_reasoning' â†’ qwen3:8b
  â”‚        + single-pass thinking masquÃ© <think>â€¦</think> Â· zÃ©ro injection SOC/PVE
  â”‚
  â””â”€ 5. ðŸ¤– Branche GÃ‰NÃ‰RAL â€” tout le reste â†’ gemma4:latest
           + profil "â—Ž GÃ©nÃ©raliste â€” Gemma4" Â· [NO_SOC]
           + infra Â· quotidien Â· vision (multimodal)
           + sans contexte sÃ©curitÃ©
```

**PrioritÃ©** : Bypass > CODE REASONING > SOC > CODE > GÃ‰NÃ‰RAL  
**RÃ¨gle** : `soc_trigger=True` force phi4:14b. Switch manuel via boutons `SOC / GÃ‰NÃ‰RAL / CODE / CÂ·R` dans l'UI.  
âš  SupprimÃ©s : phi4-reasoning:plus Â· qwen2.5:14b Â· deepseek-r1:14b Â· llava-phi3:latest (2026-05-08) Â· nomic-embed-text (2026-05-10)

### 3.1 Mots-clÃ©s SOC â€” liste exacte

**Outils** : `soc` Â· `monitoring` Â· `crowdsec` Â· `fail2ban` Â· `suricata` Â· `ufw` Â· `waf` Â· `bouncer`  
**IPs** : `bannir` Â· `dÃ©bannir` Â· `ip suspecte` Â· `ip bloquÃ©e` Â· `ip malveillante`  
**Ã‰vÃ©nements** : `menace` Â· `attaque` Â· `hacker` Â· `intrusion` Â· `incident` Â· `exploit` Â· `cve` Â· `rce` Â· `ddos` Â· `brute force` Â· `injection` Â· `scan de port` Â· `comportement suspect`  
**Kill chain** : `kill chain` Â· `recon`  
**Phrases composÃ©es** : `analyse la situation` Â· `Ã©tat soc` Â· `rapport soc` Â· `score menace` Â· `niveau de menace` Â· `sÃ©curitÃ© rÃ©seau` Â· `trafic rÃ©seau` Â· `trafic suspect` Â· `anomalie rÃ©seau` Â· `tentative de connexion` Â· `journal sÃ©curitÃ©` Â· `dÃ©fense rÃ©seau`

> Mots seuls trop gÃ©nÃ©riques **exclus** : `sÃ©curitÃ©`, `trafic`, `score`, `tentative`, `anomalie`, `reconnaissance`, `dÃ©fense` â†’ remplacÃ©s par des phrases composÃ©es.

### 3.2 Continuations GÃ‰NÃ‰RAL reconnues

AprÃ¨s une rÃ©ponse infra/GÃ‰NÃ‰RAL, les confirmations courtes restent sur la branche GÃ‰NÃ‰RAL (gemma4) :
```python
_INFRA_CONFIRM_RE = re.compile(
    r'^\s*(oui|non|ok|vas-y|go|confirme|yes|allez|d.accord|lance|fais.le|applique)\s*[!.]?\s*$', re.I)
```

---

## 4. SÃ©curitÃ© â€” Audit 10/10

### 4.1 Points verts (0 gap â€” 2026-05-06 v2.6)

| Domaine | Mesure |
|---|---|
| Exposition rÃ©seau | `host=127.0.0.1` Â· `debug=False` Â· Windows Firewall bloque LAN |
| CORS | Whitelist stricte : localhost + 192.168.1.50 uniquement |
| Headers HTTP | `X-Frame-Options:DENY` Â· `nosniff` Â· `Server` header supprimÃ© |
| Terminal intÃ©grÃ© | IP check 127.0.0.1/192.168.1.x Â· `shell=False` Â· blacklist destructive |
| SSH tools | 4 hÃ´tes Â· 29 patterns bloquÃ©s `_BLOCKED_SSH` Â· lecture seule + write whitelist |
| Rate limiting | 8 routes gÃ©nÃ©rales + SOC Blueprint 5â€“120/min |
| LLM | Ollama localhost:11434 â€” zÃ©ro cloud |
| RFC1918 | IPs LAN intouchables â€” code ET tous les profils LLM |
| Logs | `tts.log` rotation 50 KBÃ—3 Â· `_SEC_EVENTS` journal sÃ©curitÃ© interne |

### 4.2 Garde-fous non nÃ©gociables

- **RFC1918 intouchable** : aucun LLM ni outil ne peut bannir 192.168.x / 10.x / 172.16-31.x
- **`_ALLOWED_SERVICES`** : restart autorisÃ© uniquement nginx / crowdsec / fail2ban / apache2
- **DonnÃ©es** : zÃ©ro logs bruts, zÃ©ro IPs vers Anthropic â€” rÃ©sumÃ©s structurÃ©s uniquement

### 4.3 _BLOCKED_SSH â€” 29 patterns bloquÃ©s sur les 4 hÃ´tes

```
Suppression/destruction : rm Â· rmdir Â· mkfs Â· dd if= Â· truncate
ArrÃªt systÃ¨me          : shutdown Â· reboot
Services               : systemctl stop Â· systemctl disable
Firewall               : iptables -F
Redirections           : > / Â· | sh Â· | bash Â· curl.*sh | Â· wget.*sh |
Proxmox destructif     : qm destroy Â· qm suspend Â· qm migrate Â· qm set Â· qm create Â· qm clone Â· qm unlock
LXC                    : pct stop Â· pct start Â· pct destroy Â· pvectl
Fichiers systÃ¨me       : tee Â· sed -i Â· chmod Â· chown Â· echo > Â· echo >> Â· > /etc Â· > /var Â· > /opt
DÃ©placement            : mv Â· cp
```

### 4.4 Historique passes d'audit

| Date | Score | Points clÃ©s |
|---|---|---|
| 2026-03-22 | CONFORME | host 0.0.0.0 â†’ 127.0.0.1 |
| 2026-04-11 | 10/10 | Rate limiters SOC Â· Blueprint Â· STT/Vision |
| 2026-04-15 | 10/10 | CSRF Â· `shlex.quote` Â· XSS mixing/main |
| 2026-04-17 | 10/10 | `'use strict'` IIFE Â· `_esc()` Â· `except Exception` typÃ©s |
| 2026-04-18 | 10/10 | 288 onclick â†’ data-action Â· 86 dispatchers |
| 2026-05-03 | 10/10 | NDT 100/100 Â· dette zÃ©ro absolue |
| 2026-05-04 | 10/10 | SSH tools 4 hÃ´tes Â· `_BLOCKED_SSH` Â· fix 500 Ollama |
| 2026-05-05 | 10/10 | STT large-v3-turbo Â· num_ctx adaptatif Â· RAG 599 chunks |
| 2026-05-05 v2.2 | 10/10 | NDT-CSS `_stColor()` Â· `/api/soc/ip-history` Â· historique IP MCP |
| 2026-05-06 v2.5 | 10/10 | NDT-LONG jarvis_mcp_server.py â€” 0 fonction >80L |
| 2026-05-06 v2.6 | 10/10 | NDT-CSS `_vpSetInfo` 2 IIFEs Â· `except OSError` Â· audit complet |
| 2026-05-08 s17  | 10/10 | NDT-MAGIC 14 constantes timeout Â· NDT-ERR 8 catchâ†’warn Â· NDT-CSS impact-bar classList |
| 2026-05-10 s26  | NDT 100/100 | NDT-DUP SSH `_tool_commande_ssh_run()` Â· NDT-HTML-MAGIC Jinja2 `{{ dev_ip }}` Â· NDT-ERR~15 blocs documentÃ©s Â· NDT-DEAD 5 imports/consts supprimÃ©s |
| 2026-05-13 s33  | **89/100** (valeur d'Ã©poque) | Phase 3 split monolithe Python complÃ¨te (30 modules Â· -31% jarvis.py) Â· 25 tests E2E Playwright Â· ESLint 0 errors Â· audit sÃ©curitÃ© 8/10 |
| 2026-05-13 s33c | **92/100** (valeur d'Ã©poque) | Split JS partiel : `recorder.js` + `voice_print.js` extraits Â· `jarvis_main.js` 10507â†’8994L (-14.4%) |
| 2026-05-14       | **78/100 honnÃªte** (recalibrÃ©) | âš  Audit strict : le 91 Ã©tait optimiste, dÃ©part rÃ©el **62/100**. Chantier dette 2026-05-14 (**62â†’78, +16**) : Ruff 98â†’0 (2 bugs F821 rÃ©els corrigÃ©s) + `ruff.toml` Â· **git initialisÃ©** (100% local) Â· **pre-commit hooks bloquants** Â· `jarvis.css` â†’ 8 fichiers CSS Â· `audio_dsp.py` extrait Â· 2 smoke tests LLM Â· **refactor JS partiel** (3 modules : terminal_code/voice_lab/stt) |
| 2026-05-14 soir  | **~82/100 honnÃªte** | **Refactor JS massif** : `jarvis_main.js` 7828â†’**4013 L** (âˆ’49%) Â· **11 modules** extraits dans `static/js/` Â· mÃ©thode byte-identique vÃ©rifiÃ©e (node --check Â· eslint 0 Â· validation E2E prod) Â· 1 rÃ©gression d'ordre dÃ©tectÃ©e+corrigÃ©e |
| 2026-05-15       | **~94/100 honnÃªte** | **Refactor JS terminÃ©** + **Phase 4 tests massifs Ã©tendus** + **Phase 4 finale** : `jarvis_main.js` 4013â†’**148 L** (âˆ’98,1% cumul depuis 7828) Â· 21 modules JS Â· **936 tests pytest** sur **32 modules Â· 25 Ã  100% cov** avec coverage **39% lignes** (tts_engines 83% Â· 42 tests, jarvis_mcp_server 91% Â· 52 tests, ollama_circuit 100% Â· 23 tests, proxmox_api 93%, bypass_backup 96%, voice_lab 71%, deepfilter 84%, ssh_terminal 100%, stt 98%, rag_live 92%, soc.py 33%, jarvis.py 26%, audio_dsp 25%) Â· **fix perf systÃ©mique IPv6** (-97% latence interne via `OLLAMA_URL`/`JARVIS_BASE` â†’ `127.0.0.1`) Â· **circuit breaker Ollama Ã©tendu 8 call-sites** + bouton SOC PING JARVIS enrichi Ã©tat Ollama Â· **prÃ©-warm Kokoro CUDA au boot** (Ã©limine cold start 42.8 s mesurÃ©) Â· **profiling TTS dÃ©taillÃ©** (`tools/profile_tts.py` : mÃ©dianes chaud edge 1453ms / kokoro 203ms / piper 219ms / sapi 563ms) Â· **hook pre-push pytest** Â· 3 bugs prod dÃ©tectÃ©s+fixÃ©s Â· outils `tools/profile_perf.py` + `tools/profile_tts.py` |
| 2026-05-20       | **92/100** (inchangÃ©) | **Correctif structurel pipeline voix** : invariant Â« jamais de source TTS sur AudioContext suspendu Â» (`processQueue`/`playSentence`) â€” supprime gel dÃ©finitif + chevauchement Â· `_splitForTts` (textes > 280 car. dÃ©coupÃ©s aux frontiÃ¨res de phrase â†’ voix en ~1 s vs ~15-24 s) Â· dÃ©verrouillage audio multi-gestes armÃ© tÃ´t Â· **optimisation VRAM** : `_SOC_NUM_CTX`/`DEFAULT_SOC_NUM_CTX` 16384â†’8192 (phi4 ~12.4â†’~11.56 Go), embed `mxbai` dÃ©-Ã©pinglÃ© `keep_alive` -1â†’"10m", prÃ©-warm phi4 en `num_ctx 8192` + dÃ©lai RAG prewarm 20sâ†’5s (VRAM libre ~1.3â†’~2.0-2.8 Go) Â· **instrumentation** `[TTS-PERF]` + log persistant `tts_perf.log` Â· tuile VRAM tri stable Â· phi4:14b conservÃ© comme modÃ¨le SOC (dÃ©cision actÃ©e) |

---

## 5. QualitÃ© logicielle â€” 2 scores distincts

âš  **Distinction critique** :
- **NDT 100/100** = score script automatisÃ© maison (D1/D2/D6/D13 dans le code Python). Mesure fonction longue, silent pass, magic numbers, params >6. Reste vrai au 2026-05-15.
- **Score honnÃªte global** = ce que mesure JARVIS dans son ensemble (Python + JS + tests + CI + perf) â€” valeur courante : [`06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md` Â§0](../06-BILAN-ET-HISTORIQUE/06-01-BILAN-TECHNIQUE.md) (source unique). Audit dette complet honnÃªte 2026-05-22 (9 findings + 1 Ã©cart code/doc corrigÃ©s ; le 92/100 auto-affichÃ© Ã©tait inflatÃ©). Audit 2026-05-23 nuit : **95/100** post refonte documentaire + extension Playwright `api-coverage.spec.js` (14 tests E2E ciblÃ©s sur les 4 Blueprints HTTP sous-couverts en pytest) â€” **plafond pratique atteint** (les ~5 pts manquants sont des dÃ©cisions architecturales assumÃ©es documentÃ©es dans `07-02-DETTE-TECHNIQUE.md`).

### NDT (script automatisÃ©) â€” 100/100

| CatÃ©gorie NDT | Violations | RÃ©solution |
|---|---|---|
| NDT-CSS (style inline extractable) | 0 | `_stColor()` Â· 7 classes st-* Â· classList partout Â· pÃ©rimÃ¨tre 3 fichiers JS |
| NDT-LONG (fonction >80 lignes) | 0 | `_sse_tok()` Â· `_ssh_base()` Â· `list_tools` 2L Â· `call_tool` 13L |
| NDT-ERR (bare except:) | 0 | Tous `except: pass` documentÃ©s (raison commentÃ©e) Â· catÃ©gories : fallback lÃ©gitime Â· API throws by design Â· network poll resilience |
| NDT-DUP (blocs dupliquÃ©s) | 0 | `_sse_tok()` Â· `_tool_commande_ssh_run()` Â· `_clearAfter()` Â· `_TOOLS_DEFS` Â· `_TOOL_HANDLERS` |
| NDT-MAGIC (nombres magiques) | 0 | 14 constantes timeout nommÃ©es `_*_TIMEOUT_S` Â· `_NUM_CTX_*` Â· `_SOC_TEMPERATURE` Â· etc. |
| NDT-DEAD (code mort) | 0 | 74 MB nettoyÃ©s (Piper mort Â· WAV dev Â· logs stale) |
| NDT-LOG (console.log prod) | 0 | |
| NDT-HTML (handler inline) | 0 | data-action Â· data-oninput Â· data-onchange dispatchers |

PÃ©rimÃ¨tre : `jarvis.py` Â· `soc.py` Â· `jarvis_mcp_server.py` Â· `audio_dsp.py` + 30 modules Â· `jarvis_main.js` Â· `static/css/` (8 fichiers)

---

## 6. Architecture multi-agent â€” JARVIS + Claude

### 6.1 Philosophie

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  CLAUDE CODE (Anthropic â€” cloud)                     â”‚
â”‚  Code Â· architecture Â· incidents inconnus            â”‚
â”‚  RÃ¨gle : ne voit que l'escalade structurÃ©e de JARVIS â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                       â”‚ rÃ©sumÃ© structurÃ© (max 5 points)
                       â”‚ jamais de raw data ni IPs brutes
                       â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  JARVIS (local â€” RTX 5080)                           â”‚
â”‚  SOC Â· infra Â· gÃ©nÃ©raliste Â· filtrage                â”‚
â”‚  CoÃ»t : Ã©lectricitÃ© GPU (quasi zÃ©ro)                 â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### 6.2 SÃ©paration des rÃ´les

| JARVIS traite seul | Claude intervient |
|---|---|
| Monitoring SOC Â· bans Â· alertes vocales | Modifier jarvis.py / soc.py / configs nginx |
| Espace disque Â· MAJ Â· Ã©tat services SSH | Incident inconnu / nouveau pattern |
| ArrÃªt/dÃ©marrage VMs (bypass LLM direct) | DÃ©cision architecturale |
| Questions gÃ©nÃ©rales (Gemma4 auto) | Bug non rÃ©solu aprÃ¨s 2 tentatives |

### 6.3 Impact tokens

| ScÃ©nario | Avant | AprÃ¨s |
|---|---|---|
| "Ã‰tat de la menace ?" | ~3 000 tokens (logs bruts) | ~200 tokens (rÃ©sumÃ© JARVIS) |
| Monitoring normal | Claude consultÃ© Ã  chaque poll | 0 token (JARVIS seul) |
| "Espace disque sur pa85 ?" | ~800 tokens | 0 token (gemma4 + SSH tool calling) |
| Question gÃ©nÃ©rale | phi4 polluÃ© SOC | Gemma4 direct (0 contexte sÃ©curitÃ©) |

---

## 7. MCP â€” pont Claude Code â†” JARVIS

### 7.1 Configuration

```json
// .mcp.json â€” racine workspace VSCode
{
  "mcpServers": {
    "jarvis": {
      "command": "pythonw",
      "args": ["C:/Users/mmsab/Documents/0xCyberLiTech/JARVIS/scripts/jarvis_mcp_server.py"]
    }
  }
}
```

`pythonw` : supprime la fenÃªtre console Windows, maintient les pipes stdio MCP.

### 7.2 Les 12 outils MCP

| Outil | Endpoint | RÃ´le |
|---|---|---|
| `jarvis_chat` | POST `/api/chat` SSE | Chat LLM avec routing automatique (4 branches + bypass) |
| `jarvis_soc_status` | GET `/api/soc/context` | Ã‰tat SOC : menace, bans, services |
| `jarvis_stats` | GET `/api/stats` | Uptime, GPU, sessions, TTS/STT |
| `jarvis_soc_ask` | POST `/api/chat` SSE | Question SOC + logs SSH + historique IP 30j |
| `jarvis_infra_status` | POST `/api/chat` SSE | Ã‰tat infra (Proxmox VMs, srv-nginx, clt, pa85) |
| `jarvis_proxmox_vms` | POST `/api/chat` SSE | Ã‰tat VMs Proxmox |
| `jarvis_read_file` | POST `/api/chat` SSE | Lecture fichiers SSH |
| `jarvis_model_switch` | POST `/api/models` | Changement modÃ¨le Ollama actif |
| `jarvis_last_response` | GET `/api/conversation/last` | Derniers Ã©changes de la conversation JARVIS |
| `jarvis_code_exec` | bypass `_code_scp_exec_sse` | Ã‰crit + SCP + exÃ©cute un fichier sur srv-dev-1 |

> DÃ©tail complet des 12 outils : voir [`docs/MCP-SERVER.md`](MCP-SERVER.md).

### 7.3 Injection historique IP dans jarvis_soc_ask

Si IPv4 dÃ©tectÃ©e dans la question â†’ appel `/api/soc/ip-history` (~1.2s) â†’ injection :
```
[HISTORIQUE IP x.x.x.x â€” 30 jours]
CrowdSec : 5 alertes Â· actif maintenant : 1
```
RÃ©sout le cas "IP rÃ©cidiviste dont le ban a expirÃ©" â€” JARVIS recommande le ban plutÃ´t que la surveillance.

### 7.4 Identifiant visuel JARVIS_HEADER

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘  â—ˆ  JARVIS  â€”  phi4:14b  â—ˆ  â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```
Sans ce cadre = rÃ©ponse Claude directe.

### 7.5 Structure jarvis_mcp_server.py

```
jarvis_mcp_server.py (NDT-LONG refactorisÃ© â€” 0 fonction >80L)
â”œâ”€â”€ _TOOLS_DEFS        â† 12 outils dÃ©finis en constante
â”œâ”€â”€ _TOOL_HANDLERS     â† dict nom â†’ handler (dispatch)
â”œâ”€â”€ _RE_IPV4           â† regex dÃ©tection IPv4
â”œâ”€â”€ _collect_sse_tokens()  â† consomme le stream SSE JARVIS
â”œâ”€â”€ _fetch_ip_history(ip)  â† POST /api/soc/ip-history
â”œâ”€â”€ _fetch_soc_context()   â† GET /api/soc/context
â”œâ”€â”€ 10 Ã— _handle_*()   â† un handler par outil
â”œâ”€â”€ list_tools()       â† 2L
â””â”€â”€ call_tool()        â† 13L
```

---

## 8. Outils SSH â€” pÃ©rimÃ¨tre et rÃ¨gles

### 8.1 4 hÃ´tes disponibles

| Outil | HÃ´te | IP | Port | ClÃ© SSH |
|---|---|---|---|---|
| `commande_ssh_nginx` | srv-nginx (VM 108) | 192.168.1.50 | 2272 | `~/.ssh/id_nginx` |
| `commande_ssh_proxmox` | Proxmox VE | 192.168.1.20 | 2272 | `~/.ssh/id_proxmox` |
| `commande_ssh_clt` | clt (VM 106) | 192.168.1.12 | 2272 | `~/.ssh/id_clt` |
| `commande_ssh_pa85` | pa85 (VM 107) | 192.168.1.13 | 2272 | `~/.ssh/id_pa85` |

### 8.2 RÃˆGLES ABSOLUES SSH (profil GÃ‰NÃ‰RAL â€” Gemma4)

| # | RÃ¨gle |
|---|---|
| NÂ°1 | SSH obligatoire AVANT de rÃ©pondre â€” jamais de mÃ©moire, jamais d'estimation |
| NÂ°2 | Valeurs SSH reproduites EXACTES â€” zÃ©ro arrondi, zÃ©ro reformulation des chiffres |
| NÂ°3 | UN seul appel outil par question â€” pas de boucle |
| NÂ°4 | `qm/pvesh/pvesm` exclusifs Ã  l'hÃ´te Proxmox â€” jamais via nginx/clt/pa85 |
| NÂ°5 | `systemctl restart` autorisÃ© pour apache2/nginx/crowdsec/fail2ban + vÃ©rification `is-active` obligatoire aprÃ¨s |

### 8.3 OpÃ©rations autorisÃ©es avec confirmation

```bash
DEBIAN_FRONTEND=noninteractive apt-get update -q && apt-get upgrade -y
# Uniquement aprÃ¨s confirmation explicite : "oui", "go", "applique", "vas-y"
```

---

## 9. IntÃ©grations

### 9.1 Dashboard SOC (monitoring-index.html v3.97.157 â€” 35 tuiles)

| Ã‰lÃ©ment | Description |
|---|---|
| Tuile JARVIS | Grille INFRASTRUCTURE â€” statut, modÃ¨le, compteurs session |
| Auto-engine | Analyse toutes les 60s si JARVIS ONLINE â€” ban auto si >500 req/h |
| TTS SOC | Lecture vocale via `/api/speak` (edge-tts localhost:5000) |
| Quick prompts | 14 prompts rapides dans le panel bas-droite |
| Alertes vocales | Si niveau Ã‰LEVÃ‰ ou CRITIQUE â†’ TTS automatique |

JARVIS reste **optionnel** â€” le SOC dashboard fonctionne Ã  100% sans lui.

### 9.2 Infrastructure rÃ©seau couverte

| HÃ´te | IP | RÃ´le |
|---|---|---|
| srv-nginx (VM 108) | 192.168.1.50 | nginx + CrowdSec WAF + Suricata + fail2ban |
| clt (VM 106) | 192.168.1.12 | Apache Â· site cybersÃ©curitÃ© CLT |
| pa85 (VM 107) | 192.168.1.13 | Apache Â· site associatif PA85 |
| Proxmox VE | 192.168.1.20 | Hyperviseur Â· ZFS 3.5 To |

---

## 10. Roadmap

### Items ouverts (v3.3)

| PrioritÃ© | Item | Gain |
|---|---|---|
| ðŸ”µ | **3.1 Vision active SOC** â€” analyse screenshot SOC | Analyse visuelle |
| ðŸ”µ | **1.2 Wake word** â€” activation vocale sans clic | Vocal hands-free |
| ðŸŸ¡ | **SSH write ops** â€” apt upgrade Â· restart Ã©tendu (validation) | Maintenance automatisÃ©e |

### Items fermÃ©s (ne pas rÃ©-ouvrir)

```
âœ… Routing 3 branches SOC/GÃ‰NÃ‰RAL/CODE + switch  âœ… SSH tools 4 hÃ´tes Â· _BLOCKED_SSH
âœ… VM multi-stop/start bypass LLM                 âœ… MCP 8 outils Â· JARVIS_HEADER
âœ… RAG 599 chunks Â· seuil 0.35 Â· mxbai-embed      âœ… RAG Live SOC (logs SSH temps rÃ©el)
âœ… Vision gemma4 multimodal (remplace llava-phi3) âœ… STT large-v3-turbo + initial_prompt
âœ… ThreatScore 30j historique + tendance           âœ… /api/soc/ip-history + MCP injection
âœ… MÃ©moire inter-sessions + session-end summary    âœ… SSH write ops (RÃˆGLE NÂ°5)
âœ… NDT 10/10 session 17 (MAGICÂ·ERRÂ·CSS rÃ©solus)   âœ… Audit 10/10 (0 gap)
âœ… Mots-clÃ©s SOC affinÃ©s (gÃ©nÃ©riques exclus)      âœ… Sauvegarde JARVIS via chat
âœ… 4 LLM supprimÃ©s (phi4-reasoning:plus/qwen2.5:14b/deepseek-r1:14b/llava-phi3) Â· gemma4 couvre GÃ‰NÃ‰RAL+vision
âœ… nomic-embed-text supprimÃ© (2026-05-10) Â· mxbai-embed-large seul embed actif
```

### Ce qui ne sera pas ajoutÃ©

| FonctionnalitÃ© | Raison |
|---|---|
| AccÃ¨s LAN (0.0.0.0) | DÃ©cision sÃ©curitÃ© â€” loopback strict conservÃ© |
| WebSocket (remplacement poll) | Refonte trop lourde pour le gain |
| Cloud LLM (OpenAI, Groq) | Principe zÃ©ro dÃ©pendance externe |
| Base de donnÃ©es SQL | JSON files suffisent |

---

*REFERENCE-TECHNIQUE.md Â· JARVIS 0xCyberLiTech Â· 2026-05-14 v1.6*

