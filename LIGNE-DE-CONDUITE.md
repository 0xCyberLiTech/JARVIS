# Ligne de conduite — le travail à trois

> **Pour qui** : le propriétaire du projet, l'agent de contrôle (Claude Code), et l'outil
> producteur qui travaille dans le laboratoire de développement.
> **Établie le** : 2026-08-18, à l'issue d'une migration qui a coûté cher.
> **Statut** : ligne de conduite permanente. Elle ne se modifie que par décision du
> propriétaire du projet.

---

## 1. Trois rôles, et ils ne se recouvrent pas

| Qui | Décide de quoi | Ne décide PAS de |
|---|---|---|
| **Le propriétaire** | la direction, les priorités, l'usage — « est-ce que ça me convient » | — |
| **Le producteur** (laboratoire) | l'analyse, le plan d'action, la correction | ce qui entre en production |
| **Le contrôle** (Claude) | la conformité, la non-régression, l'avis technique | la direction du projet |

**Le producteur est aux commandes de SON travail** : à lui l'analyse et la solution. Le contrôle
ne code pas à sa place, il mesure. Et personne ne décide de la direction sauf le propriétaire.

---

## 2. Le cycle, fermé des deux côtés

1. **Le contrôle informe le producteur** de toute évolution, *quelle qu'elle soit*. Il ne doit
   jamais découvrir un changement après coup, ni défaire de bonne foi un correctif qu'il ignorait.
2. **Le propriétaire pousse vers le laboratoire** du code **fraîchement validé** — jamais un état
   intermédiaire, jamais un dossier écrasé, **toujours avec son historique git**.
3. **Le propriétaire mandate le producteur** : maintenance ou expérimentation. Le laboratoire
   avance **même quand le contrôle n'est pas disponible** — c'est sa raison d'être.
4. **Tout revient au contrôle** : mise en conformité, avis sur le fond, cohérence d'ensemble.
   Puis le propriétaire tranche.

**Le laboratoire ne remonte jamais vers la production DE LUI-MÊME.** Ce qui est interdit, c'est
**l'automatisme**, pas le retour : aucun lien permanent entre les deux emplacements, aucune synchronisation,
aucune tâche planifiée. L'échange se fait dans les **deux sens**, par un fichier inerte qu'il faut tirer à
la main — et au retour, **le contrôle passe AVANT tout merge**.

> ⚠ **Corrigé le 2026-08-19, sur décision du propriétaire.** Cette ligne disait *« un seul sens »* — trop
> restrictive, et en contradiction avec le point 4 ci-dessus qui décrit déjà un retour vers le contrôle.
> Le garde-fou n'a jamais été le sens unique : c'est **le geste manuel**.

---

## 3. Ce qui ne se négocie pas

- **La production ne reçoit que du validé.** « C'est petit, on pousse directement, juste cette
  fois » est la phrase qui annule tout le dispositif.
- **Toujours par git, jamais par copie écrasée.** Sans les commits, la question *« qu'est-ce qui a
  bougé d'autre ? »* devient impossible à poser — et c'est elle qui trouve le plus de défauts.
- **Un travail n'est validé que s'il est PROUVÉ** : la faute injectée est détectée, le test échoue
  sans le correctif, la mesure est prise au point de livraison. « Ça marche » n'est pas une preuve.
- **Un verdict rouge ne se contourne pas.** « Pré-existant », « pas mon lot », « systémique » ne
  sont pas des motifs. On le ferme, ou on l'inscrit explicitement avec sa cause.
- **Aucune règle ne se modifie sans l'accord du propriétaire.** Un fait prouvé faux se corrige avec
  sa preuve et sa date ; une règle, jamais en silence.

---

## 4. Petit et souvent, plutôt que gros et rare

**C'est la leçon la plus chère de la journée du 18/08.** Cinq lots produits sur deux jours sont
arrivés en un bloc : il a fallu **six cycles de contrôle** pour démêler ce qu'ils avaient déplacé,
et les trois quarts des défauts trouvés avaient été introduits *en réparant*.

Un petit lot se contrôle en une passe. Le risque n'est pas de produire beaucoup — c'est
**d'accumuler sans repasser par le contrôle**.

> **Test avant d'élargir un chantier en cours** : « si cette ligne se ferme, le chantier
> avance-t-il ? » Si non, elle s'inscrit ailleurs — elle ne s'ouvre pas maintenant.

---

## 5. Deux registres, à ne jamais confondre

Quand le contrôle rend un avis, il dit toujours dans quel registre il parle :

- **« c'est mesuré »** — lu, exécuté, vérifié ; le propriétaire peut le rejouer
- **« c'est mon avis »** — une lecture, faillible, qui peut être écartée sans argument

Sans cette distinction, une opinion prend l'autorité d'un fait, et le propriétaire tranche sur du
vide en croyant décider. **Et quand c'est possible, un avis se teste avant d'être donné.**

---

## 6. Ce que seul l'humain peut fermer

Dans ce système, **la voix est l'interface primaire, pas un confort** : c'est une propriété de
conception, pas une préférence. Une régression vocale ne se prouve donc ni par un test vert, ni par
une lecture de code — **elle se prouve à l'oreille, et seul un humain peut le faire.**

Aucun agent, producteur ou contrôleur, ne ferme cette étape à sa place. Un livrable qui touche à la
voix reste **non validé** tant qu'il ne l'a pas entendu.

---

## 7. Pourquoi cette ligne existe

Le 18/08, entre 6h46 et 19h02, l'assistant a annoncé **à voix haute** qu'il n'avait plus ses
outils — c'était faux, et personne ne pouvait le savoir. Quatre régressions vocales ont vécu en
production ce jour-là, parce que les essais y étaient entrés directement.

Le laboratoire ne fait pas gagner du travail. Il fait gagner **les heures pendant lesquelles
l'assistant se trompe sans que personne ne s'en aperçoive**.
