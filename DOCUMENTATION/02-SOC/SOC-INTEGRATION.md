# Circuit SOC ↔ JARVIS

> Intégration complète entre JARVIS et le dashboard SOC homelab.
> Auto-engine de détection, ban automatique, alertes vocales, injection de contexte sécurité.

---

## Vue d'ensemble

```
Dashboard SOC (srv-nginx)
    │  monitoring.json — poll 30s
    ▼
JARVIS (localhost:5000)
    ├── Mode SOC (phi4:14b) — injection contexte live
    ├── Auto-engine Python (poll 60s) — bans/restarts automatiques
    └── Alertes vocales TTS (seuils ÉLEVÉ/CRITIQUE)
```

---

## Auto-engine SOC

L'auto-engine tourne en **thread Python indépendant** (poll 60s).
Il surveille en continu même quand le dashboard navigateur est fermé.

### Boucle de traitement

```
_soc_monitor_loop() — poll 60s
    │
    ├── _soc_exploit_gap_check()   ← ban EXPLOIT avant vérification seuil
    │
    │── GATE : dashboard ouvert ?
    │
    ├── _soc_autoban()             ← BRUTE/SCAN/honeypot
    ├── _soc_reqhour_check()       ← spike > 500 req/h → ban auto
    ├── _soc_suricata_check()      ← alertes sévérité 1/2/3
    └── _soc_threat_level()        ← alerte vocale (cooldown 30 min)
```

### Déclencheurs de ban automatique

| Condition | Action |
|-----------|--------|
| > 500 requêtes/heure depuis une IP | Ban CrowdSec automatique |
| Tentative Suricata sévérité 1 ou 2 | Ban + alerte vocale |
| Hit sur honeypot | Ban immédiat |
| Service critique down | Restart automatique (whitelist) |

**Garde-fou RFC1918** : les IPs de plages privées ne peuvent jamais être bannies, quelle que soit la condition.

---

## Injection de contexte sécurité

Le contexte SOC est injecté **côté serveur** dans chaque prompt LLM en mode SOC :

- ThreatScore en cours (0–100)
- IPs actives suspectes (filtrées RFC1918)
- Bans récents CrowdSec
- État Kill Chain (PROBE → RECON → SCAN → EXPLOIT → WAF → BRUTE → NEUTRALISÉ)
- Alertes Suricata actives

**Important** : cette injection se fait en side-channel — elle n'entre **jamais** dans l'historique chat.

---

## Routes SOC disponibles

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/soc/monitor` | GET | Relaye monitoring.json en temps réel |
| `/api/soc/ban-ip` | POST | Ban une IP via CrowdSec |
| `/api/soc/unban-ip` | POST | Unban une IP via CrowdSec |
| `/api/soc/restart-service` | POST | Restart un service (whitelist stricte) |
| `/api/soc/force-autoban` | POST | Scan immédiat des candidats au ban |
| `/api/soc/actions` | GET | Journal des actions des 30 derniers jours |
| `/api/soc/ip-history` | GET | Historique 30j d'une IP donnée |

---

## Alertes vocales

JARVIS déclenche une alerte vocale TTS si le ThreatScore dépasse le seuil configuré :

- Niveau **ÉLEVÉ** → voix Antoine fr-CA + message d'alerte
- Niveau **CRITIQUE** → voix Antoine fr-CA + message d'urgence + cooldown 30 min

Le cooldown évite le spam vocal lors d'attaques prolongées.

---

## Persistance des bans automatiques

Les bans effectués par l'auto-engine sont persistés dans `jarvis_soc_autobanned.json`.
Le cooldown de 15 min par IP survit aux redémarrages du serveur JARVIS.

---

*SOC-INTEGRATION.md · 0xCyberLiTech · 2026-06-09*
