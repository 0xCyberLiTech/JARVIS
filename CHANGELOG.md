# Changelog

Toutes les évolutions notables de la vitrine **JARVIS** sont consignées dans ce fichier.

Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet suit le [versionnage sémantique](https://semver.org/lang/fr/).

## [Non publié] — 2026-08-11

Le contexte injecté ne peut plus se faire passer pour une commande — et la vitrine est
réalignée sur le code réel.

> *Aucune version n'est revendiquée ici : cette section décrit l'état livré au 2026-08-11 et
> attend son étiquette. Les sections datées ci-dessous ne sont pas réécrites — un journal
> s'ajoute, il ne se refait pas.*

### Sécurité
- **Un contexte injecté n'atteint plus les détecteurs déterministes.** Devant le modèle, JARVIS
  place des détecteurs qui exécutent des commandes directes — certains **écrivent**. Leur surface
  d'entrée doit être la parole de l'utilisateur, et rien d'autre. Un outil d'analyse collait le
  contexte de sécurité **devant** la question, dans le même champ : le bloc de données traversait
  donc ces détecteurs, et l'un d'eux a mordu sur une tournure venue **des données** — JARVIS a
  répondu à une commande que personne n'avait tapée, pendant que la question, tronquée, n'atteignait
  jamais le modèle. L'injection est désormais **demandée au serveur** ; ce qui n'a pas de chemin
  serveur passe par un **canal dédié** qui n'atteint que le *prompt système*.
- **Garde-fou de classe, pas de rustine.** Un contrôle statique (analyse du code, pas une liste de
  formes interdites : il **suit la valeur**) refuse, chez les clients internes, tout envoi où un
  texte de contexte dérive jusqu'au message — et refuse qu'un envoi ne **déclare** pas sa pureté.
  Il est câblé à la barrière de publication. **Sa portée est écrite noir sur blanc dans la
  documentation, limites comprises** : la garde à l'exécution est *déclarative*, et un client
  externe n'est pas couvert.

### Corrigé — documentation publique réalignée sur le code
- **Audio** : le débruitage IA était annoncé « désactivé par défaut » — il est **actif** par défaut ;
  une « règle absolue » de calibration des effets n'en était pas une (repli neutre pour les effets
  non calibrés) ; le schéma décrivait une topologie d'effets *send/return* qui n'existe plus, et
  omettait l'étage de compensation de gain. La chaîne **serveur**, jusqu'ici absente, est décrite —
  avec ce qu'elle ne contient pas.
- **Agent** : la brique de mémoire nommait des fichiers qui ne portaient pas ce qu'on leur prêtait ;
  le pont MCP était présenté comme destiné à un client qui n'est pas celui qui est configuré ; le
  mode pédagogique était dit couper la documentation locale, alors qu'il l'injecte.
- **Latences non mesurées** : les durées avancées pour les commandes déterministes étaient des
  **valeurs jamais instrumentées**, et fausses pour les commandes qui sortent de la machine. Ce qui
  est vrai de toutes est conservé : **zéro token consommé, zéro hallucination possible**.
- **Outils MCP** : la description de l'état d'infrastructure annonçait des accès SSH par machine —
  l'outil agrège en réalité deux endpoints de faits, et ne passe jamais par le modèle.

### Modifié
- **Zéro constante recopiée** : seuils, ratios, gains et bornes de rotation des journaux ne sont
  plus dupliqués dans ces pages. Ils avaient **déjà dérivé** — le code porte encore, en commentaire,
  les anciennes valeurs que la vitrine publiait comme actuelles. Une page publique cite désormais
  *où* vit la valeur, jamais la valeur elle-même.

## [1.1.0] — 2026-06-24

Accessibilité — l'interface pensée pour un usage en **basse vision**.

### Ajouté
- **Navigation clavier complète + ARIA** — barre d'onglets entièrement pilotable au clavier (flèches, Entrée/Espace, Début/Fin, focus roving) et touche **Échap** pour revenir à l'écran principal, fermer une fenêtre ou quitter un champ. Onglets et panneaux exposés aux technologies d'assistance (`role=tablist`/`tab`/`tabpanel`).
- **Support lecteur d'écran** — libellés accessibles (`aria-label`) en français sur les contrôles, et annonces vocales discrètes (`aria-live`) sur les zones de résultat (jamais sur le fil de conversation).
- **Aide intégrée** — un bouton **Aide** affiche la liste des commandes, générée dynamiquement, et JARVIS peut la **lire à voix haute**.

### Modifié
- **Contraste renforcé** — textes pâles remplacés par une palette lisible centralisée, pour rester confortables sur fond sombre.
- **Lisibilité des polices** — élimination des textes trop petits ; toutes les tailles dérivent désormais d'un jeu de tokens unique, garantissant une lecture confortable.

### Sécurité
- **Vérificateurs d'accessibilité intégrés à la CI** — des contrôles automatisés (fail-closed) vérifient à chaque évolution que la navigation clavier/ARIA, le contraste et la lisibilité ne régressent jamais.

[1.1.0]: https://github.com/0xCyberLiTech/JARVIS/releases/tag/v1.1.0

## [1.0.0] — 2026-06-15

Première version publique de la vitrine.

### Ajouté
- **Galerie de l'interface** — tour visuel des modules : écran d'accueil, réglages LLM & profils GPU, poste de pilotage, studio audio DSP, Voice Lab, accès web gouverné, monitoring GPU/VRAM, SOC.
- **Hermès — l'agent persistant** : cœur de l'agent, architecture (entrée → Hermès → LLM → réponse), croissance du cerveau (mémoire qui s'accumule).
- **Console de maintenance & reprise après sinistre** (menu terminal : statut, modèles, DSP, sauvegarde & restauration, API).
- **Documentation** — 6 pages : Hermès, intégration SOC, architecture globale, audio DSP, installation, MCP server.

### Caractéristiques présentées
- LLM 100 % local via Ollama : `qwen3.5:9b` unifié (SOC · général · code · think · **vision** multimodal natif) · `qwen3-embedding:4b` (RAG).
- Voix Edge Antoine → repli Kokoro neural local · STT faster-whisper `large-v3-turbo`.
- RAG hybride (~1150 chunks) · MCP outils (COMPTÉ LIVE — `_TOOLS_DEFS`) · auto-engine SOC.
- Accélération CUDA (RTX 5080) avec garde-fou anti-débordement VRAM.

### Sécurité
- Doctrine vitrine : aucune donnée actionnable publiée (IP, clés, configurations). La vitrine **décrit**, elle ne branche rien de live.

[1.0.0]: https://github.com/0xCyberLiTech/JARVIS/releases/tag/v1.0.0
