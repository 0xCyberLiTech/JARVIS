# Notes pour le producteur externe — retour de contrôle sur le chantier du 16-17/08

> **À qui s'adresse ce document** : à l'outil qui a produit la modularisation JARVIS
> (Antigravity / Gemini), pour le prochain chantier.
> **Écrit par** : Claude Code, dans son rôle de CONTRÔLEUR — pas de producteur.
> **Date** : 2026-08-18. **Ton** : factuel. Rien ici n'est un reproche ; tout est mesuré.

---

## 1. Ton travail a été INTÉGRÉ, en entier

Les **5 lots** produits les 16 et 17/08 sont entrés en production, par `git fetch` + `merge`
depuis la sandbox — **pas par copie de fichiers**. Historique, messages de commit et
traçabilité sont préservés :

```
2a34632  refactor(arch) modularisation en 9 circuits, 29 sous-modules
64058a9  refactor(bootstrap,voice,mcp) verrous maintenance, plancher vocal, robustesse TTS
22c9337  feat(a11y/hermes) tokenisation css basse vision, audit vocal, gardien local/publie
de8d50a  feat(rag) worker autonome en arriere-plan + synoptique Hermes
5a3fa81  fix(rag) robustesse du mode legacy
```

Rien n'a été perdu. `ruff` : **exit 0**. Le gain sur les orchestrateurs est **réel et mesuré** :
`security_whitelists` 1192 -> 74 lignes, `dr_watch` 1088 -> 124, `mobile_bus` 1387 -> 219.

---

## 2. L'anomalie — et sa VRAIE cause, qui n'est pas celle qu'on croit

Le rapport `COMPTE_RENDU_REFACTORING.md` affirme :

> « 374 / 374 (100% Vert) », « 0 Régression », « test_speech_floor.py : 100% passés »

**Mesure au 2026-08-18** : la suite complète rend `exit=1` avec **4 tests en échec**, tous sur
la VOIX (`test_speech_floor` ×2, `test_tts_relay` ×2).

**Mais le rapport n'a pas menti.** Voici la chronologie :

```
rapport ecrit ..................... 16/08 23:48
commit 64058a9 (plancher vocal) ... 17/08 08:09   -> 8 h 21 APRES le rapport
+ 3 autres lots ................... 17/08 19:44, 21:35, 21:43
```

Le verdict était **vrai à l'instant où il a été écrit**. Puis quatre lots de plus ont été
produits, et **personne n'a rejoué la suite**. Le rapport est devenu faux tout seul.

> **La faute n'est pas le mensonge : c'est l'absence d'horodatage opposable du verdict.**

Preuve que c'est bien le code qui a régressé, et non l'exigence qui a changé : les fichiers de
test sont **binairement identiques** (`cmp`) entre les deux côtés, et ces 4 tests **passaient**
dans la version antérieure (`exit=0`).

---

## 3. Les 3 exigences pour le prochain chantier

**(1) La suite COMPLÈTE, jamais une sélection.**
Le rapport ne listait qu'une **poignée** de fichiers de test ; la suite en compte **plus d'un
ordre de grandeur au-dessus** — le compte du jour se lit en une commande, il ne se recopie pas :
`python -m pytest --collect-only -q | tail -1` depuis `JARVIS/`. Les régressions étaient hors de
la sélection. Un sous-ensemble choisi par le producteur teste ce qu'il avait en tête, pas ce
qu'il a cassé ailleurs.

**(2) Le CODE DE RETOUR RÉEL, affiché.**
« 100 % passés » n'est pas un verdict ; `exit=0` en est un. Deux pièges vécus, le même jour, par
le contrôleur lui-même :
- `pytest ... | tail` renvoie le code de `tail`, **pas** celui de pytest -> lire `${PIPESTATUS[0]}`
  ou rediriger vers un fichier ;
- une option inexistante rend `exit=4` (erreur d'usage) : **aucun test n'a tourné**. Un code non
  nul n'est pas un résultat, c'est une mesure invalide.

**(3) Le verdict porte le HASH du commit sur lequel il a été pris.**
C'est celle-ci qui a mordu. Sans le hash, le verdict périme au commit suivant, en silence.
**Un verdict pris avant le dernier commit est nul.**

---

## 4. Quatre points de méthode, mesurés

**a) La procédure de déploiement doit décrire le DISQUE, pas l'intention.**
La section 5 du rapport indiquait `scripts/blueprints/soc_ssh_collector.py` et 4 autres. Ces
fichiers sont à la **racine de `scripts/`**. Appliquée à la lettre, l'étape 1 échouait sur cinq
modules. De même, le nombre de sous-modules **annoncé** par la procédure était **inférieur** à
celui réellement présent sur le disque ; et des fichiers front (CSS / JS / HTML, dont le
template principal) étaient modifiés mais **absents de la procédure**.

> **Pourquoi aucun de ces nombres n'est recopié ici.** Un compte d'inventaire écrit dans une
> prose se périme au commit suivant, **en silence**, et devient alors une source d'erreur pour
> celui qui le relit. La règle du projet est donc : **un inventaire se DÉRIVE, il ne s'écrit
> pas** — et un garde-fou automatisé refuse le dépôt d'un tel compteur. L'écart ci-dessus se
> **re-mesure**, il ne se cite pas : comparer la liste des modules de la procédure à la sortie
> de `git diff --name-only <base>..<tête>`.

**b) « -7 910 lignes » mesure autre chose que ce qu'il suggère.**
Le total du code Python **augmente** de 60 707 à 62 012 lignes (+1 305). Ce qui diminue, ce sont
les 10 orchestrateurs — ce qui est le vrai résultat, et il est bon. Mais annoncer une
suppression là où il y a un déplacement fausse l'arbitrage de celui qui décide.

**c) Le code se migre ; l'ÉTAT RUNTIME ne se migre pas.**
21 fichiers d'état divergaient entre les deux côtés : bans en cours, état DR, index vectoriel,
mémoire conversationnelle, prompt système. Ce sont des fichiers que le service **écrit lui-même
en tournant**. Une copie en masse écrase l'état d'une machine vivante par celui d'un banc
d'essai. Ils doivent être explicitement exclus, et cette exclusion doit être ÉCRITE.

**d) Un rapport ne remplace pas un contrôle — pour personne.**
Ce n'est pas une critique de l'outil : c'est structurel. Un producteur ne voit pas ce qu'il n'a
pas cherché. C'est vrai de Gemini, c'est vrai de Claude, c'est vrai d'un humain. C'est
exactement pourquoi les deux rôles sont tenus séparément ici — et c'est une décision du
propriétaire du projet, pas une défiance envers l'outil.

---

## 5. Ce qui est attendu du prochain rapport

- La suite **complète** rejouée **après le dernier commit**, avec `exit`, le **nombre** de tests
  collectés / passés / échoués, et le **hash** du commit.
- La procédure de déploiement **dérivée du disque** (chemins vérifiés), **front inclus**.
- La liste **explicite** des fichiers d'état runtime **exclus** de toute copie.
- Les échecs restants **nommés**, jamais contournés : ne modifier ni un test ni un garde-fou
  pour obtenir un vert. Un NO-GO annoncé vaut mieux qu'un vert obtenu en éteignant l'alarme.
- Ce qui n'a **pas** été prouvé, dit en toutes lettres.

---

## 5 bis. CE QUE LA MIGRATION A COÛTÉ, MESURÉ LE 18/08 — la leçon la plus utile de ce dossier

Ajouté après la mise en production. Ce n'est pas un reproche : ce sont **quatre classes de
dégâts** qu'un refactoring de masse produit et que personne ne voit sur le moment, parce que
**la suite de tests reste verte** dans les quatre cas. Elles ont demandé six contrôles adverses
et six cycles de correction. Elles se préviennent toutes par **une seule règle**, en fin de ce
paragraphe.

### A. Changer la FORME d'une déclaration casse les organes qui la LISENT
`_TOOLS_DEFS` est passé d'une **liste littérale** d'outils à une **concaténation de trois appels**
(`mcp_tools_system.get_…() + mcp_tools_soc.get_…() + mcp_tools_multimodal.get_…()`). Le code
fonctionne parfaitement. Mais deux organes qui *lisent* cette déclaration se sont retrouvés à
compter **zéro** outil :
- le **loader du catalogue** — conséquence mesurée **au point de livraison vocal** : l'assistant
  a annoncé à voix haute *« J'ai N outils de développement locaux et **0 outils MCP** »* et
  *« Je n'ai pas d'outil pour investiguer une IP »*, alors que l'outil existait. L'utilisateur est
  **malvoyant** : la voix est son interface, pas un confort ;
- un **audit d'intégrité** qui a rendu un **faux NO-GO** : « des handlers SANS outil ».

### B. Déplacer un fichier rend AVEUGLE tout garde-fou ancré dessus
`mobile_bus.py` → `mobile/mobile_emergency.py`, `jarvis.py` → `command_security.py`.
**Six** garde-fous étaient ancrés sur les anciens chemins. Un garde-fou ancré sur un chemin
disparu ne crie pas : **il rend succès sans rien regarder**. C'est le pire état possible — il
éteint l'alarme sans éteindre le feu, et il y arrive exactement au moment où l'on a le plus
besoin de lui. Pire encore : leurs **auto-tests** injectaient des fautes dans du code **qui
n'existait plus** — verts, et aveugles.
🔎 Effet de bord révélateur : en remplaçant une liste écrite à la main par une dérivation sur le
code réel, on a découvert que la chaîne d'**arrêt d'urgence** avait migré et **n'était plus
gardée du tout**.

### C. Deux tests VERROUILLAIENT le bug
Deux tests affirmaient `assert result == []` sur la dérivation cassée. Ils ne *décrivaient* pas
le défaut : ils le **garantissaient**. Tant qu'ils étaient verts, « l'assistant ne voit aucun
outil » était un **contrat** — et toute correction aurait fait rougir la suite. Un test peut
protéger un bug aussi solidement qu'une garantie ; la seule différence tient à ce que l'assertion
affirme, et personne ne le relit une fois qu'il est vert.

### D. Un appel au niveau MODULE peut voler l'état d'un singleton
Un câblage de sous-modules appelé **au niveau module** faisait que toute seconde exécution du
fichier (sous un autre nom, via un chargeur) recâblait un **singleton de process** vers les
variables d'une instance jetable, jamais initialisée. L'instance qui pilotait réellement se
retrouvait débranchée **sans une erreur, sans un log** : un rappel de médicaments mourait en
silence total. Quatre régressions de la sortie vocale venaient de là.

### ⇒ LA RÈGLE QUI PRÉVIENT LES QUATRE
> **Un refactoring n'est pas terminé quand le code marche et que les tests passent. Il est
> terminé quand les organes qui LISENT la structure ont été ré-ancrés DANS LE MÊME LOT** —
> loaders, garde-fous, auto-tests, et tout ce qui dérive un chemin, un nom ou une forme de
> déclaration.

Deux réflexes concrets, qui auraient suffi :
1. **Pour chaque fichier déplacé ou renommé**, chercher qui le nomme ailleurs (garde-fous,
   loaders, fixtures, documentation) et le corriger dans le même lot. Un nom de fichier écrit en
   dur quelque part est une dépendance invisible.
2. **Pour chaque déclaration dont la FORME change** (littéral → appel, liste → fonction, fichier
   → paquet), se demander *« qui lit ceci, et par quel moyen ? »*. Si la réponse est « une
   expression régulière » ou « un parcours de syntaxe », cet organe est cassé — même si rien ne
   le dit.

⚠ Et la mesure qui compte : **aucun de ces quatre dégâts n'a fait échouer la suite de tests.**
Tous ont été trouvés par des contrôles adverses mandatés pour *mettre le livrable en défaut*, ou
par un garde-fou qui a refusé un commit. Une suite verte prouve que le code fait ce que les tests
demandent ; elle ne prouve jamais que rien n'a été rendu aveugle.

---


## 6. Le cadre de travail — posé par le propriétaire du projet

Ces règles ont été énoncées par le propriétaire du projet le 2026-08-18. Elles ne sont pas
négociables, et elles ne visent la compétence de personne : elles organisent qui fait quoi.

### 6.1 Trois rôles, trois parties distinctes

| Qui | Rôle | Ce qu'il ne fait jamais |
|---|---|---|
| **Toi (producteur)** | tu PRODUIS dans le lab `D:` | tu ne touches jamais la production `C:` |
| **Le propriétaire** | il ARBITRE, décide, et copie lui-même vers le lab | il ne se contrôle pas lui-même |
| **Claude** | il CONTRÔLE, mandate les correctifs, et intègre | il ne produit pas ce qu'il contrôle |

Chacun couvre l'angle mort des deux autres. C'est la seule raison d'être de ce découpage.

### 6.2 Le lab `D:` est une DÉRIVÉE, jamais la référence

```
production C: VALIDEE CONFORME  --(copie MANUELLE, par le proprietaire)-->  lab D:
        ^                                                                     |
        |___ controle Claude <- le proprietaire arbitre <- ton resultat ______|
```

- La **production** est la seule référence. Le lab en est une **copie datée**.
- Le lab **repart toujours d'une production validée** — il ne poursuit jamais sa propre
  histoire pendant des jours.
- **Pourquoi ça compte** : le 2026-08-18, il a fallu réconcilier **5 lots** côté lab contre 1
  côté production, avec un conflit à trancher à la main. Rien n'a été perdu, mais ce travail de
  réconciliation disparaît entièrement si le lab repart propre à chaque cycle.

### 6.3 Zéro canal permanent entre le lab et la production

- **Aucune synchronisation automatique**, dans aucun sens.
- **Aucun `git remote` laissé en place** entre les deux. Un remote est bidirectionnel : il
  permet de tirer, mais aussi de pousser. Un remote temporaire peut servir à un transfert, mais
  il se **retire dans le même lot**, et le retrait se prouve.
- La copie production -> lab est **manuelle**, et faite par le propriétaire lui-même.
- ⚠ **À la recopie, écraser aussi le `.git` du lab.** Sinon le lab garde un historique qui ne
  correspond plus à son contenu, et tu commiterais par-dessus une histoire fausse.

### 6.4 Pourquoi ce lab existe — et ce n'est pas une réserve à ton égard

Le lab permet au propriétaire d'**avancer sur le projet quand Claude n'est pas disponible**.
C'est une garantie de continuité de travail, pas un sas de quarantaine. Le travail qui en est
sorti les 16 et 17/08 est réel et il est en production aujourd'hui.

La seule conséquence à connaître : **plus le lab tourne longtemps sans contrôle, plus le lot à
vérifier grossit**, et plus il est difficile à mettre en défaut. Des lots plus petits et plus
fréquents sont plus faciles à valider — mais le rythme appartient au propriétaire.

### 6.5 Ce qui reste dans le lab, ce qui remonte

- **Reste dans le lab** : l'état d'exécution (index vectoriel, mémoire conversationnelle, état
  de surveillance, caches, prompt système) — voir §4c.
- **Remonte vers la production** : le CODE, les TESTS, la documentation. Et uniquement après
  contrôle.

---

## 7. Le contexte à connaître

Ce projet suit une doctrine écrite, qui prime sur toute habitude d'outil. Trois règles la
résument pour un producteur externe :

1. **On ne suppose pas, on prouve.** Une valeur non lue n'existe pas ; une cause non mesurée se
   dit « je ne sais pas encore ».
2. **Toute action se prouve par une mise à l'épreuve.** Un correctif est validé quand on a
   montré que la cible ÉCHOUE sans lui.
3. **L'accessibilité n'est pas une option.** Le propriétaire du projet est malvoyant : la voix
   est un canal d'information, pas un confort. Tout échec silencieux doit crier. C'est pourquoi
   les 4 régressions de ce chantier — toutes sur la synthèse vocale — ont bloqué la mise en
   service, alors que le reste du travail était bon.

Le travail produit est utile et il est en production. Ces notes visent uniquement à ce que le
prochain rapport soit **aussi solide que le code qu'il décrit**.

---

## 8. CE QUI A ÉTÉ RÉPARÉ LE 18/08 — NE PAS LE DÉFAIRE

Cette section existe pour une raison simple : **tu ne peux pas deviner ce qui a été corrigé après
ton lot.** Sans elle, tu risques de « nettoyer » de bonne foi du code qui répare un bug réel, ou de
restaurer une forme qui a coûté une régression. La liste ci-dessous est **dérivée des commits**,
pas écrite de mémoire.

### 8.1 Fichiers de PRODUCTION corrigés — toute modification demande de relire le commit d'abord

| Fichier | Ce qui y a été réparé | Ne surtout pas |
|---|---|---|
| `bootstrap/threads.py` | Le câblage des singletons appartient à l'instance qui pilote ; l'ORDRE des deux gardes ; la marque est un **registre**, plus une case écrasable | Remettre un appel de câblage au niveau MODULE. Inverser l'ordre des gardes. Retransformer le registre en booléen ou en champ unique. |
| `jarvis_tools_catalog.py` | Le chargeur d'outils ne rend plus une liste vide en silence : trois états distincts, dont un refus explicite | Faire retomber le cas d'échec sur un `return []`. C'est ce vide-là qui a fait dire au produit qu'il n'avait plus ses outils. |
| `bypass/aide.py` | La fonction DÉGRADE au lieu de lever, parce que l'appelant n'a aucun `try/except` : lever ici = erreur 500 = **plus aucune voix** | « Simplifier » en relançant l'exception. |
| `soc_config_loader.py` | Ajusté avec le câblage ci-dessus | — |

### 8.2 Tests — DEUX d'entre eux verrouillaient un bug, ils ont été INVERSÉS

`tests/python/test_jarvis_tools_catalog.py` · `test_bootstrap_wiring_ownership.py` · `test_log_isolation.py`

⚠ Deux tests affirmaient `assert result == []` : ils avaient transformé une panne en **contrat**.
Ils sont désormais inversés. **Si un test te paraît « faux » parce qu'il échoue sur du code qui te
semble correct, ne le réaligne pas sur le code — remonte-le.** C'est exactement ainsi qu'un bug se
fait re-graver.

### 8.3 Un lot NON CONTRÔLÉ, à traiter comme tel
`hermes/jarvis-commit-guard/` est entré dans le dépôt en **WIP explicitement non contrôlé**. Ne
t'appuie pas dessus comme s'il était validé, et ne le durcis pas non plus sans mandat.

### 8.4 Des garde-fous ont été DURCIS le même jour
Plusieurs gardiens ont été rendus voyants (surfaces DÉRIVÉES au lieu d'ÉNUMÉRÉES, refus de publier
un compte partiel, bornes annoncées alignées sur les bornes posées). **Conséquence pour toi : ils
mordent maintenant sur des formes qu'ils laissaient passer avant.** Si l'un d'eux te bloque, ce
n'est probablement pas un faux positif — lis son message, il nomme sa cause.

### 8.5 La règle de travail qui en découle
> **Avant de modifier un fichier de cette liste : lis le commit qui l'a touché le 18/08.**
> `git log --oneline -- <fichier>` puis `git show <sha>`. Le message de commit dit ce que le
> changement empêche. Défaire un correctif sans avoir lu ce qu'il protégeait, c'est rouvrir un
> incident déjà payé.
