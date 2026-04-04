<div align="center">

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=30&duration=6000&pause=1000000000&color=00FF88&center=true&vCenter=true&width=900&lines=%3EJARVIS+—+Assistant+IA+Local_" alt="JARVIS" />
  </a>

  <h3>Assistant IA personnel — Architecture Iron Man, stack 100% locale</h3>

  <p>
    <img src="https://img.shields.io/badge/LLM-Ollama%20local-00FF88?style=flat-square" />
    <img src="https://img.shields.io/badge/TTS-edge--tts%20%7C%20Piper-blue?style=flat-square" />
    <img src="https://img.shields.io/badge/STT-faster--whisper-orange?style=flat-square" />
    <img src="https://img.shields.io/badge/Audio-DeepFilterNet-purple?style=flat-square" />
    <img src="https://img.shields.io/badge/Backend-Flask%20Python-lightgrey?style=flat-square&logo=python" />
    <img src="https://img.shields.io/badge/GPU-RTX%205080%20CUDA%2012-76B900?style=flat-square&logo=nvidia" />
    <img src="https://img.shields.io/badge/Statut-Production-brightgreen?style=flat-square" />
  </p>

</div>

---

## Vue d'ensemble

JARVIS est un assistant IA personnel inspiré de l'Iron Man universe — interface holographique,  
voix synthétique naturelle, écoute vocale continue, intégration complète avec le SOC de sécurité.

> 100% local — aucune donnée n'est envoyée vers des services cloud. LLM, TTS et STT tournent sur la machine.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Interface Web (navigateur)                 │
│          UI holographique — 10 onglets — ~17 400 lignes      │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP (localhost:5000)
┌──────────────────────────▼──────────────────────────────────┐
│                  Flask Backend (jarvis.py)                    │
│              ~3 600 lignes — 55 routes — 124 fonctions       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Ollama LLM  │  │  edge-TTS    │  │  faster-whisper  │  │
│  │  local       │  │  + DeepFilter│  │  STT "small" FR  │  │
│  │  phi4-reason │  │  NR audio    │  │  CUDA accéléré   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└──────────────────────────┬──────────────────────────────────┘
                           │ SSH / API
┌──────────────────────────▼──────────────────────────────────┐
│                    SOC (srv-ngix)                             │
│         Ban-IP / Unban-IP / Restart-Service / Alertes        │
└─────────────────────────────────────────────────────────────┘
```

---

## Stack technique

| Composant | Technologie | Détail |
|-----------|-------------|--------|
| **Backend** | Python 3.11 + Flask | 55 routes, sessions, streaming SSE |
| **LLM** | Ollama (local) | phi4-reasoning:plus (actif), deepseek-r1:14b, mistral-small3.1:24b... |
| **TTS** | edge-tts | fr-CA-AntoineNeural — voix naturelle |
| **TTS fallback** | Piper / SAPI5 | Hors ligne total |
| **STT** | faster-whisper | Modèle "small" FR, CUDA 12, accélération GPU |
| **Audio NR** | DeepFilterNet | Réduction de bruit temps réel (RTX 5080) |
| **UI** | HTML/CSS/JS | Interface holographique ~17 400 lignes, 10 onglets |
| **GPU** | RTX 5080 16 GB GDDR7 | Inférence LLM + STT + NR accélérés CUDA |

---

## Fonctionnalités principales

### Conversation & LLM
- Conversation continue avec contexte persistant
- Streaming de la réponse (affichage token par token)
- Paramètres LLM configurables (température, context window, num_predict)
- Changement de modèle à chaud (sans redémarrage)
- Mémoire de session — JARVIS se souvient du contexte de la conversation

### Voix
- **TTS** : synthèse vocale naturelle (fr-CA-AntoineNeural) avec DSP audio
- **STT** : dictée vocale continue — transcription automatique vers le chat
- **DeepFilterNet** : suppression de bruit micro en temps réel
- Égaliseur audio séparé Voix/Musique
- File d'attente TTS avec verrou anti-dédoublement

### Intégration SOC (onglet ◈ SOC)
- Actions proactives automatiques : ban-IP si > seuil d'attaque, restart service si down
- Journal des actions SOC avec horodatage
- Analyse LLM sur demande des logs de sécurité
- Alertes vocales si niveau de menace ÉLEVÉ ou CRITIQUE
- Quick prompts contextuels : "Analyse les dernières alertes CrowdSec", "Explique cette IP"

### Interface
- 10 onglets : Chat, SOC, Paramètres, Modèles, Audio, Logs, etc.
- Mode sombre holographique (thème Iron Man)
- Raccourcis clavier
- Responsive

---

## Modèles LLM disponibles (Ollama local)

| Modèle | Usage |
|--------|-------|
| `phi4-reasoning:plus` | **Actif par défaut** — raisonnement, analyse sécurité |
| `deepseek-r1:14b` | Raisonnement approfondi |
| `phi4:14b` | Polyvalent rapide |
| `mistral-small3.1:24b` | Multimodal |
| `qwen2.5:14b` | Code et analyse |
| `gemma3:12b` | Conversation générale |

---

## Intégration SOC — Actions automatiques

JARVIS surveille en arrière-plan les métriques du dashboard SOC et déclenche des actions :

```
Si taux de ban CrowdSec > seuil → analyse LLM → ban automatique
Si service détecté DOWN → restart automatique via SSH
Si niveau de menace ÉLEVÉ → alerte vocale TTS
Si pic d'attaque détecté → notification + log dans l'onglet SOC
```

---

## Sécurité

- Bind sur `127.0.0.1` uniquement — non exposé au réseau
- Aucune API cloud — LLM, TTS, STT entièrement locaux
- Aucun token ou credential dans le code source
- Actions SOC (ban/unban) protégées par validation interne

---

## Prérequis

```
Python 3.11
Ollama (avec au moins un modèle)
CUDA 12 (pour accélération GPU — fonctionne aussi sans)
Git Bash (Windows) ou terminal Linux
```

---

## Lancement

```bash
cd scripts
python jarvis.py
# → http://localhost:5000
```

---

<div align="center">
  <a href="https://github.com/0xCyberLiTech/SOC">
    <img src="https://img.shields.io/badge/Voir%20aussi-SOC%20Dashboard-00D9FF?style=for-the-badge&logo=github" />
  </a>
  <a href="https://github.com/0xCyberLiTech">
    <img src="https://img.shields.io/badge/Profil-0xCyberLiTech-181717?style=for-the-badge&logo=github" />
  </a>
</div>

<div align="center">
  <br/>
  <b>🤖 Projet homelab par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> — IA locale, zéro cloud 🤖</b>
</div>
