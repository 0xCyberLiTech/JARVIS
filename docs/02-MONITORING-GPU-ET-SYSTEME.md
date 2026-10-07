<div align="center">

  <br></br>

  <a href="../README.md">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=40&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS+·+02+MONITORING+GPU+RTX+5080_" alt="Fiche 02 GPU RTX 5080" />
  </a>

  <br></br>

  <h2>Fiche 02 · Moniteur Système & Inférence GPU RTX 5080</h2>

  <p align="center">
    <a href="../README.md">
      <img src="https://img.shields.io/badge/🏠_Hub-Principal-8B5CF6?style=flat-square" alt="Hub Principal" />
    </a>
    <a href="01-PILE-HERMES-ET-RAG.md">
      <img src="https://img.shields.io/badge/🧠_01-Hermès_%26_RAG-181717?style=flat-square" alt="01 Hermès & RAG" />
    </a>
    <a href="02-MONITORING-GPU-ET-SYSTEME.md">
      <img src="https://img.shields.io/badge/🖥️_02-GPU_RTX_5080-00d9ff?style=flat-square" alt="02 GPU RTX 5080" />
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
  <img src="https://img.icons8.com/fluency/96/000000/processor.png" alt="GPU Icon" width="80"/>
</div>

<div align="center">
  <p>
    <strong>Inférence Blackwell 16 Go GDDR7</strong> &nbsp;•&nbsp; <strong>Oscilloscopes Bi-Canaux</strong> &nbsp;•&nbsp; <strong>Architecture Multi-GPU Ready</strong>
  </p>
</div>

> [!IMPORTANT]
> **Vitrine Technologique : Architecture & Démonstration d'Ingénierie**  
> Ce document technique détaille le monitoring matériel, l'accélération tensorielle RTX 5080 et l'orchestration multi-GPU de JARVIS.  
> 🔒 **Propriété Intellectuelle & Sécurité Opérationnelle** : Les scripts de télémétrie matérielle, adresses physiques et métriques internes restent **strictement confinés** au sein de l'Atelier souverain 0xCyberLiTech.

---

## 🎯 Introduction & Rôle Opérationnel

L'exécution locale de modèles de langage à grande échelle (12B paramètres) et de moteurs vectoriels impose une surveillance thermique et matérielle sans compromis. L'interface **Moniteur Système** de JARVIS constitue le tableau de bord d'avionique du réacteur physique de la station hôte.

Déployé sur une architecture de dernière génération **NVIDIA GeForce RTX 5080 (Blackwell GB203)** équipée de **16 Go de VRAM GDDR7**, ce module assure :
1. La visualisation en temps réel de la charge des cœurs Tensor et CUDA.
2. L'auscultation continue des oscilloscopes thermodynamiques et énergétiques.
3. La régulation stricte de l'allocateur hybride évitant tout débordement mémoire (*swap thrashing*).
4. La préparation logicielle à l'orchestration d'un cluster **Multi-GPU**.

---

## 📸 L'Interface Complète du Moniteur Système

<div align="center">

[![Moniteur Système et GPU RTX 5080](../assets/jarvis-monitoring-gpu.png)](../assets/jarvis-monitoring-gpu.png)

*Console complète du Moniteur Système (1920x2082) : télémétrie instantanée, oscilloscopes double canal, cœurs Tensor/CUDA, allocateur hybride et I/O hôte.*

</div>

---

## 🔬 Décomposition Technique des 5 Niveaux de Surveillance

### Tier 1 · Le Bus de Télémétrie Instantanée
* **GPU Core :** Mesure de la charge instantanée du processeur graphique Blackwell GB203.
* **VRAM GDDR7 :** Occupation précise de la mémoire vidéo (ex: 14.8 Go / 16 Go).
* **Thermique Jonction :** Température directe de la puce silicium (55 °C nominal sous charge).
* **Puissance (Watts) :** Consommation instantanée du GPU face à son budget enveloppe (TDP 360W).
* **CPU Hôte & RAM Système :** Charge globale du processeur multicœur hôte et remplissage des 64 Go de RAM DDR5.

### Tier 2 · Les Oscilloscopes Haute Résolution (Scopes Bi-Canaux)
* **#SCOPE-01 · Spectre Analytique Cœur & VRAM :**
  Oscilloscope temps réel traçant en canal double l'activité de calcul des cœurs (Channel A) et la courbe d'allocation de la VRAM vidéo (Channel B).
* **#SCOPE-02 · Spectre Thermodynamique & Énergie :**
  Tracé simultané de l'évolution de la température de jonction face à la courbe de puissance en Watts, permettant d'anticiper tout phénomène d'emballement thermique.

### Tier 3 · Cœur RTX 5080 & Accélération CUDA
* **Ressources matérielles mobilisées :** 10 752 cœurs CUDA et 336 cœurs Tensor de 5e génération.
* **Moteurs multimédias :** Surveillance des encodeurs/décodeurs matériels NVENC/NVDEC dédiés au transcodage de flux et au traitement visuel.
* **Horloges dynamiques :** Fréquence d'horloge GPU Core et mémoire GDDR7 en mégahertz réels.

### Tier 4 · L'Allocateur de Mémoire Hybride & Scalabilité Multi-GPU
JARVIS orchestre dynamiquement deux classes de modèles sans concurrence d'accès :
* **Modèle de Raisonnement (`Mistral-Nemo 12B`) :** Sanctuarisé à 100 % en VRAM GDDR7 (11.6 Go alloués) pour une vitesse de génération maximale.
* **Modèle d'Embeddings Vectoriels (`Qwen3-Embedding 4B`) :** Déployé en mémoire vive système CPU (4.1 Go alloués) pour décharger la carte graphique et préserver le budget VRAM des contextes longs.
* **Conception Native Multi-GPU (Cluster Ready) :** L'interface d'inférence est conçue sous forme de routeur d'accélérateurs. Elle permet d'adresser dynamiquement un second GPU ou un nœud d'inférence distant sans aucune refonte d'interface.

### Tier 5 · Métriques Système Hôte & I/O
* **Calcul Multicœur :** Fréquence d'horloge stabilisée à 4300 MHz et temps de fonctionnement (*uptime*).
* **Bande Passante Réseau :** Débits entrants/sortants sur l'interface réseau haut débit.
* **Stockage NVMe Array :** Vitesse de lecture et d'écriture sur le volume ultra-rapide hébergeant la base vectorielle.

---

<div align="center">

| [← 🧠 Page Précédente : Pile Hermès](01-PILE-HERMES-ET-RAG.md) | [🏠 Hub Principal](../README.md) | [🌐 Page Suivante : The Grid 3D ➔](03-THE-GRID-3D-SYNOPTIQUE.md) |
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
