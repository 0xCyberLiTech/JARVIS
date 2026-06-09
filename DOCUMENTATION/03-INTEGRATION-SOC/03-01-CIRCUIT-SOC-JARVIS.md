---
title: "Circuit d'intÃ©gration SOC â†” JARVIS"
code: "JARVIS-DOC-03-01"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Valide"
categorie: "IntÃ©gration"
mots_cles: ["soc", "jarvis", "integration", "circuit", "defense-chain"]
---

ï»¿# Circuit logique SOC + JARVIS â€” 0xCyberLiTech
**Date : 2026-05-22 â€” v2.7** Â· routing 4 branches (soc/general/code/code_reasoning) Â· MCP **12 outils** Â· 32 modules Python Â· jarvis.css â†’ 8 fichiers Â· git local + pre-commit + pre-push pytest Â· mÃ©triques courantes (score, lignes, tests, coverage) â†’ [BILAN-TECHNIQUE.md Â§0](BILAN-TECHNIQUE.md)

> **Ã€ lire en premier** : la nouvelle section [HiÃ©rarchie des appels et autonomie](#hi%C3%A9rarchie-des-appels-et-autonomie) clarifie qui appelle qui (Claude / MCP / JARVIS / srv-nginx) et ce qui tombe si X est Ã©teint. Les autres schÃ©mas du document montrent des flux de **donnÃ©es** (ce qui circule), pas des dÃ©pendances d'**exÃ©cution** (qui a besoin de qui pour vivre).

---

## HiÃ©rarchie des appels et autonomie

Cette section rÃ©pond Ã  la question : **Â« qui appelle qui, et qui tombe si tel composant est Ã©teint ? Â»** â€” distinction critique pour comprendre l'autonomie de JARVIS vis-Ã -vis du MCP et de Claude.

### SchÃ©ma de la chaÃ®ne d'appels (sens des flÃ¨ches = sens des appels)

```
                    Claude Desktop / Claude Code               Navigateur (toi)
                    (consommateur externe optionnel)           (consommateur web)
                              â”‚                                       â”‚
                              â”‚ JSON-RPC over HTTP                    â”‚ HTTP direct
                              â”‚ (transport streamable)                â”‚
                              â–¼                                       â”‚
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                         â”‚
                    â”‚  MCP server :5010     â”‚                         â”‚
                    â”‚  jarvis_mcp_server.py â”‚   â† PROXY / BUS         â”‚
                    â”‚  12 outils exposÃ©s    â”‚     d'OUTILS            â”‚
                    â”‚  autonome de Claude   â”‚                         â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                         â”‚
                              â”‚ HTTP REST                             â”‚
                              â”‚ (localhost:5000)                      â”‚
                              â–¼                                       â”‚
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                         â”‚
                    â”‚  JARVIS :5000         â”‚                         â”‚
                    â”‚  jarvis.py + soc.py   â”‚   â† ORCHESTRATEUR       â”‚
                    â”‚  ~73 routes Flask     â”‚     (autoritÃ© locale)   â”‚
                    â”‚  + auto-engine 60s    â”‚                         â”‚
                    â”‚  + 5 modÃ¨les Ollama   â”‚                         â”‚
                    â”‚  + 4 TTS Â· STT Â· RAG  â”‚                         â”‚
                    â”‚  + SSH 5 hÃ´tes        â”‚                         â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                         â”‚
                              â”‚ HTTP GET (cache 30s)                  â”‚
                              â”‚ /api/soc/defense                      â”‚
                              â”‚ /api/soc/context                      â”‚
                              â–¼                                       â–¼
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚  srv-nginx :8080                                 â”‚
                    â”‚  â€¢ defense_24h.json (cron 60s)                  â”‚
                    â”‚  â€¢ monitoring.json (cron 60s)                   â”‚
                    â”‚  â€¢ xdr_events.json / ...                        â”‚
                    â”‚    (router.json retirÃ© 2026-05-17 â€” migration   â”‚
                    â”‚     vers Freebox directe)                       â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                              â–²
                              â”‚ Ã©crit (cron + scripts)
                              â”‚
                    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                    â”‚  defense_aggregator.pyâ”‚
                    â”‚  monitoring_gen.py    â”‚   â† PRODUCTEURS
                    â”‚  (Python sur srv-nginx)â”‚
                    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### RÃ¨gle de lecture

- **Une flÃ¨che pointe dans le sens de l'appel** : `A â”€â”€â–¶ B` signifie Â« A appelle B Â» (donc A consomme un service de B).
- **Aucune flÃ¨che ne remonte** dans le schÃ©ma : JARVIS n'appelle jamais MCP, MCP n'appelle jamais Claude. Le sens des appels est strictement descendant.
- **Une exception au flux principal** : le navigateur dashboard SOC court-circuite JARVIS et appelle srv-nginx directement.

### Tableau des dÃ©pendances rÃ©elles

| Composant | Niveau | Appelle | Est appelÃ© par | Effet si Ã©teint |
|---|---|---|---|---|
| **Claude** (Desktop/Code) | 5 (sommet) | MCP server | *(rien â€” sommet humain/IA)* | JARVIS continue Ã  100 % Â· MCP continue Â· tout est intact |
| **MCP server** :5010 | 4 | JARVIS :5000 | Claude (+ tout client MCP) | Claude perd les 12 outils JARVIS Â· JARVIS continue Ã  100 % |
| **JARVIS** :5000 | 3 | srv-nginx :8080, Ollama, SSH 5 hÃ´tes | MCP, UI JARVIS, dashboard SOC (heartbeat) | MCP perd ses outils SOC Â· UI HS Â· auto-engine HS Â· dashboard SOC continue (lit srv-nginx direct) |
| **srv-nginx** :8080 | 2 | (sert des fichiers) | JARVIS, navigateur dashboard | JARVIS rÃ©pond 503 sur `/api/soc/*` Â· pas de bloc dÃ©fense injectÃ© Â· auto-engine SOC silencieux Â· dashboard SOC vide |
| **defense_aggregator.py** | 1 (base) | rien (cron) | *(produit les JSON)* | `defense_24h.json` se fige Â· les chiffres deviennent obsolÃ¨tes mais restent lisibles |
| **Navigateur** dashboard | alt. | srv-nginx direct | utilisateur | court-circuit total : tu vois les chiffres sans dÃ©pendre de JARVIS ni MCP |

### ScÃ©narios extrÃªmes â€” qui tombe vraiment

| Tu Ã©teinsâ€¦ | JARVIS | MCP | Dashboard SOC | Page DÃ‰FENSE | Claude |
|---|---|---|---|---|---|
| Claude (dÃ©connecte) | âœ… | âœ… | âœ… | âœ… | â€” |
| MCP server | âœ… | â€” | âœ… | âœ… | perd les 12 outils |
| JARVIS | â€” | partiel (perd les outils) | âœ… | âœ… | perd accÃ¨s local |
| srv-nginx | partiel (perd SOC) | partiel | âŒ | âŒ | â€” |
| Producteur (defense_aggregator) | âœ… (chiffres figÃ©s) | âœ… | âœ… (stale) | âœ… (stale) | âœ… |

### Pourquoi JARVIS est l'**orchestrateur** et pas le **consommateur** du MCP

**JARVIS ne consomme pas le MCP.** JARVIS **expose ses capacitÃ©s Ã  travers** le MCP. Le bÃ©nÃ©fice circule dans ce sens :

- **Claude profite du MCP** pour accÃ©der aux 11 fonctions JARVIS (chat, soc_ask, defense_24h, infra, code_execâ€¦)
- **MCP** est un pont neutre (un bus de capacitÃ©s)
- **JARVIS profite de Claude** : via le MCP, Claude devient un *bras d'analyse externe* qui peut interroger, raisonner et exÃ©cuter du code sur l'infra sans intervention manuelle de l'utilisateur

JARVIS reste l'autoritÃ© locale : c'est lui qui hÃ©berge les LLM Ollama, le routing 4 modes, l'auto-engine SOC, les 5 connexions SSH, les 4 TTS, le STT, le RAG, et qui pilote (subprocess.Popen + watchdog psutil) le process MCP enfant lui-mÃªme. **MCP est un produit de JARVIS, pas un fournisseur.**

### Effet de l'Ã©tape 6 (intÃ©gration `defense_24h.json`)

L'Ã©tape 6 ajoute **3 canaux de consommation** d'une mÃªme source (`defense_24h.json` produit cÃ´tÃ© SOC) :

1. **Page web `/defense.html`** : le navigateur lit directement `srv-nginx:8080/defense_24h.json` â€” court-circuit total, aucun composant intermÃ©diaire
2. **JARVIS phi4 (mode SOC)** : `chat_soc_inject.py:_format_defense_block()` ajoute un bloc compact (~400 chars) au system prompt phi4, fetchÃ© via la route locale `/api/soc/defense` (cache 30 s, fetch HTTP direct vers srv-nginx)
3. **Outil MCP `jarvis_defense_24h`** : 11e outil exposÃ© via MCP, qui appelle `/api/soc/defense` sur JARVIS pour servir Claude

**Aucun de ces 3 canaux ne crÃ©e une nouvelle dÃ©pendance montante**. La rÃ¨gle Â« MCP autonome de Claude Â» et Â« JARVIS autonome du MCP Â» est intacte.

---

## SchÃ©ma maÃ®tre

```
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘                         RÃ‰SEAU LAN â€” 192.168.1.x                               â•‘
â•‘                                                                                  â•‘
â•‘   INTERNET                                                                       â•‘
â•‘      â”‚  trafic entrant                                                           â•‘
â•‘      â–¼                                                                           â•‘
â•‘  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                      â•‘
â•‘  â”‚              srv-nginx  192.168.1.50                    â”‚                      â•‘
â•‘  â”‚                                                        â”‚                      â•‘
â•‘  â”‚  nginx â—„â”€â”€â”€ requÃªtes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ â”‚â—„â”€â”€ WAN               â•‘
â•‘  â”‚    â”‚                                                   â”‚                      â•‘
â•‘  â”‚    â”œâ”€â”€â–¶ CrowdSec bouncer â†’ DROP / PASS                â”‚                      â•‘
â•‘  â”‚    â”‚         â”‚                                         â”‚                      â•‘
â•‘  â”‚    â”‚    CrowdSec engine â—„â”€â”€ AppSec WAF (150 CVE)      â”‚                      â•‘
â•‘  â”‚    â”‚         â”‚                                         â”‚                      â•‘
â•‘  â”‚    â”œâ”€â”€â–¶ Suricata IDS (af-packet, 90k rÃ¨gles)          â”‚                      â•‘
â•‘  â”‚    â”‚         â”‚  sÃ©v.1 C2 Â· sÃ©v.2 HIGH Â· sÃ©v.3 NMAP   â”‚                      â•‘
â•‘  â”‚    â”‚         â”‚                                         â”‚                      â•‘
â•‘  â”‚    â””â”€â”€â–¶ fail2ban  (nginx-cve Â· sshd)                  â”‚                      â•‘
â•‘  â”‚                                                        â”‚                      â•‘
â”‚                      â•‘
â•‘  â”‚  monitoring_gen.py (cron */5min)                       â”‚                      â•‘
â•‘  â”‚    â”œâ”€â”€ agrÃ¨ge : nginx+CrowdSec+Suricata+F2B+Proxmox  â”‚                      â•‘
â•‘  â”‚    â””â”€â”€ Ã©crit : monitoring.json â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–ºâ”‚â”€â”€ HTTP 8080          â•‘
â•‘  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                      â•‘
â•‘            â–²                    â–²                â–²                               â•‘
â•‘            â”‚ SSH ban/restart    â”‚ fetch JSON     â”‚ push JSON /5min              â•‘
â•‘            â”‚                   â”‚                â”‚                               â•‘
â•‘  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â•‘
â•‘  â”‚  JARVIS            â”‚  â”‚  SOC Dashboard  â”‚  â”‚  Proxmox VE  192.168.1.20   â”‚ â•‘
â•‘  â”‚  localhost:5000    â”‚  â”‚  browser        â”‚  â”‚                              â”‚ â•‘
â•‘  â”‚                    â”‚â—„â”€â”¤                 â”‚  â”‚  fail2ban-monitor-push.sh    â”‚ â•‘
â•‘  â”‚  Flask + Ollama    â”‚  â”‚  35 tuiles      â”‚  â”‚  ufw-monitor-push.sh         â”‚ â•‘
â•‘  â”‚  phi4:14b          â”‚  â”‚                 â”‚  â”‚  (cron */5min â†’ srv-nginx)    â”‚ â•‘
â•‘  â”‚                    â”‚  â”‚  computeThreat  â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â•‘
â•‘  â”‚  auto-engine       â”‚  â”‚  Score 0-100    â”‚                                   â•‘
â•‘  â”‚  _soc_monitor_loop â”‚  â”‚                 â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â•‘
â•‘  â”‚  (poll 60s)        â”‚  â”‚  checkAutoBan() â”‚  â”‚  clt  192.168.1.12           â”‚ â•‘
â•‘  â”‚                    â”‚  â”‚  checkReqPerH() â”‚  â”‚  pa85 192.168.1.13           â”‚ â•‘
â•‘  â”‚  TTS : Antoine (edge)â”‚  â”‚  â”€â”€â–¶ JARVIS ban â”‚  â”‚  fail2ban apache jails       â”‚ â•‘
â•‘  â”‚  Onglet â—ˆ SOC      â”‚  â”‚                 â”‚  â”‚  (SSH depuis monitoring_gen) â”‚ â•‘
â•‘  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â•‘
â•‘            â”‚                                                                     â•‘
â•‘            â”‚  windows-disk-report.ps1 (push /var/www/monitoring/)               â•‘
â•‘            â”‚  â—„â”€â”€ GPU RTX5080 Â· CPU Â· RAM Â· disk Â· backup status               â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
```

### LÃ©gende des flux

| FlÃ¨che | Signification |
|--------|--------------|
| `â”€â”€â–¶` | DonnÃ©es / commande |
| `â—„â”€â”€` | RÃ©ception / lecture |
| SSH ban | JARVIS â†’ `cscli decisions add -i IP` sur srv-nginx |
| SSH restart | JARVIS â†’ `systemctl restart <service>` sur srv-nginx |
| fetch JSON | Dashboard browser â†’ `monitoring.json` toutes 30s |
| push JSON | Proxmox/Windows â†’ srv-nginx via SCP/SSH toutes 5min |

### RÃ¨gle dashboard ouvert / fermÃ©

```
Dashboard OUVERT  â”€â”€â–¶  JS checkAutoBan() + checkReqPerHour() actifs
                        JARVIS reÃ§oit heartbeat â†’ mode passif (pas de doublon)

Dashboard FERMÃ‰   â”€â”€â–¶  JARVIS _soc_monitor_loop() prend le relais
                        Python _soc_autoban() + _soc_reqhour_check()
                        + _soc_suricata_check() + _soc_service_check()
```

---

## Vue d'ensemble

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                        SOURCES DE DONNÃ‰ES                           â”‚
â”‚                                                                     â”‚
â”‚  nginx logs  CrowdSec  fail2banÃ—4  Suricata  Proxmox  Freebox  WAN â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â”‚
                               â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚              monitoring_gen.py  (srv-nginx, cron */5min)             â”‚
â”‚                                                                     â”‚
â”‚  â€¢ Parse nginx access.log â†’ trafic, proto_breakdown, kill_chain     â”‚
â”‚  â€¢ API CrowdSec local â†’ dÃ©cisions, machines, bouncers               â”‚
â”‚  â€¢ fail2ban-client local + SSH clt/pa85 â†’ jails 4 hÃ´tes            â”‚
â”‚  â€¢ fail2ban Proxmox â† push JSON /5min (proxmox-fail2ban.json)       â”‚
â”‚  â€¢ Suricata eve.json â†’ sÃ©v.1/2/3, top IPs, MITRE, recent_scans,    â”‚
â”‚                         enabled_sources                             â”‚
â”‚  â€¢ API Proxmox HTTPS â†’ CPU/RAM/VMs + SSH sensors tempÃ©rature        â”‚
â”‚  â€¢ push windows-disk.json (Windows â†’ srv-nginx)                      â”‚
â”‚  â€¢ Freebox API locale, GeoIP, CVE/threat feeds, SSL check           â”‚
â”‚                                                                     â”‚
â”‚  â”€â”€â–¶  gÃ©nÃ¨re  /var/www/monitoring/monitoring.json  (toutes /5min)   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                               â”‚
              â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
              â”‚                                 â”‚
              â–¼                                 â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   SOC Dashboard         â”‚      â”‚   JARVIS  (Windows localhost:5000)â”‚
â”‚   monitoring-index.html â”‚      â”‚   jarvis.py â€” Flask + Ollama      â”‚
â”‚   (browser client)      â”‚      â”‚   phi4:14b                        â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## 1. Collecte des donnÃ©es (srv-nginx)

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  srv-nginx 192.168.1.50                               â”‚
â”‚                                                      â”‚
â”‚  nginx â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ access.log               â”‚
â”‚  CrowdSec â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ /run/crowdsec/sock        â”‚
â”‚  fail2ban â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ fail2ban-client status    â”‚
â”‚  Suricata IDS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ /var/log/suricata/eve.jsonâ”‚
â”‚                                                      â”‚
â”‚  SSH â”€â”€â–¶ clt (192.168.1.12)  fail2ban + apache jails â”‚
â”‚  SSH â”€â”€â–¶ pa85 (192.168.1.13) fail2ban + apache jails â”‚
â”‚                                                      â”‚
â”‚  â—€â”€â”€ push Proxmox cron /5min â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€  â”‚
â”‚       proxmox-fail2ban.json                          â”‚
â”‚       proxmox-ufw.json                               â”‚
â”‚                                                      â”‚
â”‚  â—€â”€â”€ push Windows /5min â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€  â”‚
â”‚       windows-disk.json (CPU/RAM/GPU/disk/backup)    â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

---

## 2. Dashboard SOC (browser)

```
Browser â”€â”€â–¶ fetch monitoring.json (toutes les 30s)
              â”‚
              â”œâ”€â”€ render() â”€â”€â–¶ 35 tuiles mises Ã  jour
              â”‚
              â”œâ”€â”€ computeThreatScore()
              â”‚     Sources : CrowdSec + Suricata sÃ©v.1Ã—5 + sÃ©v.2Ã—recal
              â”‚               + F2B 4 hÃ´tes + Apache bots + WAF AppSec
              â”‚               + services DOWN + anomalies firewall
              â”‚     â”€â”€â–¶ score 0-100 â†’ FAIBLE / MODÃ‰RÃ‰ / Ã‰LEVÃ‰ / CRITIQUE
              â”‚
              â”œâ”€â”€ checkAutoBan()           â”€â”€â–¶ si dashboard OUVERT
              â”‚     EXPLOIT CVE (1 hit) â†’ ban
              â”‚     honeypot (1 hit)    â†’ ban
              â”‚     BRUTE â‰¥30          â†’ ban
              â”‚     Suricata sÃ©v.1     â†’ ban
              â”‚     â”€â”€â–¶ POST localhost:5000/api/soc/ban-ip
              â”‚
              â”œâ”€â”€ checkReqPerHour()        â”€â”€â–¶ si dashboard OUVERT
              â”‚     spike >500 req/h â†’ ban top 3 IPs (EXPLOIT>BRUTE>SCAN)
              â”‚     â”€â”€â–¶ POST localhost:5000/api/soc/ban-ip
              â”‚
              â””â”€â”€ JARVIS heartbeat POST /api/soc/heartbeat (toutes 30s)
                    TTL 90s â€” dashboard ouvert = JARVIS en mode passif
```

---

## 3. JARVIS auto-engine (Python, dashboard FERMÃ‰)

```
_soc_monitor_loop()  â”€â”€  poll monitoring.json via SSH toutes les 60s
         â”‚
         â”œâ”€â”€ _soc_autoban(data)
         â”‚     MÃªme logique que JS checkAutoBan()
         â”‚     EXPLOIT / honeypot / BRUTE / Suricata sÃ©v.1
         â”‚     â”€â”€â–¶ _ssh_nginx("cscli decisions add -i IP")
         â”‚     â”€â”€â–¶ _soc_log("ban_ip", ...) â†’ jarvis_soc_actions.json
         â”‚
         â”œâ”€â”€ _soc_reqhour_check(data)
         â”‚     spike >500 req/h â†’ ban top 3 IPs kill chain
         â”‚     + Suricata recent_scans IPs comme candidats EXPLOIT
         â”‚     â”€â”€â–¶ _ssh_nginx("cscli decisions add -i IP")
         â”‚
         â”œâ”€â”€ _soc_suricata_check(data)
         â”‚     sÃ©v.1 C2/Trojan â†’ ban immÃ©diat
         â”‚     sÃ©v.3 NMAP (recent_scans) â‰¥3 hits â†’ ban 24h
         â”‚     sÃ©v.2 recal : >3000/+10pts  >1500/+7pts  >600/+4pts
         â”‚     â”€â”€â–¶ _ssh_nginx("cscli decisions add -i IP -d 24h")
         â”‚
â”œâ”€â”€ _soc_rsyslog_check(data)
         â”‚     C2 outbound cross-hÃ´tes â†’ ban 48h
         â”‚     recon multi-cible Apache â†’ ban 24h
         â”‚     (rsyslog multi-hÃ´tes v1.6.1 â€” 5 hÃ´tes)
         â”‚
         â””â”€â”€ _soc_service_check(data)
               service DOWN + in _ALLOWED_SERVICES
               â”€â”€â–¶ _ssh_nginx("systemctl restart <service>")
               cooldown 15min par service
```

---

## 3bis. Modes JARVIS â€” routing 4 branches (sessions 28-29)

JARVIS expose 4 modes â€” un seul actif Ã  la fois, persistÃ© dans `_jarvis_mode` (variable globale `jarvis.py:3082`) et exposÃ© via `GET/POST /api/mode`.

| Mode | ModÃ¨le Ollama | VRAM | Comportement SOC |
|------|---------------|------|------------------|
| **SOC** (dÃ©faut) | `phi4:14b` | 9.1 GB | **ACTIF** â€” auto-engine + alertes vocales + injection contexte monitoring.json |
| **GENERAL** | `gemma4:latest` | 9.6 GB | **SUSPENDU** â€” conversation fluide + vision, zÃ©ro action SOC |
| **CODE** | `qwen2.5-coder:14b` | 9.0 GB | **SUSPENDU** â€” code + infogÃ©rance srv-dev-1 (SCP+exec), zÃ©ro action SOC |
| **CODE REASONING** (CR) | `qwen3:8b` | ~5 GB | **SUSPENDU** â€” single-pass thinking masquÃ© `<think>â€¦</think>`, zÃ©ro action SOC |

âš  **RÃ¨gle absolue** : la surveillance SOC (auto-engine, alertes vocales, ban auto, monitoring live) n'est active qu'en mode SOC. Les 3 autres modes sont **100% suspendus cÃ´tÃ© SOC** â€” c'est un comportement voulu (pas de conflits, pas de bruit pendant le code/conversation).

### SpÃ©cificitÃ© mode CODE REASONING (qwen3:8b)

- Pipeline `code_reasoning.generate()` (module `scripts/code_reasoning.py`) â€” sortie SSE en streaming
- Thinking tokens `<think>â€¦</think>` filtrÃ©s cÃ´tÃ© serveur, JAMAIS envoyÃ©s au client
- Bypass `chat_soc_inject.inject()` et `proxmox_api.inject()` â€” zÃ©ro injection contexte (cf. modules dÃ©diÃ©s)
- Cible : refactoring multi-fichiers oÃ¹ le LLM doit "penser longtemps" sans contamination par contexte SOC/Proxmox

### Switch mode

- **UI** : 4 boutons dans tab CHAT (`#btn-mode-soc/general/code/code-reasoning`)
- **API** : `POST /api/mode` body `{"mode":"soc|general|code|code_reasoning"}`
- **Side-effect mode CODE** : `setModeCode()` JS appelle aussi `devTerminalOpen()` qui ouvre le WebSocket SSH `/ws/ssh/dev1` vers srv-dev-1

Voir [`docs/ROUTING-JARVIS.md`](docs/ROUTING-JARVIS.md) pour le dÃ©tail bypass Python (9 catÃ©gories) et sÃ©curitÃ© (RFC1918, _BLOCKED_SSH, whitelists).

---

## 4. Circuit ban complet (de la dÃ©tection au blocage effectif)

```
DÃ‰TECTION
   â”‚
   â”œâ”€â”€ [Source A] nginx log â†’ CrowdSec parser â†’ dÃ©cision locale
   â”‚
   â”œâ”€â”€ [Source B] Suricata sÃ©v.1 C2/Trojan â†’ JARVIS _soc_suricata_check
   â”‚
   â”œâ”€â”€ [Source C] Suricata sÃ©v.3 NMAP â‰¥3 hits â†’ JARVIS recent_scans
   â”‚
   â”œâ”€â”€ [Source D] spike trafic >500 req/h â†’ JS checkReqPerHour / Python _soc_reqhour_check
   â”‚
   â””â”€â”€ [Source E] EXPLOIT/honeypot/BRUTE â†’ JS checkAutoBan / Python _soc_autoban
                               â”‚
                               â–¼
                  JARVIS POST /api/soc/ban-ip  (si dashboard ouvert)
                  OU
                  _ssh_nginx() direct            (si dashboard fermÃ©)
                               â”‚
                               â–¼
                  srv-nginx : cscli decisions add -i <IP> [-d <durÃ©e>]
                               â”‚
                               â–¼
                  CrowdSec bouncer nginx â†’ DROP immÃ©diat
                  fail2ban bridge crowdsec-sync â†’ sync jails
                               â”‚
                               â–¼
                  _soc_log() â†’ jarvis_soc_actions.json
                  TTS vocale si score Ã‰LEVÃ‰/CRITIQUE
                  Onglet â—ˆ SOC jarvis.html mis Ã  jour
```

---

## 5. Flux donnÃ©es Proxmox â†’ SOC

```
Proxmox VE (192.168.1.20)
      â”‚
      â”œâ”€â”€ fail2ban-monitor-push.sh  (cron /5min)
      â”‚     â”€â”€â–¶ SSH srv-nginx â†’ /var/www/monitoring/proxmox-fail2ban.json
      â”‚
      â””â”€â”€ ufw-monitor-push.sh       (cron /5min)
            â”€â”€â–¶ SSH srv-nginx â†’ /var/www/monitoring/proxmox-ufw.json
                   â”‚
                   â–¼
            monitoring_gen.py lit ces fichiers â†’ intÃ©grÃ© dans monitoring.json
            â”€â”€â–¶ tuile FAIL2BAN (panel Proxmox) + tuile FIREWALL
```

---

## 6. Flux donnÃ©es Windows â†’ SOC

```
Windows (192.168.1.x â€” machine locale)
      â”‚
      â””â”€â”€ windows-disk-report.ps1  (tÃ¢che planifiÃ©e ou manuel)
            â”€â”€â–¶ SCP windows-disk.json â†’ srv-nginx
                   â”‚
                   â–¼
            monitoring_gen.py lit windows-disk.json
            â”€â”€â–¶ tuile WINDOWS RESSOURCES (CPU/RAM/GPU/disk/backup)

      JARVIS localhost:5000
            â”‚
            â””â”€â”€ GET /api/stats  (polling SOC dashboard toutes 30s)
                   â”€â”€â–¶ tuile JARVIS (statut, GPU, modÃ¨le actif)
```

---

## 7. Rapport quotidien

```
soc-daily-report.py  (cron 08h00 quotidien)
      â”‚
      â”œâ”€â”€ Lit monitoring.json (snapshot courant)
      â”œâ”€â”€ Sections : trafic 24h + CrowdSec + fail2ban 4 hÃ´tes
      â”‚              + Suricata (sÃ©v.1/2/3, top IPs, sources actives)
      â”‚              + SSL + CVE sync + services
      â”œâ”€â”€ Niveau CRITIQUE si surSev1 > 0
      â””â”€â”€ â”€â”€â–¶ email HTML envoyÃ©
```

---

## 8. RÃ©sumÃ© des cooldowns et seuils

| MÃ©canisme | Seuil | Cooldown |
|-----------|-------|---------|
| Ban EXPLOIT/honeypot | 1 hit | 15 min/IP |
| Ban BRUTE SSH | â‰¥30 tentatives | 15 min/IP |
| Ban spike req/h | >500 req/h | 20 min global |
| Ban Suricata sÃ©v.1 C2 | 1 alert | 15 min/IP |
| Ban Suricata sÃ©v.3 NMAP | â‰¥3 hits | 15 min/IP (24h ban) |
| Restart service DOWN | service DOWN | 15 min/service |
| Ban rsyslog C2 outbound | 1 dÃ©tection cross-hÃ´tes | 15 min/IP â€” ban 48h |
| Ban rsyslog recon Apache | multi-cible â‰¥2 hÃ´tes | 15 min/IP â€” ban 24h |
| Alerte vocale TTS | score Ã‰LEVÃ‰/CRITIQUE | selon preset actif |
| TTS chain : Antoineâ†’Kokoroâ†’SAPI5 (fallback internet KO) | â€” | 1 TTS Ã  la fois (blocking=False) |

---

## 9. Fichiers persistÃ©s (Ã©tat survit aux redÃ©marrages)

| Fichier | Contenu | Lieu |
|---------|---------|------|
| `jarvis_soc_actions.json` | Journal toutes actions proactives (rotation 30j) | Windows local |
| `jarvis_soc_autobanned.json` | Cooldowns auto-ban (filtre expiry au boot) | Windows local |
| `proxmox-cpu-history.json` | Historique CPU Proxmox 48 pts (4h) | srv-nginx |
| `net-history.json` | Historique RX/TX rÃ©seau | srv-nginx |
| `autoban-log.json` | Journal bans cÃ´tÃ© serveur | srv-nginx |
| `monitoring.json` | Snapshot sÃ©curitÃ© complet | srv-nginx (toutes /5min) |

---

## 10. Conclusion â€” Analyse de la soliditÃ© de l'architecture

### Points forts

**Redondance de dÃ©tection**
L'architecture superpose trois couches indÃ©pendantes : CrowdSec (signatures + AppSec), Suricata (analyse rÃ©seau profonde), fail2ban (bruteforce applicatif). Une attaque qui passerait l'une sera captÃ©e par les deux autres. Les faux nÃ©gatifs sont structurellement rares.

**ContinuitÃ© opÃ©rationnelle dashboard ouvert/fermÃ©**
La bascule automatique JS â†’ Python est un mÃ©canisme solide. Le heartbeat JARVIS comme signal de prÃ©sence est simple et fiable â€” pas de race condition possible car les cooldowns sont cÃ´tÃ© Python, persistÃ©s sur disque.

**Couverture 4 hÃ´tes**
La centralisation des donnÃ©es fail2ban (SSH depuis monitoring_gen + push JSON Proxmox) donne une vue unifiÃ©e sans agent sur chaque hÃ´te. C'est lÃ©ger et maintenable.

**Suricata en mode IDS (pas IPS inline)**
Le choix de rester en IDS + ban CrowdSec plutÃ´t qu'IPS NFQUEUE est le bon pour une VM prod unique. La latence de rÃ©action (dÃ©tection â†’ ban) est de l'ordre de 60 secondes max â€” acceptable pour des attaques qui se dÃ©roulent sur des minutes.

**Persistance des Ã©tats**
`jarvis_soc_autobanned.json` qui survit aux redÃ©marrages Ã©vite les doubles bans et prÃ©serve les cooldowns. C'est un dÃ©tail d'implÃ©mentation qui aurait pu crÃ©er des boucles â€” bien rÃ©solu.

---

### Points de fragilitÃ© Ã  surveiller

**Point unique de dÃ©faillance : srv-nginx**
Toute la chaÃ®ne nginx + CrowdSec + Suricata + monitoring_gen.py est sur une seule VM. Si la VM tombe, plus de protection ni de visibilitÃ©. Mitigation actuelle : sauvegardes vzdump hebdomadaires + auto-restart JARVIS des services connus.

**JARVIS dÃ©pend de Windows local**
Si la machine Windows est Ã©teinte, l'auto-engine s'arrÃªte. Le dashboard reste lisible depuis un autre poste, mais les bans automatiques Python tombent. Acceptable pour un homelab, Ã  noter en contexte production.

**Suricata 90k rÃ¨gles â€” faux positifs sÃ©v.2**
La recalibration Ã—10 des seuils sÃ©v.2 montre que le volume d'alertes HIGH est Ã©levÃ© (~1400/jour). Les seuils actuels sont corrects mais Ã  rÃ©Ã©valuer si de nouvelles sources de rÃ¨gles sont ajoutÃ©es.

**CorrÃ©lation temporelle â€” implÃ©mentÃ©e (v3.3)**
`_soc_rsyslog_check()` corrÃ¨le les logs rsyslog multi-hÃ´tes : C2 outbound cross-hÃ´tes â†’ ban 48h Â· recon multi-cible Apache â‰¥2 hÃ´tes â†’ ban 24h Â· campagnes lentes /24 sur 14 jours dÃ©tectÃ©es.

---

### Verdict global

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚  SOLIDITÃ‰ GLOBALE DE L'ARCHITECTURE : â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ 9/10  â”‚
â”‚                                                     â”‚
â”‚  DÃ©tection       â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ  EXCELLENT (Ã—3 couches) â”‚
â”‚  RÃ©action        â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ    TRÃˆS BON  (<60s ban)   â”‚
â”‚  Couverture      â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ  EXCELLENT (4 hÃ´tes)    â”‚
â”‚  RÃ©silience      â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ      BON       (1 VM prod)  â”‚
â”‚  ObservabilitÃ©   â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ  EXCELLENT (35 tuiles)  â”‚
â”‚  MaintenabilitÃ©  â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆ    TRÃˆS BON  (code clair) â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

Pour un homelab avec une seule VM de prod, cette architecture dÃ©passe largement le niveau standard. Elle couvre les cas d'usage rÃ©els (bots, scanners, bruteforce, C2) avec une rÃ©ponse automatisÃ©e, un journal d'actions persistÃ©, et une observabilitÃ© complÃ¨te. Les limites identifiÃ©es (SPOF VM, dÃ©pendance Windows) sont inhÃ©rentes au contexte homelab et non Ã  des dÃ©fauts de conception.

---

*Document mis Ã  jour le 2026-05-14 â€” 0xCyberLiTech*
