<div align="center">

<img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=36&duration=6000&pause=1000000000&color=00FF88&center=true&vCenter=true&width=960&lines=%3E+J.A.R.V.I.S+—+Assistant+IA+Local_" alt="JARVIS" />

<br/>

<p>
  <img src="https://img.shields.io/badge/Version-Production-00FF88?style=for-the-badge" />
  <img src="https://img.shields.io/badge/LLM-Ollama%20100%25%20Local-00FF88?style=for-the-badge&logo=ollama&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/GPU-CUDA%2012-76B900?style=for-the-badge&logo=nvidia&logoColor=white" />
</p>

<p>
  <img src="https://img.shields.io/badge/TTS-edge--tts%20Neural-4A9EFF?style=flat-square" />
  <img src="https://img.shields.io/badge/STT-faster--whisper-FF8C00?style=flat-square" />
  <img src="https://img.shields.io/badge/NR-DeepFilterNet-9B59B6?style=flat-square" />
  <img src="https://img.shields.io/badge/Backend-Flask-lightgrey?style=flat-square&logo=flask" />
  <img src="https://img.shields.io/badge/SOC-Intégré-FF4444?style=flat-square" />
  <img src="https://img.shields.io/badge/Cloud-Zéro-00FF88?style=flat-square" />
</p>

<br/>

<img src="./images/Jarvis-01.jpg" alt="JARVIS — Écran de démarrage" width="95%" />

<br/><br/>

<i>Assistant IA personnel inspiré de l'univers Iron Man — interface holographique, voix naturelle, écoute vocale continue.<br/>
Toutes les données restent sur votre machine. Aucune connexion cloud requise.</i>

</div>

---

## Sommaire

| | |
|---|---|
| [Vue d'ensemble](#vue-densemble) | [Architecture](#architecture) |
| [Screenshots](#screenshots) | [Installation](#installation-rapide) |
| [Guide complet](#guide-dinstallation--étape-par-étape) | [Modèles LLM](#modèles-llm) |
| [Stack technique](#stack-technique) | [Intégration SOC](#intégration-soc) |

---

## Vue d'ensemble

**J.A.R.V.I.S** est un assistant IA personnel complet, opérationnel en production 24/7.  

| Capacité | Détail |
|----------|--------|
| **Conversation** | LLM Ollama local — streaming token par token, contexte persistant |
| **Voix** | TTS Neural (edge-tts) + STT Whisper + réduction de bruit DeepFilterNet |
| **Monitoring** | Suivi CPU / RAM / GPU / disques / réseau en temps réel |
| **SOC** | Ban-IP automatique, restart services, alertes vocales sur menaces |
| **Multi-modèles** | Changement de LLM à chaud sans redémarrage |
| **Interface** | 10 onglets — thème holographique sombre — 17 400+ lignes |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Interface Web — localhost:5000                  │
│              Thème holographique · 10 onglets · SSE streaming     │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP / Server-Sent Events
┌────────────────────────────▼─────────────────────────────────────┐
│                  Flask Backend — jarvis.py                         │
│                  ~3 600 lignes · 55 routes · 124 fonctions        │
│                                                                   │
│   /chat        ──▶  Ollama LLM  (streaming)                       │
│   /tts         ──▶  edge-tts    (synthèse vocale)                 │
│   /stt         ──▶  faster-whisper  (transcription micro)         │
│   /soc/ban     ──▶  SSH ──▶ CrowdSec  (ban-IP)                   │
│   /soc/restart ──▶  SSH ──▶ systemctl (redémarrage service)       │
│   /status      ──▶  Dashboard SOC  (état JARVIS)                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │ paramiko SSH
         ┌───────────────────▼───────────────────┐
         │          Serveur SOC (optionnel)        │
         │  CrowdSec · fail2ban · nginx · Suricata │
         └─────────────────────────────────────────┘
```

---

## Screenshots

### Écran de démarrage

<div align="center">
  <img src="./images/Jarvis-01.jpg" alt="Écran de démarrage JARVIS" width="95%" />
  <br/><sub>Initialisation du système — statuts des modules, message de bienvenue</sub>
</div>

<br/>

### Interface de conversation & Monitoring système

<table border="0" cellspacing="0" cellpadding="8">
  <tr>
    <td width="60%">
      <img src="./images/Jarvis-03.jpg" alt="Interface de conversation LLM" width="100%" />
      <p align="center"><sub>Onglet <b>JARVIS IA</b> — conversation en temps réel, streaming SSE, sidebar système</sub></p>
    </td>
    <td width="40%">
      <img src="./images/Jarvis-02.jpg" alt="Onglet Monitor" width="100%" />
      <p align="center"><sub>Onglet <b>MONITOR</b> — CPU, RAM, GPU, disques, sparklines 24h</sub></p>
    </td>
  </tr>
</table>

### Paramètres LLM & Gestion des modèles

<table border="0" cellspacing="0" cellpadding="8">
  <tr>
    <td width="35%">
      <img src="./images/Jarvis-04.jpg" alt="Paramètres GPU et LLM" width="100%" />
      <p align="center"><sub>Onglet <b>SETTINGS</b> — GPU RTX Health, profils CUDA, sliders LLM</sub></p>
    </td>
    <td width="65%">
      <img src="./images/Jarvis-05.jpg" alt="Profils et presets modèles" width="100%" />
      <p align="center"><sub>Onglet <b>JARVIS IA</b> — profils prédéfinis (SOC, Code, Conversation, Raisonnement...)</sub></p>
    </td>
  </tr>
</table>

### Pipeline audio — DSP & Voice Lab

<table border="0" cellspacing="0" cellpadding="8">
  <tr>
    <td width="40%">
      <img src="./images/Jarvis-06.jpg" alt="DSP Audio" width="100%" />
      <p align="center"><sub>Onglet <b>DSP AUDIO</b> — égaliseur multi-bandes, compresseur, filtres, visualisation temps réel</sub></p>
    </td>
    <td width="60%">
      <img src="./images/Jarvis-07.jpg" alt="Voice Lab" width="100%" />
      <p align="center"><sub>Onglet <b>VOICE LAB</b> — source vocale, paramètres fins, bibliothèque de voix, comparateur A/B</sub></p>
    </td>
  </tr>
</table>

### Intégration SOC — Actions proactives

<div align="center">
  <img src="./images/Jarvis-08.jpg" alt="Onglet SOC — Actions proactives" width="95%" />
  <br/><sub>Onglet <b>SOC</b> — compteurs de bans/alertes, graphique d'activité 24h, journal horodaté des actions proactives</sub>
</div>

---

## Guide d'installation — étape par étape

<table>
  <tr>
    <th>Étape</th>
    <th>Description</th>
    <th>Guide</th>
  </tr>
  <tr>
    <td align="center"><b>01</b></td>
    <td>Python 3.11, Ollama, CUDA, dépendances</td>
    <td><a href="./docs/01-PREREQUIS.md">→ Prérequis</a></td>
  </tr>
  <tr>
    <td align="center"><b>02</b></td>
    <td>LLM local, API Ollama, streaming SSE, gestion modèles</td>
    <td><a href="./docs/02-LLM-OLLAMA.md">→ LLM Ollama</a></td>
  </tr>
  <tr>
    <td align="center"><b>03</b></td>
    <td>TTS edge-tts, file d'attente, STT Whisper VAD, DeepFilterNet NR</td>
    <td><a href="./docs/03-PIPELINE-AUDIO.md">→ Pipeline Audio</a></td>
  </tr>
  <tr>
    <td align="center"><b>04</b></td>
    <td>Serveur Flask, routes, Server-Sent Events, modèles à chaud</td>
    <td><a href="./docs/04-BACKEND-FLASK.md">→ Backend Flask</a></td>
  </tr>
  <tr>
    <td align="center"><b>05</b></td>
    <td>Intégration SOC, ban/unban IP via SSH, alertes proactives auto</td>
    <td><a href="./docs/05-INTEGRATION-SOC.md">→ Intégration SOC</a></td>
  </tr>
</table>

---

## Installation rapide

```bash
# 1. Cloner le dépôt
git clone https://github.com/0xCyberLiTech/JARVIS.git
cd JARVIS

# 2. Installer les dépendances Python
pip install -r scripts/requirements.txt

# 3. Installer Ollama + un modèle
#    → https://ollama.com
ollama pull phi4

# 4. Configurer (copier les templates)
cp config/jarvis_model.json.example      scripts/jarvis_model.json
cp config/jarvis_llm_params.json.example scripts/jarvis_llm_params.json

# 5. Lancer JARVIS
cd scripts && python jarvis.py
```

```
✔  JARVIS disponible sur  →  http://localhost:5000
```

---

## Modèles LLM

| Modèle | RAM | Points forts |
|--------|-----|-------------|
| `phi4` | 8 Go | ⭐ Recommandé — polyvalent, rapide |
| `mistral:7b` | 6 Go | Léger — idéal faible RAM |
| `phi4-reasoning` | 12 Go | Analyse complexe, SOC |
| `deepseek-r1:14b` | 14 Go | Raisonnement avancé |
| `qwen2.5:14b` | 14 Go | Code et analyse |

---

## Stack technique

<div align="center">

| Couche | Technologie | Rôle |
|--------|------------|------|
| LLM | Ollama (local) | Génération de texte — aucun cloud |
| TTS | edge-tts Neural | Synthèse vocale naturelle (fr-CA-AntoineNeural) |
| STT | faster-whisper | Transcription vocale — modèle small FR, CUDA |
| NR  | DeepFilterNet | Réduction de bruit micro temps réel |
| Backend | Flask + CORS | API REST + SSE streaming |
| SSH | paramiko | Actions SOC à distance (ban, restart) |
| GPU | CUDA 12 | Accélération STT + NR + inférence LLM |

</div>

---

## Intégration SOC

JARVIS se connecte au [dashboard SOC](https://github.com/0xCyberLiTech/SOC) pour :

- **Surveiller** les métriques de sécurité (CrowdSec, fail2ban, Suricata) toutes les 30s
- **Bannir automatiquement** les IPs en cas de pic d'attaque (via CrowdSec SSH)
- **Redémarrer** les services critiques si détectés DOWN
- **Alerter vocalement** si le score de menace dépasse les seuils configurés
- **Journaliser** chaque action dans l'onglet SOC avec horodatage

---

## Sécurité

```
✔  Bind 127.0.0.1 — non exposé sur le réseau
✔  Liste blanche des services autorisés (SSH)
✔  Validation des IPs avant toute action
✔  Aucun credential dans le code source
✔  Aucune donnée envoyée vers des services tiers
```

---

<div align="center">

<br/>

[![SOC Dashboard](https://img.shields.io/badge/Projet%20lié-SOC%20Dashboard-00D9FF?style=for-the-badge&logo=github&logoColor=white)](https://github.com/0xCyberLiTech/SOC)
&nbsp;
[![Profil GitHub](https://img.shields.io/badge/Auteur-0xCyberLiTech-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/0xCyberLiTech)

<br/><br/>

<sub>Projet homelab en production — <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · Cybersécurité & IA locale</sub>

</div>
