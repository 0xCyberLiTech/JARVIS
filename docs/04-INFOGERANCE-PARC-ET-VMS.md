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

### 5. Pupitre de Convergence // Sas & Triage IA (#INF-07 à #INF-10)

L'une des innovations majeures de l'Atelier 0xCyberLiTech réside dans la **sanctuarisation absolue de la boîte de messagerie personnelle de Marc** et l'interception chirurgicale de 100 % des signaux techniques du Homelab via un sas forensique souverain.

<div align="center">
  <br/>
  <img src="../assets/jarvis-infog-sas-convergence.png" alt="Pupitre de Convergence // Sas & Triage IA Homelab" width="100%"/>
  <p><em>Figure 4.1 — Pupitre de Convergence // Sas & Triage IA : Goulot de filtration déterministe (< 50ms), Canaux souverains sans SMTP et Bannette unitaire anti-fatigue.</em></p>
  <br/>
</div>

#### 🏛️ Philosophie Fondatrice : Zéro Bruit & Zéro SMTP Sortant
Dans une infrastructure classique, les serveurs, hyperviseurs et équipements réseau inondent l'administrateur de courriels d'alertes redondants (cron jobs, synchronisations, logs de scan).  
**La doctrine de l'Atelier 0xCyberLiTech inverse ce paradigme :**
* **0 SMTP Sortant :** Aucun octet d'alerte ne quitte le réseau local vers Internet. Tout est capté, horodaté et traité localement.
* **Boîte Marc Sanctuarisée :** Interception déterministe en amont ; la messagerie personnelle de Marc reste vierge de tout spam d'exploitation.

---

#### 🧱 Analyse Détaillée Brique par Brique du Synoptique

```mermaid
flowchart TD
    classDef capt fill:#0e1e38,stroke:#00f0ff,stroke-width:1.5px,color:#fff;
    classDef filtre fill:#142850,stroke:#00ff9d,stroke-width:1.5px,color:#fff;
    classDef goulot fill:#2a1b4e,stroke:#a855f7,stroke-width:2px,color:#fff;
    classDef ia fill:#3b122d,stroke:#ff0055,stroke-width:2px,color:#fff;
    classDef atelier fill:#08241b,stroke:#10b981,stroke-width:2px,color:#fff;

    subgraph CAPTAGE["📡 1. CAPTAGE INFRA & BUS LOCAL (.1.0/24)"]
        S1["srv-dev-1 (VM 101)"]:::capt
        S2["srv-clt (VM 106)"]:::capt
        S3["srv-pa05 (VM 107)"]:::capt
        S4["kali (VM 108)"]:::capt
        S5["PVE Host (Bare-Metal)"]:::capt
        LOGS["Journal Forensique Local<br/><code>/var/log/soc-mail.jsonl</code>"]:::capt
    end

    subgraph FILTRES["⚡ 2. LES 4 FILTRES DÉTERMINISTES (< 50ms · 0 LLM)"]
        F1["FILTRE 01 · CYBER (SOC)<br/>CrowdSec · WAF · Blocages"]:::filtre
        F2["FILTRE 02 · CRONS & SYSTÈME<br/>Détection Dérives & Pannes"]:::filtre
        F3["FILTRE 03 · ROUTEUR ROG<br/>Syslog UDP 514 · AiProtection"]:::filtre
        F4["FILTRE 04 · COFFRES DR<br/>Snapshots ZFS · 16 Coffres"]:::filtre
    end

    subgraph CONVERGENCE["🔀 3. GOULOT DE CONVERGENCE & ARBITRAGE NEURAL"]
        PIPE["Conduits Fil de Fer & Goulot Central"]:::goulot
        ARBITRE["Arbitrage Neural & Bascule Déterministe<br/>(LLM Local + Fail-Safe RTC < 1ms)"]:::goulot
        VOIX["Synthèse Vocale Antoine HD<br/>(Enceintes Windows Marc)"]:::goulot
    end

    subgraph GOUVERNANCE["🧠 4. CERVEAU IA & BANNETTE UNITAIRE (RÈGLE 10.5)"]
        BANNETTE["Bannette IA Cadenassée<br/>(1 seul micro-chantier à la fois)"]:::ia
    end

    subgraph REMEDIATION["🛠️ 5. REMÉDIATION RACINE ATELIER D:"]
        ATELIER["Atelier D: (Marc & Antigravity)<br/>Correction Racine · Zéro Rustine · Scellé Git"]:::atelier
    end

    S1 & S2 & S3 & S4 & S5 --> LOGS
    LOGS --> F1 & F2 & F3 & F4
    F1 & F2 & F3 & F4 --> PIPE
    PIPE --> ARBITRE
    ARBITRE --> VOIX
    ARBITRE --> BANNETTE
    BANNETTE --> ATELIER
```

##### 1. Brique #INF-07 · Pupitre de Convergence & Compteurs Étalons
Le bandeau supérieur restitue en temps réel l'impact de la sanctuarisation :
* **908 Mails Épargnés (28j) :** Nombre exact de courriels d'exploitation neutralisés et évités sur la boîte personnelle de Marc.
* **4 577 Signaux Absorbés Bus :** Télémétrie brute captée par le bus local et analysée sans latence.
* **0 En Cours (Dossier Qualifié par l'IA) :** Indique qu'aucun blocage non résolu n'est en suspens.
* **100% Fiabilisation Racine :** Taux de résolution définitive sans contournement ni rustine temporaire.

##### 2. Brique #INF-10 · Goulot de Convergence & Les 4 Filtres Déterministes (< 50 ms)
Le cœur du moteur s'appuie sur une bipartition stricte : **aucun LLM n'intervient sur le calcul d'état des machines**. Tout est évalué par du code machine déterministe en moins de 50 millisecondes :
* **Filtre 01 · Cyber (SOC) :** Traque permanente sur le réseau `/24`, synchronisation avec la Kill Chain et CrowdSec (270 événements traités, 0 fuite SMTP).
* **Filtre 02 · Crons & Système :** Auscultation des tâches planifiées des VMs Linux et de l'hyperviseur (3 638 événements filtrés, élimination des crons verbeux).
* **Filtre 03 · Routeur ROG :** Collecte des trames Syslog UDP 514 en provenance du routeur central Wi-Fi 7 et des modules de sécurité Trend Micro AiProtection (133 événements).
* **Filtre 04 · Coffres DR :** Contrôle de fraîcheur et de cohérence des 16 coffres souverains de sauvegarde Proxmox VE et NAS OMV8 (39 signaux, 100% GO).

##### 3. Conduits Fil de Fer & Arbitrage Neural
* **Esthétique Vectorielle Fil de Fer :** Reprenant le langage graphique des coffres-forts DR, les conduits représentent l'entonnoir où convergent les flux hétérogènes de l'infrastructure.
* **Bascule Déterministe Fail-Safe (< 1 ms) :** Le moteur dispose d'un basculement instantané (RTC swap) : si le moteur neural local est sollicité, il est encadré par des gardiens déterministes inviolables. Les alertes critiques sont synthétisées vocalement par **Antoine HD** directement sur les enceintes Windows de Marc via le moteur MCI souverain, sans dépendance réseau externe.

##### 4. Brique #INF-01 · Captage Infra & Bus Local (.1.0/24)
Surveillance passive et dérivation en continu vers `/var/log/soc-mail.jsonl`. Les 5 cœurs vitaux du réseau sont auscultés sans agents lourds :
* `srv-dev-1` (VM 101) · Segment laboratoire
* `srv-clt` (VM 106) · Serveur web
* `srv-pa05` (VM 107) · Applicatifs internes
* `kali` (VM 108) · Passerelle sécurité & SOC
* `PVE Host` (Nœud MS-01) · Hyperviseur bare-metal

##### 5. Brique #INF-08 · Cerveau IA & Bannette Unitaire (Règle 10.5 AGENTS.md)
* **Principe de l'Alimentation Mesurée :** Pour préserver la clarté d'esprit de l'opérateur et prévenir toute fatigue décisionnelle face au flux technique, le débit est strictement régulé.
* **Débit Régulé :** La Bannette IA ne présente **qu'un seul micro-chantier prioritaire à la fois**. Quand le homelab est sain, la bannette affiche fièrement son état cadenassé : *"Bannette 100% vidée — Aucun chantier en attente — Homelab sain"*.

##### 6. Brique #INF-09 · Remédiation Atelier D: & Registre Workflow Scellé
* **Mandat Exclusif Atelier D: :** JARVIS est strictement confiné en lecture seule. L'infogérance active (remédiations, scripts de maintenance, modifications crontab) est exécutée exclusivement par Antigravity et Marc sur l'Atelier `D:\0xCyberLiTech`.
* **Registre Immuable des Actions Scellées :** Chaque remédiation fait l'objet d'un ticket forensique vérifiable, avec l'action PowerShell exécutée, la preuve machine associée et l'horodatage UTC inviolable.

##### 7. Sas Forensique Temps Réel (`/var/log/soc-mail.jsonl`)
Un terminal déroulant en pied de page permet à l'opérateur d'inspecter à tout moment le flux brut des signaux captés pour une traçabilité forensic totale.

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
