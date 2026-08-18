# Notes pour le producteur externe — retour de contrôle sur le chantier du 16-17/08

> **À qui s'adresse ce document** : à l'outil qui a produit la modularisation JARVIS
> (Antigravity / Gemini), pour le prochain chantier.
> **Écrit par** : Claude Code, dans son rôle de CONTRÔLEUR — pas de producteur.
> **Créé le** : 2026-08-18. **Dernière mise à jour** : 2026-08-19 (§6.3 réécrite, §9 à §12 ajoutées).
> **Ton** : factuel. Rien ici n'est un reproche ; tout est mesuré.
>
> ⚠ **CE DOCUMENT EST PUBLIC** — il vit dans un dépôt poussé sur une forge publique, et publier
> est irréversible (indexé même après suppression). Il ne contient donc **aucune adresse IP,
> aucun nom d'hôte interne, aucun chemin nominatif, aucun nom de personne, aucune donnée
> personnelle, aucun secret**. Les rôles sont nommés génériquement : « le propriétaire du
> projet », « le producteur externe », « l'opérateur ». **Si tu écris à ton tour dans ce dépôt,
> tiens la même règle** — §9.4 explique pourquoi la barrière automatique ne suffit pas.

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
  *« Je n'ai pas d'outil pour investiguer une IP »*, alors que l'outil existait. Dans ce système,
  **la voix est l'interface primaire, pas un confort** — un mensonge prononcé est donc un défaut
  critique, pas une gêne d'affichage ;
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
- Les deux transferts sont **manuels**, et déclenchés par le propriétaire lui-même.
- ⚠ **À la recopie, écraser aussi le `.git` du lab.** Sinon le lab garde un historique qui ne
  correspond plus à son contenu, et tu commiterais par-dessus une histoire fausse.

**Depuis le 2026-08-19, l'échange a un véhicule outillé** — voir **§11**, qui décrit ce qui
change concrètement pour toi (ce que tu reçois, ce que tu renvoies, et les deux gestes qui font
refuser ton retour).

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
3. **L'accessibilité n'est pas une option.** Dans ce système, la voix est un canal d'information
   primaire, pas un confort — c'est une propriété de conception. Tout échec silencieux doit crier. C'est pourquoi
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

---

## 9. RELEVÉ DE TRAVAUX — du 18/08 au 19/08 au matin

La §8 ci-dessus couvre les correctifs de la **journée** du 18/08. Cette section couvre **la
suite** : la soirée et la nuit. Elle est **dérivée des commits** des dépôts `JARVIS`,
`JARVIS/scripts`, `JARVIS/tests` et de l'atelier d'outillage, pas écrite de mémoire.

**Chaque point dit la même chose, dans le même ordre** : le **défaut** · la **cause MESURÉE** ·
le **correctif** · la **preuve** (code de sortie réel) · **ce qui n'est PAS prouvé**. Le dernier
champ n'est pas de la modestie : c'est là que se trouvent tes prochains pièges.

> **Pourquoi aucun compte n'est écrit dans cette section.** Un total de tests, un nombre de
> modules ou d'outils écrit dans une prose devient faux tout seul au commit suivant, **en
> silence** — et un garde-fou du dépôt refuse le commit qui en introduit un (cf. §9.3). Quand tu
> as besoin d'un chiffre, la **commande qui le mesure** est donnée à la place.

### 9.1 LA VOIX — le barge-in du micro était armé d'un « si »

**Le défaut.** Ouvrir le micro ne coupait pas toujours la parole en cours. Dans trois états,
l'assistant continuait de parler **par-dessus** le micro qui venait de s'ouvrir — dans la pièce
**et** dans l'enregistrement.

**La cause, mesurée.** `static/js/stt.js::sttStart` n'appelait `stopAudio()` que *si*
`_currentAudioSource !== null`. Or cette variable n'est posée qu'**entre** `source.start()` et
`onended` (`audio_viz.js::playSentence`) : c'est un **sous-ensemble strict** de « l'assistant
parle ». Elle vaut `null` — donc la condition était fausse, donc le barge-in ne se déclenchait
pas — pendant la **synthèse** (l'aller-retour vers la route de synthèse, mesuré à quelques
secondes), **entre deux morceaux** d'un texte découpé (la file d'attente est encore pleine), et
pendant **tout le repli voix navigateur** (`speechSynthesis`, qui ne pose jamais cette variable).

**Le correctif** (`JARVIS/scripts`, commit `e944c2c`). Le barge-in **ne se conditionne plus** :
`stopAudio()` est idempotent (file vidée, génération invalidée, synthèse navigateur annulée,
source stoppée si elle existe). L'appeler à vide ne coûte rien. Les deux autres entrées
d'engagement — clavier et micro mobile — l'appelaient **déjà** sans condition ; cette porte-ci
était la dernière armée d'un « si ». Le commentaire du fichier conserve la forme fautive **en
toutes lettres**, pour que personne ne la restaure de bonne foi.

**La preuve.** Un garde-fou d'atelier a été étendu dans le même lot : sa surface est **dérivée**
(tout `.js` de `static/**` qui ouvre une capture micro **et** porte la route de capture ou un
rôle d'engagement), et **un `stopAudio()` remis sous condition, sous `&&`, dans un ternaire ou
différé rend NO-GO**. Forme d'origine réinjectée → `exit 1` ; forme corrigée → `exit 0`. Suite
complète et lint au vert au commit.

> ⛔ **NE PAS LE DÉFAIRE.** Remettre ce `stopAudio()` sous une condition — même « propre », même
> « défensive » — rouvre exactement le défaut. Si une condition te paraît nécessaire, **remonte
> la question** au lieu de la réintroduire.

**Ce qui n'est PAS prouvé.** Le garde-fou n'a **pas** de parseur JS : son analyse est
structurelle (appariement d'accolades, en-tête de bloc, borne d'instruction). Il ne prétend pas
voir une condition portée par une **indirection dynamique** (un booléen calculé ailleurs, un
dispatch). Et il vit dans l'**atelier d'outillage**, pas dans le dépôt que tu reçois : **il ne
se déclenchera pas chez toi** — il mordra au moment de l'intégration.

### 9.2 LE CAVIARDAGE DES SECRETS — trois formes sortaient en clair vers le modèle

**Le défaut.** La deuxième couche anti-exfiltration (le caviardage **par contenu**, celui qui
retire un secret du corps d'un fichier avant qu'il n'atteigne le modèle de langage, le serveur
d'outils ou l'agent) **laissait passer trois formes de secrets en clair** : un condensé de mot
de passe au format `apr1`, un condensé préfixé d'un schéma entre accolades (famille `{SHA}`,
`{SSHA}`, `{MD5}`, `{CRYPT}`…), et les jetons d'un hébergeur cloud à préfixe versionné.

**La cause, mesurée.** Défaut **pré-existant** — la fonction datait de plusieurs semaines.
(1) L'alternation des identifiants du format de condensé modulaire ne contenait pas `apr1` ;
(2) le schéma entre accolades n'est **pas** au format modulaire, donc **aucune** règle ne le
voyait ; (3) le préfixe versionné du fournisseur cloud n'était couvert par aucun motif. Le
verdict de l'audit était `exit 1` sur l'axe CLASSE, avec les trois formes comptées à zéro
caviardage.

**Le correctif** (`JARVIS/scripts/security_whitelists_sub/exfil_guard.py`, commit `f55fd8e`).
**L'outil d'audit n'a PAS été touché** — c'eût été du blanchiment : faire passer le contrôle
sans supprimer la cause. Les trois motifs ferment la **CLASSE**, pas l'instance du corpus :
l'identifiant de condensé varie, la structure `$id$[params$]sel$hash` ne varie pas ; le préfixe
de schéma est conservé (même parti pris que pour un bloc PEM : on garde la structure, on
caviarde la valeur) ; le préfixe versionné est la partie **stable** de la forme.

**La preuve.** Audit **avant** le fix `exit 1` (trois anomalies) · **après** `exit 0` ·
**après retrait du correctif** `exit 1`, **les mêmes trois anomalies** — c'est ce dernier point
qui prouve que c'est bien **ce** fix qui ferme, et pas autre chose. Suite complète `exit 0`,
lint `exit 0`, audit du serveur d'outils `exit 0`. Anti-débordement rejoué sur le code réel de
tout l'espace de travail, avec et sans le fix : les seuls caviardages nouveaux sont les fixtures
elles-mêmes — **zéro faux positif sur du code réel, zéro forme perdue**.

**Le filet de non-régression** (`JARVIS/tests`, commit `da944d6`). Il **ne recopie pas** les
fixtures de l'outil d'audit : il porte des **variantes** (casse, guillemets, séparateurs,
préfixes et suffixes, schémas voisins, variantes de préfixe fournisseur), plus une série de
voisins **légitimes qui ne doivent pas bouger** (une variable qui s'appelle `$apr1`, un
`md5sum`, un `{SHA}` cité en prose, un espace réservé). **L'outil garde la forme exacte ; les
tests gardent la classe.** Correctif retiré → `pytest -k redact` rend `exit 1` sur « aucun
caviardage » : **le test échoue sans le fix**, il n'est donc pas du théâtre.

> ⛔ **NE PAS LE DÉFAIRE.** Ces motifs ont l'air redondants ; ils ne le sont pas. Toutes les
> valeurs de test sont **inventées** : aucun secret réel n'a été lu, affiché ni journalisé, et
> aucun ne doit l'être. Si tu ajoutes une forme de secret, ajoute-lui **une variante**, jamais
> une copie de la fixture.

**Ce qui n'est PAS prouvé.** Le caviardage par contenu est la **deuxième** barrière ; la
première est la denylist **par chemin**. Un fichier qui ne porte **que** la valeur brute d'un
secret, sans nom de variable ni affectation, échappe à l'axe contenu — c'est l'axe chemin qui le
rattrape. **Ni l'un ni l'autre n'est une barrière unique suffisante.** Et rien ici ne prouve
qu'il n'existe pas une **quatrième** forme non couverte : une liste de motifs est par nature une
denylist, et une denylist rouvre toujours à la forme suivante.

### 9.3 LES COMPTEURS FIGÉS — retirés, puis outillés

**Le défaut.** Plusieurs inventaires écrits **en toutes lettres** dans la prose de ce document
même et dans un commentaire du produit. Un compte figé devient faux tout seul au commit suivant,
sans que personne ait menti — et la mémoire documentaire du produit l'ingère ensuite.

**La cause, mesurée — et elle est de mon côté.** Deux de ces compteurs ont été écrits **par le
contrôleur, dans ce document, une heure avant** que le garde-fou ne les morde. L'un d'eux était
**déjà périmé au moment où il a été écrit**. C'est exactement la classe que ce document reproche
au rapport du producteur — reproduite dans le document qui la dénonce. Un troisième vivait dans
un commentaire de fixture du produit. Le NO-GO n'a pas été trouvé par moi : il a été **remonté
par l'agent producteur** que j'avais mandaté.

**Le correctif.** Commits `034e043` et `77ec5f6` (dépôt `JARVIS`), `1e7364b` et `1a8dc5c`
(dépôt `JARVIS/scripts`). Les nombres sont remplacés par la **commande qui les mesure**, ou par
une formulation qui n'en a pas besoin. Aucun sens n'est perdu : ce qui comptait dans ces phrases
était le **zéro annoncé** et le **faux NO-GO**, jamais le total.

**La preuve.** `jarvis-frozen-count-guard` : `exit 1` avant, `exit 0` après — verdict rejoué à
chaque exécution, et **câblé au pre-push** : un compteur figé introduit dans un `.md` de ce
dépôt **bloque le commit**.

> ⚠ **Conséquence directe pour toi.** Si tu écris un inventaire chiffré — un nombre de modules,
> d'outils, de routes, de couches, de collecteurs, de handlers, ou un total de suite de tests —
> dans un document de ce dépôt, **le garde-fou refusera ton commit**. Ce n'est pas un faux
> positif : écris la commande qui dérive le nombre. Un rapport qui donne la commande est **plus**
> solide qu'un rapport qui donne le nombre — il reste vrai demain.

**Ce qui n'est PAS prouvé.** Le garde-fou reconnaît une **liste d'unités** fermée. Un inventaire
dit avec un **autre mot** lui échappe — c'est déjà arrivé deux fois et c'est écrit dans son
propre en-tête. Sa portée est **volontairement étroite** : l'élargir le ferait crier sur des
ratios et des énumérations légitimes, et un garde-fou qui inonde est un garde-fou qu'on éteint.

### 9.4 LA SANITISATION PUBLIQUE — et le trou de classe qui reste ouvert

**Le défaut.** Des **données personnelles** vivaient dans des fichiers **publics** de ce dépôt :
une donnée de **santé** accolée au prénom du propriétaire (présente dans un fichier de
configuration tracké et **publié depuis environ sept semaines**), son **prénom** dans des
commentaires de plusieurs fichiers, une **tierce personne** du foyer — quelqu'un qui n'a rien
demandé —, une **pièce du domicile**, et des **noms d'hôtes internes**.

**Le correctif** (commits `fa90655`, `ef9c263`, `8db1135`, `65d3707`). Tout cela est retiré. Les
commentaires **gardent leur argument technique intact** : seule l'identification personnelle
disparaît, remplacée par « l'opérateur », « un proche du foyer », « la pièce de vie », des
descriptions génériques de rôle. **Aucun gate, aucun invariant, aucune clé fonctionnelle n'a
été touché** ; les fichiers structurés ont été revalidés par leurs parseurs respectifs après
correction. Décision du propriétaire : **retirer oui, réécrire l'historique non** — les
occurrences restent dans les commits antérieurs déjà publiés, c'est **assumé et dit**.

**Une faute de méthode, dans le même lot, et elle mérite d'être connue.** Le balayage de
vérification était **sensible à la casse** : deux occurrences écrites en **MAJUSCULES** l'ont
traversé — pendant que le script imprimait « VIDE = fermé », **un libellé écrit en dur, affiché
inconditionnellement, qui mentait quand le balayage trouvait quelque chose**. C'est la même
classe que celle qui a coûté cher plus haut : *un contrôle ancré sur une **forme** rouvre à la
forme suivante, et un verdict qui ne **lit** pas son propre résultat est un veilleur sans
lecteur*. Corrigé : balayage insensible à la casse, **verdict calculé depuis le compte réel**.

> ### ⛔ LA CLASSE À CONNAÎTRE — le garde-fou de publication ne couvre PAS l'identité en prose
> Le dépôt possède une barrière de publication (`scripts/hermes/jarvis-public-doc-guard/`,
> câblée au pre-push). Elle porte **deux** invariants, et **deux seulement** :
> - **I1** — aucune **adresse IP privée concrète** dans un `.md` tracké de cette vitrine (les
>   espaces réservés génériques passent) ;
> - **I2** — aucun **identifiant nominatif dans un chemin utilisateur**, sur **tous** les dépôts
>   publics de l'espace de travail — surface **dérivée** de la configuration des remotes, jamais
>   une liste écrite.
>
> **Il n'existe AUCUN invariant sur l'identité en PROSE.** Un prénom, un nom, une donnée de
> santé, un tiers, une adresse écrits dans une phrase ou un commentaire **ne déclenchent rien**.
> C'est précisément pourquoi **rien n'a crié pendant sept semaines**. Un chantier d'invariant
> supplémentaire est **ouvert** — au 2026-08-19 il **n'est pas implémenté** : je l'ai vérifié
> dans le fichier du garde-fou, il ne porte que I1 et I2.
>
> **Ce que ça t'impose, concrètement** : un vert de cette barrière prouve **son invariant**, pas
> la classe. Ce qu'un garde-fou ne couvre pas **se relit à la main, sur le diff réel**, avant
> tout commit dans ce dépôt.

**Ce qui n'est PAS prouvé.** Le retrait est prouvé sur l'**arbre de travail actuel** (balayage
insensible à la casse, résultat vide). Il n'est **pas** prouvé sur l'**historique** — et c'est
une décision assumée, pas un oubli. Et je n'ai pas de moyen mécanique d'affirmer qu'aucune autre
donnée personnelle ne subsiste **sous une autre forme** : par construction, on ne trouve que ce
qu'on pense à chercher.

---

## 10. LES TROIS DÉFAUTS LATENTS — ouverts, connus, non fermés

Un contrôle adverse indépendant les a trouvés. Ils sont **pré-existants**, ils **n'ont aucune
occurrence réelle dans le code d'aujourd'hui**, et ils sont **ouverts**. Je les ai **re-mesurés
moi-même** avant de les écrire ici — chacun par une sonde en lecture seule qui appelle le
prédicat du garde-fou concerné avec des sources forgées, sans rien écrire sur le disque.

**Pourquoi tu dois les connaître.** Ce sont trois endroits où **un garde-fou dit GO alors que le
défaut est là**. Si ton travail passe par l'une de ces formes, le vert que tu obtiendras ne
voudra rien dire — et personne ne le verra.

### 10.1 Une chaîne de caractères traverse le garde-fou du barge-in

Le garde-fou du §9.1 retire les **commentaires** avant d'analyser (il s'était déjà fait berner
par sa propre documentation par le passé) — mais **pas les chaînes de caractères**. Un jeton
`stopAudio(` situé **à l'intérieur d'une chaîne**, dans une position par ailleurs
inconditionnelle, est compté comme un vrai barge-in.

**Mesuré, prédicat appelé directement, formes forgées :**

```
faute d'origine (barge-in sous un « if »)        -> NO-GO   (le garde-fou voit)
forme conforme (barge-in inconditionnel)         -> GO      (aucun faux positif)
chaine simple  const a = 'x stopAudio() y'       -> NO-GO   (ne traverse PAS)
chaine contenant un point-virgule interne        -> GO      <== TRAVERSE
gabarit multiligne contenant un point-virgule    -> GO      <== TRAVERSE
```

Dans les deux dernières formes, le **vrai** barge-in est remis sous condition et le garde-fou
rend quand même GO. **Aucune occurrence réelle aujourd'hui** : toutes les mentions de ce jeton
dans le code du produit sont soit des appels réels, soit des commentaires — vérifié.

### 10.2 La fenêtre horaire peut museler une alerte vitale

Un invariant interdit qu'une **fenêtre horaire** (le silence nocturne) puisse faire taire une
alarme **vitale** : rappels de médicaments, arrêt d'urgence, alarme serveur, portail d'urgence.
Les surfaces vitales sont **dérivées** du code et jugées sur la **présence brute** d'un jeton de
fenêtre — cette partie-là est solide.

**Le trou est ailleurs, et il est déclaré dans le code du garde-fou lui-même** : la détection de
mise sous condition dans le **code ordinaire** ne travaille que sur les jetons **d'amorçage**,
pas sur leur clôture. Conséquence : un **helper** de fenêtre défini dans la source unique de
configuration — l'endroit le plus naturel pour l'écrire — et consommé par un **répartiteur
ordinaire** qui décide s'il appelle l'alarme vitale, **n'est vu par personne**.

**Mesuré, prédicat appelé directement :**

```
fenetre lue DANS la surface vitale elle-meme                 -> NO-GO  (vu)
helper dans la source unique + condition dans le repartiteur -> GO     <== TRAVERSE
```

Dans le second cas, le canal des rappels de médicaments est **muet la nuit** et le verdict est
**GO**. **Aucune occurrence réelle aujourd'hui** : l'exécution live rend GO avec toutes les
surfaces vitales prouvées sans aucun jeton de fenêtre, et le helper en question n'existe pas.

> ⛔ **Ce que ça t'interdit, sans discussion possible.** Ne place **jamais** une condition
> horaire — ni directement, ni par un helper, ni par un relais — sur un chemin qui commande un
> rappel de santé ou un arrêt d'urgence. **Ces canaux ne se taisent jamais.** Le garde-fou ne
> t'arrêtera pas ; la règle, elle, existe.

### 10.3 Le garde-fou de journalisation reste une énumération de formes

Ce garde-fou prouve qu'aucun module ne journalise **dans le vide** (hors de l'arbre de
journalisation du produit). Il **résout** désormais le module — il ne reconnaît plus une
orthographe — et il couvre les liaisons de nom courantes. Mais l'énumération des liaisons reste
une **denylist** : ce qui n'y figure pas traverse.

**Mesuré, prédicat appelé directement :**

```
temoin : appel direct                     -> NO-GO   (vu)
temoin : liaison en chaine  a = b = mod   -> NO-GO   (ferme le 18/08)
residuel : for lg in (mod,):              -> GO      <== TRAVERSE
residuel : with ... as lg:                -> GO      <== TRAVERSE
residuel : parametre par defaut lg=mod    -> GO      <== TRAVERSE
```

Ces formes sont **nommées dans l'en-tête du garde-fou** comme angles morts résiduels — elles ne
sont donc pas cachées, elles sont **assumées**. **Aucune occurrence réelle aujourd'hui** :
l'exécution live rend GO et une recherche de ces formes dans le produit ne rend rien.

> **La leçon commune aux trois.** Une denylist rouvre **toujours** à la forme suivante ; seule
> une allowlist fermée est sûre par construction. Les trois défauts ci-dessus sont trois
> endroits où l'allowlist n'a pas encore remplacé l'énumération. **Un garde-fou vert prouve son
> invariant sur les formes qu'il connaît — jamais la classe entière.**

---

## 11. L'ÉCHANGE AVEC LE LABORATOIRE — comment ça marche de ton côté

Depuis le 2026-08-19, l'aller et le retour passent par **deux options de menu** côté
propriétaire. Le véhicule est un **fichier d'archive git inerte** (`git bundle`). C'est **le**
garde-fou, pas un détail d'implémentation : un fichier ne synchronise rien tout seul.

**Ce que le dispositif n'ajoute pas, par construction** : aucun remote entre les deux
emplacements, aucun `pull`/`fetch`/`merge` automatique dans un sens ou dans l'autre, aucune
tâche planifiée, aucun observateur de dossier, aucune copie écrasante. L'option de **retour**
**imprime** la commande de fusion — **elle ne la joue pas**. La fusion reste un geste humain,
après contrôle.

### 11.1 L'ALLER — production → laboratoire

Tu reçois une archive par dépôt, accompagnée d'un fichier d'accompagnement qui porte **la
commande exacte** et **l'empreinte de tête attendue**, plus un manifeste d'empreintes. Avant
d'être produite, l'archive est refusée si un dépôt de production est **sale**, et son
**historique** est passé au contrôle anti-secret. L'archive est vérifiée (`git bundle verify`,
code de sortie réel) avant d'être remise.

**Ce que tu fais** : tu clones ou tu tires **depuis le fichier**. Tu vérifies que ta tête
correspond à l'empreinte annoncée. **C'est tout.**

### 11.2 LE RETOUR — laboratoire → production

**Deux vérifications refusent ton retour. Elles ne sont pas négociables, et il vaut mieux les
connaître avant qu'après :**

1. **Un côté sale ⇒ refus.** Commite ou remise ton travail avant de demander un retour.
2. **Un historique étranger ⇒ refus.** Le dispositif **prouve** que ton historique **descend
   d'un commit connu de la production**. Concrètement : si tu **ré-initialises** le dépôt, si tu
   **réécris** l'historique, ou si tu repars d'une copie sans son `.git`, ton travail **ne peut
   plus revenir** par ce canal. C'est la contrepartie directe de la règle §6.2 (« le lab repart
   toujours d'une production validée »).

### 11.3 Le contrôle anti-secret porte sur l'HISTORIQUE, pas sur le disque

C'est le point le plus contre-intuitif du dispositif, et il a été **mesuré** : une archive git
transporte **tout l'historique**. Un secret retiré du disque **et de l'index** par un
`git rm --cached` **reste dans les objets** et **part quand même**. Un contrôle limité à l'arbre
de travail est donc un **faux vert** : sur un dépôt jetable où le secret a été retiré des deux,
le contrôle « disque » rend `exit 0` (il ne voit rien) et le contrôle « historique » rend
`exit 1`.

Le contrôle travaille sur **deux axes** — le **chemin** (un fichier dont le nom dit qu'il est
sensible) et le **contenu** (le caviardage du §9.2) —, parce qu'un fichier qui ne porte que la
valeur brute échappe au second et n'est rattrapé que par le premier. **Jamais une seule
barrière.** Aucune valeur de secret n'est jamais lue ni imprimée : le contrôle nomme le dépôt,
le chemin, l'objet et les commits.

> ⚠ **Ce que ça t'impose.** Ne commite **jamais** un jeton, une clé, un mot de passe ou un
> fichier de configuration porteur d'un secret dans un dépôt du laboratoire — pas même
> temporairement, pas même « je le retirerai au commit suivant ». **Le retirer plus tard ne le
> retire pas**, et c'est ton retour entier qui sera refusé.

**Un fait mesuré et remonté, non corrigé** : un objet de ce type est **toujours présent dans
l'historique** de l'un des dépôts du produit, alors que le fichier correspondant est aujourd'hui
non suivi et ignoré. Ce dépôt-là **n'a aucun remote** — il n'est donc pas publié — mais le fait
est dit plutôt que tu.

### 11.4 Ce qui reste dans le lab, ce qui remonte — inchangé

Voir §6.5. **L'état d'exécution ne remonte jamais** : index vectoriel, mémoire
conversationnelle, état de surveillance, caches, invite système. Ce sont des fichiers que le
service **écrit lui-même en tournant** ; les copier écrase l'état d'une machine vivante par
celui d'un banc d'essai.

---

## 12. CE QUI N'EST PAS PROUVÉ DANS CE DOCUMENT — mes propres angles morts

Un relevé qui ne raconte que ses succès ment par omission. Voici, en toutes lettres, ce que ce
document **ne** prouve **pas** :

- **La liste des travaux est dérivée des commits**, dépôt par dépôt. Elle ne prouve pas qu'aucun
  autre changement n'a eu lieu **hors dépôt** (état d'exécution, configuration de poste).
- **Les codes de sortie cités ont été rejoués** pour les garde-fous consultables ; ceux des
  suites complètes de tests sont **repris des messages de commit** et n'ont pas été re-mesurés à
  la rédaction. Un verdict pris avant le dernier commit est **nul** (§3, exigence 3) : rejoue-la
  toi-même avant ton prochain rapport.
- **Les trois défauts latents du §10 sont prouvés OUVERTS** (formes forgées, verdicts mesurés).
  Il n'est **pas** prouvé qu'ils soient les **seuls** : trois formes trouvées ne disent rien de
  la quatrième.
- **« Aucune occurrence réelle aujourd'hui » est un constat daté**, obtenu par recherche
  syntaxique. Une recherche syntaxique ne peut jamais être close : un chemin construit par
  concaténation, une variable, une indirection lui échappent.
- **La sanitisation est prouvée sur l'arbre de travail, pas sur l'historique** (§9.4), et un
  garde-fou de publication ne couvre pas l'identité en prose. **Relis ton diff.**
- **Un lot non contrôlé subsiste** dans le dépôt (§8.3), et un commit de sauvegarde d'atelier a
  été pris **avec les vérifications désactivées**, assumé et justifié dans son propre message :
  l'agent était en train d'écrire les garde-fous que le contrôle aurait lancés. Ce sont des
  états intermédiaires **dits**, pas des livraisons.

**Rien de tout cela n'est un reproche envers qui que ce soit.** C'est la carte du terrain
meuble — pour que tu ne marches pas dessus, et pour que le prochain rapport soit aussi solide
que le code qu'il décrit.
