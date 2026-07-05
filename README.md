<div align="center">

  <br></br>

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=50&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS_" alt="Titre dynamique JARVIS" />
  </a>

  <h2>Assistant IA 100 % local · voix broadcast · interface holographique · SOC autonome 24/7</h2>

  <p align="center">
    <a href="https://0xcyberlitech.github.io/">
      <img src="https://img.shields.io/badge/Portfolio-0xCyberLiTech-181717?logo=github&style=flat-square" alt="Portfolio" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/tags">
      <img src="https://img.shields.io/github/v/tag/0xCyberLiTech/JARVIS?sort=semver&label=version&style=flat-square&color=8B5CF6" alt="Dernière version" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/blob/main/CHANGELOG.md">
      <img src="https://img.shields.io/badge/%F0%9F%93%84%20Changelog-JARVIS-8B5CF6?style=flat-square" alt="Changelog" />
    </a>
    <img src="https://img.shields.io/badge/LLM-100%25%20local-0a7d33?style=flat-square" alt="LLM 100% local" />
    <img src="https://img.shields.io/badge/LLM%20cloud-0%25-0a7d33?style=flat-square" alt="0% LLM cloud" />
  </p>

  <sub><strong>IA 100 % locale</strong> &nbsp;·&nbsp; <strong>Voix naturelle STT / TTS</strong> &nbsp;·&nbsp; <strong>Automatisation SOC</strong> &nbsp;·&nbsp; <strong>RTX 5080</strong></sub>

</div>

---

<div align="center">

### *Une IA qui vit sur votre machine — elle voit, parle, se souvient, apprend et veille. Seule.*

</div>

**JARVIS** est un assistant IA personnel de type *Iron Man* qui tourne **entièrement en local** sur un seul poste — Python/Flask + Ollama, RTX 5080. Pas un chatbot de plus : un **agent** doté d'une voix broadcast, d'une mémoire qui ne s'efface pas, d'une vision multimodale, et d'un **SOC qui défend l'infrastructure 24/7 sans intervention**. Zéro LLM cloud, zéro abonnement — **le raisonnement, la mémoire et les données restent sur le poste** *(voix edge-tts en ligne au choix, repli Kokoro neural local hors-ligne)*.

> [!IMPORTANT]
> **Vitrine — pas une procédure d'installation.**
> Ce dépôt **présente** le projet (architecture, conception, capacités). Le **code opérationnel reste privé** : JARVIS n'est **pas déployable** depuis ce dépôt. On y montre le *quoi* et le *pourquoi* — jamais le *comment* exact.

<div align="center">
  <img src="Images/accueil.webp" alt="Écran de démarrage JARVIS — séquence SYS.INIT" width="820"/>
  <br/><sub><em>Au démarrage, JARVIS s'auto-diagnostique — <b>NEURAL CORE · VOICE ENGINE · AUDIO DSP · KNOWLEDGE BASE</b> à 100 % — puis annonce son état : modèle <code>qwen3.5:9b</code> via Ollama, voix Edge Antoine, DSP (EQ · compresseur · DeepFilterNet), accélération CUDA sm_120 Blackwell.</em></sub>
</div>

---

<h2 align="center">✦ Ce qui rend JARVIS unique</h2>

<div align="center">

<table align="center">
<tr><td>🔒 <b>IA 100 % locale</b></td><td>LLM, RAG, mémoire, données sur le poste — zéro LLM cloud, zéro abonnement. Voix edge-tts en ligne (repli Kokoro local).</td></tr>
<tr><td>🧠 <b>Un agent, pas un chatbot</b></td><td><em>Hermès</em> observe, mémorise, apprend et <b>agit</b> — sans être re-briefé à chaque session.</td></tr>
<tr><td>🛡️ <b>SOC autonome 24/7</b></td><td>Détecte, bannit et redémarre <b>seul</b> · alertes vocales · contexte sécurité en direct.</td></tr>
<tr><td>🎙️ <b>Voix qualité broadcast</b></td><td>Chaîne DSP pro (débruitage IA · compresseur · FX) + voix Edge, repli Kokoro neural local.</td></tr>
<tr><td>⚡ <b>RTX 5080 maîtrisée</b></td><td>Modèle 100 % en VRAM, garde-fou anti-débordement, CUDA partout (Whisper · DeepFilterNet).</td></tr>
<tr><td>♿ <b>Pensé accessible</b></td><td>Haute lisibilité, commandes vocales déterministes (&lt; 100 ms), briefing matinal.</td></tr>
</table>

</div>

<div align="center">

**Visite guidée** &nbsp;·&nbsp; [🕹️ Cockpit](#sec-1) &nbsp;·&nbsp; [🧠 Réglages](#sec-2) &nbsp;·&nbsp; [📊 Monitoring](#sec-3) &nbsp;·&nbsp; [🎛️ Studio DSP](#sec-4) &nbsp;·&nbsp; [🎙️ Voice Lab](#sec-5) &nbsp;·&nbsp; [🌐 Accès Web](#sec-6) &nbsp;·&nbsp; [🛡️ SOC](#sec-7) &nbsp;·&nbsp; [✦ Hermès](#hermes)

</div>

---

<h2 align="center">🖼️ L'interface en action</h2>

<a id="sec-1"></a>

<h3 align="center">1 · Le cockpit</h3>

<div align="center">
  <img src="Images/interface.webp" alt="Cockpit JARVIS — interface neurale, modes de routage, télémétrie live" width="900"/>
</div>

Le poste de pilotage complet. À gauche, **l'interface neurale** (loopback-only · bind `127.0.0.1`) et la barre de commande avec ses **modes de routage** — `SOC · GÉN · CODE · THINK` + entrées `MIC`, `IMG` (vision), `WEB`, `AIDE` — qui orientent chaque requête vers le bon comportement, **un seul modèle `qwen3.5:9b`, zéro swap**. À droite, la **télémétrie temps réel** : cœur d'intégrité, coordonnées, **GPU** (VRAM, température, watts), système et modèle neural. Onze modules accessibles d'un clic depuis la barre du haut.

<a id="sec-2"></a>

<h3 align="center">2 · Réglages LLM & profils GPU</h3>

*Le centre de contrôle fin de l'inférence locale — chaque carte pilote un aspect de la RTX 5080 et du modèle.*

<table>
<tr>
<td width="50%" align="center"><img src="Images/set-gpu-health.webp" width="410" alt="GPU Health"/><br/><sub><b>GPU Health</b> — VRAM / 16 Go, charge, température et puissance de la RTX 5080, en direct.</sub></td>
<td width="50%" align="center"><img src="Images/set-impact.webp" width="410" alt="Impact VRAM"/><br/><sub><b>Impact VRAM</b> — coût mémoire estimé <em>avant</em> lancement (~9 Go : modèle ~5,5 Go + cache KV), garde la « zone sûre ».</sub></td>
</tr>
<tr>
<td width="50%" align="center"><img src="Images/set-profils.webp" width="410" alt="Profils RTX 5080"/><br/><sub><b>Profils RTX 5080</b> — 6 préréglages en un clic : Rapide · Équilibré · Code · Créatif · Précis · MAX.</sub></td>
<td width="50%" align="center"><img src="Images/set-params.webp" width="410" alt="Paramètres LLM"/><br/><sub><b>Paramètres LLM</b> — température, top-p/k, contexte, repeat penalty + 3 modes d'optimisation latence.</sub></td>
</tr>
</table>

> Le **prompt système gouverné** (anti-hallucination, méthodologie SOC, profils sauvegardés) vit dans le même onglet — volontairement non exposé ici (il contient des références internes).

<a id="sec-3"></a>

<h3 align="center">3 · Monitoring GPU · CPU · VRAM</h3>

<div align="center">
  <img src="Images/monitor.webp" alt="Moniteur RTX 5080 — GPU, VRAM, température, CPU, RAM temps réel" width="900"/>
</div>

Surveillance **temps réel** de toute la machine : six jauges (GPU, VRAM / 16 Go, température, puissance, CPU, RAM) puis le détail — **GPU Core** (horloges, encodeur/décodeur), **thermique & puissance**, **mémoire VRAM** (utilisée / libre), processeur (32 cœurs, fréquence, uptime), réseau et disque I/O.

<div align="center">
  <img src="Images/monitor-llm-vram.webp" alt="Empreinte LLM en VRAM — qwen3.5:9b + embedding RAG" width="900"/>
  <br/><sub><em><b>Empreinte LLM en VRAM</b> — le modèle <code>qwen3.5:9b</code> (~5,5 Go) et l'embedding RAG <code>qwen3-embedding:4b</code> (~4,1 Go) cohabitent dans les 16 Go, ~40 % libre. Débit live (tok/s), <code>num_ctx</code> et <b>SWAP RAM = 0</b> : tout tient sur la carte, pleine vitesse.</em></sub>
</div>

C'est le garde-fou du LLM 100 % local : tant que le modèle **+ son cache KV** tiennent dans les 16 Go, l'inférence reste **pleine vitesse GPU** ; s'ils débordent, Ollama « spille » en RAM et la vitesse s'effondre — d'où la surveillance de l'empreinte.

<a id="sec-4"></a>

<h3 align="center">4 · Studio audio DSP — le rack broadcast</h3>

Une **chaîne broadcast complète** appliquée à la voix de synthèse, accélérée **CUDA** :
`TTS → DeepFilterNet → Compresseur → Stereo → Analyseur → FX → EQ → Output`. **Huit étages**, chacun sa fonction — tout en Web Audio, temps réel, en local.

<table>
<tr>
<td width="50%" align="center"><img src="Images/dsp-deepfilter.webp" width="410" alt="DeepFilterNet"/><br/><sub><b>① DeepFilterNet</b> — débruitage IA (DeepFilterNet3) : supprime bruit de fond et artefacts TTS.</sub></td>
<td width="50%" align="center"><img src="Images/dsp-compressor.webp" width="410" alt="Compresseur dynamique"/><br/><sub><b>② Compresseur</b> — dynamique VCA (seuil · ratio · attaque · relâche) : voix homogène, sans pics.</sub></td>
</tr>
<tr>
<td width="50%" align="center"><img src="Images/dsp-stereo.webp" width="410" alt="Stereo Widener"/><br/><sub><b>③ Stereo Widener</b> — effet Haas : élargit l'image stéréo, compatibilité mono préservée.</sub></td>
<td width="50%" align="center"><img src="Images/dsp-fx.webp" width="410" alt="FX Rack"/><br/><sub><b>④ FX Rack</b> — reverb · echo · delay · chorus · flanger par convolution : le caractère sonore.</sub></td>
</tr>
<tr>
<td width="50%" align="center"><img src="Images/dsp-analyser.webp" width="410" alt="Analyseur spectral"/><br/><sub><b>⑤ Analyseur spectral</b> — FFT temps réel, plusieurs modes d'affichage + goniomètre de phase.</sub></td>
<td width="50%" align="center"><img src="Images/dsp-eq.webp" width="410" alt="EQ paramétrique"/><br/><sub><b>⑥ EQ paramétrique</b> — 4 bandes (LOW/MID/HIGH/AIR) couplées à la voix, avec presets.</sub></td>
</tr>
<tr>
<td width="50%" align="center"><img src="Images/dsp-voice-engine.webp" width="410" alt="Moteur vocal"/><br/><sub><b>⑦ Moteur vocal</b> — bascule Edge (cloud) ↔ Kokoro (neural local), voix Antoine CA, test à la volée.</sub></td>
<td width="50%" align="center"><img src="Images/dsp-voice-print.webp" width="410" alt="Voice Print"/><br/><sub><b>⑧ Voice Print</b> — analyse vocale (librosa/scipy) : forme d'onde, pitch F0, spectre Mel.</sub></td>
</tr>
</table>

<h4 align="center">Schéma logique du circuit — état des étages & CUDA</h4>

*Le signal vocal traverse une chaîne de circuits : un étage **CUDA (GPU)** pour le débruitage IA, le reste en **Web Audio** temps réel dans le navigateur.*

```mermaid
flowchart LR
    TTS["🎙️ TTS<br/>Edge · Kokoro"] --> DFN
    subgraph CUDA["⚡ CUDA — GPU RTX 5080"]
        DFN["DeepFilterNet3<br/>débruitage IA"]
    end
    DFN --> CMP["Compresseur<br/>VCA"] --> STE["Stereo<br/>Widener"] --> EQ["EQ<br/>4 bandes"] --> FX["FX Rack<br/>convolution"] --> AN["Analyseur<br/>FFT + phase"] --> OUT["🎚️ Output L+R<br/>gain · VU"]
```

<div align="center">

<table align="center">
<tr><th>Étage</th><th>Rôle logique</th><th>Circuit</th></tr>
<tr><td><b>TTS</b></td><td>synthèse vocale — Edge Antoine / Kokoro neural local</td><td>source</td></tr>
<tr><td><b>DeepFilterNet3</b></td><td>débruitage IA — retire bruit de fond + artefacts TTS</td><td><b>⚡ CUDA (GPU)</b></td></tr>
<tr><td><b>Compresseur</b></td><td>homogénéise le volume (seuil · ratio · attaque · relâche, VCA)</td><td>Web Audio</td></tr>
<tr><td><b>Stereo Widener</b></td><td>élargit l'image stéréo (effet Haas), compatibilité mono</td><td>Web Audio</td></tr>
<tr><td><b>EQ</b></td><td>modelage du timbre — bandes LOW · MID · HIGH · AIR</td><td>Web Audio</td></tr>
<tr><td><b>FX Rack</b></td><td>reverb · echo · delay · chorus (convolution)</td><td>Web Audio</td></tr>
<tr><td><b>Analyseur</b></td><td>FFT temps réel + goniomètre de phase</td><td>Web Audio</td></tr>
<tr><td><b>Output L+R</b></td><td>bus master : gain de sortie + VU-mètres</td><td>Web Audio</td></tr>
</table>

</div>

> Côté **entrée**, la reconnaissance vocale (STT `faster-whisper large-v3-turbo`) est elle aussi **accélérée CUDA** — le GPU couvre toute la chaîne voix.

<a id="sec-5"></a>

<h3 align="center">5 · Voice Lab</h3>

<div align="center">
  <img src="Images/voice-lab.webp" alt="Voice Lab — moteurs TTS, paramètres vocaux, bibliothèque, comparateur A/B" width="900"/>
</div>

L'atelier de la voix de l'assistant. **Source** commutable — **Edge** (Antoine fr-CA) ↔ **Kokoro** neural CUDA, 100 % local hors-ligne — puis **paramètres vocaux** fins (vitesse, hauteur, volume + égalisation LOW/MID/HIGH/AIR synchronisée au DSP), une **bibliothèque** de voix (JARVIS Standard, Grave, Aiguë, Radio FM, Kokoro Neural) et un **comparateur A/B** pour trancher à l'oreille. C'est ce qui donne à JARVIS une voix naturelle et homogène, en ligne comme hors-ligne.

<a id="sec-6"></a>

<h3 align="center">6 · Accès Web gouverné</h3>

<div align="center">
  <img src="Images/acces-web.webp" alt="Accès Web gouverné — allowlist explicite, lecture seule, journalisé" width="900"/>
</div>

L'agent peut consulter le web — mais **sous contrôle strict**. JARVIS ne visite QUE les domaines d'une **allowlist explicite** : des **sites système verrouillés** (météo, veille IA, recherche — non supprimables) plus ceux que *tu* autorises nommément. Tout est en **lecture seule**, **chaque accès est journalisé**, et tout le reste est **refusé**. Même principe de moindre privilège que pour le SOC : la curiosité de l'agent reste gouvernée.

<a id="sec-7"></a>

<h3 align="center">7 · SOC — réponse automatique</h3>

<div align="center">
  <img src="Images/soc.webp" alt="SOC — activité 30 jours et compteurs de défense temps réel" width="920"/>
</div>

Le **centre de défense** de JARVIS. Courbe d'**activité sur 30 jours** (pics offensifs) et **compteurs en direct** — actions, **bans IP**, restarts, succès / échecs, détections **IDS**. JARVIS surveille nginx / CrowdSec / fail2ban / Suricata en continu et **agit seul** (ban, restart) selon des seuils : l'agent ne se contente pas d'alerter, il **répond**.

> 🔒 Volontairement **non publiés** : le journal des IP d'attaquants, le terminal d'actions SOC, les leçons apprises. La vitrine *décrit* le SOC et montre son activité **agrégée** — **aucune donnée actionnable, aucune IP**.

---

<h2 align="center">⌨️ Terminal SSH intégré (mode Code)</h2>

<div align="center">
  <img src="Images/terminal.webp" alt="Terminal SSH JARVIS — PTY xterm-256color, raccourcis, HUD ressources, chat inline" width="920"/>
</div>

Un **vrai terminal SSH interactif** (PTY `xterm-256color`) intégré à JARVIS — pour piloter le serveur de dev **sans quitter l'interface**. À gauche, des **raccourcis en un clic** (SYS : `ls`, `df`, `uptime`, `ports`, `ps`, `top`… · DEV : `git`, `python3`, `find`, `syslog`…). En bas, un **HUD ressources en direct** (load · RAM · disque · réseau · uptime) et une barre **« Demandez à JARVIS depuis le terminal »** : l'agent lit la sortie et propose la commande suivante. Sortie **couleur** complète, redimensionnement à chaud.

> 🔒 **Gouverné** : le PTY est **loopback-only** — bind `127.0.0.1` + contrôle d'origine WebSocket + anti-DNS-rebinding, jamais exposé hors la machine. L'IP réelle est masquée sur cette capture (`192.168.x.x`).

---

<a id="hermes"></a>

<h2 align="center">◈ Hermès — l'agent persistant</h2>

> **Hermès transforme un assistant en agent.**
> Là où un assistant répond, un agent **observe, mémorise, apprend et agit** — sans être re-briefé à chaque session.

<div align="center">
  <img src="Images/hermes.webp" alt="Hermès — cœur de l'agent, état moteur et pipeline temps réel" width="920"/>
</div>

Le tableau de bord vivant de l'agent. Au centre, le **cœur** qui « respire » tant que JARVIS tourne — il **s'illumine** quand il parle (*JE PARLE*), vire à l'**or/ambre** quand la menace monte. Autour, le **diagnostic** (RAG, mémoire, connaissance) et l'**état moteur** (mode, modèle `qwen3.5:9b`, niveau de menace + sa cause). En bas, le **pipeline temps réel** : `ENTRÉE → BYPASS (< 100 ms, zéro LLM) → MÉMOIRE (RAG auto-borné à 4 000 chunks) → SOC LIVE → WEB → PVE → LLM LOCAL → OUTILS → RÉPONSE` — **chaque brique affiche sa métrique live**. L'agentification rendue visible.

<h3 align="center">Schéma logique de la pile — le rôle de chaque tuile</h3>

*Le chemin d'une requête à travers les circuits de l'agent — chaque tuile a un rôle précis et affiche sa métrique en direct.*

```mermaid
flowchart LR
    IN["ENTRÉE"] --> BY["BYPASS<br/>&lt; 100 ms"] --> MEM["MÉMOIRE<br/>RAG"] --> SOC["SOC<br/>LIVE"] --> WEB["WEB"] --> PVE["PVE"] --> LLM["LLM LOCAL<br/>qwen3.5:9b"] --> TL["OUTILS"] --> OUT["RÉPONSE<br/>texte + voix"]
```

<div align="center">

<table align="center">
<tr><th>Tuile du flux</th><th>Rôle logique</th></tr>
<tr><td><b>ENTRÉE</b></td><td>voix (STT Whisper) · texte · image (vision multimodale)</td></tr>
<tr><td><b>BYPASS</b></td><td>commandes directes <b>déterministes</b>, &lt; 100 ms, <b>zéro LLM</b></td></tr>
<tr><td><b>MÉMOIRE</b></td><td>faits + leçons <b>RAG</b>, auto-borné à 4 000 chunks</td></tr>
<tr><td><b>SOC LIVE</b></td><td>injecte le <b>contexte sécurité</b> temps réel</td></tr>
<tr><td><b>WEB</b></td><td>recherche <b>gouvernée</b> (allowlist, lecture seule)</td></tr>
<tr><td><b>PVE</b></td><td>état <b>Proxmox</b> temps réel</td></tr>
<tr><td><b>LLM LOCAL</b></td><td>raisonnement <code>qwen3.5:9b</code> — <b>100 % local</b></td></tr>
<tr><td><b>OUTILS</b></td><td>fichiers / SSH — <b>appelés par le LLM</b></td></tr>
<tr><td><b>RÉPONSE</b></td><td>texte + voix (cache TTS)</td></tr>
</table>

</div>

Autour du flux, les **briques transversales** (enrichissent · protègent · agissent), chacune une tuile d'état :

<div align="center">

<table align="center">
<tr><th>Brique transversale</th><th>Rôle logique</th></tr>
<tr><td><b>VISION</b></td><td>analyse d'images (<code>qwen3.5:9b</code> multimodal natif)</td></tr>
<tr><td><b>MCP</b></td><td>pont gouverné vers Claude Desktop (outils exposés)</td></tr>
<tr><td><b>APPRENTISSAGE</b></td><td>mémorise les leçons (« souviens-toi… »)</td></tr>
<tr><td><b>RÉFLEXION</b></td><td>apprend de tes corrections (proposées → validées)</td></tr>
<tr><td><b>DR CERVEAU</b></td><td>sauvegarde / restauration de la mémoire</td></tr>
<tr><td><b>BRIEFING</b></td><td>résumé proactif au réveil</td></tr>
<tr><td><b>ALARMES</b></td><td>rappels à l'heure</td></tr>
<tr><td><b>PÉDAGOGIE</b></td><td>explique vs analyse (mode tuteur)</td></tr>
<tr><td><b>INFOGÉRANCE</b></td><td>mise à jour des VMs, fail-closed</td></tr>
</table>

</div>

<h3 align="center">Les capacités de l'agent</h3>

<div align="center">
  <img src="Images/hermes-briques.webp" alt="Briques transversales de l'agent" width="920"/>
  <br/><sub><em>Les <b>briques transversales</b> qui enrichissent, protègent et prolongent l'agent — <b>Vision</b> (analyse d'images), <b>MCP</b> (pont gouverné vers Claude Desktop), <b>Apprentissage</b>, <b>Réflexion</b>, <b>DR Cerveau</b> (sauvegarde/restauration), <b>Briefing</b> matinal proactif, <b>Alarmes</b>, <b>Pédagogie</b> (explique vs analyse), <b>Infogérance</b> (MAJ des VMs, fail-closed). Chacune affiche sa métrique live.</em></sub>
</div>

<h3 align="center">Le tableau de bord vivant</h3>

<div align="center">
  <img src="Images/hermes-sante.webp" alt="Six panneaux de santé de l'agent" width="920"/>
  <br/><sub><em>Six panneaux d'auto-diagnostic d'un coup d'œil — <b>Cerveau/Mémoire</b> (leçons apprises, rythme), <b>Sauvegarde</b> (instantané + auto quotidien 21 h), <b>Santé mémoire</b> (verdict GO/NO-GO, intégrité : 0 orphelin, 0 lien cassé), <b>SOC Auto-engine</b>, <b>Historique</b> persisté, <b>Réflexion</b> (corrections proposées vs apprises, taux d'apprentissage).</em></sub>
</div>

<table>
<tr>
<td width="50%" align="center"><img src="Images/hermes-growth.webp" width="430" alt="Croissance du cerveau"/><br/><sub><b>Croissance du cerveau</b> — cumul des leçons + rythme d'apprentissage : la mémoire s'accumule, persistée et réinjectée, jamais repartie de zéro.</sub></td>
<td width="50%" align="center"><img src="Images/hermes-nodrift.webp" width="430" alt="Non-dérive des leçons"/><br/><sub><b>Non-dérive</b> — chaque leçon porte un statut (active · promouvable · doublon · périmée) ; corpus sain → bandeau <b>« AUCUNE DÉRIVE »</b>.</sub></td>
</tr>
</table>

<h3 align="center">Le maintien en vie autonome</h3>

> **Le pari : un agent qui ne se contente pas d'apprendre — il se maintient lui-même en vie.**
> Hermès reste *sain* indéfiniment **sans intervention** : il se diagnostique, se répare, se borne, et **alerte seul** si sa propre mécanique d'entretien s'arrête.

Un **moteur d'entretien autonome** enchaîne des étapes **idempotentes et réversibles** — chaque échec force une sortie en erreur (*fail-closed cumulatif*) : un entretien partiel ne se fait **jamais** passer pour un succès.

```mermaid
flowchart TB
    subgraph CYCLE["♻️ Boucle d'entretien autonome"]
        direction LR
        A["1 · Intégrité"] --> B["2 · Santé<br/>GO / NO-GO"]
        B --> C["3 · Consolidation<br/>des leçons"]
        C --> D["4 · Ré-indexation<br/>auto-bornée"]
        D --> E["5 · Ressources<br/>+ purge RAG"]
        E --> F["6 · Anti-dérive<br/>fail-closed"]
    end
    F --> V{"Toutes les<br/>étapes OK ?"}
    V -->|oui| OK["✅ Mémoire saine<br/>état publié au cockpit"]
    V -->|non| ERR["🛑 Sortie en erreur<br/>entretien invalidé"]
    OK --> COCK[("◈ Cockpit Hermès<br/>santé · leçons · croissance")]
    GARD["🛡️ Gardien de connaissance<br/>GO / DÉRIVE"] -.-> ALERT["🔔 ALERTE"]
    SENT["🛰️ Sentinelle d'autonomie<br/>le moteur tourne-t-il ?"] -.->|inactif| ALERT
    URG["⛑ Bouton d'urgence<br/>sauvegarde AVANT écriture"] -.->|déclenche le moteur| A
```

- 🧠 **Mémoire qui ne dérive pas** — se consolide, se borne, se purge seule.
- ⛑ **Auto-réparation** — régénère les états de santé et ré-indexe la connaissance sans moi.
- 🚨 **Aucune panne silencieuse** — si l'entretien s'arrête, une sentinelle alerte.
- 🔒 **Fail-closed de bout en bout** — au moindre doute, refuser ; sauvegarde avant toute écriture.

> Détail technique complet — moteur d'entretien, états publiés, garde-fous outillés, les 5 briques, comparatif Avant / Après — dans **[01 — Hermès](DOCUMENTATION/01-HERMES.md)**.

---

<h2 align="center">📚 Documentation</h2>

<div align="center">

<table align="center">
<tr><th>#</th><th>Document</th><th>Description</th></tr>
<tr><td>01</td><td><a href="DOCUMENTATION/01-HERMES.md">Hermès</a></td><td>Mémoire · bypass · RAG · DR</td></tr>
<tr><td>02</td><td><a href="DOCUMENTATION/02-SOC-INTEGRATION.md">Intégration&nbsp;SOC</a></td><td>Auto-engine · bans · alertes</td></tr>
<tr><td>03</td><td><a href="DOCUMENTATION/03-ARCHITECTURE.md">Architecture&nbsp;globale</a></td><td>Flask · Blueprints · modules</td></tr>
<tr><td>04</td><td><a href="DOCUMENTATION/04-AUDIO-DSP.md">Audio&nbsp;DSP</a></td><td>Broadcast · TTS · STT · DSP</td></tr>
<tr><td>06</td><td><a href="DOCUMENTATION/06-MCP-SERVER.md">MCP&nbsp;Server</a></td><td>Outils exposés · conception</td></tr>
</table>

</div>

---

<h2 align="center">🧩 Stack technique</h2>

<div align="center">

<table align="center">
<tr><th>Couche</th><th>Technologie</th></tr>
<tr><td><b>Backend</b></td><td>Python 3.11 · Flask · Blueprints autoportants · DI pur</td></tr>
<tr><td><b>LLM local</b></td><td>Ollama · qwen3.5:9b (SOC + général + code + think + <b>vision</b> multimodal · un seul modèle, zéro swap)</td></tr>
<tr><td><b>RAG</b></td><td>qwen3-embedding:4b (dim 2560) · BM25 hybride · auto-borné · TTL 5 min</td></tr>
<tr><td><b>TTS</b></td><td>edge-tts fr-CA Antoine → repli Kokoro CUDA neural (hors-ligne, local)</td></tr>
<tr><td><b>STT</b></td><td>faster-whisper large-v3-turbo CUDA · vocabulaire SOC</td></tr>
<tr><td><b>Frontend</b></td><td>Vanilla JS · Web Audio API · xterm.js · Monaco Editor</td></tr>
<tr><td><b>Agent Hermès</b></td><td>synoptique · bypass regex · scheduler daemon · indépendant du LLM</td></tr>
<tr><td><b>Qualité</b></td><td>suite pytest · gate de couverture pré-push · ruff 0 · eslint 0 · hooks pré-commit/pré-push</td></tr>
</table>

</div>

---

<h2 align="center">🛡️ Sécurité</h2>

<div align="center">

<table align="center">
<tr><th>Principe</th><th>Implémentation</th></tr>
<tr><td><b>100 % local</b></td><td>JARVIS filtre et agrège localement — rien ne part vers un LLM cloud</td></tr>
<tr><td><b>RFC1918 immuable</b></td><td>Les plages IP privées ne peuvent jamais être bannies</td></tr>
<tr><td><b>SSH lecture seule</b></td><td>Patterns dangereux bloqués · whitelist explicite pour l'écriture</td></tr>
<tr><td><b>SOC side-channel</b></td><td>Le contexte sécurité n'entre jamais dans l'historique chat</td></tr>
<tr><td><b>Audit forensique</b></td><td>Toute opération SSH d'écriture tracée dans un journal JSONL</td></tr>
</table>

</div>

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

<sub>🔒 Projet proposé par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · développé en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🔒</sub>

</div>
