---
title: "Historique des incidents et rÃ©solutions"
code: "JARVIS-DOC-06-03"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "ValidÃ©"
categorie: "Bilan"
mots_cles: ["incidents", "bugs", "resolutions", "historique", "post-mortem"]
---

# Historique des incidents et rÃ©solutions

> Recueil chronologique des incidents notables, bugs rÃ©solus, et leur cause
> racine. Sert de **post-mortem light** pour Ã©viter la rÃ©introduction et
> pour les futurs Claude / contributeurs qui reprennent le projet.

## 2026-05-23 â€” Bug Â« UI qui se relance ponctuellement Â»

### SymptÃ´mes observÃ©s (15+ jours)

- L'interface web JARVIS rechargeait alÃ©atoirement pendant l'usage
- CoÃ¯ncidait souvent avec des actions prÃ©cises (switch voix Edge, slider EQ
  pendant lecture audio, switch de mode chat)
- Marc avait initialement pensÃ© que la cause Ã©tait dans ces actions
- **En rÃ©alitÃ©** : coÃ¯ncidence visuelle, le dÃ©clencheur Ã©tait autre

### Diagnostic chronologique (post-mortem 2026-05-23)

| Heure | Ã‰vÃ©nement | DÃ©tail |
|---|---|---|
| 14:07 | 1er rapport | Marc : lecture audio + slider EQ â†’ UI sautÃ©e |
| 14:30 | 2e occurrence | Marc : changement param audio EQ |
| 14:33 | HypothÃ¨se 1 (incomplÃ¨te) | Fix idempotence `_log.addHandler` + `start_all()` (commit `06e4297`). RÃ©sout les **doublons de log** et l'interfÃ©rence threads boot, mais pas le reload UI lui-mÃªme. |
| 14:46 | Instrumentation passive | Commit `30462b1` : JS-DIAG v1 (hooks `error` + `unhandledrejection` + monkey-patch `location.reload`) |
| 14:50 | Ã‰chec monkey-patch | Log montre : `reload monkey-patch failed: Cannot redefine property: reload`. Les navigateurs modernes refusent `Object.defineProperty` sur `location.reload`. |
| 14:51:37 | 3e reproduction | Marc : Â« UI rebooted Â». Log JS-DIAG montre **2 `jsdiag.ready` espacÃ©es 93s** = **vrai reload page** confirmÃ©. AUCUN `window.error` ni `unhandledrejection` capturÃ© â†’ c'est un `location.reload()` JS direct. |
| 14:53 | JS-DIAG v2 | Commit `da7384d` : bascule sur `beforeunload` event (capte toute navigation sortante avec stack trace) |
| 14:56:17 | **Capture stack !** | `[JS-DIAG] kind=beforeunload | src=Error: ... at boot_init.js:870:55` |
| 15:00 | **Cause racine identifiÃ©e** | `boot_init.js:870` = `if (d.boot_id && d.boot_id !== stored) location.reload();` dans `_pollBootId`. Le code JS dÃ©tectait Ã  juste titre un nouveau `boot_id` cÃ´tÃ© serveur. â†’ **Le serveur rÃ©gÃ©nÃ©rait son `_JARVIS_BOOT_ID`** |
| 15:01 | Investigation Python | `_JARVIS_BOOT_ID = str(int(time.time()))` est au top-level de `jarvis.py`. RÃ©gÃ©nÃ©rÃ© Ã  chaque rÃ©-exÃ©cution du top-level. |
| 15:02 | **MÃ©canisme compris** | `blueprints/soc.py` fait `from jarvis import _CODE_REASONING_MODE, _jarvis_mode, MODEL, OLLAMA_URL` **dans des fonctions thread** (lignes 1149/1153/1154/1463 â€” pattern lazy import). Python ne voit pas `jarvis` dans `sys.modules` (qui tournait en `__main__`), donc il importe `jarvis.py` UNE 2Ã¨me fois comme module â†’ top-level rÃ©-exÃ©cutÃ© â†’ `_JARVIS_BOOT_ID` rÃ©gÃ©nÃ©rÃ© â†’ `_pollBootId` dÃ©tecte la diffÃ©rence â†’ reload. **UNE fois par session** (sys.modules cache aprÃ¨s) â†’ d'oÃ¹ le caractÃ¨re alÃ©atoire et non corrÃ©lÃ© aux actions utilisateur. |
| 15:02 | Palliatif | Commit `8e3d518` : `_JARVIS_BOOT_ID` mis en cache `os.environ` (partagÃ© entre tous les imports du mÃªme process Python). SymptÃ´me neutralisÃ©. |
| 15:10 | Validation Marc | Test stress : switch modes + EQ + voix â†’ Â« l'UI ne bronche pas top Â» |
| 17:00 | **Fix racine** | Commit `709049f` : DI explicite via `init_soc(get_jarvis_mode, code_reasoning_mode, get_model, ollama_url)`. Les 4 `from jarvis import` Ã©liminÃ©s. Le palliatif `8e3d518` reste en place par sÃ©curitÃ© mais n'est plus nÃ©cessaire. |

### Pourquoi le bug paraissait alÃ©atoire

- Le dÃ©clencheur n'Ã©tait **pas** une action Marc (slider EQ, switch mode, voix)
- Le dÃ©clencheur Ã©tait le **PREMIER appel** d'une fonction thread `_soc_llm_call`
  (auto-engine SOC) qui faisait `from jarvis import` â€” moment imprÃ©visible
- Une seule fois par session (aprÃ¨s c'est en cache `sys.modules`)
- D'oÃ¹ l'apparente non-reproductibilitÃ© sur action prÃ©cise

### LeÃ§ons apprises

1. **`from X import` dans une fonction n'est pas "gratuit"** quand `X` tourne
   en `__main__` : Python rÃ©-importe `X` comme module et rÃ©-exÃ©cute son top-level.
2. **Tout side-effect au top-level d'un module potentiellement rÃ©-importÃ©**
   (handler, thread, timestamp, init) doit Ãªtre protÃ©gÃ© par idempotence.
3. **L'instrumentation passive paie** : sans JS-DIAG v2 capturant la stack
   `boot_init.js:870`, on aurait continuÃ© Ã  chercher dans les sliders.
4. **Garder le palliatif mÃªme aprÃ¨s le fix racine** : double sÃ©curitÃ©.

### Outils laissÃ©s actifs (dÃ©cision Marc 2026-05-23)

Voir [`../05-EXPLOITATION/05-03-OBSERVABILITE-LOGS.md`](../05-EXPLOITATION/05-03-OBSERVABILITE-LOGS.md).

- `scripts/jarvis.log` persistant (5 MB Ã— 7)
- JS-DIAG v2 (beforeunload + visibilitychange + window.error + unhandledrejection)
- Try/except global `/api/tts` enrichi (voix + moteur au crash)
- 6 garde-fous idempotence

---

## 2026-05-23 â€” InterfÃ©rence pytest â†” JARVIS prod

### SymptÃ´mes

- Pendant la session de refactor, des comportements bizarres chez Marc
  (audio Kokoro synthÃ©tise "JARVIS opÃ©rationnel." sans raison, VRAM swap
  inattendu, modÃ¨les Ollama dÃ©chargÃ©s)
- CoÃ¯ncidait avec les commandes `pytest` lancÃ©es par Claude

### Cause racine

5 fichiers `test_jarvis_*.py` font `import jarvis` au chargement. Chaque
`pytest tests/python/` dÃ©marre donc **les 10 threads boot** (`kokoro_preload`,
`boot_vram_cleanup`, `soc_model_prewarm`, `kokoro_prewarm`, ...) dans le
process pytest, en parallÃ¨le de l'instance JARVIS de Marc.

### Fix

`tests/python/conftest.py` pose `os.environ.setdefault("JARVIS_SKIP_BOOT_THREADS", "1")`
**AVANT** tout import (commit `be4dc8b`). `bootstrap/threads.start_all()`
retourne immÃ©diatement avec log `[BOOTSTRAP] ... SHUNTÃ‰S`.

### LeÃ§ons apprises

- Les tests qui `import` une app Flask au chargement dÃ©clenchent les
  side-effects du boot. Il faut un mÃ©canisme de **bypass via env var** dÃ¨s le
  conftest.

---

## 2026-05-23 â€” Drift phi4 SOC : recommandations hallucinÃ©es malgrÃ© system prompt strict

### SymptÃ´mes observÃ©s

Marc soumet Ã  Claude une analyse SOC produite par JARVIS mode SOC (phi4:14b)
qui recommandait 4 actions correctives sur l'infrastructure :

1. Bannir l'IP `177.141.47.123` via CrowdSec
2. RÃ©activer ModSec sur les serveurs Apache (qualifiÃ© de Â« dÃ©sactivÃ© Â»)
3. VÃ©rifier AppArmor (qualifiÃ© d'Â« inaccessible Â»)
4. Appliquer Â« 17 mises Ã  jour de sÃ©curitÃ© en attente Â»

### VÃ©rifications croisÃ©es en live (SSH read-only sur clt, pa85, srv-nginx)

| Recommandation phi4 | RÃ©alitÃ© vÃ©rifiÃ©e | Verdict |
|---|---|---|
| Bannir 177.141.47.123 | `cscli decisions list -i 177.141.47.123` â†’ **dÃ©jÃ  bannie** (`fail2ban-nginx-cve`, expire ~24h) | âŒ phi4 a violÃ© sa propre RÃˆGLE ABSOLUE Â« IPs DÃ‰JÃ€ NEUTRALISÃ‰ES Â» |
| ModSec dÃ©sactivÃ© Apache | `apache2ctl -M` â†’ `security2_module (shared)` actif sur clt **ET** pa85 | âŒ Hallucination pure |
| AppArmor inaccessible | `aa-status` â†’ 127 profils chargÃ©s / 7 enforce (clt) Â· 106 / 7 (pa85) | âŒ Hallucination pure |
| 17 updates sÃ©curitÃ© | `apt list --upgradable` â†’ **0** sur clt, pa85, srv-nginx | âŒ Chiffre inventÃ© |

**4/4 recommandations hallucinÃ©es.** L'attaque rÃ©elle (`/cgi-bin/%2e%2e/.../bin/sh` payload `libredtail-http` depuis 177.141.47.123) avait Ã©tÃ© dÃ©tectÃ©e par Suricata, escaladÃ©e par fail2ban-nginx-cve et bannie automatiquement par CrowdSec **sans intervention humaine** â€” la chaÃ®ne dÃ©fensive a fonctionnÃ©.

### Cause racine

phi4 a produit une **Â« checklist gÃ©nÃ©rique SOC Â»** issue de ses connaissances de prÃ©-entraÃ®nement plutÃ´t que de s'appuyer sur l'Ã©tat live qui lui Ã©tait injectÃ© dans le contexte SOC (snapshot `monitoring.json`).

Le system prompt contenait dÃ©jÃ  :
- `RÃˆGLE ABSOLUE â€” FIDÃ‰LITÃ‰ SOC` (utiliser uniquement les donnÃ©es du contexte)
- `RÃˆGLE ABSOLUE â€” IPs DÃ‰JÃ€ NEUTRALISÃ‰ES` (ne jamais re-bannir)
- `RÃˆGLE ABSOLUE â€” RECOMMANDATION DE BAN PROPORTIONNÃ‰E`

Mais ces rÃ¨gles Ã©taient **toutes ciblÃ©es sur les recommandations de ban d'IP**. Aucune rÃ¨gle ne couvrait explicitement les recommandations sur **les services (ModSec, AppArmor, WAF) ou les mises Ã  jour systÃ¨me**. Le modÃ¨le a comblÃ© le silence par une checklist gÃ©nÃ©rique.

### Fix

Commit `<next>` : alignement du prompt SOC dans `scripts/jarvis_prompt_profiles.json` profil `Phi4 â€” Analyse AvancÃ©e` :

1. **GÃ©nÃ©ralisation de la rÃ¨gle FIDÃ‰LITÃ‰ SOC** : Ã©tendue des IPs/scores aux **services, configurations, mises Ã  jour** â€” interdiction d'extrapoler l'Ã©tat d'un service non mentionnÃ© dans le contexte.
2. **Nouvelle RÃˆGLE ABSOLUE â€” ANTI-CHECKLIST GÃ‰NÃ‰RIQUE** : interdit explicitement les recommandations issues de connaissances gÃ©nÃ©rales (Â« rÃ©activer le WAF Â», Â« appliquer les mises Ã  jour Â») sans support d'une donnÃ©e prÃ©sente dans le contexte SOC injectÃ©.
3. **Renforcement de la rÃ¨gle IPs DÃ‰JÃ€ NEUTRALISÃ‰ES** : ajout d'une Ã©tape de vÃ©rification **OBLIGATOIRE** avant toute recommandation de ban (Â« Si tu envisages de recommander un ban, tu DOIS d'abord vÃ©rifier que l'IP n'apparaÃ®t pas dans la section "IPs DÃ‰JÃ€ BANNIES" du contexte. Cette vÃ©rification doit Ãªtre explicite dans ton raisonnement Â»).

### LeÃ§ons apprises

1. **Un prompt strict ne suffit pas Ã  empÃªcher le drift sur les zones non couvertes explicitement.** Si la rÃ¨gle anti-hallucination ne mentionne que les IPs, le modÃ¨le hallucine sur les services. Il faut une rÃ¨gle gÃ©nÃ©rique (Â« anti-checklist Â») en plus des rÃ¨gles ciblÃ©es.
2. **VÃ©rification croisÃ©e systÃ©matique avant toute action sur la prod.** MÃªme quand phi4 propose une action plausible et conforme Ã  son rÃ´le, valider chaque prÃ©-condition en live (SSH read-only). Ce cas est l'illustration parfaite de pourquoi la rÃ¨gle ABSOLUE `feedback_jarvis_no_regression` (Marc) existe.
3. **L'auto-engine SOC a dÃ©jÃ  fait son travail.** Les recommandations conversationnelles de phi4 doivent Ãªtre pensÃ©es comme **un complÃ©ment** Ã  l'automatisation dÃ©jÃ  en place, pas comme une checklist d'audit indÃ©pendante.
4. **Les recommandations type Â« rÃ©activer le WAF / appliquer les mises Ã  jour Â» sont des smells.** Si phi4 les produit alors que le contexte SOC ne les supporte pas, c'est un drift Ã  corriger cÃ´tÃ© prompt.

### Validation

- Plan d'action proposÃ© Ã  Marc : **rien Ã  faire sur l'infra**, l'attaque a Ã©tÃ© automatiquement neutralisÃ©e.
- Alignement prompt SOC validÃ© par Marc puis appliquÃ© (commit `<next>`).
- Ã€ surveiller : les prochaines analyses SOC phi4 â€” vÃ©rifier que les recommandations restent ancrÃ©es dans le contexte injectÃ©.

---

## 2026-06-05 — MCP orphelin port 5010 à chaque démarrage

### Symptômes observés

- `jarvis.log` affichait `[MCP] kill orphelin` à chaque démarrage JARVIS
- Le port 5010 restait occupé si JARVIS était arrêté par `taskkill /F` ou fermeture fenêtre
- Le sous-processus MCP (`jarvis_mcp_server.py`) survivait à l'arrêt de Flask

### Cause racine

L'enfant `Popen` du MCP n'était nettoyé que dans le `finally` du bloc principal — donc uniquement sur Ctrl+C. Les arrêts forcés (`taskkill /F`, fermeture fenêtre, crash) sautaient le `finally` → MCP orphelin.

### Fix

Nouveau module `proc_guard.py` (commit `02e53dc`) : Job Object Windows avec flag `KILL_ON_JOB_CLOSE`. L'OS tue le MCP quand le process parent (JARVIS/Flask) meurt par n'importe quel moyen. Best-effort : no-op hors Windows, constantes `winnt.h` sans hardcode, filets existants (`finally` + nettoyage orphelin au boot) conservés. **+2 tests pytest** (dont kill-on-close bout-en-bout réel). **Prouvé en prod** : port 5010 libre immédiatement après arrêt.

### Leçons apprises

1. **Les sous-processus `Popen` doivent être rattachés à un Job Object Windows** si on veut garantir leur mort quelle que soit la cause d'arrêt du parent.
2. Le `finally` ne protège que Ctrl+C — insuffisant pour un service démarré depuis un script `.bat`.

---

## 2026-06-09 — RAG : affichage "1 780 970 605 secondes" dans le synoptique Hermès

### Symptômes observés

- Tuile RAG du synoptique Hermès affichait `chargé 1780970605s` au lieu de l'âge réel en secondes
- Le TTL restant affichait `0s / 300s` (cache semblait toujours expiré)
- Le cache était pourtant valide — le RAG fonctionnait correctement

### Cause racine

Mismatch entre deux fonctions utilisant deux horloges différentes :
- `_rag_load()` stockait `ts = time.monotonic()` (~secondes depuis le boot, ~7000s)
- `get_status()` calculait `now = time.time()` (timestamp unix ~1 780 000 000s)
- `age = int(now - ts) = 1 780 000 000 - 7000 ≈ 1 780 000 000` → affiché comme "1,78 milliard secondes"

### Fix

`rag/engine.py` : `get_status()` corrigé pour utiliser `time.monotonic()` (commit Hermès session 2026-06-09). Cohérence garantie — les deux fonctions utilisent désormais la même horloge.

### Leçons apprises

1. **Ne jamais mélanger `time.time()` et `time.monotonic()`** dans des calculs de durée inter-fonctions. Si une fonction stocke un timestamp monotonic, toutes les fonctions qui le consomment doivent utiliser monotonic.
2. **Tester le synoptique après chaque restart** — l'âge du cache est la première chose visible dans Hermès.

---

## Template pour futurs incidents

```markdown
## YYYY-MM-DD â€” Titre court de l'incident

### SymptÃ´mes observÃ©s
- ...

### Diagnostic chronologique
| Heure | Ã‰vÃ©nement | DÃ©tail |
|---|---|---|

### Cause racine
...

### Fix
- Commit `HASH` : description
- Fichiers touchÃ©s : ...

### LeÃ§ons apprises
1. ...
2. ...

### Validation
- ...
```

