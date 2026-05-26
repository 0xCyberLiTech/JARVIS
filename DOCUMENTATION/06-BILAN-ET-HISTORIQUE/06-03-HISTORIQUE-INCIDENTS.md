---
title: "Historique des incidents et résolutions"
code: "JARVIS-DOC-06-03"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "Bilan"
mots_cles: ["incidents", "bugs", "resolutions", "historique", "post-mortem"]
---

# Historique des incidents et résolutions

> Recueil chronologique des incidents notables, bugs résolus, et leur cause
> racine. Sert de **post-mortem light** pour éviter la réintroduction et
> pour les futurs Claude / contributeurs qui reprennent le projet.

## 2026-05-23 — Bug « UI qui se relance ponctuellement »

### Symptômes observés (15+ jours)

- L'interface web JARVIS rechargeait aléatoirement pendant l'usage
- Coïncidait souvent avec des actions précises (switch voix Edge, slider EQ
  pendant lecture audio, switch de mode chat)
- Marc avait initialement pensé que la cause était dans ces actions
- **En réalité** : coïncidence visuelle, le déclencheur était autre

### Diagnostic chronologique (post-mortem 2026-05-23)

| Heure | Événement | Détail |
|---|---|---|
| 14:07 | 1er rapport | Marc : lecture audio + slider EQ → UI sautée |
| 14:30 | 2e occurrence | Marc : changement param audio EQ |
| 14:33 | Hypothèse 1 (incomplète) | Fix idempotence `_log.addHandler` + `start_all()` (commit `06e4297`). Résout les **doublons de log** et l'interférence threads boot, mais pas le reload UI lui-même. |
| 14:46 | Instrumentation passive | Commit `30462b1` : JS-DIAG v1 (hooks `error` + `unhandledrejection` + monkey-patch `location.reload`) |
| 14:50 | Échec monkey-patch | Log montre : `reload monkey-patch failed: Cannot redefine property: reload`. Les navigateurs modernes refusent `Object.defineProperty` sur `location.reload`. |
| 14:51:37 | 3e reproduction | Marc : « UI rebooted ». Log JS-DIAG montre **2 `jsdiag.ready` espacées 93s** = **vrai reload page** confirmé. AUCUN `window.error` ni `unhandledrejection` capturé → c'est un `location.reload()` JS direct. |
| 14:53 | JS-DIAG v2 | Commit `da7384d` : bascule sur `beforeunload` event (capte toute navigation sortante avec stack trace) |
| 14:56:17 | **Capture stack !** | `[JS-DIAG] kind=beforeunload | src=Error: ... at boot_init.js:870:55` |
| 15:00 | **Cause racine identifiée** | `boot_init.js:870` = `if (d.boot_id && d.boot_id !== stored) location.reload();` dans `_pollBootId`. Le code JS détectait à juste titre un nouveau `boot_id` côté serveur. → **Le serveur régénérait son `_JARVIS_BOOT_ID`** |
| 15:01 | Investigation Python | `_JARVIS_BOOT_ID = str(int(time.time()))` est au top-level de `jarvis.py`. Régénéré à chaque ré-exécution du top-level. |
| 15:02 | **Mécanisme compris** | `blueprints/soc.py` fait `from jarvis import _CODE_REASONING_MODE, _jarvis_mode, MODEL, OLLAMA_URL` **dans des fonctions thread** (lignes 1149/1153/1154/1463 — pattern lazy import). Python ne voit pas `jarvis` dans `sys.modules` (qui tournait en `__main__`), donc il importe `jarvis.py` UNE 2ème fois comme module → top-level ré-exécuté → `_JARVIS_BOOT_ID` régénéré → `_pollBootId` détecte la différence → reload. **UNE fois par session** (sys.modules cache après) → d'où le caractère aléatoire et non corrélé aux actions utilisateur. |
| 15:02 | Palliatif | Commit `8e3d518` : `_JARVIS_BOOT_ID` mis en cache `os.environ` (partagé entre tous les imports du même process Python). Symptôme neutralisé. |
| 15:10 | Validation Marc | Test stress : switch modes + EQ + voix → « l'UI ne bronche pas top » |
| 17:00 | **Fix racine** | Commit `709049f` : DI explicite via `init_soc(get_jarvis_mode, code_reasoning_mode, get_model, ollama_url)`. Les 4 `from jarvis import` éliminés. Le palliatif `8e3d518` reste en place par sécurité mais n'est plus nécessaire. |

### Pourquoi le bug paraissait aléatoire

- Le déclencheur n'était **pas** une action Marc (slider EQ, switch mode, voix)
- Le déclencheur était le **PREMIER appel** d'une fonction thread `_soc_llm_call`
  (auto-engine SOC) qui faisait `from jarvis import` — moment imprévisible
- Une seule fois par session (après c'est en cache `sys.modules`)
- D'où l'apparente non-reproductibilité sur action précise

### Leçons apprises

1. **`from X import` dans une fonction n'est pas "gratuit"** quand `X` tourne
   en `__main__` : Python ré-importe `X` comme module et ré-exécute son top-level.
2. **Tout side-effect au top-level d'un module potentiellement ré-importé**
   (handler, thread, timestamp, init) doit être protégé par idempotence.
3. **L'instrumentation passive paie** : sans JS-DIAG v2 capturant la stack
   `boot_init.js:870`, on aurait continué à chercher dans les sliders.
4. **Garder le palliatif même après le fix racine** : double sécurité.

### Outils laissés actifs (décision Marc 2026-05-23)

Voir [`../05-EXPLOITATION/05-03-OBSERVABILITE-LOGS.md`](../05-EXPLOITATION/05-03-OBSERVABILITE-LOGS.md).

- `scripts/jarvis.log` persistant (5 MB × 7)
- JS-DIAG v2 (beforeunload + visibilitychange + window.error + unhandledrejection)
- Try/except global `/api/tts` enrichi (voix + moteur au crash)
- 6 garde-fous idempotence

---

## 2026-05-23 — Interférence pytest ↔ JARVIS prod

### Symptômes

- Pendant la session de refactor, des comportements bizarres chez Marc
  (audio Kokoro synthétise "JARVIS opérationnel." sans raison, VRAM swap
  inattendu, modèles Ollama déchargés)
- Coïncidait avec les commandes `pytest` lancées par Claude

### Cause racine

5 fichiers `test_jarvis_*.py` font `import jarvis` au chargement. Chaque
`pytest tests/python/` démarre donc **les 10 threads boot** (`kokoro_preload`,
`boot_vram_cleanup`, `soc_model_prewarm`, `kokoro_prewarm`, ...) dans le
process pytest, en parallèle de l'instance JARVIS de Marc.

### Fix

`tests/python/conftest.py` pose `os.environ.setdefault("JARVIS_SKIP_BOOT_THREADS", "1")`
**AVANT** tout import (commit `be4dc8b`). `bootstrap/threads.start_all()`
retourne immédiatement avec log `[BOOTSTRAP] ... SHUNTÉS`.

### Leçons apprises

- Les tests qui `import` une app Flask au chargement déclenchent les
  side-effects du boot. Il faut un mécanisme de **bypass via env var** dès le
  conftest.

---

## 2026-05-23 — Drift phi4 SOC : recommandations hallucinées malgré system prompt strict

### Symptômes observés

Marc soumet à Claude une analyse SOC produite par JARVIS mode SOC (phi4:14b)
qui recommandait 4 actions correctives sur l'infrastructure :

1. Bannir l'IP `177.141.47.123` via CrowdSec
2. Réactiver ModSec sur les serveurs Apache (qualifié de « désactivé »)
3. Vérifier AppArmor (qualifié d'« inaccessible »)
4. Appliquer « 17 mises à jour de sécurité en attente »

### Vérifications croisées en live (SSH read-only sur clt, pa85, srv-nginx)

| Recommandation phi4 | Réalité vérifiée | Verdict |
|---|---|---|
| Bannir 177.141.47.123 | `cscli decisions list -i 177.141.47.123` → **déjà bannie** (`fail2ban-nginx-cve`, expire ~24h) | ❌ phi4 a violé sa propre RÈGLE ABSOLUE « IPs DÉJÀ NEUTRALISÉES » |
| ModSec désactivé Apache | `apache2ctl -M` → `security2_module (shared)` actif sur clt **ET** pa85 | ❌ Hallucination pure |
| AppArmor inaccessible | `aa-status` → 127 profils chargés / 7 enforce (clt) · 106 / 7 (pa85) | ❌ Hallucination pure |
| 17 updates sécurité | `apt list --upgradable` → **0** sur clt, pa85, srv-nginx | ❌ Chiffre inventé |

**4/4 recommandations hallucinées.** L'attaque réelle (`/cgi-bin/%2e%2e/.../bin/sh` payload `libredtail-http` depuis 177.141.47.123) avait été détectée par Suricata, escaladée par fail2ban-nginx-cve et bannie automatiquement par CrowdSec **sans intervention humaine** — la chaîne défensive a fonctionné.

### Cause racine

phi4 a produit une **« checklist générique SOC »** issue de ses connaissances de pré-entraînement plutôt que de s'appuyer sur l'état live qui lui était injecté dans le contexte SOC (snapshot `monitoring.json`).

Le system prompt contenait déjà :
- `RÈGLE ABSOLUE — FIDÉLITÉ SOC` (utiliser uniquement les données du contexte)
- `RÈGLE ABSOLUE — IPs DÉJÀ NEUTRALISÉES` (ne jamais re-bannir)
- `RÈGLE ABSOLUE — RECOMMANDATION DE BAN PROPORTIONNÉE`

Mais ces règles étaient **toutes ciblées sur les recommandations de ban d'IP**. Aucune règle ne couvrait explicitement les recommandations sur **les services (ModSec, AppArmor, WAF) ou les mises à jour système**. Le modèle a comblé le silence par une checklist générique.

### Fix

Commit `<next>` : alignement du prompt SOC dans `scripts/jarvis_prompt_profiles.json` profil `Phi4 — Analyse Avancée` :

1. **Généralisation de la règle FIDÉLITÉ SOC** : étendue des IPs/scores aux **services, configurations, mises à jour** — interdiction d'extrapoler l'état d'un service non mentionné dans le contexte.
2. **Nouvelle RÈGLE ABSOLUE — ANTI-CHECKLIST GÉNÉRIQUE** : interdit explicitement les recommandations issues de connaissances générales (« réactiver le WAF », « appliquer les mises à jour ») sans support d'une donnée présente dans le contexte SOC injecté.
3. **Renforcement de la règle IPs DÉJÀ NEUTRALISÉES** : ajout d'une étape de vérification **OBLIGATOIRE** avant toute recommandation de ban (« Si tu envisages de recommander un ban, tu DOIS d'abord vérifier que l'IP n'apparaît pas dans la section "IPs DÉJÀ BANNIES" du contexte. Cette vérification doit être explicite dans ton raisonnement »).

### Leçons apprises

1. **Un prompt strict ne suffit pas à empêcher le drift sur les zones non couvertes explicitement.** Si la règle anti-hallucination ne mentionne que les IPs, le modèle hallucine sur les services. Il faut une règle générique (« anti-checklist ») en plus des règles ciblées.
2. **Vérification croisée systématique avant toute action sur la prod.** Même quand phi4 propose une action plausible et conforme à son rôle, valider chaque pré-condition en live (SSH read-only). Ce cas est l'illustration parfaite de pourquoi la règle ABSOLUE `feedback_jarvis_no_regression` (Marc) existe.
3. **L'auto-engine SOC a déjà fait son travail.** Les recommandations conversationnelles de phi4 doivent être pensées comme **un complément** à l'automatisation déjà en place, pas comme une checklist d'audit indépendante.
4. **Les recommandations type « réactiver le WAF / appliquer les mises à jour » sont des smells.** Si phi4 les produit alors que le contexte SOC ne les supporte pas, c'est un drift à corriger côté prompt.

### Validation

- Plan d'action proposé à Marc : **rien à faire sur l'infra**, l'attaque a été automatiquement neutralisée.
- Alignement prompt SOC validé par Marc puis appliqué (commit `<next>`).
- À surveiller : les prochaines analyses SOC phi4 — vérifier que les recommandations restent ancrées dans le contexte injecté.

---

## Template pour futurs incidents

```markdown
## YYYY-MM-DD — Titre court de l'incident

### Symptômes observés
- ...

### Diagnostic chronologique
| Heure | Événement | Détail |
|---|---|---|

### Cause racine
...

### Fix
- Commit `HASH` : description
- Fichiers touchés : ...

### Leçons apprises
1. ...
2. ...

### Validation
- ...
```
