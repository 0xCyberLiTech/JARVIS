<div align="center">

<a href="../README.md"><img src="https://img.shields.io/badge/🏠_Hub-Principal-8B5CF6?style=for-the-badge" alt="Hub Principal" /></a>
<a href="01-PILE-HERMES-ET-RAG.md"><img src="https://img.shields.io/badge/🧠_01-Hermès_%26_RAG-3b82f6?style=for-the-badge" alt="01 Hermès & RAG" /></a>
<a href="02-MONITORING-GPU-ET-SYSTEME.md"><img src="https://img.shields.io/badge/🖥️_02-GPU_RTX_5080-1e1b4b?style=for-the-badge" alt="02 GPU RTX 5080" /></a>
<a href="03-THE-GRID-3D-SYNOPTIQUE.md"><img src="https://img.shields.io/badge/🌐_03-The_Grid_3D-1e1b4b?style=for-the-badge" alt="03 The Grid 3D" /></a>
<a href="04-INFOGERANCE-PARC-ET-VMS.md"><img src="https://img.shields.io/badge/🏢_04-Infogérance_PVE-1e1b4b?style=for-the-badge" alt="04 Infogérance PVE" /></a>
<a href="05-BITE-DIAGNOSTIC-STATION.md"><img src="https://img.shields.io/badge/🧪_05-Station_BITE-1e1b4b?style=for-the-badge" alt="05 Station BITE" /></a>
<a href="06-MOBILE-ET-VOIX-SOUVERAINE.md"><img src="https://img.shields.io/badge/📱_06-Mobile_%26_Voix-1e1b4b?style=for-the-badge" alt="06 Mobile & Voix" /></a>

<br/><br/>

# 🧠 Fiche 01 · La Pile Cognitive Hermès & Moteur RAG Vectoriel
### Cœur Réacteur Arc Stark · Fast-Path Déterministe · Mémoire Long-Terme Anti-Dérive

</div>

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

| [← 🏠 Hub Principal](../README.md) | [🖥️ Page Suivante : Moniteur GPU RTX 5080 ➔](02-MONITORING-GPU-ET-SYSTEME.md) |
|:---|---:|

</div>
