<div align="center">

  <br></br>

  <a href="../README.md">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=40&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS+·+04+INFOGERANCE+PROXMOX+VE_" alt="Fiche 04 Infogérance PVE" />
  </a>

  <br></br>

  <h2>Fiche 04 · Infogérance Active Proxmox VE & Flotte de VMs</h2>

  <p align="center">
    <a href="../README.md">
      <img src="https://img.shields.io/badge/🏠_Hub-Principal-8B5CF6?style=flat-square" alt="Hub Principal" />
    </a>
    <a href="01-PILE-HERMES-ET-RAG.md">
      <img src="https://img.shields.io/badge/🧠_01-Hermès_%26_RAG-181717?style=flat-square" alt="01 Hermès & RAG" />
    </a>
    <a href="02-MONITORING-GPU-ET-SYSTEME.md">
      <img src="https://img.shields.io/badge/🖥️_02-GPU_RTX_5080-181717?style=flat-square" alt="02 GPU RTX 5080" />
    </a>
    <a href="03-THE-GRID-3D-SYNOPTIQUE.md">
      <img src="https://img.shields.io/badge/🌐_03-The_Grid_3D-181717?style=flat-square" alt="03 The Grid 3D" />
    </a>
    <a href="04-INFOGERANCE-PARC-ET-VMS.md">
      <img src="https://img.shields.io/badge/🏢_04-Infogérance_PVE-00d9ff?style=flat-square" alt="04 Infogérance PVE" />
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
  <img src="https://img.icons8.com/fluency/96/000000/server.png" alt="Server Icon" width="80"/>
</div>

<div align="center">
  <p>
    <strong>Démon Serveur Autonome 24/7</strong> &nbsp;•&nbsp; <strong>Supervision Déterministe PVE</strong> &nbsp;•&nbsp; <strong>Bannette IA & Sas Forensique</strong>
  </p>
</div>

> [!IMPORTANT]
> **Vitrine Technologique : Architecture & Démonstration d'Ingénierie**  
> Ce document technique détaille le sous-système d'**Infogérance Active** sous Proxmox VE 9 et l'orchestration déterministe de la flotte de VMs.  
> 🔒 **Propriété Intellectuelle & Sécurité Opérationnelle** : Les scripts d'automatisation interne, clés privées et configurations physiques restent **strictement confinés** au sein de l'Atelier souverain 0xCyberLiTech.

---

## 🎯 Introduction & Rôle Opérationnel

L'exploitation d'une infrastructure privée exige une vigilance continue et un découpage strict des responsabilités. Le module **Infogérance Active** de JARVIS assure l'auscultation en direct de l'hyperviseur bare-metal, la santé des machines virtuelles et la surveillance thermique des équipements réseau.

Conformément à la doctrine de l'Atelier 0xCyberLiTech, **JARVIS observe en temps réel mais n'exécute aucune action destructive sans arbitrage** :
1. **Mesure factuelle directe :** Aucune métrique n'est inventée ou estimée ; tout provient des sockets Unix et de l'API Proxmox.
2. **Sas Forensique Découplé :** Les alertes systèmes sont centralisées dans un journal d'ingestion sans saturer l'opérateur.
3. **Bannette IA à Rythme Unitaire :** Traitement unitaire des micro-chantiers pour éteindre le bruit technique à la racine.

---

## 🏗️ Schéma Directeur de l'Infogérance & Topologie Hyperviseur

Afin de préserver la sanctuarisation de l'infrastructure physique tout en exposant l'ingénierie sous-jacente, la topologie de supervision est modélisée par l'architecture ci-dessous :

```mermaid
flowchart TD
    classDef wan fill:#1e1b4b,stroke:#8b5cf6,stroke-width:2px,color:#fff;
    classDef pve fill:#0f2e2e,stroke:#00d9ff,stroke-width:2px,color:#fff;
    classDef vm fill:#143419,stroke:#10b981,stroke-width:2px,color:#fff;
    classDef nas fill:#312e10,stroke:#f59e0b,stroke-width:2px,color:#fff;
    classDef jarvis fill:#31102f,stroke:#ef4444,stroke-width:2px,color:#fff;

    WAN["🌐 UPLINK FIBRE 10G & ROUTEUR CENTRAL SOUVERAIN"]:::wan

    subgraph PVE["🖥️ HYPERVISEUR BARE-METAL PROXMOX VE"]
        CT109["⚡ CT 109 · JARVIS Core<br/>(Moteur Cognitif Souverain)"]:::jarvis
        VM108["🛡️ VM 108 · SRV-NGINX<br/>(Reverse Proxy, WAF, CrowdSec, SOC)"]:::vm
        VM106["💼 VM 106 · Services Web Entreprise"]:::vm
        VM107["⚙️ VM 107 · Services Applicatifs Internes"]:::vm
        VM101["🧪 VM 101 · Sandbox Qualification Découplée"]:::vm
    end

    subgraph STORAGE["💾 CHÂSSIS PHYSIQUE STOCKAGE ZFS (NAS)"]
        NAS["SRV-NAS · Volumes ZFS & Sondes Thermiques Bare-Metal"]:::nas
    end

    subgraph SDNBUS["🔀 COMMUTATION LOGIQUE SDN (4 PONTS LINUX BRIDGES)"]
        VMBR0["vmbr0 · Trunk Réseau Production"]
        VMBR1["vmbr1 · Management Hors-Bande (OOB)"]
        VMBR2["vmbr2 · Zone Démilitarisée (DMZ)"]
        VMBR3["vmbr3 · Segment Laboratoire & Qualification"]
    end

    WAN --> SDNBUS
    SDNBUS --> PVE
    SDNBUS --> STORAGE
    CT109 -.->|Supervision Déterministe API & Sysfs| PVE
    CT109 -.->|Sondes Matérielles & Métriques ZFS| STORAGE
```

---

## 🔬 Les Blocs Fonctionnels du Parc Matériel

### 1. Passerelle WAN & Routeur 10G
* **Passerelle Fibre 10G :** Télémétrie optique du module SFP+ (puissance reçue, atténuation dBm, débits instantanés symétriques).
* **Routeur 10G Frontal :** Surveillance du processeur multicœur 2.6 GHz, moteur DPI matériel, et statut du tunnel VPN privé WireGuard.

### 2. Le Rack Central des Machines (Homelab 6U)
Chaque instance fait l'objet d'un suivi individualisé avec bargraphes segmentés LED étalons :
* **CT 109 · Moteur JARVIS :** Conteneur LXC Debian 13 hébergeant le moteur cognitif souverain.
* **VM 108 · Passerelle Sécurité :** Reverse Proxy frontal, pare-feu applicatif WAF, moteur CrowdSec et tableau de bord SOC.
* **VM 106 · Plateforme Web :** Serveur d'applications web d'entreprise.
* **VM 107 · Services Internes :** Serveur applicatif dédié aux services internes.
* **VM 101 · Sandbox Qualif :** Environnement confiné et isolé pour le développement et la qualification adverse.

### 3. Les Châssis Physiques Bare-Metal
* **Châssis NAS :** Serveur de stockage physique 8 baies ZFS, sonde thermique matérielle et volumétrie des pools de disques.
* **Nœud Proxmox VE :** Hyperviseur principal, surveillance de la charge CPU globale, allocation RAM et détection des paquets système à mettre à jour.

### 4. Commutation Logique Hôte (4 Ponts Virtuels SDN)
Visualisation de l'interconnexion réseau isolant les segments :
* `vmbr0` : Trunk Réseau Production.
* `vmbr1` : Segment Administration Hors-Bande (OOB / MGMT).
* `vmbr2` : Zone Démilitarisée (DMZ).
* `vmbr3` : Segment Laboratoire & Tests.

### 5. Sas Forensique & Bannette IA à Traitement Unitaire
* **Sas d'Ingestion Centralisé :** Capture automatique des rapports cron, alertes SMART et notifications de sécurité.
* **Principe de l'Alimentation Mesurée (Règle 10.5) :** Afin de prévenir toute fatigue décisionnelle, les anomalies sont traitées une par une à leur cause racine dans l'Atelier D:, garantissant un homelab sain et silencieux.

---

<div align="center">

| [← 🌐 Page Précédente : The Grid 3D](03-THE-GRID-3D-SYNOPTIQUE.md) | [🏠 Hub Principal](../README.md) | [🧪 Page Suivante : Station BITE ➔](05-BITE-DIAGNOSTIC-STATION.md) |
|:---|:---:|---:|

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
