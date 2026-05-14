# Circuit logique SOC + JARVIS — 0xCyberLiTech
**Date : 2026-05-14 — v2.4** · routing 4 branches (soc/general/code/code_reasoning) · MCP 10 outils · 31 modules Python (jarvis.py 4633L) · jarvis.css → 8 fichiers · git initialisé + pre-commit hooks · score honnête 75/100 (chantier dette 2026-05-14 : 62→75)

---

## Schéma maître

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║                         RÉSEAU LAN — 192.168.1.x                               ║
║                                                                                  ║
║   INTERNET                                                                       ║
║      │  trafic entrant                                                           ║
║      ▼                                                                           ║
║  ┌───────────────────────────────────────────────────────┐                      ║
║  │              srv-ngix  192.168.1.50                    │                      ║
║  │                                                        │                      ║
║  │  nginx ◄─── requêtes ──────────────────────────────── │◄── WAN               ║
║  │    │                                                   │                      ║
║  │    ├──▶ CrowdSec bouncer → DROP / PASS                │                      ║
║  │    │         │                                         │                      ║
║  │    │    CrowdSec engine ◄── AppSec WAF (150 CVE)      │                      ║
║  │    │         │                                         │                      ║
║  │    ├──▶ Suricata IDS (af-packet, 90k règles)          │                      ║
║  │    │         │  sév.1 C2 · sév.2 HIGH · sév.3 NMAP   │                      ║
║  │    │         │                                         │                      ║
║  │    └──▶ fail2ban  (nginx-cve · sshd)                  │                      ║
║  │                                                        │                      ║
│                      ║
║  │  monitoring_gen.py (cron */5min)                       │                      ║
║  │    ├── agrège : nginx+CrowdSec+Suricata+F2B+Proxmox  │                      ║
║  │    └── écrit : monitoring.json ──────────────────────►│── HTTP 8080          ║
║  └───────────────────────────────────────────────────────┘                      ║
║            ▲                    ▲                ▲                               ║
║            │ SSH ban/restart    │ fetch JSON     │ push JSON /5min              ║
║            │                   │                │                               ║
║  ┌─────────┴──────────┐  ┌─────┴──────────┐  ┌─┴────────────────────────────┐ ║
║  │  JARVIS            │  │  SOC Dashboard  │  │  Proxmox VE  192.168.1.20   │ ║
║  │  localhost:5000    │  │  browser        │  │                              │ ║
║  │                    │◄─┤                 │  │  fail2ban-monitor-push.sh    │ ║
║  │  Flask + Ollama    │  │  35 tuiles      │  │  ufw-monitor-push.sh         │ ║
║  │  phi4:14b          │  │                 │  │  (cron */5min → srv-ngix)    │ ║
║  │                    │  │  computeThreat  │  └──────────────────────────────┘ ║
║  │  auto-engine       │  │  Score 0-100    │                                   ║
║  │  _soc_monitor_loop │  │                 │  ┌──────────────────────────────┐ ║
║  │  (poll 60s)        │  │  checkAutoBan() │  │  clt  192.168.1.12           │ ║
║  │                    │  │  checkReqPerH() │  │  pa85 192.168.1.13           │ ║
║  │  TTS : Antoine (edge)│  │  ──▶ JARVIS ban │  │  fail2ban apache jails       │ ║
║  │  Onglet ◈ SOC      │  │                 │  │  (SSH depuis monitoring_gen) │ ║
║  └────────────────────┘  └─────────────────┘  └──────────────────────────────┘ ║
║            │                                                                     ║
║            │  windows-disk-report.ps1 (push /var/www/monitoring/)               ║
║            │  ◄── GPU RTX5080 · CPU · RAM · disk · backup status               ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

### Légende des flux

| Flèche | Signification |
|--------|--------------|
| `──▶` | Données / commande |
| `◄──` | Réception / lecture |
| SSH ban | JARVIS → `cscli decisions add -i IP` sur srv-ngix |
| SSH restart | JARVIS → `systemctl restart <service>` sur srv-ngix |
| fetch JSON | Dashboard browser → `monitoring.json` toutes 30s |
| push JSON | Proxmox/Windows → srv-ngix via SCP/SSH toutes 5min |

### Règle dashboard ouvert / fermé

```
Dashboard OUVERT  ──▶  JS checkAutoBan() + checkReqPerHour() actifs
                        JARVIS reçoit heartbeat → mode passif (pas de doublon)

Dashboard FERMÉ   ──▶  JARVIS _soc_monitor_loop() prend le relais
                        Python _soc_autoban() + _soc_reqhour_check()
                        + _soc_suricata_check() + _soc_service_check()
```

---

## Vue d'ensemble

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SOURCES DE DONNÉES                           │
│                                                                     │
│  nginx logs  CrowdSec  fail2ban×4  Suricata  Proxmox  Freebox  WAN │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              monitoring_gen.py  (srv-ngix, cron */5min)             │
│                                                                     │
│  • Parse nginx access.log → trafic, proto_breakdown, kill_chain     │
│  • API CrowdSec local → décisions, machines, bouncers               │
│  • fail2ban-client local + SSH clt/pa85 → jails 4 hôtes            │
│  • fail2ban Proxmox ← push JSON /5min (proxmox-fail2ban.json)       │
│  • Suricata eve.json → sév.1/2/3, top IPs, MITRE, recent_scans,    │
│                         enabled_sources                             │
│  • API Proxmox HTTPS → CPU/RAM/VMs + SSH sensors température        │
│  • push windows-disk.json (Windows → srv-ngix)                      │
│  • Freebox API locale, GeoIP, CVE/threat feeds, SSL check           │
│                                                                     │
│  ──▶  génère  /var/www/monitoring/monitoring.json  (toutes /5min)   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
┌─────────────────────────┐      ┌──────────────────────────────────┐
│   SOC Dashboard         │      │   JARVIS  (Windows localhost:5000)│
│   monitoring-index.html │      │   jarvis.py — Flask + Ollama      │
│   (browser client)      │      │   phi4:14b                        │
└─────────────────────────┘      └──────────────────────────────────┘
```

---

## 1. Collecte des données (srv-ngix)

```
┌──────────────────────────────────────────────────────┐
│  srv-ngix 192.168.1.50                               │
│                                                      │
│  nginx ──────────────────── access.log               │
│  CrowdSec ──────────────── /run/crowdsec/sock        │
│  fail2ban ──────────────── fail2ban-client status    │
│  Suricata IDS ──────────── /var/log/suricata/eve.json│
│                                                      │
│  SSH ──▶ clt (192.168.1.12)  fail2ban + apache jails │
│  SSH ──▶ pa85 (192.168.1.13) fail2ban + apache jails │
│                                                      │
│  ◀── push Proxmox cron /5min ──────────────────────  │
│       proxmox-fail2ban.json                          │
│       proxmox-ufw.json                               │
│                                                      │
│  ◀── push Windows /5min ───────────────────────────  │
│       windows-disk.json (CPU/RAM/GPU/disk/backup)    │
└──────────────────────────────────────────────────────┘
```

---

## 2. Dashboard SOC (browser)

```
Browser ──▶ fetch monitoring.json (toutes les 30s)
              │
              ├── render() ──▶ 35 tuiles mises à jour
              │
              ├── computeThreatScore()
              │     Sources : CrowdSec + Suricata sév.1×5 + sév.2×recal
              │               + F2B 4 hôtes + Apache bots + WAF AppSec
              │               + services DOWN + anomalies firewall
              │     ──▶ score 0-100 → FAIBLE / MODÉRÉ / ÉLEVÉ / CRITIQUE
              │
              ├── checkAutoBan()           ──▶ si dashboard OUVERT
              │     EXPLOIT CVE (1 hit) → ban
              │     honeypot (1 hit)    → ban
              │     BRUTE ≥30          → ban
              │     Suricata sév.1     → ban
              │     ──▶ POST localhost:5000/api/soc/ban-ip
              │
              ├── checkReqPerHour()        ──▶ si dashboard OUVERT
              │     spike >500 req/h → ban top 3 IPs (EXPLOIT>BRUTE>SCAN)
              │     ──▶ POST localhost:5000/api/soc/ban-ip
              │
              └── JARVIS heartbeat POST /api/soc/heartbeat (toutes 30s)
                    TTL 90s — dashboard ouvert = JARVIS en mode passif
```

---

## 3. JARVIS auto-engine (Python, dashboard FERMÉ)

```
_soc_monitor_loop()  ──  poll monitoring.json via SSH toutes les 60s
         │
         ├── _soc_autoban(data)
         │     Même logique que JS checkAutoBan()
         │     EXPLOIT / honeypot / BRUTE / Suricata sév.1
         │     ──▶ _ssh_ngix("cscli decisions add -i IP")
         │     ──▶ _soc_log("ban_ip", ...) → jarvis_soc_actions.json
         │
         ├── _soc_reqhour_check(data)
         │     spike >500 req/h → ban top 3 IPs kill chain
         │     + Suricata recent_scans IPs comme candidats EXPLOIT
         │     ──▶ _ssh_ngix("cscli decisions add -i IP")
         │
         ├── _soc_suricata_check(data)
         │     sév.1 C2/Trojan → ban immédiat
         │     sév.3 NMAP (recent_scans) ≥3 hits → ban 24h
         │     sév.2 recal : >3000/+10pts  >1500/+7pts  >600/+4pts
         │     ──▶ _ssh_ngix("cscli decisions add -i IP -d 24h")
         │
├── _soc_rsyslog_check(data)
         │     C2 outbound cross-hôtes → ban 48h
         │     recon multi-cible Apache → ban 24h
         │     (rsyslog multi-hôtes v1.6.1 — 5 hôtes)
         │
         └── _soc_service_check(data)
               service DOWN + in _ALLOWED_SERVICES
               ──▶ _ssh_ngix("systemctl restart <service>")
               cooldown 15min par service
```

---

## 3bis. Modes JARVIS — routing 4 branches (sessions 28-29)

JARVIS expose 4 modes — un seul actif à la fois, persisté dans `_jarvis_mode` (variable globale `jarvis.py:3082`) et exposé via `GET/POST /api/mode`.

| Mode | Modèle Ollama | VRAM | Comportement SOC |
|------|---------------|------|------------------|
| **SOC** (défaut) | `phi4:14b` | 9.1 GB | **ACTIF** — auto-engine + alertes vocales + injection contexte monitoring.json |
| **GENERAL** | `gemma4:latest` | 9.6 GB | **SUSPENDU** — conversation fluide + vision, zéro action SOC |
| **CODE** | `qwen2.5-coder:14b` | 9.0 GB | **SUSPENDU** — code + infogérance srv-dev-1 (SCP+exec), zéro action SOC |
| **CODE REASONING** (CR) | `qwen3:8b` | ~5 GB | **SUSPENDU** — single-pass thinking masqué `<think>…</think>`, zéro action SOC |

⚠ **Règle absolue** : la surveillance SOC (auto-engine, alertes vocales, ban auto, monitoring live) n'est active qu'en mode SOC. Les 3 autres modes sont **100% suspendus côté SOC** — c'est un comportement voulu (pas de conflits, pas de bruit pendant le code/conversation).

### Spécificité mode CODE REASONING (qwen3:8b)

- Pipeline `code_reasoning.generate()` (module `scripts/code_reasoning.py`) — sortie SSE en streaming
- Thinking tokens `<think>…</think>` filtrés côté serveur, JAMAIS envoyés au client
- Bypass `chat_soc_inject.inject()` et `proxmox_api.inject()` — zéro injection contexte (cf. modules dédiés)
- Cible : refactoring multi-fichiers où le LLM doit "penser longtemps" sans contamination par contexte SOC/Proxmox

### Switch mode

- **UI** : 4 boutons dans tab CHAT (`#btn-mode-soc/general/code/code-reasoning`)
- **API** : `POST /api/mode` body `{"mode":"soc|general|code|code_reasoning"}`
- **Side-effect mode CODE** : `setModeCode()` JS appelle aussi `devTerminalOpen()` qui ouvre le WebSocket SSH `/ws/ssh/dev1` vers srv-dev-1

Voir [`docs/ROUTING-JARVIS.md`](docs/ROUTING-JARVIS.md) pour le détail bypass Python (9 catégories) et sécurité (RFC1918, _BLOCKED_SSH, whitelists).

---

## 4. Circuit ban complet (de la détection au blocage effectif)

```
DÉTECTION
   │
   ├── [Source A] nginx log → CrowdSec parser → décision locale
   │
   ├── [Source B] Suricata sév.1 C2/Trojan → JARVIS _soc_suricata_check
   │
   ├── [Source C] Suricata sév.3 NMAP ≥3 hits → JARVIS recent_scans
   │
   ├── [Source D] spike trafic >500 req/h → JS checkReqPerHour / Python _soc_reqhour_check
   │
   └── [Source E] EXPLOIT/honeypot/BRUTE → JS checkAutoBan / Python _soc_autoban
                               │
                               ▼
                  JARVIS POST /api/soc/ban-ip  (si dashboard ouvert)
                  OU
                  _ssh_ngix() direct            (si dashboard fermé)
                               │
                               ▼
                  srv-ngix : cscli decisions add -i <IP> [-d <durée>]
                               │
                               ▼
                  CrowdSec bouncer nginx → DROP immédiat
                  fail2ban bridge crowdsec-sync → sync jails
                               │
                               ▼
                  _soc_log() → jarvis_soc_actions.json
                  TTS vocale si score ÉLEVÉ/CRITIQUE
                  Onglet ◈ SOC jarvis.html mis à jour
```

---

## 5. Flux données Proxmox → SOC

```
Proxmox VE (192.168.1.20)
      │
      ├── fail2ban-monitor-push.sh  (cron /5min)
      │     ──▶ SSH srv-ngix → /var/www/monitoring/proxmox-fail2ban.json
      │
      └── ufw-monitor-push.sh       (cron /5min)
            ──▶ SSH srv-ngix → /var/www/monitoring/proxmox-ufw.json
                   │
                   ▼
            monitoring_gen.py lit ces fichiers → intégré dans monitoring.json
            ──▶ tuile FAIL2BAN (panel Proxmox) + tuile FIREWALL
```

---

## 6. Flux données Windows → SOC

```
Windows (192.168.1.x — machine locale)
      │
      └── windows-disk-report.ps1  (tâche planifiée ou manuel)
            ──▶ SCP windows-disk.json → srv-ngix
                   │
                   ▼
            monitoring_gen.py lit windows-disk.json
            ──▶ tuile WINDOWS RESSOURCES (CPU/RAM/GPU/disk/backup)

      JARVIS localhost:5000
            │
            └── GET /api/stats  (polling SOC dashboard toutes 30s)
                   ──▶ tuile JARVIS (statut, GPU, modèle actif)
```

---

## 7. Rapport quotidien

```
soc-daily-report.py  (cron 08h00 quotidien)
      │
      ├── Lit monitoring.json (snapshot courant)
      ├── Sections : trafic 24h + CrowdSec + fail2ban 4 hôtes
      │              + Suricata (sév.1/2/3, top IPs, sources actives)
      │              + SSL + CVE sync + services
      ├── Niveau CRITIQUE si surSev1 > 0
      └── ──▶ email HTML envoyé
```

---

## 8. Résumé des cooldowns et seuils

| Mécanisme | Seuil | Cooldown |
|-----------|-------|---------|
| Ban EXPLOIT/honeypot | 1 hit | 15 min/IP |
| Ban BRUTE SSH | ≥30 tentatives | 15 min/IP |
| Ban spike req/h | >500 req/h | 20 min global |
| Ban Suricata sév.1 C2 | 1 alert | 15 min/IP |
| Ban Suricata sév.3 NMAP | ≥3 hits | 15 min/IP (24h ban) |
| Restart service DOWN | service DOWN | 15 min/service |
| Ban rsyslog C2 outbound | 1 détection cross-hôtes | 15 min/IP — ban 48h |
| Ban rsyslog recon Apache | multi-cible ≥2 hôtes | 15 min/IP — ban 24h |
| Alerte vocale TTS | score ÉLEVÉ/CRITIQUE | selon preset actif |
| TTS chain : Antoine→Kokoro→SAPI5 (fallback internet KO) | — | 1 TTS à la fois (blocking=False) |

---

## 9. Fichiers persistés (état survit aux redémarrages)

| Fichier | Contenu | Lieu |
|---------|---------|------|
| `jarvis_soc_actions.json` | Journal toutes actions proactives (rotation 30j) | Windows local |
| `jarvis_soc_autobanned.json` | Cooldowns auto-ban (filtre expiry au boot) | Windows local |
| `proxmox-cpu-history.json` | Historique CPU Proxmox 48 pts (4h) | srv-ngix |
| `net-history.json` | Historique RX/TX réseau | srv-ngix |
| `autoban-log.json` | Journal bans côté serveur | srv-ngix |
| `monitoring.json` | Snapshot sécurité complet | srv-ngix (toutes /5min) |

---

## 10. Conclusion — Analyse de la solidité de l'architecture

### Points forts

**Redondance de détection**
L'architecture superpose trois couches indépendantes : CrowdSec (signatures + AppSec), Suricata (analyse réseau profonde), fail2ban (bruteforce applicatif). Une attaque qui passerait l'une sera captée par les deux autres. Les faux négatifs sont structurellement rares.

**Continuité opérationnelle dashboard ouvert/fermé**
La bascule automatique JS → Python est un mécanisme solide. Le heartbeat JARVIS comme signal de présence est simple et fiable — pas de race condition possible car les cooldowns sont côté Python, persistés sur disque.

**Couverture 4 hôtes**
La centralisation des données fail2ban (SSH depuis monitoring_gen + push JSON Proxmox) donne une vue unifiée sans agent sur chaque hôte. C'est léger et maintenable.

**Suricata en mode IDS (pas IPS inline)**
Le choix de rester en IDS + ban CrowdSec plutôt qu'IPS NFQUEUE est le bon pour une VM prod unique. La latence de réaction (détection → ban) est de l'ordre de 60 secondes max — acceptable pour des attaques qui se déroulent sur des minutes.

**Persistance des états**
`jarvis_soc_autobanned.json` qui survit aux redémarrages évite les doubles bans et préserve les cooldowns. C'est un détail d'implémentation qui aurait pu créer des boucles — bien résolu.

---

### Points de fragilité à surveiller

**Point unique de défaillance : srv-ngix**
Toute la chaîne nginx + CrowdSec + Suricata + monitoring_gen.py est sur une seule VM. Si la VM tombe, plus de protection ni de visibilité. Mitigation actuelle : sauvegardes vzdump hebdomadaires + auto-restart JARVIS des services connus.

**JARVIS dépend de Windows local**
Si la machine Windows est éteinte, l'auto-engine s'arrête. Le dashboard reste lisible depuis un autre poste, mais les bans automatiques Python tombent. Acceptable pour un homelab, à noter en contexte production.

**Suricata 90k règles — faux positifs sév.2**
La recalibration ×10 des seuils sév.2 montre que le volume d'alertes HIGH est élevé (~1400/jour). Les seuils actuels sont corrects mais à réévaluer si de nouvelles sources de règles sont ajoutées.

**Corrélation temporelle — implémentée (v3.3)**
`_soc_rsyslog_check()` corrèle les logs rsyslog multi-hôtes : C2 outbound cross-hôtes → ban 48h · recon multi-cible Apache ≥2 hôtes → ban 24h · campagnes lentes /24 sur 14 jours détectées.

---

### Verdict global

```
┌─────────────────────────────────────────────────────┐
│  SOLIDITÉ GLOBALE DE L'ARCHITECTURE : ██████████ 9/10  │
│                                                     │
│  Détection       ████████████  EXCELLENT (×3 couches) │
│  Réaction        ██████████    TRÈS BON  (<60s ban)   │
│  Couverture      ████████████  EXCELLENT (4 hôtes)    │
│  Résilience      ████████      BON       (1 VM prod)  │
│  Observabilité   ████████████  EXCELLENT (35 tuiles)  │
│  Maintenabilité  ██████████    TRÈS BON  (code clair) │
└─────────────────────────────────────────────────────┘
```

Pour un homelab avec une seule VM de prod, cette architecture dépasse largement le niveau standard. Elle couvre les cas d'usage réels (bots, scanners, bruteforce, C2) avec une réponse automatisée, un journal d'actions persisté, et une observabilité complète. Les limites identifiées (SPOF VM, dépendance Windows) sont inhérentes au contexte homelab et non à des défauts de conception.

---

*Document mis à jour le 2026-05-10 — 0xCyberLiTech*