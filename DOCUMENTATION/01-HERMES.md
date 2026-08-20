<div align="center">

  <br></br>

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=50&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS_" alt="Titre dynamique JARVIS" />
  </a>

  <br></br>

  <h2>Assistant IA local · voix · interface holographique · automatisation SOC 24/7</h2>

  <p align="center">
    <a href="https://0xcyberlitech.github.io/">
      <img src="https://img.shields.io/badge/Portfolio-0xCyberLiTech-181717?logo=github&style=flat-square" alt="Portfolio" />
    </a>
    <a href="https://github.com/0xCyberLiTech">
      <img src="https://img.shields.io/badge/Profil-GitHub-181717?logo=github&style=flat-square" alt="Profil GitHub" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/tags">
      <img src="https://img.shields.io/github/v/tag/0xCyberLiTech/JARVIS?sort=semver&label=version&style=flat-square&color=blue" alt="Dernière version" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/blob/main/CHANGELOG.md">
      <img src="https://img.shields.io/badge/%F0%9F%93%84%20Changelog-JARVIS-blue?style=flat-square" alt="Changelog" />
    </a>
    <a href="https://github.com/0xCyberLiTech?tab=repositories">
      <img src="https://img.shields.io/badge/D%C3%A9p%C3%B4ts-publics-blue?style=flat-square" alt="Dépôts publics" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/graphs/contributors">
      <img src="https://img.shields.io/badge/%F0%9F%91%A5%20Contributeurs-cliquez%20ici-007ec6?style=flat-square" alt="Contributeurs" />
    </a>
  </p>

</div>

<div align="center">
  <img src="https://img.icons8.com/fluency/96/000000/cyber-security.png" alt="CyberSec" width="80"/>
</div>

<div align="center">
  <p>
    <strong>IA 100% locale</strong> <img src="https://img.icons8.com/color/24/000000/lock--v1.png"/> &nbsp;•&nbsp; <strong>Voix naturelle · STT · TTS</strong> <img src="https://img.icons8.com/color/24/000000/linux.png"/> &nbsp;•&nbsp; <strong>Automatisation SOC</strong> <img src="https://img.icons8.com/color/24/000000/shield-security.png"/>
  </p>
</div>

---

# Hermès — L'agent persistant

> *Dernière mise à jour : 2026-08-16 (Refactoring modulaire et étanchéité)*

## Qu'est-ce qu'Hermès ?

Un **assistant** répond à des questions — et oublie tout dès que la session se ferme.

Un **agent** est fondamentalement différent : il **observe** son environnement en permanence, **mémorise** ce qu'il apprend entre les sessions, **anticipe** les besoins récurrents, et **agit** de façon autonome quand une condition est remplie — sans attendre d'être interrogé.

**Hermès est la couche d'agentification de JARVIS.** C'est lui qui transforme un assistant LLM classique en agent autonome persistant. Il s'intercale entre l'utilisateur et le moteur LLM, et prend en charge tout ce que le LLM ne devrait pas faire : la mémoire long terme, les décisions déterministes, les actions système et le briefing proactif.

<div align="center">
  <img src="../Images/interface.webp" alt="Interface holographique JARVIS — cockpit" width="720" />
  <br/>
  <sub>Interface holographique JARVIS — état du moteur local (LLM, voix, modules, accélération GPU) en un coup d'œil.</sub>
</div>

---

## Schéma 1 — Position d'Hermès dans l'architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                 UTILISATEUR  (voix ou texte)                     ║
╚══════════════════════════╤═══════════════════════════════════════╝
                           │
              ┌────────────▼──────────────┐
              │                           │
              │       H E R M È S         │
              │ (couche agentification)   │
              │                           │
              │  ┌─────────────────────┐  │
              │  │ 1. Bypass ?         │  │  ← commande déterministe ?
              │  │    OUI → action     │  │     exécution directe
              │  │    NON ↓            │  │     zéro LLM consommé
              │  └─────────────────────┘  │
              │  ┌─────────────────────┐  │
              │  │ 2. Facts inject     │  │  ← date/heure + leçons
              │  │    Mémoire RAG      │  │     persistées entre sessions
              │  └─────────────────────┘  │
              │  ┌─────────────────────┐  │
              │  │ 3. RAG conditionnel │  │  ← documentation locale
              │  │    (si pertinent)   │  │     injectée si besoin
              │  └─────────────────────┘  │
              │  ┌─────────────────────┐  │
              │  │ 4. SOC inject       │  │  ← contexte sécurité live
              │  │    (mode SOC seul)  │  │     side-channel, jamais
              │  └─────────────────────┘  │    dans l'historique chat
              └────────────┬──────────────┘
                           │
              ┌────────────▼──────────────┐
              │          L L M            │
              │  qwen3.5:9b (unifié)   │  ← ne voit que ce qu'Hermès
              └────────────┬──────────────┘    lui prépare
                           │
              ┌────────────▼──────────────┐
              │   RÉPONSE ENRICHIE        │
              │   + TTS vocal Antoine     │
              └───────────────────────────┘
```

> **Règle fondamentale** : Hermès décide ce qui arrive au LLM. Le LLM ne voit jamais les données brutes — seulement un contexte filtré, structuré et pertinent.

---

## Schéma 2 — Les briques fondatrices d'Hermès

> Ces briques sont le socle historique. Elles sont complétées par des **briques avancées**
> (mode pédagogique, infogérance orchestrée, DR du cerveau, cache vocal) — détaillées plus
> bas — et par des briques nées de l'usage (web, PVE, vision, MCP, alarmes). **Le compte
> exact des briques n'est PAS figé ici : il VIT dans le schéma d'agentification (interface,
> onglet APPRENTISSAGE → SCHÉMA HERMÈS, nœuds `data-brick`)** — cf. l'inventaire live ci-dessous.
> Doctrine « compté LIVE, jamais figé » ; **audit** `jarvis-frozen-count-guard`, **lancé à la
> demande** — ce n'est **pas un verrou** : aucun `pre-push` ne le déclenche.

```
┌───────────────────────────────────────────────┐
│                  H E R M È S                  │
│                                               │
│  ┌──────────────────┐   ┌──────────────────┐  │
│  │  BRIQUE 1        │   │  BRIQUE 2        │  │
│  │  SYNOPTIQUE      │   │  TUILE MÉMOIRE   │  │
│  │  TEMPS RÉEL      │   │                  │  │
│  │                  │   │  ● Échanges      │  │
│  │  ● LLM actif     │   │  ● Résumés       │  │
│  │  ● RAG chunks    │   │  ● Leçons        │  │
│  │  ● STT/TTS état  │   │  ● Conventions   │  │
│  │  ● Auto-engine   │   │                  │  │
│  │  ● Mémoire état  │   │  Persistant      │  │
│  │  ● Mode actif    │   │  entre sessions  │  │
│  └──────────────────┘   └──────────────────┘  │
│                                               │
│  ┌──────────────────┐   ┌──────────────────┐  │
│  │  BRIQUE 3        │   │  BRIQUE 4        │  │
│  │  BYPASS          │   │  BOUCLE          │  │
│  │  DÉTERMINISTE    │   │  APPRENTISSAGE   │  │
│  │                  │   │                  │  │
│  │  Interception    │   │  "Souviens-toi"  │  │
│  │  avant LLM       │   │  → persisté RAG  │  │
│  │  0 LLM consommé  │   │  → réinjecté     │  │
│  │  0 hallucination │   │    auto futures  │  │
│  └──────────────────┘   └──────────────────┘  │
│                                               │
│  ┌──────────────────┐                         │
│  │  BRIQUE 5        │                         │
│  │  BRIEFING        │                         │
│  │  MATINAL         │                         │
│  │                  │                         │
│  │  "Bonjour JARVIS"│                         │
│  │  → menaces SOC   │                         │
│  │  → état machines │                         │
│  │  → alertes 24h   │                         │
│  └──────────────────┘                         │
│                                               │
│                                               │
└───────────────────────────────────────────────┘
```

---

## Inventaire LIVE des briques

> **Source de vérité = le SCHÉMA HERMÈS** rendu dans l'interface (onglet APPRENTISSAGE),
> pas ce tableau. Il est reproduit ici pour référence, dérivé des nœuds `data-brick` réels ;
> le **compte n'est jamais figé** dans la prose (**audit à la demande** `jarvis-frozen-count-guard`).
>
> ⚠ **FAIT CORRIGÉ le 2026-08-11** (§16 : preuve, daté, jamais en silence — décision de l operateur).
> Cette page présentait `jarvis-frozen-count-guard` comme un « **verrou** », **deux fois**. C'en est
> un **audit**, pas un verrou : il se lance **à la demande**, il n'est câblé à **aucun** `pre-push`,
> et il rend **NO-GO aujourd'hui**. Preuves : le fichier vit hors du produit
> (`DEV/TOOLS/jarvis-frozen-count-guard/`) · `grep jarvis-frozen-count-guard` dans le
> `.pre-commit-config.yaml` de JARVIS → **aucune occurrence** (il n'est référencé que par
> `DEV/TOOLS/audit-all.sh`, un audit manuel) · exécution du jour → **exit 1**.
> *Annoncer un verrou qui ne verrouille rien fait croire la propriété tenue par la machine alors
> qu'elle ne tient que sur la discipline (doctrine §0, Règle Zéro · §6, honnêteté).*
> Les briques marquées ✎ ont une section détaillée plus bas ; les autres, nées de l'usage,
> sont opérationnelles et instrumentées mais pas (encore) déroulées en profondeur.

<!-- doc-path-guard: DEV/TOOLS/audit-all.sh -- chemin de l'ATELIER (dépôt DEV, hors de cette vitrine). Il ne peut PAS résoudre ici, et la Règle Zéro interdit au produit d'aller le vérifier chez l'atelier. Citation VOLONTAIRE, pas une erreur. -->

**Flux d'une requête** : `ENTRÉE` → **Hermès** → `LLM LOCAL` → `OUTILS` → `RÉPONSE`
(`ENTRÉE` et `RÉPONSE` sont les E/S du flux, pas des briques).

**Couche Hermès — enrichit / filtre le contexte avant le LLM :**

| Brique | Rôle | Détaillée |
|--------|------|:---------:|
| BYPASS | commandes directes déterministes · **0 LLM** (budget de latence, cf. Brique 3) | ✎ |
| MÉMOIRE | faits + leçons (RAG) · persistance inter-sessions | ✎ |
| SOC LIVE | contexte sécurité — injection avant LLM (détail : `02-SOC-INTEGRATION.md`) | — |
| WEB | recherche internet à la demande | — |
| PVE | état Proxmox temps réel | — |

**Traitement :** `LLM LOCAL` (raisonnement) → `OUTILS` (fichiers / SSH appelés par le LLM).

**Briques transversales — enrichissent / protègent / agissent :**

| Brique | Rôle | Détaillée |
|--------|------|:---------:|
| VISION | analyse d'images (multimodal) | — |
| MCP | pont MCP local — outils exposés à un client externe compatible MCP | — |
| APPRENTISSAGE | « souviens-toi » → leçons du cerveau | ✎ |
| RÉFLEXION | apprend de tes corrections (cumul) · famille de la boucle d'apprentissage | — |
| DR CERVEAU | sauvegarde / restaure la mémoire | ✎ |
| BRIEFING | résumé proactif au réveil | ✎ |
| ALARMES | rappels à l'heure · 0 LLM | — |
| PÉDAGOGIE | tuteur : explique vs analyse | ✎ |
| INFOGÉRANCE | état du parc + journal des MAJ (lecture seule) · fail-closed | ✎ |

Le **cache vocal** (restitution TTS instantanée) agit sur la brique `RÉPONSE` (détaillé plus bas).

**Sections détaillées sans nœud `data-brick`** (capacités réelles, hors schéma live) : *Brique 1 —
Synoptique* (le tableau de bord d'observabilité lui-même, pas une brique du pipeline), *Brique 9 —
Cache vocal* (agit sur `RÉPONSE`), *Brique 10 — Connaissance vérifiable / anti-dérive* (moteur de
non-dérive), *Brique 11 — Moteur d'entretien + frontière du produit* (ce qui maintient la pile en
vie et lui permet de ressusciter seule).

**Capacités agentiques présentes côté backend / autres tuiles mais ABSENTES du SCHÉMA HERMÈS**
(le schéma sous-représente donc l'agent — à trancher : les promouvoir en nœuds `data-brick` ou les
noter explicitement hors schéma) : **AUTO-ENGINE SOC** (ban/restart proactif — tuile dédiée du même
onglet), **moniteurs proactifs** (alertes vocales GPU chaud / VM-PVE en arrêt), **AIDE** (JARVIS
explique ses propres outils).

---

## Brique 1 — Synoptique temps réel

Le synoptique est le **tableau de bord live d'Hermès** — visible en permanence dans l'interface. Il affiche l'état des couches du moteur au moment présent.

```
┌─────────────────────────────────────────────────────────┐
      ◈  HERMÈS  --  SYNOPTIQUE  MOTEUR                        
├─────────────────┬───────────────────────────────────────┤
│  LLM ACTIF      │  qwen3.5:9b  ●  CHAUD  (en mémoire)  │
│  RAG            │  <n> chunks  ●  PRÊT  TTL: <reste>    │
│  STT            │  large-v3-turbo  ●  EN ÉCOUTE         │
│  TTS            │  edge-tts  Antoine fr-CA  ●  ACTIF    │
│  AUTO-ENGINE    │  ●  ACTIF  —  dernier scan: <âge>     │
│  MÉMOIRE        │  <n> leçons  ●  résumés  ●  SYNC      │
└─────────────────┴───────────────────────────────────────┘
```

> Ce synoptique est désormais un **onglet dédié** de l'interface (`◈ APPRENTISSAGE`) :
> un tableau de bord d'observabilité Hermès où l'on voit, en direct, le moteur
> « vivre » — compteurs (leçons, chunks RAG, dernière sauvegarde, taille du
> cerveau), flux des leçons récentes en haut, et l'enseignement en direct.

L'utilisateur sait **en un coup d'œil** si JARVIS est pleinement opérationnel, si un modèle est en cours de chargement, si le RAG est à jour, ou si l'auto-engine SOC surveille activement.

---

## Brique 2 — Mémoire persistante

C'est la brique qui différencie le plus radicalement un agent d'un chatbot.

### Sans mémoire persistante (chatbot classique)

```
Session 1 :  "Appelle-moi Alex"      → JARVIS apprend
             Session fermée          → TOUT OUBLIÉ

Session 2 :  "Bonjour JARVIS"
             "Tu te souviens de moi ?" → "Je suis désolé, je n'ai pas
                                          de mémoire des sessions précédentes"
```

### Avec Hermès — mémoire persistante RAG

```
Session 1 :  "Souviens-toi : les backups le samedi soir"
                │
                ▼
             Leçon APPENDUE, horodatée, au cerveau appris
             + vecteur créé dans la base RAG

Session 2 (lendemain) :
             "Quand faire les backups ?"
                │
                ▼  RAG retrouve la leçon automatiquement
             "Les backups se font le samedi soir — tu me l'as appris hier."
```

### Structure de la mémoire

```
CERVEAU APPRIS  (fichier Markdown cumulatif, persistant sur disque)
└── leçons        : append horodaté à chaque « souviens-toi » — indexé RAG,
                    sauvegardé/restauré, consolidé (dédup) par l'entretien

FAITS STATIQUES  (fichier JSON, persistant — LECTURE seule au runtime)
└── faits         : contexte stable injecté au prompt système

HISTORIQUE DES ÉCHANGES  (fichier JSON, persistant)
└── messages      : le fil brut de la conversation

RÉSUMÉS DE SESSION  (fichier JSON distinct)
└── condensés     : les longues conversations, compressées

Base vectorielle RAG  (taille LIVE — jamais figée ici)
├── documentation technique locale
├── leçons apprises  (injection automatique)
└── résumés de sessions
```

> ⚠ **FAIT CORRIGÉ le 2026-08-11.** Ce bloc décrivait **un seul** fichier de « faits » portant à la
> fois leçons, tâches et préférences, et un fichier de « mémoire » portant les résumés. **C'était
> faux sur les deux points** : les leçons vont dans le **cerveau appris** (un Markdown cumulatif,
> pas le JSON de faits, qui n'est jamais écrit par la boucle d'apprentissage), et les résumés vivent
> dans un fichier **séparé** de l'historique. Les noms de fichiers ne sont plus recopiés ici : leur
> source est le code, et une page publique qui les épelle vieillit au premier renommage.

---

## Brique 3 — Bypass déterministe

### Le problème sans bypass

Quand on passe toutes les commandes par le LLM, on accepte deux risques :
- **Latence** : le modèle local prend plusieurs secondes pour répondre
- **Hallucination** : le LLM peut inventer une heure, un nom de fichier, un état de service

Pour des commandes simples et prévisibles, ce comportement est inacceptable.

### La solution Hermès — interception avant le LLM

```
Entrée utilisateur
       │
       ▼
┌──────────────────────────────────┐
│   MOTEUR BYPASS  (regex Python)  │
│                                  │
│   Patterns interceptés :         │
│   ● temporel     → datetime()    │
│   ● état VM      → SSH qm list   │
│   ● lecture fich → open() local  │
│   ● recharge RAG → rag.reload()  │
│   ● briefing mat → brief()       │
│   ● ... (+ autres patterns)      │
└──────────┬───────────────────────┘
           │ Match ?
    ┌──────┴──────┐
    │ OUI         │ NON
    ▼             ▼
Action       Continuer vers
directe      LLM (étapes 2-5)
0 token LLM
```

> ⏱️ **Le « < 100 ms » du bypass est un BUDGET DE CONCEPTION, pas un relevé** — et il ne vaut que
> pour les bypass **purement locaux** (heure, alarmes, aide, rechargement d'index). Les bypass qui
> **sortent de la machine** (état des VMs par SSH, sauvegardes, mises à jour) sont bornés par des
> **délais d'attente** de l'ordre de la dizaine de secondes à l'heure, déclarés dans leurs modules :
> les annoncer « en moins de 100 ms » serait faux. Ce qui est vrai de **tous** les bypass, sans
> exception, c'est ce qui compte ici : **zéro token LLM, zéro hallucination possible.**
> *(Fait corrigé le 2026-08-11 : cette page présentait « < 100 ms » comme une propriété de toute la
> brique. Aucune instrumentation de latence de bypass n'existe dans le code — c'était une valeur
> **non mesurée**, publiée comme un fait.)*

### Exemples concrets

| Commande vocale | Sans Hermès | Avec Hermès |
|-----------------|-------------|-------------|
| `"Quelle heure est-il ?"` | LLM invoqué — plusieurs secondes — risque d'hallucination | Python `datetime.now()` direct — instantané — exact |
| `"État des VMs"` | LLM génère une commande SSH — risque d'erreur de syntaxe | `qm list` SSH direct — résultat brut exact |
| `"Recharge le RAG"` | LLM interprète — résultat incertain | `rag_engine.reload()` direct — confirmation immédiate |
| `"Bonjour JARVIS"` | LLM génère un bonjour générique | Briefing matinal complet : SOC + infra + alertes 24h |

---

## Brique 4 — Boucle d'apprentissage

### Comment JARVIS apprend

```
UTILISATEUR :  "Souviens-toi que X"  (texte ou voix)
                    │
                    ▼
            Hermès détecte le pattern "souviens-toi"
                    │
         ┌──────────▼────────────────────┐
         │   PERSISTANCE                 │
         │   └── cerveau appris          │  ← append horodaté sur disque
         │       (Markdown cumulatif)    │
         └──────────┬────────────────────┘
                    │
         ┌──────────▼────────────────────┐
         │   INDEXATION RAG              │
         │   ├── embedding calculé       │  ← qwen3-embedding:4b
         │   └── chunk ajouté à l'index  │
         └──────────┬────────────────────┘
                    │
         ┌──────────▼────────────────────┐
         │   INJECTION AUTOMATIQUE       │
         │   Toute future question       │  ← sans action de
         │   pertinente reçoit cette     │    l'utilisateur
         │   leçon en contexte           │
         └───────────────────────────────┘

  RÉSULTAT :  JARVIS connaît cette règle dans TOUTES
              les sessions suivantes — sans re-briefing
```

### Exemples de leçons apprisibles

- Conventions de travail : `"Souviens-toi : les commits en anglais"`
- Règles métier : `"Souviens-toi : ne jamais redémarrer nginx sans vérifier les configs"`
- Préférences vocales : `"Souviens-toi : réponds toujours en français"`
- Contexte infra : `"Souviens-toi : le disque D est le disque de secours"`

---

## Brique 5 — Briefing matinal

Le briefing matinal est la manifestation la plus visible du comportement **proactif** d'Hermès.

Au lieu d'attendre une question, JARVIS prend l'initiative de livrer un résumé complet de la situation à la première interaction de la journée.

### Déclencheur et pipeline

```
"Bonjour JARVIS"  (ou variantes vocales)
         │
         ▼  Hermès identifie le pattern matinal
         │
         ▼  Assemblage sans LLM (bypass total — données directes)
         │
    ┌────┴────────────────────────────────────┐
    │  ● ThreatScore SOC en cours             │
    │  ● Bans actifs dernières 24h            │
    │  ● Alertes IDS / WAF                    │
    │  ● État des VMs Proxmox                 │
    │  ● Dernière sauvegarde (date + état)    │
    │  ● État LLM + RAG + mémoire JARVIS      │
    └────┬────────────────────────────────────┘
         │
         ▼  Synthèse vocale TTS Antoine fr-CA
         │
    Briefing complet lu à voix haute,
    sans interaction clavier
```

---

# Briques avancées — l'évolution d'Hermès

Aux briques fondatrices se sont ajoutées des briques nées de l'usage
quotidien. Chacune suit la même philosophie : **déterminisme, sûreté,
accessibilité** — Hermès protège le LLM et l'utilisateur.

---

## Brique 6 — Mode pédagogique (JARVIS tuteur)

**Rôle : distinguer *expliquer* de *analyser*, et enseigner.**

En mode SOC, le moteur de raisonnement tend à *analyser* la situation live à
chaque sollicitation — y compris quand l'utilisateur veut simplement
*comprendre* un concept. Hermès tranche cette ambiguïté **avant** le LLM.

```
"Analyse la situation"          "Explique-moi ce qu'est un WAF"
        │                                │
        ▼  détecteur d'intention         ▼  détecteur d'intention
   = ANALYSE                         = EXPLICATION
        │                                │
        ▼                                ▼
   Contexte SOC live injecté        Prompt PÉDAGOGIQUE neutre
   (méthode d'analyse)              (aucune donnée live injectée)
        │                                │
        ▼                                ▼
   Recommandation actionnable       Leçon claire, analogies,
   ancrée sur les données           niveau débutant
```

Un détecteur d'intention unique (source unique, réutilisé partout) reconnaît
les tournures pédagogiques (*explique, décris, apprends-moi, à quoi sert,
différence entre…*). En explication, Hermès **coupe tout ce qui est LIVE** —
contexte sécurité temps réel, accès web, état de l'hyperviseur — et sert un prompt
pédagogique dédié. La **documentation locale (RAG)**, elle, **reste injectée** : c'est
la matière même de l'explication.
JARVIS devient alors le **tuteur** de son utilisateur — utile pour monter en
compétence sur la cybersécurité défensive.

> ⚠ **FAIT CORRIGÉ le 2026-08-11.** Ce paragraphe affirmait que le mode pédagogique n'injectait
> « **ni le contexte sécurité live ni la documentation** ». La seconde moitié est **fausse** : sur ce
> chemin, le RAG documentaire est injecté — et même **inconditionnellement**, là où le chemin normal
> le soumet à une condition de pertinence.

---

## Brique 7 — Infogérance : l'agent OBSERVE, il ne lance pas la mise à jour

**Rôle : donner l'état du parc et le journal des mises à jour — sans jamais les déclencher.**

> ⚠️ **Cette brique a changé de nature.** Elle a été livrée en « orchestration » :
> un bouton unique enchaînait mise à jour → redémarrage → re-base d'intégrité.
> Cette capacité **n'existe plus dans le produit**, et cette page la décrivait
> encore. La route HTTP qui la lançait a été **retirée** : elle appelait un outil
> de l'**atelier de développement**, donc le produit ne survivait pas à une
> restauration nue. **L'atelier agit, le produit observe.**

```
Ce que JARVIS FAIT                      Ce qu'il NE FAIT PLUS
──────────────────────────────────      ─────────────────────────────
● état du parc (une carte par hôte)     ✗ lancer la MAJ complète
● journal des MAJ — LECTURE SEULE       ✗ redémarrer après la MAJ
● « copier la commande » (0 exécution)  ✗ re-baser l'intégrité fichier
● dire ce qu'il ne peut PAS vérifier
```

Ce qui reste — et pourquoi c'est plus sûr :

- **Lecture seule** — le blueprint n'expose plus **aucune** mutation. La garde
  anti-CSRF est pourtant **conservée** : le jour où une route mutante y naîtra,
  elle naîtra **déjà protégée**, plutôt que de dépendre de quelqu'un qui penserait
  à la reposer.
- **Copier ≠ exécuter** — la commande de mise à jour est placée dans le
  presse-papiers, à coller dans une console **hors de JARVIS**. C'est le **seul**
  endroit où elle est écrite : deux textes ne peuvent pas diverger.
- **Journal borné et hors de l'atelier** — seules les dernières lignes sont lues
  (mémoire bornée : un fichier qui grossit ne peut pas faire enfler JARVIS), et le
  journal survit à une restauration.
- **Fail-closed sur la donnée** — une valeur que l'agent ne sait pas vérifier
  (index de paquets périmé, sonde en échec) est **dite**, jamais repeinte en
  « à jour » : un total n'additionne que le connu et **compte à part** l'inconnu.

Pensée pour l'**accessibilité** : gros boutons, confirmation OUI/NON
inconfondable, verdict lu à voix haute, raison écrite **en toutes lettres** —
jamais un simple code couleur.

---

## Brique 8 — Mémoire protégée (DR du cerveau)

**Rôle : ne jamais perdre le savoir appris.**

La boucle d'apprentissage (brique 4) n'a de valeur que si la mémoire survit à
une panne. Hermès protège son propre cerveau par une stratégie de reprise
après sinistre, pilotable **à la voix**.

```
"Sauvegarde le cerveau"  ──►  copie légère quotidienne
                              ├─ rotation glissante
                              ├─ archives mensuelles PERMANENTES
                              └─ "latest" pour restauration 1-geste
                                   │
"Restaure le cerveau"   ──►  retour à la dernière sauvegarde
                              └─ vocal : "Cerveau restauré. <n> leçons."
```

Le fichier des leçons est **cumulatif** : la rotation ne supprime jamais le
savoir, elle ne fait que dater des photos. Le bilan annoncé (nombre de leçons)
est **extrait de la sortie réelle** du script — jamais un chiffre inventé.

---

## Brique 9 — Cache vocal (restitution instantanée)

**Rôle : rendre la voix immédiate sur les phrases répétées.**

Confirmations, menu vocal, réponses figées : ces phrases revenaient en
re-synthèse à chaque fois. Hermès mémorise le rendu audio et le ressert
instantanément.

- **Clé** = empreinte du texte + voix + moteur + réglages DSP → un changement
  de voix ou de DSP invalide l'entrée (jamais d'audio périmé).
- **Best-effort intégral** : toute erreur du cache est avalée → repli sur la
  génération normale, **la voix ne casse jamais**.
- **Borné** (LRU) : le volume disque reste maîtrisé.

> Détail technique : [04 — Audio &amp; DSP](04-AUDIO-DSP.md#cache-tts--restitution-instantanée).

---

## Brique 10 — Connaissance vérifiable (mémoire de référence anti-dérive)

**Rôle : que l'agent parle de lui-même et de l'infrastructure SANS jamais inventer.**

Quand on demande à un agent « explique ton architecture » ou « comment est faite
telle brique ? », il ne doit pas *deviner*. Un LLM local, seul, ne peut pas le
garantir : il produit du **plausible**, pas du **certain**. Hermès ajoute donc une
couche de **connaissance vérifiable** — pour qu'on puisse **s'appuyer** sur ses
réponses, pas seulement les lire.

```
Question « sur soi-même / sur l'infra »
        │
        ▼   Hermès fait REMONTER la fiche de référence concernée
        │   (prioritaire — les autres sources ne la noient pas)
        ▼
   Réponse ANCRÉE sur la source  +  CITATION du fichier
        │
        └─►  info absente ?  →  « ce n'est pas dans ma documentation »
                                 (jamais d'invention)
```

Trois principes :

- **Source de vérité** — la connaissance de l'agent (sur lui-même ET sur chaque
  brique de l'infra) vit dans des **fichiers de référence dédiés**, indexés
  localement. Une seule source par brique, pas de copie éparpillée.
- **Réponse ancrée + citée** — sur une question le concernant, sa propre fiche est
  **prioritaire** dans la recherche ; il **cite** d'où vient l'info, et s'il ne la
  trouve pas, il le **dit** plutôt que de combler le vide.
- **Garde-fou anti-dérive** — un **gardien** vérifie en continu que ces sources
  restent **justes** (présentes, cohérentes, bien rattachées) et **signale** toute
  dérive dans une file d'attente, sans jamais corriger seul.

La correction suit une règle non négociable :

```
DÉTECTION   =  autonome, locale, en continu       (le gardien)
CORRECTION  =  déclenchée par l'humain, par lots   (jugement requis)
```

> **Autonome pour surveiller et signaler — pas pour inventer la vérité.** La
> détection ne dépend de personne ; la correction reste un **acte de jugement**,
> jamais une réécriture silencieuse. C'est ce qui sépare un agent **fiable** d'un
> agent simplement **bavard**.

---

## Brique 11 — Le moteur d'entretien, et où vivent les organes

**Rôle : garder Hermès sain indéfiniment, sans intervention — et survivre à un sinistre.**

### Le moteur d'entretien

JARVIS lance ce moteur **au démarrage et en boucle**. Il enchaîne des étapes
**idempotentes et réversibles** — audit de l'index, décision de purge, signal
qualité, structure de la mémoire, ressources et seuils du corpus, consolidation
des leçons, sources de vérité, chasse aux termes périmés.

**Le nombre et l'ordre des étapes ne sont pas figés ici** : ils sont définis dans
le moteur lui-même, seule source. Ce qui est invariant, c'est la règle de sortie :

```
chaque étape échoue  ──►  cumul fail-closed  ──►  SORTIE EN ERREUR
                                                  (entretien INVALIDÉ)

toutes les étapes OK ──►  état publié au cockpit
```

Un entretien **partiel ne se fait jamais passer pour un succès**. Et le verdict
**dérive du code de sortie** — pas d'une seconde logique de verdict qui pourrait
diverger de la première.

### Où vivent les organes — la frontière du produit

> **Un outil de développement peut dépendre du produit.
> Le produit ne doit JAMAIS dépendre des outils de développement.**

Ces organes sont le **système nerveux** de JARVIS. Ils vivaient dans l'**atelier
de développement**. Le coût, mesuré et non supposé : après restauration du seul
coffre de JARVIS — **le scénario même du sinistre** — toute la pile Hermès
**mourait**, parce que son moteur n'avait jamais été sauvegardé avec le produit.
Pire, une des briques répondait « **aucun outil** » **sans une erreur, sans un
log** : l'agent affirmait sereinement une contre-vérité.

Ils ont donc **déménagé dans le produit**. Ce que cela impose :

| Règle | Ce qu'elle garantit |
|---|---|
| **Une seule copie** — l'atelier n'en garde aucune | Deux copies divergent ; une seule ne peut pas dériver |
| **Une seule déclaration de leurs chemins** | Les modules de production qui les lancent lisent tous la même ; aucun ne peut mentir en silence quand un organe bouge |
| **Fail-closed audible** | Un organe absent est **dit** (log **et** voix) — jamais une étape sautée en silence |
| **Vérifié par la machine** | Un garde-fou refuse tout chemin de production qui pointerait vers l'atelier ; son jumeau exige que tout chemin externe atteint à l'exécution soit couvert par le coffre |

> **Le test qui compte n'est pas « est-ce rangé proprement ? » mais
> « si je restaure le seul coffre après un sinistre, est-ce que ça marche
> encore ? ».** C'est la seule façon de garantir qu'un produit puisse
> **ressusciter seul**.

---

## Bilan — Ce qu'Hermès apporte à JARVIS

```
┌─────────────────────────┬────────────────────────────────────────┐
│  SANS HERMÈS            │  AVEC HERMÈS                           │
│  (chatbot LLM classique)│  (agent persistant)                    │
├─────────────────────────┼────────────────────────────────────────┤
│  Chaque session repart  │  Contexte, leçons et conventions       │
│  de zéro                │  conservés entre toutes les sessions   │
├─────────────────────────┼────────────────────────────────────────┤
│  Toutes les commandes   │  Bypass déterministe : des patterns    │
│  passent par le LLM     │  exécutés directement,                 │
│  (latence + risque      │  sans consommer un seul token LLM      │
│  d'hallucination)       │                                        │
├─────────────────────────┼────────────────────────────────────────┤
│  L'assistant attend     │  L'agent surveille en permanence,      │
│  d'être interrogé       │  alerte vocalement si seuil dépassé,   │
│                         │  agit (ban IP, restart) si configuré   │
├─────────────────────────┼────────────────────────────────────────┤
│  Le LLM voit toutes     │  Hermès filtre : le LLM ne reçoit      │
│  les données brutes     │  que le contexte utile — structuré     │
│                         │  et pertinent                          │
├─────────────────────────┼────────────────────────────────────────┤
│  Pas de conscience      │  Briefing matinal proactif :           │
│  de l'état du système   │  sécurité + infra + état JARVIS        │
│  au démarrage           │  lu vocalement sans interaction        │
├─────────────────────────┼────────────────────────────────────────┤
│  Apprentissage limité   │  Boucle d'apprentissage : une leçon    │
│  à la session courante  │  apprise persiste dans toutes les      │
│                         │  sessions futures automatiquement      │
├─────────────────────────┼────────────────────────────────────────┤
│  Répond toujours pareil │  Mode pédagogique : sait distinguer    │
│  (analyse même quand on │  expliquer d'analyser — devient un     │
│  veut comprendre)       │  tuteur cybersécurité                  │
├─────────────────────────┼────────────────────────────────────────┤
│  Opérations système     │  Infogérance en lecture seule : état   │
│  sans visibilité        │  du parc, journal des MAJ, fail-closed  │
├─────────────────────────┼────────────────────────────────────────┤
│  La mémoire peut être   │  DR du cerveau : sauvegarde/restaure   │
│  perdue                 │  pilotable à la voix, savoir cumulatif │
└─────────────────────────┴────────────────────────────────────────┘
```

> Hermès ne remplace pas le LLM — il le **protège** des tâches pour lesquelles il est mauvais (déterminisme, mémoire, temps réel), et lui réserve ce pour quoi il excelle : le raisonnement, l'analyse et la réponse contextuelle.

---

**Retour →** [README](../README.md) &nbsp;&nbsp; **Suivant →** [02 — Intégration SOC](02-SOC-INTEGRATION.md)

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

<sub>🔒 Projets proposés par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · Développés en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🔒</sub>

</div>
