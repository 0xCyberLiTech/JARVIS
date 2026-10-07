<div align="center">

<a href="../README.md"><img src="https://img.shields.io/badge/🏠_Hub-Principal-8B5CF6?style=for-the-badge" alt="Hub Principal" /></a>
<a href="01-PILE-HERMES-ET-RAG.md"><img src="https://img.shields.io/badge/🧠_01-Hermès_%26_RAG-1e1b4b?style=for-the-badge" alt="01 Hermès & RAG" /></a>
<a href="02-MONITORING-GPU-ET-SYSTEME.md"><img src="https://img.shields.io/badge/🖥️_02-GPU_RTX_5080-1e1b4b?style=for-the-badge" alt="02 GPU RTX 5080" /></a>
<a href="03-THE-GRID-3D-SYNOPTIQUE.md"><img src="https://img.shields.io/badge/🌐_03-The_Grid_3D-1e1b4b?style=for-the-badge" alt="03 The Grid 3D" /></a>
<a href="04-INFOGERANCE-PARC-ET-VMS.md"><img src="https://img.shields.io/badge/🏢_04-Infogérance_PVE-3b82f6?style=for-the-badge" alt="04 Infogérance PVE" /></a>
<a href="05-BITE-DIAGNOSTIC-STATION.md"><img src="https://img.shields.io/badge/🧪_05-Station_BITE-1e1b4b?style=for-the-badge" alt="05 Station BITE" /></a>
<a href="06-MOBILE-ET-VOIX-SOUVERAINE.md"><img src="https://img.shields.io/badge/📱_06-Mobile_%26_Voix-1e1b4b?style=for-the-badge" alt="06 Mobile & Voix" /></a>

<br/><br/>

# 🏢 Fiche 04 · Infogérance Active Proxmox VE & Flotte de VMs
### Nœud Hyperviseur Bare-Metal · Ponts SDN Linux Bridges · Sas Forensique & Bannette IA

</div>

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

### 1. Passerelle WAN & Routeur ROG GT-BE19000-AI
* **Passerelle Fibre 10G :** Télémétrie optique du module SFP+ (puissance reçue, atténuation dBm, débits instantanés symétriques).
* **Routeur ASUS ROG BE19000 :** Surveillance du processeur Quad-Core 2.6 GHz, moteur DPI matériel TrendMicro, et statut du tunnel VPN privé WireGuard (`wgs1`).

### 2. Le Rack Central des Machines (Homelab 6U)
Chaque instance fait l'objet d'un suivi individualisé avec bargraphes segmentés LED étalons :
* **CT 109 · JARVIS-CORE :** Conteneur LXC Debian 13 hébergeant le moteur cognitif souverain.
* **VM 108 · SRV-NGINX :** Reverse Proxy frontal, pare-feu applicatif WAF, moteur CrowdSec et tableau de bord SOC.
* **VM 106 · SRV-CLT :** Serveur d'applications web d'entreprise.
* **VM 107 · SRV-PA85 :** Serveur applicatif dédié aux services internes.
* **VM 101 · SRV-DEV-1 :** Environnement confiné et isolé pour le développement et la qualification adverse.

### 3. Les Châssis Physiques Bare-Metal
* **SRV-NAS (OMV8) :** Serveur de stockage physique 8 baies ZFS, sonde thermique matérielle AMD Ryzen `k10temp` (45.9 °C) et volumétrie des pools de disques.
* **PROXMOX VE HOST :** Nœud hyperviseur principal, surveillance de la charge CPU globale, allocation RAM (19.5 / 55 Go) et détection des paquets système à mettre à jour.

### 4. Commutation Logique Hôte (4 Ponts Virtuels SDN)
Visualisation de l'interconnexion réseau isolant les segments :
* `vmbr0` : Trunk Réseau Production.
* `vmbr1` : Segment Administration Hors-Bande (OOB / MGMT).
* `vmbr2` : Zone Démilitarisée (DMZ).
* `vmbr3` : Segment Laboratoire & Tests.

### 5. Sas Forensique & Bannette IA à Traitement Unitaire
* **Sas d'Ingestion `/var/log/soc-mail.jsonl` :** Capture automatique des rapports cron, alertes SMART et notifications de sécurité.
* **Principe de l'Alimentation Mesurée (Règle 10.5) :** Afin de prévenir toute fatigue décisionnelle, les anomalies sont traitées une par une à leur cause racine dans l'Atelier D:, garantissant un homelab sain et silencieux.

---

<div align="center">

| [← 🌐 Page Précédente : The Grid 3D](03-THE-GRID-3D-SYNOPTIQUE.md) | [🏠 Hub Principal](../README.md) | [🧪 Page Suivante : Station BITE ➔](05-BITE-DIAGNOSTIC-STATION.md) |
|:---|:---:|---:|

</div>
