# MCP Server — 12 outils Claude Desktop

> Le MCP Server est le pont qui permet à Claude Code (dans VSCode) d'interroger JARVIS
> et d'accéder aux données SOC en temps réel, sans exposer les données brutes vers le cloud.

---

## Architecture

```
Claude Code (VSCode)
    │  protocole MCP (stdio JSON-RPC)
    ▼
jarvis_mcp_server.py  (pythonw — arrière-plan Windows)
    │  HTTP localhost:5000
    ▼
JARVIS (Flask)
    │  SSH local + fichiers + Ollama
    ▼
Données SOC · Infrastructure · Modèles
```

**Principe clé** : JARVIS filtre et agrège en local. Claude ne voit que l'escalade — jamais les données brutes.

---

## Les 12 outils

| Outil | Description |
|-------|-------------|
| `jarvis_chat` | Envoyer un message à JARVIS (chat complet avec contexte LLM) |
| `jarvis_soc_status` | État temps réel : bans actifs, ThreatScore, alertes récentes |
| `jarvis_soc_ask` | Question SOC avec contexte enrichi — injecte l'historique 30j si une IPv4 est détectée |
| `jarvis_stats` | Stats système : CPU, GPU, VRAM, RAM, température RTX |
| `jarvis_infra_status` | État des serveurs SSH (nginx, clt, pa85, Proxmox) |
| `jarvis_proxmox_vms` | État des VMs Proxmox (`qm list` live) |
| `jarvis_read_file` | Lire un fichier sur un serveur via SSH (lecture seule) |
| `jarvis_model_switch` | Changer le modèle Ollama actif (SOC/GÉNÉRAL/CODE) |
| `jarvis_last_response` | Derniers échanges de la conversation JARVIS en cours |
| `jarvis_code_exec` | Écrire + SCP + exécuter un fichier sur le serveur de développement |
| `jarvis_defense_24h` | Résumé défense SOC 24 h : bans, Kill Chain, Suricata, ModSec |
| `jarvis_ioc_status` | Statut IOC (Indicators of Compromise) — enrichissement réputation IP |

---

## Configuration

**Fichier** : `.mcp.json` à la racine du workspace VSCode

```json
{
  "mcpServers": {
    "jarvis": {
      "command": "pythonw",
      "args": ["chemin/vers/JARVIS/scripts/jarvis_mcp_server.py"],
      "env": {}
    }
  }
}
```

`pythonw` : supprime la fenêtre console Windows — requis pour MCP sur Windows (pipes stdio).

---

## Watchdog

Le MCP Server inclut un watchdog qui redémarre automatiquement le processus en cas de crash.
Le server écoute sur le port streamable-HTTP (port 5010) et accepte aussi les connexions stdio.

---

## Identifiant visuel

Chaque réponse JARVIS est encadrée pour la différencier de Claude :

```
╔══════════════════════════════════════╗
║  ◈  JARVIS  —  phi4:14b  ◈           ║
╚══════════════════════════════════════╝
[réponse de JARVIS]
```

Différence visuelle immédiate — important pour l'utilisateur malvoyant.

---

## Principe de séparation — qui fait quoi

| JARVIS traite localement | Claude reçoit en escalade |
|--------------------------|--------------------------|
| Logs bruts → agrégation structurée | Pattern inconnu de JARVIS |
| Patterns SOC connus → auto-ban | Modification du code (jarvis.py, soc.py) |
| Questions SOC état/compteurs | Décision architecturale |
| Debugging simple à modéré | Analyse multi-fichiers complexe |
| Monitoring routine (rien d'anormal) → **0 token Claude** | Infra en panne complète |

---

*MCP-SERVER.md · 0xCyberLiTech · 2026-06-09*
