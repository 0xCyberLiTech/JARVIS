<div align="center">

<a href="../README.md"><img src="https://img.shields.io/badge/🏠_Hub-Principal-8B5CF6?style=for-the-badge" alt="Hub Principal" /></a>
<a href="01-PILE-HERMES-ET-RAG.md"><img src="https://img.shields.io/badge/🧠_01-Hermès_%26_RAG-1e1b4b?style=for-the-badge" alt="01 Hermès & RAG" /></a>
<a href="02-MONITORING-GPU-ET-SYSTEME.md"><img src="https://img.shields.io/badge/🖥️_02-GPU_RTX_5080-1e1b4b?style=for-the-badge" alt="02 GPU RTX 5080" /></a>
<a href="03-THE-GRID-3D-SYNOPTIQUE.md"><img src="https://img.shields.io/badge/🌐_03-The_Grid_3D-1e1b4b?style=for-the-badge" alt="03 The Grid 3D" /></a>
<a href="04-INFOGERANCE-PARC-ET-VMS.md"><img src="https://img.shields.io/badge/🏢_04-Infogérance_PVE-1e1b4b?style=for-the-badge" alt="04 Infogérance PVE" /></a>
<a href="05-BITE-DIAGNOSTIC-STATION.md"><img src="https://img.shields.io/badge/🧪_05-Station_BITE-3b82f6?style=for-the-badge" alt="05 Station BITE" /></a>
<a href="06-MOBILE-ET-VOIX-SOUVERAINE.md"><img src="https://img.shields.io/badge/📱_06-Mobile_%26_Voix-1e1b4b?style=for-the-badge" alt="06 Mobile & Voix" /></a>

<br/><br/>

# 🧪 Fiche 05 · Station BITE MK-IX (Autodiagnostic Avionique & Banc d'Épreuve)
### Standards ARINC 604 & MIL-STD-1553B · 8 Calculateurs LRU · Synoptique Vectoriel & Simulateur d'Avaries

</div>

---

## 🧭 1. Vue d'Ensemble & Rôle Opérationnel

Inspirée directement de l'ingénierie aéronautique et spatiale (Airbus A350, Rafale, Boeing 787), la **Station BITE MK-IX** (*Built-In Test Equipment*) est le **Central Maintenance Computer** autonome de JARVIS.

Dans une infrastructure hybride souveraine, un agent d'IA ne peut pas se contenter d'« espérer » que ses briques matérielles fonctionnent. La Station BITE remplit trois missions fondamentales :
1. **La Primauté Déterministe Absolue (Règle 13) :** Zéro modèle probabiliste ni hallucination sur l'état physique. Tout indicateur est mesuré par du code machine bare-metal direct (< 200 ms).
2. **L'Accessibilité Souveraine pour Marc :** Synthèse vocale instantanée par Antoine HD (`fr-CA-AntoineNeural`) énonçant l'état de santé global et les anomalies sans imposer de lecture de logs denses.
3. **Le Banc d'Épreuve Didactique :** Pour prouver qu'un système de surveillance fonctionne, il faut être capable de **l'éprouver contre ses propres pannes**. BITE embarque un simulateur d'avaries en mémoire vive démontrant la chaîne de causalité logique sans danger pour le matériel.

---

## 📊 2. Logigramme Déterministe d'Isolation de Panne & Résilience

Le moteur BITE applique un cycle strict inspiré de la norme **ARINC 604** :

```mermaid
flowchart TD
    subgraph CYCLES["1. DÉCLENCHEMENT D'ACQUISITION"]
        PBIT["<b>PBIT</b><br/>Power-On Test (Boot)"]
        CBIT["<b>CBIT</b><br/>Continuous (30s)"]
        IBIT["<b>IBIT</b><br/>Initiated (Marc / Voix / F9)"]
    end

    CYCLES --> DISPATCH["<b>Aiguilleur BITE Central</b><br/>Cadence Bus 1000 Hz · Latence 0.42 ms"]

    subgraph AUDIT["2. AUDIT EN PARALLÈLE NON-BLOQUANT (8 LRU)"]
        ECU1["ECU-01 Moteur CT 109"]
        ECU2["ECU-02 Compute Proxmox"]
        ECU3["ECU-03 Stockage NAS OMV8"]
        ECU4["ECU-04 Réseau Fibre 10G"]
        ECU5["ECU-05 Sentinelle SOC"]
        ECU6["ECU-06 IA GPU RTX 5080"]
        ECU7["ECU-07 Mémoire Hermès"]
        ECU8["ECU-08 Chaîne Vocale"]
    end

    DISPATCH --> AUDIT

    AUDIT --> VERIFY{"Anomalie détectée sur une sonde ?"}

    VERIFY -- "NON (34/34 GO)" --> HEALTH_OK["<b>100% NOMINAL</b><br/>0 DTC actif · Voyants Vert Émeraude<br/>Synthèse vocale : 'Tous les systèmes sont nominaux.'"]

    VERIFY -- "OUI" --> ROOT_CAUSE["<b>Isolation de Cause Racine</b><br/>Corrélation croisée des invariants"]
    
    ROOT_CAUSE --> EMIT_DTC["<b>Génération Frame DTC</b><br/>Code défaut normalisé + Sévérité"]
    
    EMIT_DTC --> SHIELDING["<b>Sanctuarisation Safe-Mode</b><br/>Immunisation des calculateurs sains<br/>Interdiction des fausses alertes en cascade"]
    
    SHIELDING --> ACTION_PLAN{"Action Auto-Guérison ?"}
    ACTION_PLAN -- "OUI" --> REMEDIATION["Bascule Failover Locale / Réarmement Socket"]
    ACTION_PLAN -- "NON" --> VOCAL_ALERT["Notification Prioritaire Antoine HD & Sas Marc"]
```

---

## 📸 3. Les 3 Sous-Interfaces Maîtresses de la Station BITE

La Station BITE déploie **3 interfaces spécialisées**, interconnectées en temps réel :

### 🧰 Sous-Page 01 · La Valise & le Pupitre des 8 Calculateurs LRU

Le pupitre principal présente la vue d'ensemble télémétrique (Santé globale, Calculateurs en ligne, Sondes & Invariants, Codes Défaut DTC, Cadence de scan) et les **8 boîtiers électroniques LRU** (*Line Replaceable Units*) dotés de cabochons LED 3D et jauges segmentées :

<div align="center">

[![Pupitre 01 BITE MK-IX](../assets/jarvis-bite-health.png)](../assets/jarvis-bite-health.png)

*Sous-Page 01 : Pupitre des 8 calculateurs LRU avec statut télémétrique haute fidélité.*

</div>

---

### ⚡ Sous-Page 02 · Le Synoptique Dynamique du Bus Vectoriel SVG

Le synoptique vectoriel matérialise l'architecture avionique **MIL-STD-1553B / ARINC 604** :
- **CAN-A (Backbone Principal 10 Gbps) :** Magistral principal actif (tracé cyan néon) reliant le cœur JARVIS aux calculateurs d'infrastructure.
- **CAN-B (Canal de Secours Redondant 1 Gbps) :** Canal de secours en attente chaude (tracé ambre néon) assurant la continuité de service en cas de rupture de lien.
- **JARVIS Bus Master :** Cœur de synchronisation central cadencé à **1000 Hz** (latence mesurée de **0.42 ms**, gigue de **0.01 ms**).

<div align="center">

[![Synoptique Bus BITE](../assets/jarvis-bite-synoptic.png)](../assets/jarvis-bite-synoptic.png)

*Sous-Page 02 : Synoptique vectoriel SVG du double bus de données et des 8 boîtiers blindés.*

</div>

---

### 🛡️ Sous-Page 03 · Le Banc d'Épreuve Pédagogique & Matrice des Codes Défaut (DTC)

Véritable laboratoire de résilience, cette sous-page permet d'injecter des scénarios d'avarie contrôlés pour visualiser en direct la propagation des pannes et leur confinement étanche :
- **Annunciator Lamp Test :** Bouton `💡 TEST LAMPES` allumant instantanément tous les voyants LED du pupitre pour certifier l'absence d'ampoule ou d'indicateur grillé.
- **4 Scénarios Réels d'Avarie :**
  1. `SC-01 · FIBRE WAN` : Rupture de porteuse 10G Freebox (cascade Réseau ➔ SOC ➔ bascule sur voix locale autonome).
  2. `SC-02 · PROXMOX WAF` : Arrêt brutal du reverse-proxy srv-nginx VM 108 (confinement : le conteneur CT 109 et le GPU restent au vert).
  3. `SC-03 · GPU BLACKWELL` : Surchauffe simulée > 85°C sur la RTX 5080 (verrouillage thermique VRAM immédiat pour protéger le composant bare-metal).
  4. `SC-04 · STOCKAGE NAS` : Perte de la sonde de température AMD k10temp (panne locale isolée sans impact sur les volumes ZFS).
- **Deck de Contrôle & Fiche Didactique :** Injection, réarmement instantané au réel, et ouverture d'une fiche didactique détaillant la cause racine, les répercussions et la procédure de dépannage.
- **Matrice des Codes Défaut (DTC Frame) :** Registre officiel des pannes actives avec horodatage, sévérité et remédiation directe.

<div align="center">

[![Banc d'Épreuve et DTC BITE](../assets/jarvis-bite-dtc-bench.png)](../assets/jarvis-bite-dtc-bench.png)

*Sous-Page 03 : Banc d'épreuve pédagogique, injecteur de pannes et matrice des codes DTC.*

</div>

---

## 🔬 4. Cartographie Technique des 8 Calculateurs LRU

| LRU Code | Désignation | Équipements Physiques & Virtuels Rattachés | Sondes Machine Contrôlées |
|:---:|:---|:---|:---|
| **ECU-01** | **Moteur Hôte & Conteneur** | Conteneur LXC 109 Debian 13 (Flask/Waitress) | RSS RAM (< 2 Go), Threads (33), Socket MCP :5010, WebSocket PTY :5001 |
| **ECU-02** | **Compute Proxmox VE** | Hyperviseur Minisforum MS-01 (i9-13900H) | API PVE, 4 VMs Debian (101, 106, 107, 108), KVM hyperviseur |
| **ECU-03** | **Stockage NAS OMV8** | Serveur bare-metal 8 baies NVMe / ZFS | Sonde AMD Ryzen `k10temp` (45.8 °C), montages NFS/SMB, volumes ZFS |
| **ECU-04** | **Réseau Routeur & Fibre** | Freebox Ultra 10G + Routeur ASUS ROG GT-BE19000-AI | Porteuse 10G-EPON, latence WAN, débit crête, uplink inter-switch 2.5G |
| **ECU-05** | **Cyberdéfense SOC** | Sentinelle SOC Cockpit & Threat Intelligence | Détection Suricata NIDS, IP bannies CrowdSec, jails Fail2ban, score C2 |
| **ECU-06** | **IA & Inférence Ollama** | Station Tour Windows Bare-metal (RTX 5080) | VRAM GDDR7 (11.6 Go / 16 Go), port 11434, tunnel SSH, modèle NeMo 12B |
| **ECU-07** | **Mémoire Hermès & RAG** | Base Vectorielle & Sceau Hermès | 356 fiches mémoire, base ChromaDB (4469 chunks), intégrité cognitive |
| **ECU-08** | **Voix & Multimédia** | Pipeline Vocal Antoine HD & Edge-TTS | Plancher de parole (68 ms/caractère), player MCI Windows, latence < 100 ms |

---

## 🎖️ 5. Pourquoi Cette Approche dans un Projet Personnel ?

La plupart des assistants virtuels grand public masquent leurs défaillances derrière des messages vagues (*« Oups, une erreur est survenue »*). 

Dans le cadre d'un système autonome conçu pour un opérateur malvoyant, **l'incertitude est proscrite**. La Station BITE apporte une traçabilité totale :
* Chaque panne a un nom, un code, une cause et un périmètre de confinement.
* Marc sait à la milliseconde près si un ralentissement provient de la liaison fibre de l'opérateur, d'une chauffe temporaire de la carte graphique, ou d'une maintenance sur l'hyperviseur.
* La résilience n'est pas un concept théorique : elle est prouvée, mesurée et démontrée en permanence.

---

<div align="center">

| [← 🏢 Page Précédente : Infogérance Parc](04-INFOGERANCE-PARC-ET-VMS.md) | [🏠 Hub Principal](../README.md) | [📱 Page Suivante : Mobile & Voix ➔](06-MOBILE-ET-VOIX-SOUVERAINE.md) |
|:---|:---:|---:|

</div>
