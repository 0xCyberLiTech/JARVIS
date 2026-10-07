<div align="center">

  <br></br>

  <a href="../README.md">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=40&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS+·+01+PILE+HERMES+%26+RAG_" alt="Fiche 01 Hermès & RAG" />
  </a>

  <br></br>

  <h2>Fiche 01 · La Pile Cognitive Hermès & Moteur RAG Vectoriel</h2>

  <p align="center">
    <a href="../README.md">
      <img src="https://img.shields.io/badge/🏠_Hub-Principal-8B5CF6?style=flat-square" alt="Hub Principal" />
    </a>
    <a href="01-PILE-HERMES-ET-RAG.md">
      <img src="https://img.shields.io/badge/🧠_01-Hermès_%26_RAG-00d9ff?style=flat-square" alt="01 Hermès & RAG" />
    </a>
    <a href="02-MONITORING-GPU-ET-SYSTEME.md">
      <img src="https://img.shields.io/badge/🖥️_02-GPU_RTX_5080-181717?style=flat-square" alt="02 GPU RTX 5080" />
    </a>
    <a href="03-THE-GRID-3D-SYNOPTIQUE.md">
      <img src="https://img.shields.io/badge/🌐_03-The_Grid_3D-181717?style=flat-square" alt="03 The Grid 3D" />
    </a>
    <a href="04-INFOGERANCE-PARC-ET-VMS.md">
      <img src="https://img.shields.io/badge/🏢_04-Infogérance_PVE-181717?style=flat-square" alt="04 Infogérance PVE" />
    </a>
    <a href="05-BITE-DIAGNOSTIC-STATION.md">
      <img src="https://img.shields.io/badge/🧪_05-Station_BITE-181717?style=flat-square" alt="05 Station BITE" />
    </a>
    <a href="06-MOBILE-ET-VOIX-SOUVERAINE.md">
      <img src="https://img.shields.io/badge/📱_06-Mobile_%26_Voix-181717?style=flat-square" alt="06 Mobile & Voix" />
    </a>
  </p>

</div>

<div align="center">
  <img src="https://img.icons8.com/fluency/96/000000/brain.png" alt="Brain Icon" width="80"/>
</div>

<div align="center">
  <p>
    <strong>Mémoire Long-Terme Anti-Dérive</strong> &nbsp;•&nbsp; <strong>Fast-Path Déterministe (< 200 ms)</strong> &nbsp;•&nbsp; <strong>Indexation Vectorielle Locale</strong>
  </p>
</div>

> [!IMPORTANT]
> **Vitrine Technologique : Architecture & Démonstration d'Ingénierie**  
> Ce document technique détaille l'architecture de la **Pile Cognitive Hermès** et du moteur vectoriel RAG de JARVIS.  
> 🔒 **Propriété Intellectuelle & Sécurité Opérationnelle** : Les scripts d'automatisation interne, clés privées et configurations physiques restent **strictement confinés** au sein de l'Atelier souverain 0xCyberLiTech.

---

## 🎯 Introduction & Rôle Opérationnel

La **Pile Cognitive Hermès** constitue le cerveau central de JARVIS. Elle assure la transition fondamentale entre un grand modèle de langage passif et un **agent autonome souverain** capable de raisonner, d'apprendre au fil des semaines et de piloter une infrastructure critique en temps réel.

Contrairement aux chatbots conventionnels qui oublient tout à la fermeture de session ou inventent des réponses approximatives, Hermès combine :
1. Un **Cœur Arc Reactor** animé en direct, visualisant l'état de conscience et le rythme cardiaque de l'IA (~1.05s LUB-DUB).
2. Un **Fast-Path déterministe (< 200 ms)** qui élimine 100 % des hallucinations sur les faits machine.
3. Une **Mémoire Épisodique & Vectorielle** scellée contre le *factual drift* par des gardiens d'intégrité automatiques.

---

## ⚡ Le Cœur Réacteur Vivant (Stark Arc Reactor)

Le pupitre supérieur d'Hermès est dominé par l'**Arc Reactor MK-VII**, une modélisation dynamique haute précision rendue sur canvas WebGL :

<div align="center">

[![Cœur Arc Reactor Vivant](../assets/jarvis-hermes-arc-reactor.png)](../assets/jarvis-hermes-arc-reactor.png)

*Scène du Cœur Arc Reactor en production : réacteur central animé à anneaux contra-rotatifs, bobines magnétiques, graduations d'azimut et pods télémétriques latéraux.*

</div>

### 📊 Les Pods de Télémétrie Cognitive :

* **Moteur Cognitif :** Indique le modèle d'inférence actuellement chargé en VRAM (par défaut `Mistral-Nemo 12B` ou `Qwen3.5:9B`).
* **Posture Active :** Mode d'arbitrage en cours (`AUTONOME`, `SOC`, `INFOGÉRANCE`, `CODE`, `THINK`).
* **Battement Cœur (~1.05s LUB-DUB) :** Pulsation cyclique modélisant le cycle interne de veille et de rafraîchissement d'état.
* **Canal Micro (STT) :** Détection d'activité vocale temps réel avec VU-mètre à LED orange lors de la prise de parole.
* **Connaissances & Leçons :** Compteur en direct des chunks vectoriels indexés et des leçons doctrinales gravées en mémoire.
* **Intégrité Hermès (100 % Nominale) :** Contrôle continu de non-corruption de la base vectorielle.

---

## 🔬 Architecture Système des 5 Couches Hermès

Le pipeline cognitif d'Hermès est structuré en 5 couches étanches sans interdépendance circulaire :

```mermaid
flowchart TD
    classDef client fill:#1e1b4b,stroke:#8b5cf6,stroke-width:2px,color:#fff;
    classDef fastpath fill:#31102f,stroke:#ef4444,stroke-width:2px,color:#fff;
    classDef rag fill:#0f2e2e,stroke:#00d9ff,stroke-width:2px,color:#fff;
    classDef gpu fill:#143419,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef output fill:#261845,stroke:#a855f7,stroke-width:2px,color:#fff;

    REQ["🎙️ Requête Opérateur<br/>(Voix Antoine / Web HUD / WireGuard Mobile)"]:::client

    subgraph FastPath["⚡ 1. ROUTEUR D'ARBITRAGE FAST-PATH (< 200 ms)"]
        FP_DECIDE{"Type d'Intention ?"}:::fastpath
        FP_FACT["Bypass LLM Total (0 ms)<br/>Sondes Directes: Proxmox, ZFS, GPU, Réseau"]:::fastpath
    end

    subgraph Cognitive["🧠 2. MOTEUR COGNITIF & MÉMOIRE PERSISTANTE HERMÈS"]
        RAG_VEC["Indexation Vectorielle RAG<br/>qwen3-embedding:4b (Embeddings Locaux)"]:::rag
        HERMES_MEM["Mémoire Épisodique & Doctrine<br/>Contrôle anti-dérive factual-drift"]:::rag
        CTX_BUILD["Construction Chirurgicale du Contexte"]:::rag
    end

    subgraph Reacteur["🚀 3. RÉACTEUR D'INFÉRENCE GPU BLACKWELL"]
        LLM_GPU["Mistral-Nemo 12B (Ollama)<br/>Accélération Matérielle RTX 5080 VRAM GDDR7"]:::gpu
        REASON["Inférence Cognitive & Synthèse d'Action"]:::gpu
    end

    OUT["🎙️ Restitution Vocale Antoine HD (MCI Windows)<br/>& Télémétrie Extreme HUD"]:::output

    REQ --> FP_DECIDE
    FP_DECIDE -->|Grandeur Physique / État Machine| FP_FACT
    FP_FACT --> OUT
    FP_DECIDE -->|Analyse Complexe / Décision| RAG_VEC
    RAG_VEC --> HERMES_MEM
    HERMES_MEM --> CTX_BUILD
    CTX_BUILD --> LLM_GPU
    LLM_GPU --> REASON
    REASON --> OUT
```

---

## 🛠️ Description Détaillée des Mécanismes Techniques

### 1. Le Fast-Path Déterministe (< 200 ms)
* **Zéro LLM sur les faits :** Conformément à la Règle 13.2 de la Doctrine Universelle, aucun modèle de langage n'est autorisé à deviner ou extrapoler une métrique matérielle.
* **Résolution réflexe :** Les requêtes portant sur les charges CPU, la RAM, l'état ZFS, les adresses IP, les règles pare-feu ou le statut d'une VM sont interceptées en amont et résolues par appel direct aux APIs internes (< 200 ms).

### 2. Le Moteur RAG Vectoriel Hybride (`qwen3-embedding:4b`)
* **100 % Local :** Tous les calculs de plongement sémantique (*embeddings*) s'exécutent localement sans aucune dépendance cloud.
* **Filtrage cosinus adaptatif :** Seuls les passages de documentation ou d'incidents passés dont la similarité vectorielle dépasse le seuil de confiance sont injectés dans le prompt système.

### 3. La Mémoire Épisodique & Le Gardien Anti-Dérive
* **Capitalisation des retours :** Chaque consigne validée par l'opérateur est enregistrée avec son horodatage et son contexte d'exécution.
* **Gardien `jarvis-knowledge-audit.py` :** Script d'audit automatique qui compare périodiquement la mémoire textuelle stockée avec l'état réel de l'infrastructure pour interdire tout désalignement cognitif.

### 4. Le Réacteur d'Inférence GPU Blackwell
* **Modèle d'élite :** `Mistral-Nemo 12B` quantifié, offrant une précision de raisonnement optimale pour l'aide à la décision cyber et l'analyse de code.
* **Circuit Breaker :** Coupe-circuit logiciel surveillant la charge du serveur Ollama pour prévenir tout blocage.

---

## 📸 L'Interface Complète du Laboratoire d'Apprentissage

<div align="center">

[![Vue Globale Apprentissage Hermès](../assets/jarvis-hermes-apprentissage.png)](../assets/jarvis-hermes-apprentissage.png)

*Console complète d'Apprentissage Hermès (1920x2102) : scène du réacteur, schéma du pipeline cognitif, et matrice des 9 services transversaux souverains.*

</div>

---

<div align="center">

| [← 🏠 Retour au Hub Principal](../README.md) | [🖥️ Page Suivante : Fiche 02 · Moniteur GPU RTX 5080 ➔](02-MONITORING-GPU-ET-SYSTEME.md) |
|:---|---:|

<br/>

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
  <a href="https://threejs.org/"><img src="https://skillicons.dev/icons?i=threejs" width="48" title="Three.js" /></a>
</td>
<td align="center">
  <a href="https://ollama.com"><img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" /></a>
  <br/><br/>
  <a href="https://developer.nvidia.com/cuda-zone"><img src="https://img.shields.io/badge/NVIDIA%20CUDA-76B900?style=for-the-badge&logo=nvidia&logoColor=white" alt="NVIDIA CUDA" /></a>
</td>
</tr>
</table>

<br/>

<sub>🔒 Conçu et maintenu par <a href="https://github.com/0xCyberLiTech">Marc (0xCyberLiTech)</a> · Ingénierie souveraine & Pair-Programming IA d'élite 🔒</sub>

</div>
