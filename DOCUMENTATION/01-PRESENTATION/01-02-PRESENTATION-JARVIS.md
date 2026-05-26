---
title: "Présentation détaillée — JARVIS SOC Platform"
code: "JARVIS-DOC-01-02"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "Présentation"
mots_cles: ["jarvis", "soc", "presentation", "platform", "homelab"]
---

# JARVIS SOC PLATFORM — Architecture IA & Cybersécurité Homelab
### Agent autonome local · Surveillance proactive · Contrôle d'infrastructure · LLM on-premise
<!-- 0xCyberLiTech · v3.3 · 2026-05-22 — routing 4 branches · phi4:14b + qwen3:8b CR + gemma4 + qwen2.5-coder + mxbai-embed · 25 tests E2E Playwright · ESLint 0 · MCP **12 outils** · 32 modules Python · refactor JS terminé · fix perf IPv6 · circuit breaker Ollama 8 call-sites · pré-warm Kokoro CUDA · SSH write ops 4 couches + audit log forensic · Ollama 0.24.0 · métriques courantes (score, lignes, tests, coverage) → BILAN-TECHNIQUE.md §0 -->

---

## 1. Vision

Homelab cybersécurité personnel construit autour d'un agent IA local (JARVIS) qui surveille, détecte et agit en autonomie sur l'infrastructure. Architecture hybride : poste Windows 11 avec GPU RTX 5080 + VMs Linux sur Proxmox. Zéro cloud pour les données sensibles — LLM, TTS, STT, détection menaces : tout est on-premise.

Le système repose sur deux niveaux d'intelligence complémentaires :

**Philosophie opérationnelle — deux niveaux d'intelligence :**

```
┌──────────────────────────────────────────────────────────────────────┐
│  JARVIS — agent local autonome (phi4:14b)                            │
│                                                                      │
│  Surveille · Détecte · Agit · Alerte — sans être sollicité          │
│                                                                      │
│  ├─ Monitoring SOC 24/7 (poll 30s)                                   │
│  ├─ Détection menaces : score, kill chain, EXPLOIT non bloqué        │
│  ├─ Actions proactives : ban auto >500 req/h · restart si service down│
│  ├─ Alertes vocales TTS sur niveau ÉLEVÉ / CRITIQUE                  │
│  ├─ Réponses SOC immédiates : score, IPs bannies, services           │
│  ├─ Infra SSH : disque, CPU, logs, services sur 4 hôtes              │
│  └─ Contrôle VMs Proxmox : start/stop sans LLM (SSH direct 2-3s)    │
│                                                                      │
│  CLAUDE — escalade uniquement (via MCP)                              │
│                                                                      │
│  ├─ Incidents nouveaux ou inconnus                                    │
│  ├─ Modifications de code (jarvis.py, soc.py, dashboard)             │
│  ├─ Décisions architecturales et refactoring                         │
│  └─ Debugging complexe multi-composants                              │
│                                                                      │
│  Règle : JARVIS filtre et agrège en local → Claude reçoit            │
│  uniquement l'escalade structurée. Zéro IP brute, zéro log raw       │
│  vers Anthropic.                                                     │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. Infrastructure

### 2.1 Réseau LAN

| Hôte | IP | Rôle | Clé SSH / Port |
|------|----|------|----------------|
| Windows 11 | localhost | JARVIS · dev · Proxmox client | — |
| Proxmox VE | 192.168.1.20 | Hyperviseur · ZFS 3.5 To | `~/.ssh/id_proxmox` · 2272 |
| srv-nginx (VM 108) | 192.168.1.50 | nginx · CrowdSec · SOC dashboard | `~/.ssh/id_nginx` · 2272 |
| clt (VM 106) | 192.168.1.12 | Apache · site CLT | `~/.ssh/id_clt` · 2272 |
| pa85 (VM 107) | 192.168.1.13 | Apache · site PA85 | `~/.ssh/id_pa85` · 2272 |

### 2.2 Matériel local

| Composant | Détail |
|-----------|--------|
| OS | Windows 11 Pro |
| GPU | RTX 5080 Blackwell — 16 Go GDDR7 · CUDA 12 · sm_120 natif |
| Python | 3.11 |
| Ollama | 0.20.4 · `OLLAMA_FLASH_ATTENTION=1` |

### 2.3 Projets actifs

| Projet | Hébergement | État |
|--------|-------------|------|
| JARVIS | localhost:5000 | ✅ Production · v3.3 · score dette honnête ~90/100 (recalibré post-audit pytest --cov : refactor JS −98,1% + 568 tests pytest sur 27/34 modules avec coverage 35% lignes + fix perf IPv6 + hook pre-push) |
| SOC Dashboard | 192.168.1.50:8080 | ✅ v3.97.157 · 35 tuiles · LAN uniquement |
| srv-nginx | 192.168.1.50 | ✅ nginx · CrowdSec · WAF · audit 10/10 |
| CLT | 192.168.1.12 | ✅ Apache · SEO validé GSC |
| PA85 | 192.168.1.13 | ✅ Apache · PHP · XFF fix |
| Proxmox backups | local D:\ | ✅ Auto samedi 23h · quota 300 Go |

---

## 3. JARVIS — Architecture complète

### 3.1 Stack technique

```
Windows 11 — localhost:5000
├── jarvis.py              Flask · ~150 routes · host=127.0.0.1 (31 modules extraits)
├── blueprints/soc.py      Blueprint SOC · rsyslog v1.6.1
├── audio_dsp.py           Chaîne DSP audio · 508 L (extrait chantier 2026-05-14)
├── 30 modules Phase 3     audio · bypass · infra/RAG · chat/LLM core
├── templates/
│   ├── jarvis.html        Shell Jinja2 · 211 L · ?v={{ boot_id }} cache-bust
│   └── tabs/              tab_monitor · tab_chat · tab_settings · tab_dsp
│                          tab_terminal · tab_taches · tab_voicelab · tab_soc
└── static/
    ├── jarvis_main.js     point d'entrée JS · refactor terminé (−98,1%)
    ├── jarvis_mixing.js   1375 L · recorder.js 660 L · voice_print.js 852 L
    ├── js/               18 modules JS extraits (voir docs/ROUTING-JARVIS.md)
    └── css/               8 fichiers par secteur (ex-jarvis.css 5270L · chantier 2026-05-14)
```

**LLM (Ollama local) :**

| Modèle | Usage | Déclencheur |
|--------|-------|-------------|
| phi4:14b | SOC · raisonnement · 9.1 GB · zéro swap | mode SOC défaut (`#btn-mode-soc`) |
| gemma4:latest | GÉNÉRAL · VOCAL · vision (multimodal) · 9.6 GB | switch manuel ◎ GÉNÉRAL (`#btn-mode-general`) |
| qwen2.5-coder:14b | CODE · dev srv-dev-1 · boucle dev complète · 9.0 GB | switch manuel ◆ CODE (`#btn-mode-code`) |
| **qwen3:8b** | **CODE REASONING · single-pass thinking masqué `<think>` · ~5 GB** | **switch manuel ⬡ C·R (`#btn-mode-code-reasoning`)** |
| mxbai-embed-large | RAG embeddings · 1024 dims · 0.7 GB | systématique · keep_alive 10m (dé-épinglé 2026-05-20) |

⚠ Supprimés : phi4-reasoning:plus (remplacé par qwen3:8b en session 29) · qwen2.5:14b · deepseek-r1:14b · llava-phi3:latest · nomic-embed-text

**Routing 4 branches** — voir [`docs/ROUTING-JARVIS.md`](docs/ROUTING-JARVIS.md) pour le détail complet (bypass Python, sécurité RFC1918/_BLOCKED_SSH, whitelists).

**TTS (synthèse vocale) :**

```
edge-tts (fr-CA-AntoineNeural) ──► internet OK
     │ internet KO
     ▼
Kokoro neural (ff_siwis · CUDA) ──► local GPU
     │ non disponible
     ▼
Piper (fr_FR-upmc-medium) ──► local CPU
     │ non disponible
     ▼
SAPI5 (Hortense FR) ──► Windows natif
```

**STT :** faster-whisper turbo FR · CUDA
**XTTS v2 :** coqui-tts 0.27.5 · 58 voix + voice prints · GPU
**RAG :** mxbai-embed-large · 1024 dims · seuil 0.35 · TTL 300s · RAG Live SSH logs
**DSP :** EQ 5 bandes · compresseur · Haas stéréo · DeepFilterNet GPU

---

### 3.2 JARVIS se déplace dans l'infrastructure

JARVIS dispose de 4 canaux SSH permanents. Il agit sur chaque nœud sans intervention humaine.

```
Windows 11 — JARVIS :5000
│
├──► SSH → srv-nginx (192.168.1.50) · port 2272 · id_nginx
│         ├─ Lire : nginx logs · CrowdSec decisions · fail2ban · Suricata
│         ├─ Lire : monitoring.json (source SOC temps réel · poll 30s)
│         ├─ Agir : ban IP   → cscli decisions add --ip X --duration 24h
│         ├─ Agir : unban IP → cscli decisions delete --ip X
│         └─ Agir : restart  → systemctl restart nginx|crowdsec|fail2ban
│
├──► SSH → Proxmox VE (192.168.1.20) · port 2272 · id_proxmox
│         ├─ Lire  : qm list · pvesm status · état VMs
│         ├─ Agir  : qm stop VMID   (bypass LLM → subprocess direct · 2-3s)
│         └─ Agir  : qm start VMID  (bypass LLM → subprocess direct · 2-3s)
│                   VMs gérées : 106 clt · 107 pa85 · 108 srv-nginx
│
├──► SSH → clt (192.168.1.12) · port 2272 · id_clt
│         └─ Lire : df -h · systemctl status apache2 · error.log
│
└──► SSH → pa85 (192.168.1.13) · port 2272 · id_pa85
          └─ Lire : df -h · systemctl status apache2 · error.log

Gardes de sécurité SSH (toutes connexions) :
├─ _BLOCKED_SSH : 29 patterns interdits (rm -rf · qm destroy · mkfs · dd…)
├─ shell=False : zéro injection commande système
├─ timeout adaptatif : 15s standard · 30s apt · 25s autoban
└─ write ops restreintes : ban/unban/restart uniquement (validation manuelle sinon)
```

---

### 3.3 JARVIS proactif — boucles autonomes

JARVIS ne dort pas. 5 threads daemon tournent en permanence dès le démarrage :

```
Thread monitoring-poll (30s)
├─ Fetch monitoring.json → window._jarvisMonData (JS)
├─ checkThreatLevel() :
│    niveau change → ÉLEVÉ ou CRITIQUE ?
│    → TTS immédiate : "Alerte SOC. Niveau CRITIQUE, score 78/100."
│    → mention EXPLOIT non bloqué si présent
└─ Données prêtes en mémoire (0ms latence au prochain chat)

Thread auto-engine SOC (continu)
├─ Analyse monitoring.json toutes les 30s
├─ >500 req/h depuis une IP → ban automatique CrowdSec
├─ Service nginx/crowdsec/fail2ban down → restart automatique
└─ Toutes les actions journalisées → onglet ◈ SOC (timestamps · résultat)

Thread rag-live-prewarm (démarrage +15s)
└─ SSH srv-nginx → cache Suricata fast.log + CrowdSec decisions + fail2ban
   TTL 300s · injecté dans le contexte LLM sur questions logs/alertes

Thread gpu-monitor (poll 30s)
└─ Température · VRAM utilisée · utilisation GPU → onglet Settings

Thread tts-connectivity (continu)
└─ Internet KO → bascule engine edge-tts → Kokoro local (zéro coupure vocale)
```

---

### 3.4 Routing des messages — décision LLM (3 branches + bypass)

Pipeline de décision strict. L'ordre est important — bypass VM toujours en premier.

```
Message utilisateur (JS)
        │
        ▼
[ JS : _SOC_CHAT_KW — mots cyber stricts uniquement ]
  soc · menace · ban · crowdsec · fail2ban · attaque
  ddos · bruteforce · cve · rce · exploit · suricata…
        │                     │
    SOC keyword           Pas de match
        │                     │
        ▼                     ▼
  Injecte monitoring.json   Message propre
  soc_ctx_injected=true     envoyé direct
        │
        └─────────────────────► api_chat() Python
                                       │
                           _orig_last extrait
                           (message avant injection SOC)
                                       │
                   ┌───────────────────┼──────────────────────┐
                   │                   │                      │
          VM command ?          Bypass direct ?         ROUTING
          arrête/démarre        service restart          3 branches
          pa85/clt/ngix         backup · fichier         │
                   │                   │                      │
                   ▼                   ▼                      ▼
          subprocess direct    SSH direct / PS1     _jarvis_mode ?
          SSH Proxmox          sans LLM · <1s        │
          sans LLM · 2-3s                    ┌────────┼──────────┐
                                             │        │          │
                                         'general' 'code'    SOC défaut
                                         ou VOCAL    │          │
                                             ▼        ▼          ▼
                                       gemma4:latest qwen2.5-coder:14b phi4:14b
                                       (GÉNÉRAL+VOCAL) (CODE·dev) (chaud·SOC)
```

**Switch mode** : bouton `⚡ SOC` / `◎ GÉNÉRAL` dans l'UI · `/api/mode` GET/POST · reset SOC au redémarrage Flask

---

## 4. Chaîne de sécurité

### 4.1 Défense en profondeur

```
Internet
   │
   ▼
Freebox (NAT)
   │  zéro port exposé sauf 80/443 redirigés vers srv-nginx
   │
   ▼
srv-nginx (192.168.1.50)
   ├─ UFW                    pare-feu kernel (whitelist ports)
   ├─ GeoIP nginx            restriction géographique → 403
   ├─ CrowdSec bouncer       blacklist comportementale (IPs bannies)
   ├─ AppSec WAF             ~150 vpatch CVE : SQLi · RCE · XSS · LFI…
   ├─ fail2ban               bans SSH + HTTP brute force
   ├─ Suricata IDS           détection réseau (eve.json · fast.log)
   └─ nginx reverse proxy ──► clt (106) / pa85 (107)

Windows 11 (LAN uniquement)
   ├─ JARVIS :5000           host=127.0.0.1 · debug=False · loopback strict
   └─ Ollama :11434          localhost uniquement · zéro exposition LAN

SOC Dashboard (LAN uniquement)
   ├─ monitoring_gen.py      génère monitoring.json toutes les 60s
   ├─ JARVIS JS poll 30s     window._jarvisMonData (circuit temps réel)
   └─ Alertes vocales        TTS sur ÉLEVÉ/CRITIQUE (checkThreatLevel)
```

### 4.2 Kill Chain nginx (niveaux de menace)

| Stage | Description | Action JARVIS |
|-------|-------------|---------------|
| RECON | Reconnaissance passive · fingerprinting | Surveillance |
| SCAN | Scan ports/services · path discovery | Surveillance |
| BRUTE | Force brute SSH/HTTP · credential stuffing | Alerte si seuil |
| EXPLOIT | Tentative CVE · RCE · injection | Alerte immédiate · ban si non bloqué |

**Score de menace :** 0-29 FAIBLE · 30-49 MOYEN · 50-69 ÉLEVÉ · ≥70 CRITIQUE
Source unique : `monitoring_gen.py` sur srv-nginx → jamais recalculé par JARVIS.

---

## 5. Chantier 2026-05-05 — Session 10

### 5.1 Contexte

Commandes de contrôle VM peu fiables : `arrête pa85`, `démarre srv-nginx` → phi4 générait une analyse SOC au lieu d'exécuter SSH. Lenteur 20-60s. Typos non reconnues. Trois problèmes distincts résolus en cascade.

---

### 5.2 Problème A — Le LLM hallucine au lieu d'agir

**Symptôme :** "arrête les vms du serveur" → phi4 répond par une analyse SOC.

**Cause :**

```
"démarre srv-nginx"
      │
      ▼
JS : _SOC_CHAT_KW contenait "serveur", "nginx", "ip"…
     → match sur "srv-nginx"
     → injection monitoring.json en tête du message
     → soc_ctx_injected = true
      │
      ▼
Python api_chat()
  last_user = "[CONTEXTE SOC... score: 45 IPs: 3...]\n\nDémarre srv-nginx"
  _INFRA_KW.search(last_user)   ← cherche dans le texte CONTAMINÉ → fail
  soc_trigger = True (mots SOC présents dans le JSON injecté)
      │
      ▼
  phi4:14b reçoit contexte SOC → analyse SOC, pas de SSH
```

**Fix :**

```python
# JS — _SOC_CHAT_KW recentré sur mots cyber stricts uniquement
# Supprimé : serveur · nginx · ip · trafic · log · état · rapport

# Python — extraire le message AVANT l'injection SOC
_orig_last = last_user.split("\n\n", 1)[-1] if soc_ctx_injected else last_user

# Le routing infra et VM vérifient _orig_last (message propre)
vm_cmd = _detect_vm_command(_orig_last)
if _INFRA_KW.search(_orig_last): ...
```

---

### 5.3 Problème B — Le bypass SSH trop lent (20-60s)

**Symptôme :** VM commandes = 20-60s même quand le bypass était actif.

**Cause :**

```
_vm_command_sse("stop", [(106,"clt")])
      │
      ▼
_ssh_proxmox(cmd)        ← appelle _ssh_host() avec _SSH_LOCK
      │
      ▼
with _SSH_LOCK:           ← lock global partagé avec monitoring loop
    subprocess.run(...)   ← bloqué — monitoring loop occupe le lock (SSH ngix 30s)
```

**Fix :** subprocess direct sans passer par le lock :

```python
# Avant — via _SSH_LOCK (bloquant)
ok, output = _ssh_proxmox(cmd, timeout=15)

# Après — subprocess direct (non bloquant)
r = subprocess.run(_SSH_PROXMOX + [cmd], capture_output=True, text=True, timeout=15)
```

Résultat : **2-3s constant**, indépendant du monitoring loop.

---

### 5.4 Problème C — "arréter" (é accent aigu) non reconnu

**Symptôme :** `arréter clt` → aucune action.

**Cause :** double bug regex :

```
[eê]    → couvre ê (U+00EA) uniquement
           l'utilisateur tape é (U+00E9) — caractère différent

arr[eê]te?  → \b word-boundary satisfait après "arrête"
               mais cassé sur "arrêter" : le 'r' final n'est pas consommé
```

**Fix :**

```python
# Avant
r'arr[eê]te?\b'

# Après — arrête · arrêter · arrêtez · arréter · arrêtes
r'arr[eêé]te[rz]?[sz]?'
```

Appliqué dans `_VM_STOP_RE`, `_VM_ALL_STOP_RE`, `_INFRA_KW` (3 occurrences).

---

### 5.5 Autres corrections session 10

| Correction | Détail |
|------------|--------|
| Cache navigateur | `SEND_FILE_MAX_AGE_DEFAULT=0` + `?v={{ boot_id }}` sur jarvis_main.js + 8 fichiers css/ |
| `_rag_live_query` orpheline | Stub `return []` jamais appelé — supprimé |
| `arr[eê]` résiduel `_INFRA_KW` | Aligné avec VM regexes → `arr[eêé]te[rz]?[sz]?` |

### 5.6 Résultats audit code

| Vérification | Résultat |
|-------------|----------|
| Fonctions orphelines jarvis.py | 1 supprimée (`_rag_live_query`) |
| Fonctions orphelines soc.py | 0 |
| Imports inutilisés | 0 |
| Regex inconsistantes | 3 corrigées |
| Code mort introduit cette session | 0 |
| **jarvis.py final** | **Orchestrateur Flask · 32 modules extraits · refactor JS terminé (−98,1%)** — audit dette complet 2026-05-22 · score/lignes/tests/coverage → `BILAN-TECHNIQUE.md` §0 |

### 5.7 Validé en prod

```
"arréter clt"         → qm stop 106  → "clt arrêtée."     ✓  2-3s
"démarrer pa85"       → qm start 107 → "pa85 démarrée."   ✓  2-3s
"Démarrer clt + pa85" → qm start 106 + qm start 107       ✓
"arrêter les vms"     → qm stop 107 (pa85) + qm stop 106 (clt)
                         srv-nginx (108) exclu — dashboard SOC protégé  ✓
```

---

## 6. Historique des travaux — Sessions 1 à 9

| Date | Besoin | Réalisé |
|------|--------|---------|
| 2026-05-04 | Routing LLM automatique | `_INFRA_KW` · profil "Infra — Qwen2.5" · 3 RÈGLES ABSOLUES anti-hallucination |
| 2026-05-04 | Contrôle VM multi-stop/start | `_detect_vm_command` · `_VM_ALL_STOP_RE` · `_VM_SAFE_STOP_LIST` |
| 2026-05-04 | Vision LLM | Pipeline llava-phi3 → phi4-reasoning · SSE `vision_desc` |
| 2026-05-04 | Résilience Ollama hors ligne | try/except SSE error token — plus de 500 silencieux |
| 2026-05-04 | Pont Claude ↔ JARVIS | MCP 5 outils initiaux : jarvis_chat · soc_status · stats · soc_ask · infra_status |
| 2026-05-08 → 2026-05-13 | Extension MCP | **MCP 10 outils** : + jarvis_proxmox_vms · jarvis_read_file · jarvis_model_switch · jarvis_last_response · jarvis_code_exec |
| 2026-05-04 | RAG logs temps réel | SSH srv-nginx · Suricata/CrowdSec/fail2ban · TTL 300s · pré-chauffe 15s |
| 2026-05-03 | XTTS v2 | coqui-tts 0.27.5 · 58 voix + voice prints · GPU CUDA |
| 2026-05-03 | Moteur vocal complet | edge-tts → Kokoro → Piper → SAPI5 · fallback auto · LED état |
| 2026-05-03 | Anti-hallucination SOC | SCORE OFFICIEL · règle FIDÉLITÉ tous profils · `_monCtxStr` aligné |
| 2026-05-02 | SOC temps réel chatbot | `window._jarvisMonData` poll 30s · zéro divergence JARVIS/dashboard |
| 2026-05-02 | Audit dette technique | NDT-LONG ×4 · NDT-DUP · NDT-CSS → score 10/10 |
| 2026-05-01 | Centralisation score menace | Source unique `monitoring_gen.py` · NE PAS recalculer |

---

## 7. Roadmap — Besoins ouverts

| État | Item | Session |
|------|------|---------|
| ✅ | STT `initial_prompt` — vocabulaire SOC (CrowdSec, fail2ban, kill chain…) | session 15 |
| ✅ | ThreatScore 30j historique — sparkline SVG + modal Canvas 30j | session 21 |
| ✅ | Rapport quotidien JARVIS vocal `_check_daily_report()` soc.py | session 21 |
| ✅ | Corrélation temporelle — campagnes lentes /24 · 14j · bloc MENACE + alerte vocale | session 21 |
| ✅ | Proxmox API directe — `_pve_fetch_state()` + ticket+token auth · cache 30s | session 21 |
| ✅ | NDT 100/100 — dette zéro absolue CSS/JS/HTML/Python (session 26) | session 26 |
| ✅ | NDT-DUP SSH : `_tool_commande_ssh_run()` générique · 4 fonctions → 1 helper | session 26 |
| ✅ | NDT-HTML-MAGIC : `dev_ip`/`dev_port` via Jinja2 ({{ dev_ip }} · {{ dev_port }}) | session 26 |
| ✅ | Tests E2E Playwright — 23 tests · suite ~1m42s · 0 régression cible | session 33 |
| ✅ | Linters intégrés — Ruff (Python) · ESLint (JS) · 0 errors · 96+132 warnings tolérés | session 33 |
| ✅ | Audit dette technique honnête — score 73 → 84/100 (+11 sur 2026-05-13) | session 33 |
| ✅ | **Phase 3 split monolithe Python complète** — **30 modules extraits** (Audio/Voice 5 + Bypass 8 + Infra/RAG 2 + Chat/LLM core 15) — `jarvis.py` 6592 → ~4520 (**-2072 lignes · -31%**) — score honnête 84 → **89/100** (+5 · pas 100 car JS toujours monolithique) | session 33b |
| ✅ | **Split JS partiel** — extraction `recorder.js` (660L) + `voice_print.js` (852L) en IIFE depuis `jarvis_main.js` 10507→8994L (**-14.4%**) — score honnête 89 → 91 (valeur d'époque) | session 33c |
| ✅ | **Chantier dette technique 2026-05-14** — recalibration honnête (le 91 était optimiste, départ réel **62**) → **78/100** (+16). Ruff 98→0 (2 bugs F821 réels corrigés) + `ruff.toml` · **git initialisé** (100% local) · **pre-commit hooks bloquants** · `jarvis.css` 5270L → 8 fichiers CSS · `audio_dsp.py` extrait · 2 smoke tests LLM · **refactor JS partiel** : 3 modules extraits de jarvis_main.js (8994→7893L) | 2026-05-14 |
| ✅ | **Chantier dette technique 2026-05-15 (extension massive)** — score 78 → **93/100** (+15). **Refactor JS terminé** (`jarvis_main.js` 7828→**148 L** −98,1% cumul, 21 modules) · **933 tests pytest** sur **32 modules · 22 à 100% cov** avec **coverage 51% lignes** (tts_engines 83% · 42 tests, jarvis_mcp_server 91% · 52 tests, ollama_circuit 100% · 23 tests, proxmox_api 93%, bypass_backup 96%, voice_lab 71%, deepfilter 84%, ssh_terminal 100%, stt 98%, rag_live 92%, soc.py 33%, jarvis.py 26% via Flask test_client) · **Phase 3 fix perf IPv6** (-97% latence interne via `OLLAMA_URL`/`JARVIS_BASE` → 127.0.0.1) · **Circuit breaker Ollama** (`ollama_circuit.py` 3 états + indicateur HUD `● OLLAMA` · étendu à **8 call-sites** dans `jarvis.py` · bouton SOC PING JARVIS enrichi état Ollama) · **Pré-warm Kokoro CUDA au boot** (`_kokoro_prewarm` 60 s · élimine cold start 42.8 s mesuré) · **profiling TTS détaillé** (`tools/profile_tts.py` 4 moteurs × 7 textes · médianes chaud edge 1453ms / kokoro 203ms / piper 219ms / sapi 563ms) · **hook pre-push pytest** · 3 bugs prod détectés+fixés (load-order, tts_cleaner, IPv6) · outils `tools/profile_perf.py` + `tools/profile_tts.py` | 2026-05-15 |
| 🟡 | SSH write ops partielles — apt upgrade · restart service (validation) | ouvert |
| 🔵 | Pour 95+ : couverture jarvis.py / soc.py / audio_dsp Flask routes (faible ROI) ou CI cloud (incompatible « rien sur le web ») — plafond pratique sans cloud atteint | future session |
| 🔵 | Tests unitaires Python · profiling performance | future session |

**Reste reporté :** refactor JS (suite incrémentale) · tests unitaires Python · profiling perf · CI cloud (incompatible « rien sur le web »).

---

## 7bis. Couverture tests E2E (Playwright · session 33 → chantier 2026-05-14)

25 tests automatisés dans `tests/e2e/` (11 fichiers `.spec.js`) qui valident la chaîne complète UI ↔ backend Flask, dont **2 smoke tests LLM** (`chat-llm-smoke.spec.js` — flux SSE réel `/api/chat`). Suite complète en ~1m48s. Pré-requis : JARVIS up sur :5000.

### Couverture par fichier

| Fichier | Tests | Domaine |
|---------|-------|---------|
| `boot.spec.js` | 2 | Page load sans erreur console · 7 tabs rendus |
| `api.spec.js` | 3 | `/api/health` · `/api/mode` GET · cycle soc↔general (REST) |
| `tabs.spec.js` | 3 | Navigation Monitor / SETTINGS / DSP AUDIO |
| `chat-ui.spec.js` | 2 | Chat tab actif par défaut · `#user-input` éditable |
| `soc-tab.spec.js` | 2 | Compteurs SOC (ban/fail/ok/ids) · actions list · chart day |
| `dsp-voicelab.spec.js` | 3 | DAT player buttons · 4 engines TTS (edge/kokoro/piper/sapi) · A/B slots |
| `settings-tasks.spec.js` | 2 | Facts list + prompt badge · task creation form |
| `mode-ui.spec.js` | 1 | Clic boutons mode → propagation `/api/mode` (UI ↔ backend) |
| `modals.spec.js` | 2 | DAT modal open+close · MIXER modal open+close |
| `dsp-interactive.spec.js` | 3 | Sliders EQ low/high/air → labels mis à jour temps réel |
| `chat-llm-smoke.spec.js` | 2 | Flux SSE réel `/api/chat` (tokens + done:true) + capture historique (chantier 2026-05-14) |

### Commandes

```bash
npm test              # suite complète (JARVIS doit être up)
npm run test:headed   # navigateur visible
npm run test:ui       # mode UI Playwright
```

### Limites connues

- Seuls 2 smoke tests LLM existent (`chat-llm-smoke.spec.js`) — la couverture LLM reste minimale (latence 3-30s rendrait une suite exhaustive trop lente)
- Aucun test n'envoie réellement de TTS audio (dépend du device)
- Le mode CODE n'est pas testé via UI (ouvre un WebSocket SSH vers srv-dev-1, side-effect réseau)

---

## 7ter. Split monolithe — Phase 3 (session 33) + chantier dette (2026-05-14)

**31 modules extraits** depuis `jarvis.py` (ex-monolithe 6592L) — Phase 3 (30 modules, session 33b) + `audio_dsp.py` (chantier dette 2026-05-14).

| Module | Lignes | Domaine | Couplage |
|--------|--------|---------|----------|
| [`scripts/stt.py`](scripts/stt.py) | 97 | Whisper transcription + initial_prompt SOC | Aucun (faster-whisper + ctranslate2) |
| [`scripts/voice_lab.py`](scripts/voice_lab.py) | 167 | Analyse acoustique librosa + voice prints CRUD | Aucun (librosa + numpy) |
| [`scripts/tts_engines.py`](scripts/tts_engines.py) | 280 | 4 engines TTS (Kokoro CUDA/Piper/SAPI5/edge-tts) | Aucun (drivers purs) |
| [`scripts/deepfilter.py`](scripts/deepfilter.py) | 132 | DeepFilterNet débruitage IA CUDA | Aucun (numpy + scipy + torch lazy) |
| [`scripts/vision.py`](scripts/vision.py) | 100 | Analyse image gemma4 multimodal | Découplé RAG (passé en param) |
| [`scripts/bypass_simple.py`](scripts/bypass_simple.py) | 38 | Bypass datetime (regex + SSE) | Aucun (datetime stdlib) |
| [`scripts/security_whitelists.py`](scripts/security_whitelists.py) | 105 | BLOCKED_SSH (29 patterns) + ALLOWED_RESTART_SVCS + ALLOWED_APT_PKGS + check_write_op() + parse_upgradable_packages() | Aucun (validation pure) |
| [`scripts/audio_dsp.py`](scripts/audio_dsp.py) | 508 | Chaîne DSP audio : reverb convolution + FX rack (6 effets) + biquad + compresseur + apply_dsp_to_mp3 | DI sur DSP_PARAMS (wrapper jarvis.py) — chantier 2026-05-14 |

> Note : tableau partiel — voir [`ROUTING-JARVIS.md`](docs/ROUTING-JARVIS.md) pour les 31 modules complets.

### Pattern d'extraction validé

1. **Module dédié** créé avec son propre `_log = logging.getLogger("jarvis.<domain>")`
2. **API publique** snake_case sans underscore prefix pour les exports
3. **`jarvis.py`** : `import <domain> as _<domain>` (alias underscore pour cohérence)
4. **Routes Flask** restent dans jarvis.py (couplage Flask) mais délèguent à `_<domain>.func()`
5. **Validation** : `py_compile` + restart JARVIS + `npm test` (25 E2E) → zéro régression à chaque palier

### Reste à extraire (sessions futures)

- **Bypass commands SSH/VM/backup/code** (~600L) — couplage paramiko/subprocess/Proxmox API. À faire en sous-modules ciblés (`bypass_filesystem.py`, `bypass_proxmox.py`, `bypass_backup.py`, `ssh_terminal.py`).
- **Chat/LLM core** (cœur Ollama + routing + RAG/SOC injection + system prompt) — couplage profond. Plus risqué.

### Bénéfices observés

- Maintenance ciblée : bug audio engine X → direct dans `tts_engines.py`, pas dans le monolithe
- Audit sécurité : `security_whitelists.py` = couche défensive isolée, immédiatement reviewable
- Tests unitaires possibles : `from stt import transcribe; transcribe("test.wav")` sans booter Flask
- Stack traces pointent les modules dédiés (debug plus rapide)

⚠ **Stabilité runtime inchangée** — c'est une réorganisation, pas une réécriture. Les bugs latents préexistants restent.

---

## 8. Disaster Recovery

Tout est documenté dans `D:\PROJETS\` (disque D: séparé — survit à une réinstallation Windows sur C:).

| Dossier / Fichier | Contenu |
|-------------------|---------|
| `RUNBOOK_0xcyberlitech.md` | Document maître · checklist reconstruction par machine |
| `CLES_SSH_0xcyberlitech/` | Clés SSH privées/publiques · tous les hôtes |
| `CLES_API_0xcyberlitech/` | AbuseIPDB · NVD · Freebox · Proxmox API · SMTP |
| `CROWDSEC_0xcyberlitech/` | Collections · bouncers · AppSec WAF · restauration |
| `FAIL2BAN_0xcyberlitech/` | Jails · paramètres · commandes restauration |
| `CRONS_0xcyberlitech/` | Tâches planifiées Windows + Linux · restauration |
| `ACLs_UFW_0xcyberlitech/` | Règles UFW annotées · commandes restauration |
| `SURICATA_0xcyberlitech/` | Config Suricata IDS |
| `D:\BACKUP-PROXMOX\` | Snapshots VMs (auto samedi 23h · quota 300 Go · rotation 10) |
| `D:\BACKUP-WINDOWS\JARVIS\` | Backup complet JARVIS (scripts · models · config) |
