# JARVIS — Routing automatique des requêtes

Référence technique : comment JARVIS décide quoi faire d'une requête utilisateur.
Tout le routing est dans [`scripts/jarvis.py`](../scripts/jarvis.py) — fonctions `_chat_try_bypass()` et `_chat_resolve_model()`.

---

## Vue d'ensemble — décision en 3 étapes

```
Requête utilisateur (texte ou [VOCAL]…)
    │
    ▼
┌───────────────────────────────────────────────────────────────────┐
│ 1. BYPASS Python (sans LLM)                                       │
│    _chat_try_bypass() · jarvis.py:5536                            │
│                                                                   │
│    Détecte : datetime, backup, VM, reboot, update, service        │
│    restart, file read, code SCP+exec, SSH terminal                │
│    → Réponse SSE directe, ZÉRO appel LLM, latence ~50ms           │
└───────────────────────────────────────────────────────────────────┘
    │ aucun bypass ne matche
    ▼
┌───────────────────────────────────────────────────────────────────┐
│ 2. Routing CODE REASONING (sortie anticipée)                      │
│    Si _jarvis_mode == "code_reasoning" → qwen3:8b streaming       │
│    avec thinking masqué <think>…</think>                          │
└───────────────────────────────────────────────────────────────────┘
    │ pas en mode CR
    ▼
┌───────────────────────────────────────────────────────────────────┐
│ 3. ROUTING MODÈLE selon mode actif                                │
│    _chat_resolve_model() · jarvis.py:5630                         │
│                                                                   │
│    Mode CODE      → qwen2.5-coder:14b  (code + infogérance)       │
│    Mode VOCAL/GEN → gemma4:latest      (conversation fluide)      │
│    Mode SOC       → phi4:14b           (cybersécurité, défaut)    │
└───────────────────────────────────────────────────────────────────┘
```

---

## Les 4 modes JARVIS

| Mode | Modèle Ollama | Trigger | Usage |
|------|--------------|---------|-------|
| **SOC** (défaut) | `phi4:14b` (9.1 GB) | Bouton `#btn-mode-soc` ou `POST /api/mode {mode:"soc"}` | Cybersécurité · monitoring nginx/CrowdSec/fail2ban · contexte SOC live injecté **côté serveur** (system prompt, frais à chaque appel) |
| **GENERAL** | `gemma4:latest` (9.6 GB) | `#btn-mode-general` | Conversation fluide · vision multimodale · pas d'infra/SOC |
| **CODE** | `qwen2.5-coder:14b` (9.0 GB) | `#btn-mode-code` (ouvre aussi le terminal SSH `srv-dev-1`) | Code + infogérance · génération multi-fichiers · SCP+exec sur srv-dev-1 |
| **CODE REASONING** (CR) | `qwen3:8b` (~5 GB) | `#btn-mode-code-reasoning` | Reasoning natif single-pass avec thinking tokens `<think>…</think>` masqués |

⚠ **Règle absolue** : la surveillance SOC (auto-engine, alertes vocales, injection contexte monitoring) est active **uniquement en mode SOC**. Modes GENERAL, CODE et CR n'ont aucune action SOC.

---

## Injection du contexte SOC (mode SOC) — 100 % serveur depuis 2026-05-14

En mode SOC, les données `monitoring.json` (srv-ngix) sont injectées dans le **system prompt** — entièrement côté serveur :

- Chaîne : `_chat_build_system_prompt()` → `chat_system_prompt.build()` → `chat_soc_inject.inject()`.
- Déclenchement : mots-clés SOC (`SOC_KW` / `SOC_VOCAL_KW`) **ou** `force_soc=True` quand `model_override='soc'` (chat du dashboard SOC — chaque message y est une question SOC par nature).
- Injecté dans le system prompt à **chaque appel**, **jamais dans l'historique** → aucun snapshot périmé empilé. Source de formatage unique : `_build_monitoring_context()` (Python).
- L'ancienne incrustation **client-side** (snapshot dans le message utilisateur) a été supprimée — elle empilait des données périmées en multi-tours et causait des hallucinations (IPs/scores fantômes).
- Garde-fou : srv-ngix injoignable → instruction anti-hallucination injectée (« données indisponibles » au lieu d'inventer).

Le contexte expose : IPs déjà bannies CrowdSec, crawlers vérifiés FCrDNS (`verified_bots`), `signal=FORT|faible` par IP Kill Chain (reco de ban proportionnée), horodatage du snapshot cité avec le score.

---

## Étape 1 — BYPASS Python (sans LLM)

Avant tout calcul coûteux, JARVIS détecte 9 catégories de commandes qu'il peut exécuter sans LLM (latence ~50ms vs ~3-30s avec LLM) :

| Détecteur | Pattern reconnu | Action |
|-----------|----------------|--------|
| `_DATETIME_RE` | "quelle heure", "quel jour", "date du jour" | Réponse directe Python `datetime.now()` |
| `_detect_backup_command` | "sauvegarde JARVIS", "backup VM 108" | Lance `backup-jarvis.ps1` ou Proxmox vzdump |
| `_detect_vm_command` | "démarre VM 108", "stoppe pa85" | Proxmox `qm start/stop` (whitelist VMID) |
| `_detect_reboot_command` | "redémarre srv-ngix", "reboot proxmox" | SSH reboot (4 hôtes connus) |
| `_detect_update_command` | "mise à jour srv-ngix", "apt upgrade clt" | SSH `apt update && apt upgrade` |
| `_detect_service_restart` | "redémarre nginx sur srv-ngix" | `systemctl restart <svc>` (whitelist `_ALLOWED_RESTART_SVCS`) |
| `_detect_file_command` | "lis /etc/nginx/nginx.conf sur srv-ngix" | SSH cat fichier |
| `_detect_code_command` | "exec test.py", "scp script.py srv-dev-1" | SCP + exécution sur srv-dev-1 |
| `_SSH_TERMINAL_RE` | "connecte srv-dev-1", "ouvre terminal proxmox" | Ouvre WebSocket SSH terminal xterm.js |

**Particularité vocal** : en mode `[VOCAL]`, seul le bypass datetime est actif. Tout le reste passe par le LLM (gemma4) pour formulation naturelle.

---

## Sécurité — couches de protection

### 1. RFC1918 immuable (mode SOC)

Le system prompt SOC (`jarvis.py:215`) impose :
- IPs RFC1918 (10/8, 172.16/12, 192.168/16) = trafic LAN légitime
- **JAMAIS** signaler une IP RFC1918 comme attaque DDoS / EXPLOIT / menace
- **JAMAIS** recommander de bannir une IP RFC1918 (techniquement bloqué côté CrowdSec aussi)

### 2. `_BLOCKED_SSH` — patterns interdits sur SSH

Liste à `jarvis.py:2483` — ~29 patterns bloqués :
- **Destructif** : `rm`, `rmdir`, `mkfs`, `dd if=`, `shutdown`, `reboot`
- **Service stop** : `systemctl stop`, `systemctl disable`
- **Network** : `iptables -F`
- **Fichiers système** : `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, `/etc/ssh/sshd_config`, `/etc/fstab`, `/etc/crontab`, etc. (lecture OK, modif bloquée)
- **Proxmox destructif** : `qm destroy`, `qm suspend`, `qm migrate`, `qm set`, `qm create`, `qm clone`, `qm unlock`, `pct stop/start/destroy`, `pvectl`
- **Édition shell** : `tee`, `sed -i`, `chmod`, `chown`, `echo >`, `truncate`, `mv`, `cp`, `> /etc`, `> /var`, `> /opt`
- **Éditeurs interactifs** : bloquent le process SSH

### 3. Whitelists strictes (write ops permises)

| Whitelist | Contenu | Usage |
|-----------|---------|-------|
| `_ALLOWED_RESTART_SVCS` (jarvis.py:2506) | nginx · fail2ban · crowdsec · bouncer · suricata · apache2 · php-fpm | Seuls ces services peuvent être redémarrés via `systemctl restart` |
| `_ALLOWED_APT_PKGS` (jarvis.py:2510) | nginx · fail2ban · crowdsec · suricata · openssl · python3 · certbot | Seuls ces paquets peuvent être mis à jour via `apt install/upgrade` |
| `_SSH_TERMINAL_MAP` (jarvis.py:5072) | dev1 (srv-dev-1) · proxmox · srv-ngix · clt · pa85 | Hôtes SSH autorisés (clés `~/.ssh/id_*` correspondantes) |

### 4. CODE = exclusivement srv-dev-1

`_CODE_DEV_IP = "192.168.1.21"` (jarvis.py:5065) — toute opération SCP+exec en mode CODE cible **uniquement** srv-dev-1, port 2272, clé `~/.ssh/id_dev1`. Aucun autre hôte n'est atteignable depuis le mode CODE.

---

## Tests E2E — couverture du routing

Validation automatisée (`tests/e2e/`) :
- `api.spec.js` × 3 : `/api/mode` GET + cycle POST (REST direct)
- `mode-ui.spec.js` × 1 : clic boutons mode → propagation UI ↔ backend (chaîne complète)

→ `npm test` (JARVIS doit être up sur :5000) — voir [README.md](../README.md#qualité--tests--linters).

---

## Références code

⚠ Les patterns/whitelists sécurité ont été extraits dans `security_whitelists.py` (Phase 3, session 33). Les détecteurs SSH/VM/backup et leurs générateurs SSE restent dans `jarvis.py` (couplage paramiko/Proxmox API).

| Symbole | Fichier:ligne | Rôle |
|---------|--------------|------|
| `_chat_try_bypass()` | `jarvis.py:~5100` | Détection bypass Python |
| `_chat_resolve_model()` | `jarvis.py:~5200` | Routing modèle selon mode |
| `_chat_build_system_prompt()` | `jarvis.py:~5180` | Construction system prompt + RAG + web + SOC/PVE |
| `BLOCKED_SSH_PATTERNS` | `security_whitelists.py:25` | Liste patterns SSH interdits (29 patterns) |
| `ALLOWED_RESTART_SVCS` | `security_whitelists.py:60` | Whitelist services restart |
| `ALLOWED_APT_PKGS` | `security_whitelists.py:65` | Whitelist paquets apt |
| `check_write_op()` | `security_whitelists.py:72` | Validation écriture sur whitelist |
| `DATETIME_RE` + `datetime_sse()` | `bypass_simple.py` | Bypass datetime (zéro IO) |
| `_GENERAL_MODEL` / `_CODE_MODEL` / `_CODE_REASONING_ANALYSIS_MODEL` | `jarvis.py:~2190` | Modèles Ollama par mode |
| `_jarvis_mode` (variable globale) | `jarvis.py:~3000` | Mode actif (modifié par POST `/api/mode`) |

---

## Modules Python extraits — Phase 3 (session 33b) + chantier dette (2026-05-14)

Le monolithe `jarvis.py` a été allégé : **modules dédiés** extraits → `jarvis.py` 6592 → **4814 lignes**.

⚠ **Note honnête** : score dette technique global = **88/100** (pas 100 — audit dette complet honnête 2026-05-22). Refactor JS terminé (`jarvis_main.js` 7828→**148 L** −98,1%, 18 modules JS) + **959 tests pytest** (0 skip) sur **35 modules · 22 à 100% cov** avec **coverage 52% lignes** + fix perf IPv6 (-97% latence interne) + circuit breaker Ollama 8 call-sites + pré-warm Kokoro CUDA. Plafond pratique sans CI cloud atteint. Pour 95+ : couverture jarvis.py / soc.py Flask routes (faible ROI) ou CI cloud (impossible « rien sur le web »).

### Audio/Voice (5)
| Module | Lignes | Rôle |
|--------|--------|------|
| [`stt.py`](../scripts/stt.py) | 97 | Whisper large-v3-turbo + initial_prompt SOC |
| [`voice_lab.py`](../scripts/voice_lab.py) | 167 | Analyse acoustique librosa + voice prints |
| [`tts_engines.py`](../scripts/tts_engines.py) | 280 | 4 engines TTS (Kokoro/Piper/SAPI5/edge-tts) |
| [`deepfilter.py`](../scripts/deepfilter.py) | 132 | DeepFilterNet CUDA débruitage IA |
| [`vision.py`](../scripts/vision.py) | 100 | Analyse image gemma4 multimodal |

### Bypass commands (8)
| Module | Lignes | Rôle |
|--------|--------|------|
| [`bypass_simple.py`](../scripts/bypass_simple.py) | 38 | Bypass datetime (zéro LLM) |
| [`security_whitelists.py`](../scripts/security_whitelists.py) | 105 | BLOCKED_SSH + whitelists + check_write_op |
| [`bypass_filesystem.py`](../scripts/bypass_filesystem.py) | 175 | Lecture fichiers SSH |
| [`bypass_proxmox.py`](../scripts/bypass_proxmox.py) | 195 | Détection VM/reboot/update |
| [`bypass_backup.py`](../scripts/bypass_backup.py) | 215 | Backups PowerShell + parser |
| [`bypass_code.py`](../scripts/bypass_code.py) | 165 | SCP+exec srv-dev-1 |
| [`ssh_terminal.py`](../scripts/ssh_terminal.py) | 75 | WebSocket PTY 5 hôtes |
| [`proxmox_api.py`](../scripts/proxmox_api.py) | 195 | REST Proxmox cache 30s |

### Infra / RAG (2)
| Module | Lignes | Rôle |
|--------|--------|------|
| [`rag_live.py`](../scripts/rag_live.py) | 100 | Cache logs SOC SSH (Suricata + CrowdSec + fail2ban + nginx) |
| [`sse_helpers.py`](../scripts/sse_helpers.py) | 35 | Utilitaires SSE Flask |

### Chat/LLM core (15)
| Module | Lignes | Rôle |
|--------|--------|------|
| [`chat_routing.py`](../scripts/chat_routing.py) | 50 | Routing modèle Ollama |
| [`tts_cleaner.py`](../scripts/tts_cleaner.py) | 100 | Markdown→TTS + IPs |
| [`chat_messages.py`](../scripts/chat_messages.py) | 50 | Build messages Ollama |
| [`tts_dedup.py`](../scripts/tts_dedup.py) | 45 | Dedup global TTS |
| [`chat_capture.py`](../scripts/chat_capture.py) | 45 | Wrapper SSE accumulation |
| [`chat_system_prompt.py`](../scripts/chat_system_prompt.py) | 50 | Orchestrateur system prompt |
| [`chat_soc_inject.py`](../scripts/chat_soc_inject.py) | 125 | Injection SOC server-side (system prompt) · 2 listes keywords · `force_soc` · garde-fou srv-ngix injoignable |
| [`code_reasoning.py`](../scripts/code_reasoning.py) | 175 | Pipeline qwen3:8b CR (thinking parsing) |
| [`llm_opts.py`](../scripts/llm_opts.py) | 65 | Construction options Ollama |
| [`stream_tokens.py`](../scripts/stream_tokens.py) | 65 | Stream + découpage TTS |
| [`deferred_speak.py`](../scripts/deferred_speak.py) | 35 | Flush TTS différé |
| [`chat_pending_bypass.py`](../scripts/chat_pending_bypass.py) | 75 | Confirme apt/reboot différé |
| [`chat_tool_calls.py`](../scripts/chat_tool_calls.py) | 90 | Boucle tool-calling |
| [`chat_stream.py`](../scripts/chat_stream.py) | 45 | Orchestrateur stream |
| [`chat_generate.py`](../scripts/chat_generate.py) | 60 | Top-level wrapper avec error handling |

**Total Python : 31 modules extraits** (Phase 3 : 30 modules ~3034L · session 33b) + `audio_dsp.py` 508L (chantier dette 2026-05-14) → `jarvis.py` 4814L
**Session 33c — Split JS partiel** : `recorder.js` 660L + `voice_print.js` 852L extraits en IIFE
**Chantier dette 2026-05-14** : Ruff 98→0 + `ruff.toml` · git initialisé (100% local, aucun remote) · pre-commit hooks bloquants · `jarvis.css` 5270L → 8 fichiers CSS · `audio_dsp.py` extrait · 2 smoke tests LLM · refactor JS partiel (3 modules : terminal_code/voice_lab/stt)
**Session 2026-05-14 (soir)** : injection SOC 100 % serveur (suppression incrustation client-side `_monCtxStr`/`_buildChatPayload` → fin des hallucinations) · `force_soc` threadé en DI · règle crawlers légitimes + reco de ban proportionnée au signal · garde-fou srv-ngix injoignable
**Refactor JS 2026-05-14/15 (TERMINÉ)** : `jarvis_main.js` **7828→148 L (−98,1% cumul)** · **21 modules JS** (15 dans `static/js/` + 6 historiques). Méthode byte-identique vérifiée (bodies identiques · `node --check` · eslint 0 · validation E2E prod à chaque étape). ⚠ `audio_viz.js` chargé juste après `jarvis_main.js` (définit `_SAMPLE_RATE`, requis au top-level par `recorder.js`). ⚠ `chat_ui.js` AVANT `chat_core.js` (chat_core utilise `addMessage`/`history`/`_esc`). ⚠ `soc_tab.js` AVANT `chat_core.js` (chat_core utilise `_buildChatPayload`).

**Score dette technique HONNÊTE 88/100** (audit dette complet 2026-05-22 · 959 tests pytest · 0 skip · 22 modules à 100% cov · coverage 52% lignes · refactor JS terminé · fix perf IPv6 · circuit breaker Ollama 8 call-sites · pré-warm Kokoro CUDA · hook pre-push pytest)
