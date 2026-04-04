<div align="center">

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=30&duration=6000&pause=1000000000&color=00FF88&center=true&vCenter=true&width=900&lines=%3EJARVIS+—+Assistant+IA+Local_" alt="JARVIS" />
  </a>

  <h3>Assistant IA personnel — 100% local, zéro cloud</h3>

  <p>
    <img src="https://img.shields.io/badge/LLM-Ollama%20local-00FF88?style=flat-square" />
    <img src="https://img.shields.io/badge/TTS-edge--tts-blue?style=flat-square" />
    <img src="https://img.shields.io/badge/STT-faster--whisper-orange?style=flat-square" />
    <img src="https://img.shields.io/badge/NR-DeepFilterNet-purple?style=flat-square" />
    <img src="https://img.shields.io/badge/Backend-Flask%20Python-lightgrey?style=flat-square&logo=python" />
    <img src="https://img.shields.io/badge/Statut-Production-brightgreen?style=flat-square" />
  </p>

  <br/>

  <img src="./images/Jarvis-01.jpg" alt="JARVIS — Écran de démarrage" width="100%" />

</div>

---

## Présentation

JARVIS est un assistant IA personnel inspiré de l'univers Iron Man.  
Interface holographique sombre, voix synthétique naturelle, écoute vocale continue,  
et intégration complète avec un **SOC de sécurité** homelab.

> Toutes les données restent sur votre machine.  
> LLM, TTS et STT tournent entièrement en local — aucune connexion cloud requise.

---

## Guide d'installation — étape par étape

| Étape | Description | Lien |
|-------|-------------|------|
| **01** | Python 3.11, Ollama, dépendances | [01 — Prérequis](./docs/01-PREREQUIS.md) |
| **02** | LLM local, streaming, gestion modèles | [02 — LLM Ollama](./docs/02-LLM-OLLAMA.md) |
| **03** | TTS edge-tts, STT Whisper, DeepFilterNet | [03 — Pipeline Audio](./docs/03-PIPELINE-AUDIO.md) |
| **04** | Serveur Flask, routes, SSE streaming | [04 — Backend Flask](./docs/04-BACKEND-FLASK.md) |
| **05** | Intégration SOC, ban-IP SSH, alertes auto | [05 — Intégration SOC](./docs/05-INTEGRATION-SOC.md) |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Interface Web (localhost:5000)                 │
│         Thème holographique — 10 onglets                     │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼──────────────────────────────────┐
│               Flask Backend (jarvis.py)                       │
│                                                              │
│  /chat     → Ollama LLM (streaming)                          │
│  /tts      → edge-tts (synthèse vocale)                      │
│  /stt      → faster-whisper (transcription)                  │
│  /soc/*    → SSH → serveur SOC (ban/unban/restart)           │
│  /status   → état de JARVIS (pour le dashboard SOC)          │
└──────────────────────────┬──────────────────────────────────┘
                           │ SSH (paramiko)
┌──────────────────────────▼──────────────────────────────────┐
│            Serveur SOC (optionnel — voir dépôt SOC)          │
│       CrowdSec · fail2ban · nginx · Suricata                 │
└─────────────────────────────────────────────────────────────┘
```

---

## Fonctionnalités

### Interface de conversation — LLM local

Dialogue en temps réel avec un LLM Ollama. Les réponses s'affichent token par token  
grâce au streaming SSE. Contexte de session persistant, changement de modèle à chaud.

<div align="center">
  <img src="./images/Jarvis-03.jpg" alt="JARVIS — Interface de conversation" width="90%" />
</div>

---

### Monitoring système

Onglet dédié au suivi des ressources machine en temps réel :  
CPU, RAM, GPU (VRAM, température, puissance), disques, réseau — sparklines 24h.

<div align="center">
  <img src="./images/Jarvis-02.jpg" alt="JARVIS — Onglet Monitor" width="90%" />
</div>

---

### Paramètres LLM & Profils GPU

Configuration fine des paramètres d'inférence (température, contexte, top-k/p)  
et gestion des profils RTX pour optimiser l'accélération CUDA selon l'usage.

<div align="center">
  <img src="./images/Jarvis-04.jpg" alt="JARVIS — Settings LLM & GPU" width="48%" />
  <img src="./images/Jarvis-05.jpg" alt="JARVIS — Profils modèles" width="48%" />
</div>

> **Gauche** : Paramètres GPU RTX et sliders LLM (température, top-p, contexte...)  
> **Droite** : Liste des presets — profils prédéfinis pour SOC, code, conversation

---

### Pipeline audio — DSP & Voice Lab

Traitement audio complet en deux onglets :
- **DSP Audio** : égaliseur graphique multi-bandes, compresseur, filtres
- **Voice Lab** : sélection de voix TTS, paramètres vocaux, bibliothèque, comparateur A/B

<div align="center">
  <img src="./images/Jarvis-06.jpg" alt="JARVIS — DSP Audio" width="48%" />
  <img src="./images/Jarvis-07.jpg" alt="JARVIS — Voice Lab" width="48%" />
</div>

> **Gauche** : Onglet DSP Audio — égaliseur, courbes de réponse, pipeline de traitement  
> **Droite** : Onglet Voice Lab — source vocale, paramètres fins, bibliothèque de voix

---

### Intégration SOC — Actions proactives

JARVIS surveille le dashboard SOC en temps réel.  
Il détecte les menaces, déclenche des actions défensives et journalise chaque intervention.

<div align="center">
  <img src="./images/Jarvis-08.jpg" alt="JARVIS — Onglet SOC" width="90%" />
</div>

> Journal des actions proactives : bans automatiques, redémarrages de services,  
> alertes vocales sur montée du score de menace — graphique d'activité 24h.

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| **LLM** | [Ollama](https://ollama.com) — phi4, deepseek-r1, mistral, qwen2.5... |
| **TTS** | [edge-tts](https://github.com/rany2/edge-tts) — voix naturelles Microsoft Neural |
| **STT** | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — modèle small/medium FR |
| **Réduction bruit** | [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet) — CUDA |
| **Backend** | [Flask](https://flask.palletsprojects.com) + CORS |
| **SSH** | [paramiko](https://www.paramiko.org) — actions SOC à distance |

---

## Installation rapide

```bash
# 1. Cloner
git clone https://github.com/0xCyberLiTech/JARVIS.git
cd JARVIS

# 2. Installer les dépendances
pip install -r scripts/requirements.txt

# 3. Installer Ollama et un modèle
# https://ollama.com
ollama pull phi4

# 4. Configurer
cp config/jarvis_model.json.example scripts/jarvis_model.json
cp config/jarvis_llm_params.json.example scripts/jarvis_llm_params.json

# 5. Lancer
cd scripts
python jarvis.py
# → http://localhost:5000
```

---

## Modèles LLM recommandés

| Modèle | RAM requise | Usage |
|--------|-------------|-------|
| `phi4` | 8 Go | Recommandé — polyvalent |
| `mistral:7b` | 6 Go | Léger et rapide |
| `phi4-reasoning` | 12 Go | Analyse complexe, SOC |
| `deepseek-r1:14b` | 14 Go | Raisonnement avancé |
| `qwen2.5:14b` | 14 Go | Code et analyse |

---

## Sécurité

- Bind sur `127.0.0.1` uniquement — non exposé réseau
- Liste blanche des services restartables via SSH
- Validation des IPs avant ban
- Aucun credential dans le code source

---

<div align="center">
  <a href="https://github.com/0xCyberLiTech/SOC">
    <img src="https://img.shields.io/badge/Intégration-SOC%20Dashboard-00D9FF?style=for-the-badge&logo=github" />
  </a>
  <a href="https://github.com/0xCyberLiTech">
    <img src="https://img.shields.io/badge/Profil-0xCyberLiTech-181717?style=for-the-badge&logo=github" />
  </a>
</div>

<div align="center">
  <br/>
  <b>🤖 Projet par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> — IA locale, zéro cloud 🤖</b>
</div>
