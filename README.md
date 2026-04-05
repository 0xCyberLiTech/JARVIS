<div align="center">

  <br></br>

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=50&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS_" alt="Titre dynamique JARVIS" />
  </a>

  <br></br>

  <h2>Laboratoire numérique pour la cybersécurité, Linux & IT.</h2>

  <p align="center">
    <a href="https://0xcyberlitech.github.io/">
      <img src="https://img.shields.io/badge/Portfolio-0xCyberLiTech-181717?logo=github&style=flat-square" alt="Portfolio" />
    </a>
    <a href="https://github.com/0xCyberLiTech">
      <img src="https://img.shields.io/badge/Profil-GitHub-181717?logo=github&style=flat-square" alt="Profil GitHub" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/releases/latest">
      <img src="https://img.shields.io/github/v/release/0xCyberLiTech/JARVIS?label=version" alt="Latest Release" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/blob/main/CHANGELOG.md">
      <img src="https://img.shields.io/badge/📄%20CHANGELOG-JARVIS-blue" alt="Changelog" />
    </a>
    <a href="https://github.com/0xCyberLiTech?tab=repositories">
      <img src="https://img.shields.io/badge/Dépôts-publics-blue?style=flat-square" alt="Dépôts publics" />
    </a>
  </p>

</div>

<div align="center">
  <img src="https://img.icons8.com/fluency/96/000000/cyber-security.png" alt="CyberSec" width="80"/>
</div>

<div align="center">
  <p>
    <strong>Cybersécurité</strong> <img src="https://img.icons8.com/color/24/000000/lock--v1.png"/> • <strong>Linux Debian</strong> <img src="https://img.icons8.com/color/24/000000/linux.png"/> • <strong>Sécurité informatique</strong> <img src="https://img.icons8.com/color/24/000000/shield-security.png"/>
  </p>
</div>

<div align="center">
  <br/>
  <img src="./images/Jarvis-01.jpg" alt="JARVIS — Écran de démarrage" width="95%" />
</div>

---

<div align="center">

## À propos & Objectifs.

</div>

Passionné d'intelligence artificielle locale et de cybersécurité, j'ai construit JARVIS avec une conviction simple : **un assistant IA personnel doit rester sous ton contrôle, sur ta machine, sans aucun cloud**.

Inspiré de l'univers Iron Man, JARVIS est un assistant opérationnel 24/7 — voix naturelle, écoute continue, interface holographique — qui tourne entièrement en local grâce à **Ollama** sur un GPU **NVIDIA RTX 5080**. Il surveille mon infrastructure SOC en temps réel, répond à mes questions vocalement, analyse des logs de sécurité, et peut bannir une IP malveillante sur simple commande naturelle.

Avec **17 400+ lignes de code**, 10 onglets, un pipeline audio complet (TTS Neural · STT Whisper · DeepFilterNet), et une intégration SOC avec actions proactives automatiques — ce n'est pas un proof-of-concept. C'est un système en production, mis à jour hebdomadairement.

> **Ce projet a été conçu et développé en collaboration avec [Claude AI](https://claude.ai) (Anthropic) — Claude Code.**
> L'ironie n'est pas perdue : un assistant IA local construit avec l'aide d'une IA. Mais c'est exactement là la force de cette approche — utiliser Claude Code pour architécter, déboguer et itérer rapidement sur un projet ambitieux. De la gestion du pipeline audio au système de ban automatique SOC, Claude AI a été un véritable co-développeur tout au long du projet.

Le contenu est structuré pour répondre aux besoins de :
- 🤖 **Passionnés d'IA locale** — déployer un assistant LLM sans cloud, 100% privé
- 🛡️ **Professionnels IT & SOC** — automatiser les réponses aux incidents de sécurité
- 🎓 **Étudiants & développeurs** — comprendre Flask, SSE, Whisper, edge-tts en pratique
- 🚀 **Explorateurs GPU** — exploiter CUDA pour l'inférence LLM + DSP audio en temps réel

---

## Sommaire

<div align="center">
<table border="0" width="600">
  <tr>
    <td align="center" width="150"><a href="#vue-densemble">Vue d'ensemble</a></td>
    <td align="center" width="150"><a href="#architecture">Architecture</a></td>
    <td align="center" width="150"><a href="#screenshots">Screenshots</a></td>
    <td align="center" width="150"><a href="#installation-rapide">Installation</a></td>
  </tr>
  <tr>
    <td align="center"><a href="#guide-dinstallation--étape-par-étape">Guide complet</a></td>
    <td align="center"><a href="#modèles-llm">Modèles LLM</a></td>
    <td align="center"><a href="#stack-technique">Stack technique</a></td>
    <td align="center"><a href="#intégration-soc">Intégration SOC</a></td>
  </tr>
</table>
</div>

---

## Vue d'ensemble

**J.A.R.V.I.S** est un assistant IA personnel complet, opérationnel en production 24/7.  

<div align="center">

| Capacité | Détail |
|----------|--------|
| **Conversation** | LLM Ollama local — streaming token par token, contexte persistant |
| **Voix** | TTS Neural (edge-tts) + STT Whisper + réduction de bruit DeepFilterNet |
| **Monitoring** | Suivi CPU / RAM / GPU / disques / réseau en temps réel |
| **SOC** | Ban-IP automatique, restart services, alertes vocales sur menaces |
| **Multi-modèles** | Changement de LLM à chaud sans redémarrage |
| **Interface** | 10 onglets — thème holographique sombre — 17 400+ lignes |

</div>

---

## Architecture

```mermaid
flowchart TD
    A["🌐 Interface Web — localhost:5000\nThème holographique · 10 onglets · SSE streaming"]
    B["⚙️ Flask Backend — jarvis.py\n~3 600 lignes · 55 routes · 124 fonctions"]
    C["🤖 LLM\n/chat → Ollama streaming"]
    D["🔊 Audio\n/tts → edge-tts · /stt → Whisper"]
    E["🛡️ SOC\n/soc/ban · /soc/restart · /status"]
    F["Serveur SOC — optionnel\nCrowdSec · fail2ban · nginx · Suricata"]

    A -->|HTTP / Server-Sent Events| B
    B --> C
    B --> D
    B --> E
    E -->|paramiko SSH| F
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

<div align="center">
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
</div>

### Paramètres LLM & Gestion des modèles

<div align="center">
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
</div>

### Pipeline audio — DSP & Voice Lab

<div align="center">
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
</div>

### Intégration SOC — Actions proactives

<div align="center">
  <img src="./images/Jarvis-08.jpg" alt="Onglet SOC — Actions proactives" width="95%" />
  <br/><sub>Onglet <b>SOC</b> — compteurs de bans/alertes, graphique d'activité 24h, journal horodaté des actions proactives</sub>
</div>

---

## Guide d'installation — étape par étape

<div align="center">
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
</div>

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

<div align="center">

| Modèle | RAM | Points forts |
|--------|-----|-------------|
| `phi4` | 8 Go | ⭐ Recommandé — polyvalent, rapide |
| `mistral:7b` | 6 Go | Léger — idéal faible RAM |
| `phi4-reasoning` | 12 Go | Analyse complexe, SOC |
| `deepseek-r1:14b` | 14 Go | Raisonnement avancé |
| `qwen2.5:14b` | 14 Go | Code et analyse |

</div>

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
  <a href="https://www.docker.com"><img src="https://skillicons.dev/icons?i=docker" width="48" title="Docker" /></a>
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
  <a href="https://pytorch.org"><img src="https://skillicons.dev/icons?i=pytorch" width="48" title="PyTorch" /></a>
  <a href="https://www.tensorflow.org"><img src="https://skillicons.dev/icons?i=tensorflow" width="48" title="TensorFlow" /></a>
  <a href="https://www.raspberrypi.com"><img src="https://skillicons.dev/icons?i=raspberrypi" width="48" title="Raspberry Pi" /></a>
  <br/><br/>
  <a href="https://ollama.com"><img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" /></a>
  &nbsp;
  <a href="https://anthropic.com"><img src="https://img.shields.io/badge/Anthropic-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic" /></a>
</td>
</tr>
</table>

<br/>

<b>🔒 Un projet proposé par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> • Développé en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🔒</b>

</div>
