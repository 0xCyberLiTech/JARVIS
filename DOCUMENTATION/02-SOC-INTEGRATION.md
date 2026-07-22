<div align="center">

  <br></br>

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=50&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS_" alt="Titre dynamique JARVIS" />
  </a>

  <br></br>

  <h2>Assistant IA local · voix · interface holographique · automatisation SOC 24/7</h2>

  <p align="center">
    <a href="https://0xcyberlitech.github.io/">
      <img src="https://img.shields.io/badge/Portfolio-0xCyberLiTech-181717?logo=github&style=flat-square" alt="Portfolio" />
    </a>
    <a href="https://github.com/0xCyberLiTech">
      <img src="https://img.shields.io/badge/Profil-GitHub-181717?logo=github&style=flat-square" alt="Profil GitHub" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/tags">
      <img src="https://img.shields.io/github/v/tag/0xCyberLiTech/JARVIS?sort=semver&label=version&style=flat-square&color=blue" alt="Dernière version" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/blob/main/CHANGELOG.md">
      <img src="https://img.shields.io/badge/%F0%9F%93%84%20Changelog-JARVIS-blue?style=flat-square" alt="Changelog" />
    </a>
    <a href="https://github.com/0xCyberLiTech?tab=repositories">
      <img src="https://img.shields.io/badge/D%C3%A9p%C3%B4ts-publics-blue?style=flat-square" alt="Dépôts publics" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/graphs/contributors">
      <img src="https://img.shields.io/badge/%F0%9F%91%A5%20Contributeurs-cliquez%20ici-007ec6?style=flat-square" alt="Contributeurs" />
    </a>
  </p>

</div>

<div align="center">
  <img src="https://img.icons8.com/fluency/96/000000/cyber-security.png" alt="CyberSec" width="80"/>
</div>

<div align="center">
  <p>
    <strong>IA 100% locale</strong> <img src="https://img.icons8.com/color/24/000000/lock--v1.png"/> &nbsp;•&nbsp; <strong>Voix naturelle · STT · TTS</strong> <img src="https://img.icons8.com/color/24/000000/linux.png"/> &nbsp;•&nbsp; <strong>Automatisation SOC</strong> <img src="https://img.icons8.com/color/24/000000/shield-security.png"/>
  </p>
</div>

---
# Intégration SOC ↔ JARVIS

## Objectif
JARVIS devient le bras armé du dashboard SOC :
- Il lit les métriques de sécurité en temps réel
- Il déclenche des actions défensives (ban IP, restart service)
- Il envoie des alertes vocales si le niveau de menace monte
- Il analyse les patterns d'attaque avec le LLM local (qwen3.5:9b)

---

## Vue d'ensemble

```
Dashboard SOC (monitoring.json)
    │ poll 30s
    ▼
JARVIS (localhost:5000)
    ├── Mode SOC (qwen3.5:9b) — injection contexte live
    ├── Auto-engine Python (poll 60s) — bans/restarts automatiques
    └── Alertes vocales TTS (seuils ÉLEVÉ / CRITIQUE)
```

---

## Auto-engine SOC

L'auto-engine tourne en **thread Python indépendant** — il surveille en continu même quand l'interface navigateur est fermée.

### Boucle de traitement

Extrait — la boucle enchaîne davantage de contrôles que ceux listés ici (le code fait foi) :

```
_soc_monitor_loop() — poll 60s
    │
    ├── Détection EXPLOIT avant seuil (ban même dashboard ouvert)
    │
    ├── _check_threat_level()   ← alerte vocale (cooldown 30 min)
    ├── _check_escalation()     ← IP qui progresse dans la Kill Chain (cooldown 10 min)
    ├── _soc_autoban()          ← BRUTE / SCAN / honeypot
    ├── _soc_reqhour_check()    ← spike req/h au-delà du seuil → ban auto
    └── _soc_suricata_check()   ← alertes IDS sévérité 1/2/3
```

### Déclencheurs de ban automatique

| Condition | Action |
|-----------|--------|
| Requêtes/heure d'une même IP au-delà du seuil configuré | Ban automatique |
| Alerte Suricata **sévérité 1** (critique) | Ban + alerte vocale |
| Suricata **sévérité 3** — scan de ports | Ban temporaire + alerte vocale |
| Suricata **sévérité 2** (HIGH) | Alerte vocale ; **ban seulement au-delà d'un seuil de surge** — une alerte sév.2 isolée ne bannit pas |
| Hit sur honeypot | Ban dès le premier hit |
| Service critique down | Restart automatique (whitelist services) |

> Les seuils (requêtes/heure, surges Suricata, durées de ban, cooldowns) sont des **constantes nommées** du blueprint SOC — elles ne sont pas recopiées ici, pour qu'un ajustement n'ait jamais à être répercuté dans deux endroits.

> **Garde-fou absolu** : les IPs de plages privées (RFC1918) ne peuvent jamais être bannies.

---

## Injection de contexte sécurité

Le contexte SOC est injecté **côté serveur** dans chaque prompt LLM en mode SOC :

- ThreatScore en cours (0–100)
- IPs actives suspectes (filtrées RFC1918)
- Bans récents
- État **Kill Chain v4** — maillons **offensifs** : `RECON → SCAN → EXPLOIT → BRUTE → NEUTRALISÉ`
  *(les couches purement **défensives** — sonde/pare-feu, WAF — ont été **sorties** de la Kill Chain : elles sont agrégées et visualisées à part, pour ne pas faire passer une défense qui a fonctionné pour une étape d'attaque)*
- Alertes IDS actives

**Important** : cette injection se fait en side-channel — elle n'entre **jamais** dans l'historique chat.

---

## Routes SOC

Extrait des routes du blueprint SOC — **pas un inventaire** (la liste réelle est celle des décorateurs de route, elle n'est pas figée ici) :

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/soc/monitor` | GET, POST | **Armement de l'auto-engine** — GET lit l'état (armé ou non), POST l'arme/le désarme (write ⇒ contrôle CSRF). ⚠ Ce n'est **pas** l'endpoint des données de monitoring |
| `/api/soc/context` | GET | Contexte SOC formaté pour injection LLM (source de monitoring indisponible ⇒ **HTTP 503**, jamais un 200 trompeur) |
| `/api/soc/ban-ip` | POST | Ban IP |
| `/api/soc/unban-ip` | POST | Unban IP |
| `/api/soc/restart-service` | POST | Restart service (whitelist stricte) |
| `/api/soc/force-autoban` | POST | Scan immédiat candidats ban |
| `/api/soc/actions` | GET | Journal des actions proactives (conservation 30 jours) + compteurs |
| `/api/soc/ip-history` | POST | Historique CrowdSec + fail2ban d'une IP (endpoint léger pour le MCP) — l'IP voyage dans le **corps** de la requête, pas dans l'URL |

---

## Alertes vocales

| Niveau | Déclencheur | Comportement |
|--------|-------------|--------------|
| **ÉLEVÉ** | ThreatScore > seuil configuré | Message vocal Antoine fr-CA |
| **CRITIQUE** | ThreatScore critique | Message vocal urgent + cooldown 30 min |

Le cooldown évite le spam vocal lors d'attaques prolongées.

---

## Persistance des bans automatiques

Les bans effectués par l'auto-engine sont persistés localement.
Le cooldown de 15 min par IP survit aux redémarrages du serveur JARVIS.

---

**Précédent ←** [01 — Hermès](01-HERMES.md) &nbsp;&nbsp; **Suivant →** [03 — Architecture](03-ARCHITECTURE.md)

---

<div align="center">

<table>
<tr>
<td align="center"><b>🖥️ Infrastructure &amp; Sécurité</b></td>
<td align="center"><b>💻 Développement &amp; Web</b></td>
<td align="center"><b>🤖 Intelligence Artificielle</b></td>
</tr>
<tr>
<td align="center">
  <a href="https://www.kernel.org/"><img src="https://skillicons.dev/icons?i=linux" width="48" title="Linux" /></a>
  <a href="https://www.debian.org"><img src="https://skillicons.dev/icons?i=debian" width="48" title="Debian" /></a>
  <a href="https://www.gnu.org/software/bash/"><img src="https://skillicons.dev/icons?i=bash" width="48" title="Bash" /></a>
  <br/>
  <a href="https://nginx.org"><img src="https://skillicons.dev/icons?i=nginx" width="48" title="Nginx" /></a>
  <a href="https://git-scm.com"><img src="https://skillicons.dev/icons?i=git" width="48" title="Git" /></a>
</td>
<td align="center">
  <a href="https://www.python.org"><img src="https://skillicons.dev/icons?i=python" width="48" title="Python" /></a>
  <a href="https://flask.palletsprojects.com"><img src="https://skillicons.dev/icons?i=flask" width="48" title="Flask" /></a>
  <a href="https://developer.mozilla.org/docs/Web/HTML"><img src="https://skillicons.dev/icons?i=html" width="48" title="HTML5" /></a>
  <br/>
  <a href="https://developer.mozilla.org/docs/Web/CSS"><img src="https://skillicons.dev/icons?i=css" width="48" title="CSS3" /></a>
  <a href="https://developer.mozilla.org/docs/Web/JavaScript"><img src="https://skillicons.dev/icons?i=js" width="48" title="JavaScript" /></a>
  <a href="https://code.visualstudio.com"><img src="https://skillicons.dev/icons?i=vscode" width="48" title="VS Code" /></a>
</td>
<td align="center">
  <a href="https://ollama.com"><img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" /></a>
  <br/><br/>
  <a href="https://anthropic.com"><img src="https://img.shields.io/badge/Anthropic-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic" /></a>
</td>
</tr>
</table>

<br/>

<sub>🔒 Projets proposés par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · Développés en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🔒</sub>

</div>
