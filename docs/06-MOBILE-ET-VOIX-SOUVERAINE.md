<div align="center">

<a href="../README.md"><img src="https://img.shields.io/badge/🏠_Hub-Principal-8B5CF6?style=for-the-badge" alt="Hub Principal" /></a>
<a href="01-PILE-HERMES-ET-RAG.md"><img src="https://img.shields.io/badge/🧠_01-Hermès_%26_RAG-1e1b4b?style=for-the-badge" alt="01 Hermès & RAG" /></a>
<a href="02-MONITORING-GPU-ET-SYSTEME.md"><img src="https://img.shields.io/badge/🖥️_02-GPU_RTX_5080-1e1b4b?style=for-the-badge" alt="02 GPU RTX 5080" /></a>
<a href="03-THE-GRID-3D-SYNOPTIQUE.md"><img src="https://img.shields.io/badge/🌐_03-The_Grid_3D-1e1b4b?style=for-the-badge" alt="03 The Grid 3D" /></a>
<a href="04-INFOGERANCE-PARC-ET-VMS.md"><img src="https://img.shields.io/badge/🏢_04-Infogérance_PVE-1e1b4b?style=for-the-badge" alt="04 Infogérance PVE" /></a>
<a href="05-BITE-DIAGNOSTIC-STATION.md"><img src="https://img.shields.io/badge/🧪_05-Station_BITE-1e1b4b?style=for-the-badge" alt="05 Station BITE" /></a>
<a href="06-MOBILE-ET-VOIX-SOUVERAINE.md"><img src="https://img.shields.io/badge/📱_06-Mobile_%26_Voix-3b82f6?style=for-the-badge" alt="06 Mobile & Voix" /></a>

<br/><br/>

# 📱 Fiche 06 · Accessibilité Mobile Nomade & Voix Souveraine MCI
### Ergonomie PWA Tactile · Tunnel VPN WireGuard Isolé · Moteur Audio Natif Windows MCI

</div>

---

## 🎯 Introduction & Rôle Opérationnel

L'accessibilité est le principe cardinal qui a guidé l'architecture de JARVIS. L'interface a été spécialement conçue pour offrir un confort auditif et un retour vocal immédiat à l'opérateur.

Le système met en œuvre deux canaux d'accès souverains complémentaires :
1. **L'Interface Mobile PWA Nomade :** Une vue tactile ultra-légère accessible en déplacement exclusivement au travers d'un tunnel VPN chiffré privé (zéro port ouvert sur Internet).
2. **La Passerelle Vocale Souveraine Antoine HD :** Un moteur de restitution sonore natif Windows MCI diffusant les alertes directement sur les enceintes de l'Atelier sans dépendre du navigateur web.

---

## 📸 L'Interface Mobile Nomade (Extreme HUD Touch)

<div align="center">

<img src="../assets/jarvis-mobile-interface.png" alt="Interface Mobile JARVIS" width="380" style="border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.6);"/>

<br/><sub><em>Interface tactile mobile JARVIS : ergonomie pensée pour le pouce, consultation instantanée de la santé globale et dialogue vocal chiffré.</em></sub>

</div>

---

## 🔬 Les Deux Vecteurs d'Interaction Souverains

### 1. L'Accès Mobile Sécurisé (Zero Trust & VPN Privé)
* **Cloisonnement Réseau Strict :** L'application mobile ne traverse aucun cloud public ni relais tiers. La liaison s'établit au travers d'un tunnel **WireGuard chiffré de bout en bout**.
* **Architecture Découplée (BFF - Backend For Frontend) :** L'IHM mobile fonctionne comme un module consommateur indépendant (`mobile_bus.py`). Le Cœur de JARVIS ne dépend pas du mobile et démarre nominalement même en l'absence de client nomade.
* **Ergonomie Pensée pour le Pouce :** Boutons d'action rapides, bascule instantanée entre les modes d'arbitrage (`SOC`, `INFOG`, `GÉN`), et déclenchement micro par simple maintien tactile.

### 2. La Synthèse Vocale Souveraine Antoine HD via Windows MCI
* **Qualité Haute Fidélité :** Voix chaleureuse et fluide d'Antoine HD générée localement.
* **Diffusion Native au Niveau OS (Windows MCI) :** La restitution sonore est confiée à l'API système MCI (*Media Control Interface*) de Windows. Cela permet à JARVIS de parler sur les enceintes de l'Atelier même lorsque le navigateur est fermé ou réduit en arrière-plan.
* **Plancher de Parole Déterministe (~68 ms/caractère) :** Calcul mathématique de la durée exacte de chaque annonce pour empêcher toute coupure intempestive de phrase.
* **Hiérarchie Vocale d'Urgence :** Toute alerte critique de sécurité coupe instantanément les bilans d'état réguliers pour transmettre l'information vitale sans latence.

---

<div align="center">

| [← 🧪 Page Précédente : Station BITE](05-BITE-DIAGNOSTIC-STATION.md) | [🏠 Retour au Hub Principal](../README.md) |
|:---|---:|

</div>
