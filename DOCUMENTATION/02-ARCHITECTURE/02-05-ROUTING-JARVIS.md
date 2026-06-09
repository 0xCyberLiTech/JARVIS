---
title: "Routing JARVIS â€” 4 modes + bypass Python + sÃ©curitÃ©"
code: "JARVIS-DOC-02-05"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "Architecture"
mots_cles: ["routing", "modes", "bypass", "securite", "rfc1918"]
---

# JARVIS â€” Routing automatique des requÃªtes

RÃ©fÃ©rence technique : comment JARVIS dÃ©cide quoi faire d'une requÃªte utilisateur.
Tout le routing est dans [`scripts/jarvis.py`](../scripts/jarvis.py) â€” fonctions `_chat_try_bypass()` et `_chat_resolve_model()`.

---

## Vue d'ensemble â€” dÃ©cision en 3 Ã©tapes

```
RequÃªte utilisateur (texte ou [VOCAL]â€¦)
    â”‚
    â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ 1. BYPASS Python (sans LLM)                                       â”‚
â”‚    _chat_try_bypass() Â· jarvis.py:5536                            â”‚
â”‚                                                                   â”‚
â”‚    DÃ©tecte : datetime, backup, VM, reboot, update, service        â”‚
â”‚    restart, file read, code SCP+exec, SSH terminal                â”‚
â”‚    â†’ RÃ©ponse SSE directe, ZÃ‰RO appel LLM, latence ~50ms           â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
    â”‚ aucun bypass ne matche
    â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ 2. Routing CODE REASONING (sortie anticipÃ©e)                      â”‚
â”‚    Si _jarvis_mode == "code_reasoning" â†’ qwen3:8b streaming       â”‚
â”‚    avec thinking masquÃ© <think>â€¦</think>                          â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
    â”‚ pas en mode CR
    â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ 3. ROUTING MODÃˆLE selon mode actif                                â”‚
â”‚    _chat_resolve_model() Â· jarvis.py:5630                         â”‚
â”‚                                                                   â”‚
â”‚    Mode CODE      â†’ qwen2.5-coder:14b  (code + infogÃ©rance)       â”‚
â”‚    Mode VOCAL/GEN â†’ gemma4:latest      (conversation fluide)      â”‚
â”‚    Mode SOC       â†’ phi4:14b           (cybersÃ©curitÃ©, dÃ©faut)    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## Les 4 modes JARVIS

| Mode | ModÃ¨le Ollama | Trigger | Usage |
|------|--------------|---------|-------|
| **SOC** (dÃ©faut) | `phi4:14b` (9.1 GB) | Bouton `#btn-mode-soc` ou `POST /api/mode {mode:"soc"}` | CybersÃ©curitÃ© Â· monitoring nginx/CrowdSec/fail2ban Â· contexte SOC live injectÃ© **cÃ´tÃ© serveur** (system prompt, frais Ã  chaque appel) |
| **GENERAL** | `gemma4:latest` (9.6 GB) | `#btn-mode-general` | Conversation fluide Â· vision multimodale Â· pas d'infra/SOC |
| **CODE** | `qwen2.5-coder:14b` (9.0 GB) | `#btn-mode-code` (ouvre aussi le terminal SSH `srv-dev-1`) | Code + infogÃ©rance Â· gÃ©nÃ©ration multi-fichiers Â· SCP+exec sur srv-dev-1 |
| **CODE REASONING** (CR) | `qwen3:8b` (~5 GB) | `#btn-mode-code-reasoning` | Reasoning natif single-pass avec thinking tokens `<think>â€¦</think>` masquÃ©s |

âš  **RÃ¨gle absolue** : la surveillance SOC (auto-engine, alertes vocales, injection contexte monitoring) est active **uniquement en mode SOC**. Modes GENERAL, CODE et CR n'ont aucune action SOC.

---

## Injection du contexte SOC (mode SOC) â€” 100 % serveur depuis 2026-05-14

En mode SOC, les donnÃ©es `monitoring.json` (srv-nginx) sont injectÃ©es dans le **system prompt** â€” entiÃ¨rement cÃ´tÃ© serveur :

- ChaÃ®ne : `_chat_build_system_prompt()` â†’ `chat_system_prompt.build()` â†’ `chat_soc_inject.inject()`.
- DÃ©clenchement : mots-clÃ©s SOC (`SOC_KW` / `SOC_VOCAL_KW`) **ou** `force_soc=True` quand `model_override='soc'` (chat du dashboard SOC â€” chaque message y est une question SOC par nature).
- InjectÃ© dans le system prompt Ã  **chaque appel**, **jamais dans l'historique** â†’ aucun snapshot pÃ©rimÃ© empilÃ©. Source de formatage unique : `_build_monitoring_context()` (Python).
- L'ancienne incrustation **client-side** (snapshot dans le message utilisateur) a Ã©tÃ© supprimÃ©e â€” elle empilait des donnÃ©es pÃ©rimÃ©es en multi-tours et causait des hallucinations (IPs/scores fantÃ´mes).
- Garde-fou : srv-nginx injoignable â†’ instruction anti-hallucination injectÃ©e (Â« donnÃ©es indisponibles Â» au lieu d'inventer).

Le contexte expose : IPs dÃ©jÃ  bannies CrowdSec, crawlers vÃ©rifiÃ©s FCrDNS (`verified_bots`), `signal=FORT|faible` par IP Kill Chain (reco de ban proportionnÃ©e), horodatage du snapshot citÃ© avec le score.

---

## Ã‰tape 1 â€” BYPASS Python (sans LLM)

Avant tout calcul coÃ»teux, JARVIS dÃ©tecte 10 catÃ©gories de commandes qu'il peut exÃ©cuter sans LLM (latence ~50ms vs ~3-30s avec LLM) :

| DÃ©tecteur | Pattern reconnu | Action |
|-----------|----------------|--------|
| `_DATETIME_RE` | "quelle heure", "quel jour", "date du jour" | RÃ©ponse directe Python `datetime.now()` |
| `_detect_backup_command` | "sauvegarde JARVIS", "backup VM 108" | Lance `backup-jarvis.ps1` ou Proxmox vzdump |
| `_detect_vm_command` | "dÃ©marre VM 108", "stoppe pa85" | Proxmox `qm start/stop` (whitelist VMID) |
| `_detect_reboot_command` | "redÃ©marre srv-nginx", "reboot proxmox" | Reboot **confirmation 2 tours** ; pve = refus (â†’ menu). Cf. P0 2026-05-31 |
| `_detect_update_command` | "mise Ã  jour srv-nginx", "apt upgrade clt" | SSH `apt update && apt upgrade` |
| `detect_routine_postmaj_command` | "routine post-maj clt", "routine post-maj srv-nginx" | **LECTURE-SEULE** : probe smoke/health-audit + compte les MAJ apt (`apt list --upgradable`, read-only, sans `apt-get update`) â†’ verdict explicite **santÃ© + N MAJ** (affichage : 1 ligne âœ“ par section + verdict final), **renvoie au menu** (n'exÃ©cute PAS). MÃªme logique que le menu. `bypass/proxmox.py` + `bypass/wrappers.py` (P5 2026-05-31) |
| `_detect_service_restart` | "redÃ©marre nginx sur srv-nginx" | `systemctl restart <svc>` (whitelist `_ALLOWED_RESTART_SVCS`) |
| `_detect_file_command` | "lis /etc/nginx/nginx.conf sur srv-nginx" | SSH cat fichier |
| `_detect_code_command` | "exec test.py", "scp script.py srv-dev-1" | SCP + exÃ©cution sur srv-dev-1 |
| `_SSH_TERMINAL_RE` | "connecte srv-dev-1", "ouvre terminal proxmox" | Ouvre WebSocket SSH terminal xterm.js |

**ParticularitÃ© vocal** : en mode `[VOCAL]`, seuls le bypass **datetime** et la **routine post-MAJ (lecture-seule)** sont actifs â€” tous deux placÃ©s AVANT le gate `if is_vocal: return None` dans `chat/dispatcher.py::chat_try_bypass`. Tout le reste (backup/VM/reboot/update/service) passe par le LLM (gemma4) en vocal. La routine post-MAJ est vocal-safe car **read-only + FAIL-CLOSED** : hÃ´te ambigu â†’ demande de prÃ©ciser (jamais d'action), pve â†’ renvoi vers le menu Proxmox (zÃ©ro SSH). JARVIS lit le verdict ; **le menu reste le seul exÃ©cuteur** (apt/reboot/rebaseline via l'option `[m]` des modules host).

---

## SÃ©curitÃ© â€” couches de protection

### 1. RFC1918 immuable (mode SOC)

Le system prompt SOC (`jarvis.py:215`) impose :
- IPs RFC1918 (10/8, 172.16/12, 192.168/16) = trafic LAN lÃ©gitime
- **JAMAIS** signaler une IP RFC1918 comme attaque DDoS / EXPLOIT / menace
- **JAMAIS** recommander de bannir une IP RFC1918 (techniquement bloquÃ© cÃ´tÃ© CrowdSec aussi)

### 2. `_BLOCKED_SSH` â€” patterns interdits sur SSH

Liste Ã  `jarvis.py:2483` â€” ~29 patterns bloquÃ©s :
- **Destructif** : `rm`, `rmdir`, `mkfs`, `dd if=`, `shutdown`, `reboot`
- **Service stop** : `systemctl stop`, `systemctl disable`
- **Network** : `iptables -F`
- **Fichiers systÃ¨me** : `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/etc/ssh/sshd_config`, `/etc/fstab`, `/etc/crontab`, etc. (lecture OK, modif bloquÃ©e)
- **Proxmox destructif** : `qm destroy`, `qm suspend`, `qm migrate`, `qm set`, `qm create`, `qm clone`, `qm unlock`, `pct stop/start/destroy`, `pvectl`
- **Ã‰dition shell** : `tee`, `sed -i`, `chmod`, `chown`, `echo >`, `truncate`, `mv`, `cp`, `> /etc`, `> /var`, `> /opt`
- **Ã‰diteurs interactifs** : bloquent le process SSH

### 3. Whitelists strictes (write ops permises)

| Whitelist | Contenu | Usage |
|-----------|---------|-------|
| `_ALLOWED_RESTART_SVCS` (jarvis.py:2506) | nginx Â· fail2ban Â· crowdsec Â· bouncer Â· suricata Â· apache2 Â· php-fpm | Seuls ces services peuvent Ãªtre redÃ©marrÃ©s via `systemctl restart` |
| `_ALLOWED_APT_PKGS` (jarvis.py:2510) | nginx Â· fail2ban Â· crowdsec Â· suricata Â· openssl Â· python3 Â· certbot | Seuls ces paquets peuvent Ãªtre mis Ã  jour via `apt install/upgrade` |
| `_SSH_TERMINAL_MAP` (jarvis.py:5072) | dev1 (srv-dev-1) Â· proxmox Â· srv-nginx Â· clt Â· pa85 | HÃ´tes SSH autorisÃ©s (clÃ©s `~/.ssh/id_*` correspondantes) |

### 4. CODE = exclusivement srv-dev-1

`_CODE_DEV_IP = "192.168.1.21"` (jarvis.py:5065) â€” toute opÃ©ration SCP+exec en mode CODE cible **uniquement** srv-dev-1, port 2272, clÃ© `~/.ssh/id_dev1`. Aucun autre hÃ´te n'est atteignable depuis le mode CODE.

---

## Tests E2E â€” couverture du routing

Validation automatisÃ©e (`tests/e2e/`) :
- `api.spec.js` Ã— 3 : `/api/mode` GET + cycle POST (REST direct)
- `mode-ui.spec.js` Ã— 1 : clic boutons mode â†’ propagation UI â†” backend (chaÃ®ne complÃ¨te)

â†’ `npm test` (JARVIS doit Ãªtre up sur :5000) â€” voir [README.md](../README.md#qualitÃ©--tests--linters).

---

## RÃ©fÃ©rences code

âš  Les patterns/whitelists sÃ©curitÃ© ont Ã©tÃ© extraits dans `security_whitelists.py` (Phase 3, session 33). Les dÃ©tecteurs SSH/VM/backup et leurs gÃ©nÃ©rateurs SSE restent dans `jarvis.py` (couplage paramiko/Proxmox API).

| Symbole | Fichier:ligne | RÃ´le |
|---------|--------------|------|
| `_chat_try_bypass()` | `jarvis.py:~5100` | DÃ©tection bypass Python |
| `_chat_resolve_model()` | `jarvis.py:~5200` | Routing modÃ¨le selon mode |
| `_chat_build_system_prompt()` | `jarvis.py:~5180` | Construction system prompt + RAG + web + SOC/PVE |
| `BLOCKED_SSH_PATTERNS` | `security_whitelists.py:25` | Liste patterns SSH interdits (29 patterns) |
| `ALLOWED_RESTART_SVCS` | `security_whitelists.py:60` | Whitelist services restart |
| `ALLOWED_APT_PKGS` | `security_whitelists.py:65` | Whitelist paquets apt |
| `check_write_op()` | `security_whitelists.py:72` | Validation Ã©criture sur whitelist |
| `DATETIME_RE` + `datetime_sse()` | `bypass_simple.py` | Bypass datetime (zÃ©ro IO) |
| `_GENERAL_MODEL` / `_CODE_MODEL` / `_CODE_REASONING_ANALYSIS_MODEL` | `jarvis.py:~2190` | ModÃ¨les Ollama par mode |
| `_jarvis_mode` (variable globale) | `jarvis.py:~3000` | Mode actif (modifiÃ© par POST `/api/mode`) |

---

## Modules Python extraits â€” Phase 3 (session 33b) + chantier dette (2026-05-14)

Le monolithe `jarvis.py` a Ã©tÃ© allÃ©gÃ© : **modules dÃ©diÃ©s** extraits (ex-monolithe 6592 lignes).

âš  **Note honnÃªte** : refactor JS terminÃ© (âˆ’98,1%, 18 modules JS) Â· suite pytest Â· fix perf IPv6 (-97% latence interne) Â· circuit breaker Ollama 8 call-sites Â· prÃ©-warm Kokoro CUDA. Score dette, lignes, tests, coverage â†’ source unique [`BILAN-TECHNIQUE.md` Â§0](../BILAN-TECHNIQUE.md). Plafond pratique sans CI cloud atteint â€” pour 95+ : couverture des routes Flask (faible ROI) ou CI cloud (impossible Â« rien sur le web Â»).

### Audio/Voice (5)
| Module | Lignes | RÃ´le |
|--------|--------|------|
| [`stt.py`](../scripts/stt.py) | 97 | Whisper large-v3-turbo + initial_prompt SOC |
| [`voice_lab.py`](../scripts/voice_lab.py) | 167 | Analyse acoustique librosa + voice prints |
| [`tts_engines.py`](../scripts/tts_engines.py) | 280 | 4 engines TTS (Kokoro/Piper/SAPI5/edge-tts) |
| [`deepfilter.py`](../scripts/deepfilter.py) | 132 | DeepFilterNet CUDA dÃ©bruitage IA |
| [`vision.py`](../scripts/vision.py) | 100 | Analyse image gemma4 multimodal |

### Bypass commands (8)
| Module | Lignes | RÃ´le |
|--------|--------|------|
| [`bypass_simple.py`](../scripts/bypass_simple.py) | 38 | Bypass datetime (zÃ©ro LLM) |
| [`security_whitelists.py`](../scripts/security_whitelists.py) | 105 | BLOCKED_SSH + whitelists + check_write_op |
| [`bypass_filesystem.py`](../scripts/bypass_filesystem.py) | 175 | Lecture fichiers SSH |
| [`bypass_proxmox.py`](../scripts/bypass_proxmox.py) | 195 | DÃ©tection VM/reboot/update |
| [`bypass_backup.py`](../scripts/bypass_backup.py) | 215 | Backups PowerShell + parser |
| [`bypass_code.py`](../scripts/bypass_code.py) | 165 | SCP+exec srv-dev-1 |
| [`ssh_terminal.py`](../scripts/ssh_terminal.py) | 75 | WebSocket PTY 5 hÃ´tes |
| [`proxmox_api.py`](../scripts/proxmox_api.py) | 195 | REST Proxmox cache 30s |

### Infra / RAG (2)
| Module | Lignes | RÃ´le |
|--------|--------|------|
| [`rag_live.py`](../scripts/rag_live.py) | 100 | Cache logs SOC SSH (Suricata + CrowdSec + fail2ban + nginx) |
| [`sse_helpers.py`](../scripts/sse_helpers.py) | 35 | Utilitaires SSE Flask |

### Chat/LLM core (15)
| Module | Lignes | RÃ´le |
|--------|--------|------|
| [`chat_routing.py`](../scripts/chat_routing.py) | 50 | Routing modÃ¨le Ollama |
| [`tts_cleaner.py`](../scripts/tts_cleaner.py) | 100 | Markdownâ†’TTS + IPs |
| [`chat_messages.py`](../scripts/chat_messages.py) | 50 | Build messages Ollama |
| [`tts_dedup.py`](../scripts/tts_dedup.py) | 45 | Dedup global TTS |
| [`chat_capture.py`](../scripts/chat_capture.py) | 45 | Wrapper SSE accumulation |
| [`chat_system_prompt.py`](../scripts/chat_system_prompt.py) | 50 | Orchestrateur system prompt |
| [`chat_soc_inject.py`](../scripts/chat_soc_inject.py) | 125 | Injection SOC server-side (system prompt) Â· 2 listes keywords Â· `force_soc` Â· garde-fou srv-nginx injoignable |
| [`code_reasoning.py`](../scripts/code_reasoning.py) | 175 | Pipeline qwen3:8b CR (thinking parsing) |
| [`llm_opts.py`](../scripts/llm_opts.py) | 65 | Construction options Ollama |
| [`stream_tokens.py`](../scripts/stream_tokens.py) | 65 | Stream + dÃ©coupage TTS |
| [`deferred_speak.py`](../scripts/deferred_speak.py) | 35 | Flush TTS diffÃ©rÃ© |
| [`chat_pending_bypass.py`](../scripts/chat_pending_bypass.py) | 75 | Confirme apt/reboot diffÃ©rÃ© |
| [`chat_tool_calls.py`](../scripts/chat_tool_calls.py) | 90 | Boucle tool-calling |
| [`chat_stream.py`](../scripts/chat_stream.py) | 45 | Orchestrateur stream |
| [`chat_generate.py`](../scripts/chat_generate.py) | 60 | Top-level wrapper avec error handling |

**Total Python : 31 modules extraits** (Phase 3 : 30 modules Â· session 33b) + `audio_dsp.py` (chantier dette 2026-05-14) â†’ `jarvis.py` allÃ©gÃ©
**Session 33c â€” Split JS partiel** : `recorder.js` 660L + `voice_print.js` 852L extraits en IIFE
**Chantier dette 2026-05-14** : Ruff 98â†’0 + `ruff.toml` Â· git initialisÃ© (100% local, aucun remote) Â· pre-commit hooks bloquants Â· `jarvis.css` 5270L â†’ 8 fichiers CSS Â· `audio_dsp.py` extrait Â· 2 smoke tests LLM Â· refactor JS partiel (3 modules : terminal_code/voice_lab/stt)
**Session 2026-05-14 (soir)** : injection SOC 100 % serveur (suppression incrustation client-side `_monCtxStr`/`_buildChatPayload` â†’ fin des hallucinations) Â· `force_soc` threadÃ© en DI Â· rÃ¨gle crawlers lÃ©gitimes + reco de ban proportionnÃ©e au signal Â· garde-fou srv-nginx injoignable
**Refactor JS (TERMINÃ‰)** : `jarvis_main.js` rÃ©duit de **âˆ’98,1%** Â· **21 modules JS** (15 dans `static/js/` + 6 historiques). MÃ©thode byte-identique vÃ©rifiÃ©e (bodies identiques Â· `node --check` Â· eslint 0 Â· validation E2E prod Ã  chaque Ã©tape). âš  `audio_viz.js` chargÃ© juste aprÃ¨s `jarvis_main.js` (dÃ©finit `_SAMPLE_RATE`, requis au top-level par `recorder.js`). âš  `chat_ui.js` AVANT `chat_core.js` (chat_core utilise `addMessage`/`history`/`_esc`). âš  `soc_tab.js` AVANT `chat_core.js` (chat_core utilise `_buildChatPayload`).

**Score dette, tests, coverage â†’ source unique [`BILAN-TECHNIQUE.md` Â§0](../BILAN-TECHNIQUE.md)** Â· audit dette complet 2026-05-22 Â· refactor JS terminÃ© Â· fix perf IPv6 Â· circuit breaker Ollama 8 call-sites Â· prÃ©-warm Kokoro CUDA Â· hook pre-push pytest.

