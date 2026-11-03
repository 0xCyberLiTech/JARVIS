<!-- MASTER-HEADER-START -->
<div align="center">

<a href="https://0xcyberlitech.com/">
  <img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/headers/header-jarvis.svg" alt="JARVIS // STARK MARK-VII FUI" width="100%" />
</a>

<p align="center">
  <a href="https://0xcyberlitech.com/"><img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/btn-portal.svg" alt="Portail 0xCyberLiTech.com" width="24%" /></a>
  <a href="https://0xcyberlitech.com/soc-rd.html"><img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/btn-soc-rd.svg" alt="Livre Blanc SOC Cockpit" width="24%" /></a>
  <a href="https://0xcyberlitech.com/jarvis-rd.html"><img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/btn-jarvis-rd.svg" alt="Livre Blanc JARVIS IA" width="24%" /></a>
  <a href="https://github.com/0xCyberLiTech?tab=repositories"><img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/btn-github.svg" alt="Catalogue des 23 Dépôts" width="24%" /></a>
</p>
<img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/divider-hud.svg" alt="" width="100%" />
</div>
<!-- MASTER-HEADER-END -->

> [!IMPORTANT]
> **Vitrine Technologique & Tremplin R&D (`0xcyberlitech.com`)**
> Ce dépôt présente un **aperçu visuel et architectural** de l'orchestrateur IA souverain **JARVIS (Stark Mark-VII FUI)** développé au sein de l'Atelier **0xCyberLiTech**.
> L'étude d'ingénierie complète, les schémas de pipeline et le blueprint matériel détaillé sont publiés sur le portail officiel :
> - [**Livre Blanc R&D : Architecture Cognitive & Temps Réel JARVIS**](https://0xcyberlitech.com/jarvis-rd.html)
> - [**Blueprint Matériel : Station IA RTX 5080 Blackwell & Topologie Proxmox**](https://0xcyberlitech.com/blueprint-jarvis.html)

---

## <img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/icons/wire-plan.svg" width="18" height="18" align="absmiddle" alt="" /> 01 // POSTE DE COMMANDEMENT STARK MARK-VII FUI (PRODUCTION 24/7)
<img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/glow-section-cyan.svg" width="100%" alt="" />

<div align="center">

[![Poste de Commandement JARVIS Stark Mark-VII FUI](assets/jarvis-dialogue-core.png)](https://0xcyberlitech.com/jarvis-rd.html)

*Interface holographique Stark Mark-VII FUI en production locale : réacteur central d'inférence, télémétrie GPU Blackwell en temps réel, matrice vocale WebRTC et couplage natif avec le SOC Cockpit.*

</div>

---

## <img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/icons/wire-plan.svg" width="18" height="18" align="absmiddle" alt="" /> 02 // LES 4 INFRANCHISSABLES D'INGÉNIERIE
<img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/glow-section-cyan.svg" width="100%" alt="" />

| Pilier Architectural | Spécification en Production | Approfondissement |
|:---|:---|:---:|
| **01 · Souveraineté Matérielle** | Inférence **100 % locale** sur GPU **NVIDIA GeForce RTX 5080 (16 Go GDDR7 Blackwell)** + LLM **Qwen 3.5 9B**. Zéro octet transmis vers des API cloud externes. | [<img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/btn-explore.svg" alt="Blueprint RTX 5080" />](https://0xcyberlitech.com/blueprint-jarvis.html) |
| **02 · Fast-Path Déterministe (`< 200 ms`)** | Bipartition stricte **SOC (Cyberdéfense)** / **Infogérance (Proxmox, Réseau, NAS)**. Les métriques d'état sont résolues par le code machine en `< 200 ms` avec **zéro hallucination LLM**. | [<img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/btn-explore.svg" alt="Dossier R&D JARVIS" />](https://0xcyberlitech.com/jarvis-rd.html) |
| **03 · Boucle Vocale Duplex & Vision** | Transcription **Faster-Whisper** (`int8_float16`), synthèse neurale **Antoine HD** (moteur natif Windows MCI sans latence navigateur) et analyse multimodale. | [<img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/btn-explore.svg" alt="Dossier R&D JARVIS" />](https://0xcyberlitech.com/jarvis-rd.html) |
| **04 · Mémoire Hermès & Pont MCP** | Persistance **SQLite WAL**, indexation vectorielle **RAG** (`SQLite-vec` & `qwen3-embedding:4b`) et serveur **MCP natif (22 outils)** en lecture seule stricte. | [<img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/btn-explore.svg" alt="Dossier R&D JARVIS" />](https://0xcyberlitech.com/jarvis-rd.html) |

```mermaid
flowchart LR
    MIC["[STT] Entree Audio WebRTC<br/>Faster-Whisper STT"] --> ROUTER["[ROUTER] Routeur Deterministe<br/>Fast-Path < 200 ms"]
    ROUTER -->|"Etat SOC / Infra (0 LLM)"| COLLECT["[SONDES] Sondes Read-Only<br/>SOC · Proxmox · NAS"]
    ROUTER -->|"Requete Cognitive"| LLM["[LLM] Qwen 3.5 9B Local<br/>RTX 5080 16 Go Blackwell"]
    LLM <--> RAG["[RAG] Memoire Hermes<br/>SQLite WAL + RAG Vectoriel"]
    COLLECT --> TTS["[TTS] Synthese Antoine HD<br/>Sortie Audio Directe"]
    LLM --> TTS
```

---

## <img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/icons/wire-plan.svg" width="18" height="18" align="absmiddle" alt="" /> 03 // APERÇU VISUEL DES MODULES (CAPTURES RETINA 2X)
<img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/glow-section-cyan.svg" width="100%" alt="" />

<div align="center">

| **Grille Synoptique 3D & Orchestration** | **Télémétrie GPU RTX 5080 Blackwell** |
|:---:|:---:|
| [![Synoptique 3D](assets/jarvis-synoptic-3d-grid.png)](https://0xcyberlitech.com/jarvis-rd.html) | [![Monitoring GPU](assets/jarvis-monitoring-gpu.png)](https://0xcyberlitech.com/blueprint-jarvis.html) |
| *Cartographie temps réel des flux cognitifs, du bus MCP et des sondes d'infrastructure.* | *Suivi granulaire VRAM GDDR7, température, latence d'inférence Qwen 3.5 9B et charge CUDA.* |

| **Convergence Infogérance & Sas d'Alertes SOC** | **Mémoire Hermès & Apprentissage Continu** |
|:---:|:---:|
| [![Convergence SOC](assets/jarvis-infog-sas-convergence.png)](https://0xcyberlitech.com/jarvis-rd.html) | [![Mémoire Hermès](assets/jarvis-hermes-apprentissage.png)](https://0xcyberlitech.com/jarvis-rd.html) |
| *Corrélation unifiée des 4 VMs Proxmox VE, du routeur critique, du NAS et des alertes SOC.* | *Indexation vectorielle RAG, graphe de connaissances SQLite WAL et auto-vérification.* |

</div>

<details>
<summary><b>Afficher les vues complémentaires (Bancs BITE Déterministes & Interfaces Mobiles LAN)</b></summary>
<br/>

<div align="center">

| **Synoptique BITE Auto-Test** | **Banc Déterministe DTC** |
|:---:|:---:|
| ![BITE Synoptic](assets/jarvis-bite-synoptic.png) | ![BITE Bench](assets/jarvis-bite-dtc-bench.png) |

| **Interface Mobile Souveraine** | **Quadrilatère Réseau Mobile** |
|:---:|:---:|
| ![Mobile Interface](assets/jarvis-mobile-interface.png) | ![Mobile Network](assets/jarvis-mobile-network-quad.png) |

</div>
</details>

---

## <img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/icons/wire-plan.svg" width="18" height="18" align="absmiddle" alt="" /> 04 // EXPLORER L'ÉTUDE COMPLÈTE SUR 0XCYBERLITECH.COM
<img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/glow-section-cyan.svg" width="100%" alt="" />

- **Dossier d'Architecture R&D JARVIS :** [https://0xcyberlitech.com/jarvis-rd.html](https://0xcyberlitech.com/jarvis-rd.html)
- **Blueprint Matériel & Infrastructure :** [https://0xcyberlitech.com/blueprint-jarvis.html](https://0xcyberlitech.com/blueprint-jarvis.html)
- **Dossier d'Architecture SOC Cockpit v5.5 :** [https://0xcyberlitech.com/soc-rd.html](https://0xcyberlitech.com/soc-rd.html)

<!-- MASTER-FOOTER-START -->
<div align="center">
<img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/divider-hud.svg" alt="" width="100%" />

<a href="https://0xcyberlitech.com/">
  <img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/footer-master.svg" alt="0xCyberLiTech — Architecture Cyberdéfense, Ingénierie Déterministe & IA Souveraine" width="100%" />
</a>

<p align="center"><a href="https://0xcyberlitech.com/"><img src="https://raw.githubusercontent.com/0xCyberLiTech/0xcyberlitech/main/assets/badge-antigravity.svg" alt="Architecturé par Marc & Antigravity (Google DeepMind)" width="520" /></a></p>

<sub><b>Architecturé &amp; Forgé par Marc &amp; Antigravity (Google DeepMind)</b> &nbsp;·&nbsp; <a href="https://0xcyberlitech.com/"><b>0xcyberlitech.com</b></a> &nbsp;·&nbsp; <a href="https://0xcyberlitech.com/soc-rd.html">Architecture SOC Cockpit v5.5</a> &nbsp;·&nbsp; <a href="https://0xcyberlitech.com/jarvis-rd.html">Architecture JARVIS Mark-VII</a> &nbsp;·&nbsp; <a href="https://0xcyberlitech.com/blueprint-jarvis.html">Blueprint Matériel RTX 5080</a></sub>

</div>
<!-- MASTER-FOOTER-END -->
