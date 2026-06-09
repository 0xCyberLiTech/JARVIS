# Référence technique — API Routes JARVIS

> Référence des routes Flask principales, structures de données et conventions API.

---

## Routes principales

### Chat & LLM

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/chat` | POST | Chat principal — SSE streaming, routing LLM, injection SOC |
| `/api/mode` | GET/POST | Lire/changer le mode actif (soc/general/code/cr) |
| `/api/stop` | POST | Interrompre la génération LLM en cours |

### TTS / STT

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/speak` | POST | Synthèse vocale TTS (edge-tts → Kokoro → SAPI5) |
| `/api/speak/stop` | POST | Arrêt immédiat du TTS en cours |
| `/api/tts` | POST | TTS avec paramètres DSP complets |
| `/api/tts-log` | GET | Dernières N lignes du log TTS |
| `/api/voices` | GET/POST | Lister/changer la voix active |
| `/api/stt` | POST | Transcription audio → texte (faster-whisper) |

### Système & Monitoring

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/stats` | GET | Stats système : CPU, RAM, GPU, VRAM, température |
| `/api/status` | GET | État JARVIS : uptime, modèle actif, mode, RAG |
| `/api/models` | GET | Liste des modèles Ollama disponibles |

### RAG & Mémoire

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/rag/status` | GET | État du moteur RAG (chunks, TTL, dernier rechargement) |
| `/api/rag/refresh` | POST | Forcer le rechargement des chunks RAG |
| `/api/rag/note` | POST | Ajouter une note dans la base RAG |
| `/api/memory` | GET/POST/DELETE | Lire/créer/supprimer une entrée mémoire |
| `/api/memory-summary` | GET | Résumé des mémoires actives |
| `/api/memory/stats` | GET | Statistiques mémoire (entrées, taille, TTL) |

### SOC

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/soc/monitor` | GET | Données monitoring.json temps réel |
| `/api/soc/ban-ip` | POST | Ban IP via CrowdSec |
| `/api/soc/unban-ip` | POST | Unban IP via CrowdSec |
| `/api/soc/restart-service` | POST | Restart service (whitelist stricte) |
| `/api/soc/actions` | GET | Journal actions 30 derniers jours |
| `/api/soc/ip-history` | GET | Historique 30j d'une IP |

### MCP

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/soc/context` | GET | Contexte SOC pour injection MCP |
| `/api/soc/ip-history` | GET | Historique IP (utilisé par `jarvis_soc_ask`) |

---

## Structures de données clés

### Réponse chat (SSE)

```
data: {"token": "...", "done": false}
data: {"token": "", "done": true, "model": "phi4:14b", "tokens": 142}
```

### Stats système

```json
{
  "cpu_percent": 12.5,
  "ram_percent": 45.2,
  "gpu_util": 8,
  "vram_used_gb": 9.8,
  "vram_total_gb": 16.0,
  "gpu_temp_c": 42,
  "gpu_power_w": 65
}
```

### Statut RAG

```json
{
  "status": "ready",
  "chunks": 599,
  "last_reload": "2026-06-09T10:23:41",
  "ttl_remaining_s": 187,
  "model": "mxbai-embed-large"
}
```

---

## Conventions

- Toutes les routes retournent du JSON sauf SSE (`/api/chat`)
- Authentification : aucune (usage local LAN uniquement)
- Erreurs : `{"ok": false, "error": "message"}` avec code HTTP approprié
- SSE : `Content-Type: text/event-stream` · `Cache-Control: no-cache`

---

## Modules Python — 33 modules

| Catégorie | Modules |
|-----------|---------|
| **Orchestrateur** | `jarvis.py` (75 routes + DI) |
| **Blueprint SOC** | `blueprints/soc.py` |
| **Chat / LLM** | `chat/orchestrator.py`, `chat/routing.py`, `chat/soc_inject.py`, `chat/soc_context.py` |
| **Bypass Hermès** | `bypass/morning_brief.py`, `bypass/learn.py`, `bypass/sysctrl.py`, `bypass/wrappers.py` |
| **RAG** | `rag/engine.py`, `rag/indexer.py`, `rag/retriever.py` |
| **Voice** | `voice/tts_engines.py`, `voice/stt.py`, `voice/routes.py`, `voice/voice_lab.py` |
| **Infra** | `infra/ssh_runner.py`, `infra/proxmox.py`, `infra/circuit_breaker.py` |
| **Sécurité** | `security_whitelists.py` |
| **Monitoring** | `runtime_stats.py`, `gpu_monitor.py` |

---

*REFERENCE-TECHNIQUE.md · 0xCyberLiTech · 2026-06-09*
