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
    <a href="https://github.com/0xCyberLiTech/JARVIS/releases/latest">
      <img src="https://img.shields.io/github/v/release/0xCyberLiTech/JARVIS?label=version&style=flat-square&color=blue" alt="Dernière version" />
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
# J.A.R.V.I.S

> **Assistant IA local · 100 % privé · Interface holographique · SOC cybersécurité**

JARVIS est un assistant IA personnel de type Iron Man construit sur Python/Flask + Ollama.
Tout tourne en local — aucune donnée ne quitte la machine.

<div align="center">
  <img src="Images/Jarvis.png" alt="JARVIS — interface holographique principale" width="900"/>
</div>

---

## Hermès — L'agent persistant

<div align="center">
  <img src="Images/Jarvis-08.png" alt="Hermès — l'agent persistant, interface holographique" width="880"/>
</div>

<br/>

> **Hermès transforme un assistant en agent.**
> Là où un assistant répond à des questions, un agent **observe, mémorise, apprend et agit** — sans être re-briefé à chaque session.

<div align="center">

| Brique | Rôle |
|--------|------|
| **Synoptique temps réel** | 6 couches moteur visibles dans l'interface : LLM actif, RAG, STT/TTS, auto-engine SOC, état mémoire |
| **Tuile Mémoire** | Mémoire vectorielle persistante — échanges, résumés, leçons apprises — rechargeable sans redémarrage |
| **Bypass déterministe** | Commandes critiques interceptées avant le LLM : exécution instantanée < 100 ms, 0 hallucination |
| **Boucle d'apprentissage** | `"Souviens-toi que X"` → leçon persistée, indexée, réinjectée automatiquement dans les futures réponses |
| **Briefing matinal** | `"Bonjour JARVIS"` → niveau de menace SOC, état des machines, alertes des 24 dernières heures |

</div>

<div align="center">

| Avant Hermès | Après Hermès |
|--------------|--------------|
| Chaque session recommence à zéro | Contexte conservé entre les sessions |
| Le contexte disparaît au redémarrage | Leçons et conventions indexées dans le RAG |
| L'assistant répond seulement | L'agent surveille, alerte et agit |
| Toutes les commandes passent par le LLM | Bypass déterministe pour les commandes critiques |

</div>

---

## À propos & Objectifs

<div align="center">

| Objectif | Description |
|----------|-------------|
| **100 % local** | LLM, STT, TTS, RAG, données — tout sur le poste de travail (GPU NVIDIA CUDA) |
| **Agentification** | Hermès — mémoire longue durée, apprentissage inter-sessions, briefing automatique |
| **SOC cybersécurité** | Auto-engine de détection, ban automatique, alertes vocales, injection contexte sécurité live |
| **Accessibilité** | Interface haute lisibilité, alertes vocales TTS, commandes vocales à bypass déterministe |
| **Qualité** | 1 465 tests · 79 % coverage · ruff 0 · eslint 0 · hooks bloquants |

</div>

---

## Galerie — L'interface en images

Tour visuel des principaux modules de l'interface holographique JARVIS.

### 1 · Écran d'accueil

<div align="center">
  <img src="Images/Jarvis-01.png" alt="Écran d'accueil JARVIS" width="880"/>
</div>

À l'ouverture, JARVIS se présente et énumère son état opérationnel : le **modèle LLM actif** (qwen3:8b via Ollama), le **moteur vocal** (Edge-TTS Antoine Neural), la **chaîne de traitement DSP** (EQ, compresseur, DeepFilterNet), les **modules disponibles** (Terminal, Fichiers, Tâches, Audio) et l'**accélération matérielle CUDA** (RTX Blackwell + Whisper STT GPU). Les trois actions principales — *Lire*, *Modifier*, *Accéder au système* — sont accessibles directement, et la première interaction de la journée déclenche le briefing matinal d'Hermès.

### 2 · Réglages LLM & profils GPU

<div align="center">
  <img src="Images/Jarvis-04.png" alt="Réglages LLM et profils GPU RTX" width="420"/>
</div>

Le centre de contrôle fin de l'inférence locale, organisé en **quatre blocs** :

<div align="center">

| Bloc | Description |
|------|-------------|
| **① GPU Health — RTX 5080** | État **temps réel** de la carte : VRAM utilisée / 16 Go, charge GPU, température, puissance (W). Le voyant vire à l'orange/rouge dès qu'une limite est approchée. |
| **② Impact sur la RTX** | Estime *avant* de lancer le **coût mémoire** des réglages courants (poids du modèle + cache KV) et la **VRAM libre restante** — pour rester en « zone sûre » sans saturer la carte. |
| **③ Profils RTX 5080** | Six préréglages cohérents en **un clic** — *Rapide · Équilibré · Code · Créatif · Précis · RTX 5080 MAX* — qui ajustent d'un coup créativité, longueur et contexte selon l'usage. |
| **④ Paramètres LLM** | Réglage **manuel fin** : température, top-p, top-k, longueur max, repeat penalty, taille de contexte — plus trois modes d'**optimisation latence** (Rapide / Équilibré / Qualité). |

</div>

### 3 · Studio audio DSP

<div align="center">
  <img src="Images/Jarvis-05.png" alt="Studio audio DSP — EQ et analyseur spectral" width="460"/>
</div>

Le rack audio professionnel de JARVIS, inspiré d'un processeur voix broadcast. On y trouve l'**égaliseur paramétrique** multibandes, l'**analyseur spectral** temps réel (waveform colorée vert→orange selon l'énergie) et les **compresseurs** de la chaîne voix. Chaque étage est réglable à la souris, avec retour visuel immédiat sur le signal traité.

### 4 · Studio audio DSP — chaîne FX

<div align="center">
  <img src="Images/Jarvis-06.png" alt="Studio audio DSP — chaîne d'effets et convolution" width="460"/>
</div>

La suite de la chaîne audio : **courbe de réponse** globale, étages d'**effets par convolution** (reverb, echo, delay) avec calibration loudness, et bus master à limiteur brick-wall. C'est cette chaîne qui donne à la voix de synthèse Antoine son rendu naturel et homogène quel que soit le moteur TTS actif.

### 5 · Voice Lab — l'atelier de la voix

<div align="center">
  <img src="Images/Jarvis-10.png" alt="Voice Lab — réglage des moteurs TTS et comparateur A/B" width="880"/>
</div>

Le **Voice Lab** règle au cordeau la voix de l'assistant : choix de la **source vocale** (cascade de 4 moteurs TTS — Edge Antoine fr-CA, Kokoro CUDA, Piper, SAPI5), **paramètres vocaux** fins, **phrase de test**, **bibliothèque** de voix et **comparateur A/B**. C'est l'atelier qui donne à JARVIS sa voix naturelle et homogène, quel que soit le moteur actif.

### 6 · Accès Web gouverné

<div align="center">
  <img src="Images/Jarvis-11.png" alt="Accès Web gouverné — allowlist, lecture seule, journalisé" width="880"/>
</div>

L'agent peut consulter le web — mais **sous contrôle strict**. JARVIS ne visite QUE les domaines d'une **allowlist explicite** (sites système verrouillés pour la météo et la veille IA), en **lecture seule** (jamais d'envoi de données), et **chaque accès est journalisé**. Tout le reste est **refusé et tracé**. La curiosité de l'agent reste gouvernée — même principe de moindre privilège que pour le SOC.

> D'autres captures (dashboard monitoring, pilotage des modèles, SOC, terminal)
> sont volontairement **non publiées** : elles relèvent de la doctrine de
> sanitisation (la vitrine *décrit* le SOC, elle n'en *expose* aucune donnée live).

---

## Sommaire

<div align="center">

| # | Document | Description | Statut | |
|---|----------|-------------|--------|---|
| 01 | [Hermès — Agent persistant](DOCUMENTATION/01-HERMES.md) | 5 briques fondatrices + avancées · bypass · apprentissage · briefing · mode tuteur · DR cerveau | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/01-HERMES.md) |
| 02 | [Intégration SOC](DOCUMENTATION/02-SOC-INTEGRATION.md) | Auto-engine · ban/unban · alertes vocales · injection contexte sécurité | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/02-SOC-INTEGRATION.md) |
| 03 | [Architecture globale](DOCUMENTATION/03-ARCHITECTURE.md) | 5 zones · Flask · Blueprints · modules · polling | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/03-ARCHITECTURE.md) |
| 04 | [Audio DSP](DOCUMENTATION/04-AUDIO-DSP.md) | Chaîne broadcast · TTS 4 moteurs · STT faster-whisper · DSP 3 étages | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/04-AUDIO-DSP.md) |
| 05 | [Installation](DOCUMENTATION/05-INSTALLATION.md) | Pré-requis matériel · Python · Ollama · lancement · vérification | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/05-INSTALLATION.md) |
| 06 | [MCP Server](DOCUMENTATION/06-MCP-SERVER.md) | 12 outils · Claude Desktop · watchdog · principe de séparation | 🟢 | [<img src="https://img.shields.io/badge/EXPLORER-8B5CF6?style=for-the-badge&logo=github&logoColor=white">](DOCUMENTATION/06-MCP-SERVER.md) |

</div>

---

## Stack technique

<div align="center">

| Couche | Technologie |
|--------|-------------|
| **Backend** | Python 3.11 · Flask · Blueprints autoportants · DI pur |
| **LLM local** | Ollama · qwen3:8b (SOC+GÉNÉRAL+CR · rapide) · qwen3:14b (THINK) · qwen2.5-coder:14b (CODE) · gemma4:latest (VISION) |
| **RAG** | mxbai-embed-large · BM25 hybride · ~1700 chunks · TTL 5 min |
| **TTS** | edge-tts fr-CA Antoine → Kokoro CUDA → SAPI5 (cascade automatique) |
| **STT** | faster-whisper large-v3-turbo CUDA · vocabulaire SOC |
| **Frontend** | Vanilla JS · 21 modules · Web Audio API · xterm.js · Monaco Editor |
| **Agent Hermès** | 5 briques · bypass regex · scheduler daemon · DI pur · indépendant du LLM |
| **MCP** | 12 outils exposés à Claude Desktop · streamable-HTTP · watchdog |
| **Qualité** | 1 465 pytest · 79 % coverage · ruff 0 · eslint 0 · hooks pré-commit/pré-push |

</div>

---

## Sécurité

<div align="center">

| Principe | Implémentation |
|----------|----------------|
| **100 % local** | JARVIS filtre et agrège localement — rien ne part vers un LLM cloud |
| **RFC1918 immuable** | Les plages IP privées ne peuvent jamais être bannies |
| **SSH lecture seule** | 29 patterns dangereux bloqués · whitelist explicite pour l'écriture |
| **SOC side-channel** | Le contexte sécurité n'entre jamais dans l'historique chat |
| **Audit forensique** | Toute opération SSH d'écriture tracée dans un journal JSONL |

</div>

---

**Commencer →** [01 — Hermès, l'agent persistant](DOCUMENTATION/01-HERMES.md)

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
