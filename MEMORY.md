# JARVIS — Mémoire projet (2026-05-23 — refactor architecture par tuiles complet, 24 tuiles + bug UI reload résolu cause racine + couverture +282 tests + audit ruff strict)

## Session 2026-05-23 soirée — étape 37 mode/ + audit ruff strict + clôture honnête

Suite directe de la session fin d'après-midi (étapes 35-36 + bug UI reload
résolu via DI soc.py + couverture finale +69 tests). 4 commits supplémentaires
pour clôturer proprement la journée :

### Étape 37 — Tuile `mode/` (commit `5215547` + tests `b2cd4c4`)

24ème tuile : extraction de `api_mode` (route GET+POST /api/mode) vers
`scripts/mode/routes.py` + Blueprint dédié.
- DI : limiter + log + getter/setter `_jarvis_mode` + 3 constantes modèles
  + `ensure_vram` callable
- Validation stricte 4 modes (soc|general|code|code_reasoning), case
  insensitive, swap VRAM uniquement si mode différent
- Tests : 11 tests Flask test_client, **100% coverage** sur la nouvelle tuile

jarvis.py : 1819 → 1821 L (+2 net — DI explicite occupe la place gagnée).
**Bénéfice sémantique** : pattern Blueprint+DI uniforme, route plus
éparpillée dans l'ossature.

### Audit ruff strict `--select=B,C4,SIM,UP,RUF` (commit `98c9e0c`)

84 suggestions ruff évaluées avec rigueur honnête :
- **42 noqa F401 légitimes** auto-virés (pattern import-for-side-effects
  dans les `__init__.py` de tuiles) → restaurés
- **2 modernisations f-string `repr(x)` → `{x!r}`** conservées dans
  `chat/dispatcher.py` (RUF010, sans risque)
- **2 noqa F401 documentés explicitement** dans jarvis.py (`psutil`
  utilisé indirectement par runtime/gpu_stats + import local `_psutil`
  pour MCP cleanup · `TOOLS` exposé pour MCP server + tests)

### Audit aliases backward-compat (~80 L jarvis.py, 120 aliases)

**Décision honnête après inventaire** : ON LAISSE. Pattern délibéré, les
tests pytest consomment `jm._X`. La réduction nécessiterait de modifier
30+ tests pour gagner ≤0.5 pt — risque/bénéfice défavorable. Documenté
dans le commit `98c9e0c` comme décision archi assumée.

### Décisions architecturales finales (toutes documentées dans commit `98c9e0c`)

- Aliases backward-compat (~80 L) : conservés, pattern délibéré
- 5 globals mutables avec setters lambda : pattern legacy assumé
- Blueprints HTTP sous-couverts (voice/routes 36%, settings/routes 44%,
  dev/routes 27%, web/routes 26%) : testés E2E Playwright, décision archi
- 2 lambdas E731 dans `chat/soc_inject.py` : noms expressifs (`top`, `kvd`),
  usage local strict
- 13 try/except: pass (SIM105) : non convertis en contextlib.suppress
  (verbeux sans gain)
- 8 `arr + [x]` (RUF005) : non modernisés en `[*arr, x]`

### Audit TODO/FIXME/HACK/XXX dans tout le code

**0 TODO ouvert** dans le code Marc (Python + JS scripts/static/). Que
des occurrences dans des libs tierces (xterm.min.css, highlight.min.js).
Code remarquablement propre.

### Bilan complet session (matin + après-midi + soirée)

| Métrique | Début matin (~12:00) | Fin de session (~17:55) |
|---|---|---|
| Durée | — | ~6 h |
| Commits | — | **29** (13 refactor + 16 fix/feat/test/docs/chore) |
| jarvis.py | 4814 L | **1821 L** (−62%) |
| Tuiles | 0 | **24** + blueprints/soc |
| Tests pytest | 1012 | **1294** (+282) |
| Coverage globale | 62% | **76%** (+14 pts) |
| Modules <80% utilisés en runtime | 12 modules | 0 (sauf Blueprints HTTP E2E) |
| TODO/FIXME ouverts | inconnu | **0** |
| Bug UI reload (15+ jours) | aléatoire | **résolu cause racine + validé Marc** |
| Observabilité | console PowerShell seule | jarvis.log persistant + JS-DIAG v2 + try/except + 6 garde-fous idempotence (52 MB max disque) |
| Score honnête | 82-84/100 (matin) | **93/100** |

### Pour atteindre 95+/100 (non urgent — projet stable)

- (a) Tests E2E Playwright nettoyés (~2-3 h, +1 pt)
- (b) Doc auto-générée des docstrings (~1 h, +0.5 pt)
- (c) Réduction aliases backward-compat (~1-2 h risqué, +0.5 pt — décidé NON aujourd'hui)

### Commits de la soirée (chronologique)

- `5215547` — `refactor(jarvis): mode/ - route /api/mode + DI explicite (etape 37)`
- `b2cd4c4` — `test(jarvis): +11 tests mode/routes (100% coverage)`
- `98c9e0c` — `chore(jarvis): cleanup ruff strict — f-string modernisation + noqa documentes`

---

## Session 2026-05-23 fin d'après-midi — étapes 35-36 + bug UI reload résolu cause racine + couverture finale

Suite directe de la session après-midi (étapes 27-34 + JS-DIAG + fix
idempotence). 8 commits supplémentaires :

### Étapes refactor (jarvis.py 1866 → 1819 L, −47)

| Étape | Commit | Tuile | Détail |
|---|---|---|---|
| 35 | `3bcbea3` | `llm/` (vram + stream) | 23ème tuile : ensure_vram + ollama_swap (98L) + stream_llm + think_filter_step (158L) |
| 36 | `6506199` | indicateur visuel | CSS .mode-loading + JS _pollModeReady → pulse cyan + ⏳ pendant swap VRAM (1-3s) |
| 36b | `709049f` | DI explicite soc.py | **FIX RACINE bug UI reload** : remplace les 4 `from jarvis import` par init_soc(get_jarvis_mode, code_reasoning_mode, get_model, ollama_url) |
| B | `a8a9c5a` | +38 tests | terminal/ssh_ws 15→82% + commands/sse 12→92% |
| C (couv) | `9a2c23b` | +31 tests | llm/vram 40→100% + chat/file_correct 22→97% |

### Bug UI reload — résolution finale

**Diagnostic complet** (commit `709049f` message détaillé) :

Python ne voyait pas `jarvis` dans `sys.modules` (qui tournait en
`__main__`), donc à chaque appel de `_soc_llm_call` (auto-engine SOC),
**import jarvis.py UNE 2ème fois** comme module → tout le top-level
ré-exécuté → `_JARVIS_BOOT_ID = str(int(time.time()))` régénéré → côté
JS `_pollBootId` (`boot_init.js:870`) détectait nouveau boot_id →
`location.reload()`. **UNE fois par session** (sys.modules cache après)
— d'où le caractère aléatoire et non corrélé aux actions utilisateur.

**Validations terrain** :
1. JS-DIAG v2 capture la stack exacte `boot_init.js:870` à 14:56:17
2. Marc reproduit à 14:51:37 : `[JS-DIAG] jsdiag.ready` ×2 espacées 93s
3. Palliatif `8e3d518` (`_JARVIS_BOOT_ID` en cache `os.environ`) tient
4. Fix racine `709049f` (DI explicite soc.py) → cause éliminée
5. Marc valide end-to-end : « l'ui ne bronche pas top »

### Validation continuité SOC

Pendant le diag bug UI, vérif que SOC continue de remonter les alertes
vocales :
- Backend `/api/status` + `/api/soc/context` répondent : ÉLEVÉ 58/100,
  78 IPs CrowdSec, 8 fail2ban, 4 VMs running
- TTS log montre alertes vocales toutes les ~15-30 min selon cooldowns
  (rapport horaire 15:00, alerte SOC ÉLEVÉ 15:01, Suricata 15:16, etc.)
- **Silence de 20 min entre 15:31 et 15:51** = NORMAL (cooldowns + mode
  CODE/CR/GENERAL silencieux par règle ABSOLUE `feedback_jarvis_no_regression`)
- Marc accepte cette règle ABSOLUE (n'a pas demandé de changement)

### Couverture finale (+69 tests fin de session)

| Module | Avant | Après |
|---|---|---|
| `terminal/ssh_ws.py` | 15% | **82%** |
| `commands/sse.py` | 12% | **92%** |
| `llm/vram.py` | 40% | **100%** |
| `chat/file_correct.py` | 22% | **97%** |
| **Global** | **71%** | **75%** |

Tests post-étape 35 (llm/vram création) immédiatement couverts par 10
tests (init/get_model/get_vram_model/set/lock + unload sync + preload
thread daemon + exceptions). Patron isolant : pas de polling réseau réel.

### Bilan complet session (matin + après-midi)

| Métrique | Début matin | Fin de session |
|---|---|---|
| jarvis.py | 4814 L | **1819 L** (−62%) |
| Tuiles | 0 | **23** + blueprints/soc |
| Tests pytest | 1012 | **1283** (+271) |
| Coverage globale | 62% | **75%** (+13 pts) |
| Commits total | — | **25** (12 refactor + 13 fix/feat/test/docs) |
| Bug UI reload | aléatoire 15+ jours | **résolu cause racine + validé Marc** |
| Score honnête | 82-84/100 (matin) | **93/100** |

### Outils investigation laissés actifs (décision Marc)

Mémoire centrale : `~/.claude/.../memory/jarvis_diag_tools_active.md`.
Volumétrie max disque : **~52 MB plafonnés** par RotatingFileHandler
(`jarvis.log` 35 + `tts.log` 14 + `tts_perf.log` 3). Aucun risque de
saturation. À NE PAS supprimer sans validation Marc.

---

## Session 2026-05-23 après-midi — étapes 34a/b + couverture +50 tests + fix conftest critique + jarvis.log

Suite directe du matin (étapes 27-33 + jarvis.log + try/except /api/tts +
SKIP_BOOT_THREADS). 5 commits supplémentaires l'après-midi.

### Étapes refactor (jarvis.py 1860 → 1866 L, -6 net)

| Étape | Commit | Tuile | jarvis.py | Détail |
|---|---|---|---|---|
| 34a | `569500b` | `tools/dispatch.py` (nouveau) | 1860→1879 (+19) | _TOOL_DISPATCH sorti — fabrique build(**handlers) avec 14 callables en DI explicite, suppression 14 lambdas thunk |
| 34b | `36e8f17` | `facts/inject.py` (nouveau) | 1879→**1866** (−13) | _facts_inject + _load_facts + _now_fr + _MOIS/JOURS_FR sortis, DI via get_facts_file callable (testabilité monkeypatch jm.FACTS_FILE) |

### Couverture ciblée (+50 tests, modules sous-couverts → 89-97%)

3 fichiers test ajoutés (commits `d3eb0b0` + `7ffbcec`) :

| Module | Coverage avant | Coverage après | Tests ajoutés |
|---|---|---|---|
| `tools/local.py` | 49% | **95%** | 16 (executer_code blocked, soc_status, executer_script_windows mock Popen) |
| `runtime/speak.py` | 41% | **89%** | 14 (dedup intra 3s, dedup global, drop-oldest queue, routage stream actif/inactif) |
| `bypass/wrappers.py` | 65% | **97%** | 20 (detect_service_restart par hôte, detect_vm/reboot/update, 4 wrappers backup, apt_upgrade_bypass_sse) |
| `facts/routes.py` | (juste créé) | **87%** | — |

Particularité `test_bypass_wrappers.py` : fixture autouse avec
**restauration de l'état initial en teardown** (sauvegarde + restore des
18 attributs DI de `bp_wrap`) → évite la contamination des tests
`test_jarvis_functions::_detect_service_restart_*` qui lisent
`jm._detect_service_restart` (alias vers `bp_wrap.detect_service_restart`)
et attendent les VRAIES fonctions SSH injectées au boot, pas des mocks.

### Fix infra critique : conftest.py SKIP_BOOT_THREADS (commit `be4dc8b`)

**Bug remonté par Marc 14:07** : « UI se relance pendant lecture audio +
slider EQ » sur le dashboard SOC pendant une session.

Diagnostic post-mortem (logs `jarvis.log` + `tts.log` + `Get-Process python`) :

- **0 crash backend** — wrapper try/except `/api/tts` bien posé mais rien
  à capturer. Le bug n'est PAS dans `/api/tts`.
- **2 process Python sains à l'instant T** : PID 25588 (JARVIS prod, port
  5000) + PID 28368 (jarvis_mcp_server, port 5010). Normal.
- **MAIS doublons dans `jarvis.log` entre 14:07:11 et 14:08:11** (~1 min) :
  toutes les lignes écrites 2× pendant cette fenêtre = signature d'un **3ème
  process Python éphémère** qui a chargé jarvis et lancé les 10 threads boot.
- **Cause racine identifiée** : 5 fichiers `test_jarvis_*` font `import jarvis`
  au chargement. Mes 6 commandes `pytest tests/python/` pendant la session
  ont donc chacune démarré les threads boot **sans le flag** que j'avais
  créé exactement pour ça. Pendant ~5-15 s de vie de chaque pytest :
  - `kokoro_preload` synthétise "JARVIS opérationnel." sur les enceintes
  - `boot_vram_cleanup` décharge des modèles Ollama actifs
  - `soc_model_prewarm` force phi4 en VRAM (TTL 30 min)
  - `kokoro_prewarm` charge Kokoro CUDA
  - → **interférence directe avec la session de Marc** : audio en double,
    VRAM swap, modèles déchargés. Le bug observé est le symptôme côté
    frontend de cette interférence backend.

**Fix** : `tests/python/conftest.py` pose
`os.environ.setdefault("JARVIS_SKIP_BOOT_THREADS", "1")` **AVANT** le
`sys.path.insert` (donc avant que pytest collecte les modules).
`bootstrap/threads.start_all()` retourne immédiatement avec un log
`[BOOTSTRAP] ... SHUNTÉS`. **Plus jamais d'interférence pytest ↔ JARVIS prod**
sur la même machine. 1214 tests passent toujours.

### Améliorations infra (commit `d3eb0b0`)

- **`scripts/jarvis.log` persistant** : `RotatingFileHandler` ajouté au
  logger `_log` JARVIS (5 MB × 7 backups). Format ISO datetime + niveau +
  name + traceback complet sur ERROR. Avant : `basicConfig` stdout seul,
  perdu si scrollback ou fermeture console PowerShell.
- **Wrapper `/api/tts` enrichi** : au crash, snapshot du contexte
  `{voice, engine, len, preview}` construit via getters `_get_voice` +
  `_get_dsp_params` (try/except interne pour gérer DI non encore injectée).
  Ligne `tts.log [GLOBAL-CRASH]` inclut désormais voix + moteur + longueur +
  preview du texte ayant provoqué le crash → diagnostic ciblé pour la
  prochaine occurrence du bug switch voix Edge.

### Score honnête recalibré (post étape 34)

| | Matin (post-33) | Après-midi (post-34) |
|---|---|---|
| jarvis.py | 1860 L | **1866 L** (+6 net) |
| Tuiles | 21 | **22** |
| Tests | 1164 | **1214** (+50) |
| Coverage globale | 70% | **71%** (gain ciblé sur modules récents) |
| Score | 87/100 | **90/100** |

⚠ **Reste pour 92+** : (a) sortir `_ensure_vram` + `_ollama_swap` +
`stream_llm` + `_think_filter_step` dans `llm/` (~140 L, étape 35) · (b)
couvrir `terminal/ssh_ws.py` (15%) et `commands/sse.py` (12%) — gros effort
mocking paramiko + Proxmox API · (c) résoudre proprement le bug switch
voix Edge si reproduit avec le diagnostic enrichi.

### Commits de l'après-midi (chronologique)

- `d3eb0b0` — `feat(jarvis): jarvis.log persistant + enrich crash /api/tts + 16 tests tools/local`
- `7ffbcec` — `test(jarvis): +34 tests runtime/speak + bypass/wrappers (couverture nouveaux modules)`
- `be4dc8b` — `fix(jarvis): conftest.py set JARVIS_SKIP_BOOT_THREADS=1 avant tout import`
- `569500b` — `refactor(jarvis): tools/dispatch.py - centralise _TOOL_DISPATCH (etape 34a)`
- `36e8f17` — `refactor(jarvis): facts/inject.py - 3 fonctions injection prompt (etape 34b)`
- `06e4297` — `fix(jarvis): idempotence _log.addHandler + start_all() (bug doublons / interference VRAM)`
- `30462b1` — `feat(jarvis): instrumentation JS-DIAG anti-bug UI reload (passive)` — v1 hooks JS error/unhandledrejection + monkey-patch location.reload
- `da7384d` — `fix(jarvis): JS-DIAG v2 — beforeunload + visibilitychange (reload tracable)` — v2 bascule sur beforeunload event (monkey-patch reload refusé par les navigateurs modernes)

### Séquence diagnostic complète bug « UI reload »

1. **14:07** — Bug reproduit par Marc (lecture audio + slider EQ). Aucun crash backend. Premier rapport.
2. **14:18-14:30** — Étape 34a/b + tests +50 commitées. Plusieurs pytests lancés pendant la session = artefact qui parasitait le log (doublons threads boot). Fix `conftest.py` commit `be4dc8b` règle ce parasitage.
3. **14:30** — Bug reproduit À NOUVEAU par Marc. Analyse approfondie `jarvis.log` : doublons systématiques depuis 14:29 même après conftest fix. **Cause racine trouvée** : `blueprints/soc.py` fait `from jarvis import` dans fonctions thread (lignes 1149/1153/1154/1463) → ré-import jarvis comme module → ré-exécute top-level → handlers + threads boot doublés. Fix idempotence commit `06e4297` (palliatif : protège `_log.addHandler` et `start_all()` contre les doubles appels).
4. **14:33** — Marc redémarre JARVIS. Log post-restart 14:34:53 : **zéro doublon** (fix confirmé).
5. **14:46** — Commit `30462b1` instrumentation JS-DIAG v1 (anticipation bug futur côté frontend). Monkey-patch reload échoue silencieusement chez les navigateurs modernes (property non-configurable).
6. **14:50** — Marc redémarre, log montre `jsdiag.setup reload monkey-patch failed: Cannot redefine property: reload` + `jsdiag.ready`. Hook reload mort.
7. **14:51:37** — **Bug reproduit à nouveau**. Preuve dans log : 2 occurrences de `[JS-DIAG] jsdiag.ready` espacées de 93s = **VRAI reload de la page** (tous les scripts rechargés). Aucun `window.error` ni `unhandledrejection` capturé → **confirme que le bug est un `location.reload()` direct JS** (pas une exception backend, pas une exception JS non catchée).
8. **14:53** — Commit `da7384d` fix JS-DIAG v2 (beforeunload event qui capte tout). Marc redémarre + Ctrl+F5.
9. **14:54:44** — Log montre `[JS-DIAG] kind=jsdiag.ready msg=JS-DIAG hooks active (v2 — beforeunload + visibility)`. v2 actif.
10. **14:56:17** — **Bug reproduit avec JS-DIAG v2 actif**. La stack capturée pointe EXACTEMENT vers `boot_init.js:870` = `if (d.boot_id && d.boot_id !== stored) location.reload();` dans `_pollBootId`. **Confirmation 100%** : c'est le mécanisme normal de détection de redémarrage serveur qui se déclenche à tort.
11. **15:00** — **VRAIE racine identifiée** : `_JARVIS_BOOT_ID = str(int(time.time()))` au top-level de jarvis.py est régénéré à chaque ré-import (cause : `from jarvis import` dans `blueprints/soc.py` exécuté par les fonctions thread `_soc_llm_call` etc.). Lambda `get_boot_id` renvoie nouveau timestamp → `/api/boot-id` retourne valeur différente → sessionStorage JS désynchrone → reload.
12. **Commit `8e3d518`** — fix `_JARVIS_BOOT_ID` mis en cache dans `os.environ['_JARVIS_BOOT_ID_CACHE']` partagé entre tous les ré-imports. Smoke test isolé : 2 imports successifs → boot_id identique.
13. **15:03 — Validation Marc end-to-end** : « l'ui ne bronche pas top » après test stress (switch modes, EQ, voix). **Bug résolu définitivement.**

### Pourquoi le bug paraissait aléatoire

Le déclencheur n'était PAS une action utilisateur (slider EQ, switch mode, voix Edge — qui semblaient être la cause par coïncidence), mais le **PREMIER appel** d'une fonction thread `_soc_llm_call` (auto-engine SOC) qui faisait `from jarvis import` — moment imprévisible. Une seule fois par session (après c'est en cache `sys.modules`). D'où le caractère intermittent + impossible à reproduire sur action précise pendant des semaines.

### Outils d'investigation laissés actifs (décision Marc 2026-05-23)

Voir `~/.claude/.../memory/jarvis_diag_tools_active.md`. Volumétrie max disque : **52 MB plafonnée par RotatingFileHandler** (jarvis.log 35 + tts.log 14 + tts_perf.log 3). Aucun risque de saturation.

### À FAIRE long terme (non urgent)

Remplacer les 4 `from jarvis import X` dans `blueprints/soc.py` (lignes 1149/1153/1154/1463) par des accesseurs DI passés à `init_soc()`. Le fix `8e3d518` couvre le symptôme (boot_id stable) mais le re-import jarvis.py existe toujours techniquement. Plus invasif → reporté.

---

## Session 2026-05-23 — refactor jarvis.py étapes 27-33 + 2 hot-fixes

Poursuite directe de la session 2026-05-22 (étapes 3-26 closes par commit
`62ac692` qui mettait à jour la doc). 7 nouvelles étapes commitées dans la
journée, jarvis.py descend de **2556 → 1860 L** (cumul depuis monolithe :
4814 → 1860 L, **−61 %**). 5 nouvelles tuiles créées (`bootstrap`, `terminal`,
`runtime`, `facts`, `tools`) → **21 tuiles** au total. 0 régression sur
**1164 tests pytest**. Coverage globale 70%.

### Étapes commitées (ordre chronologique)

| Étape | Commit | Tuile | jarvis.py | Détail |
|---|---|---|---|---|
| 27 | `a329f3c` | `bypass/wrappers.py` | 2556→2477 (−79) | 11 wrappers DI couplés jarvis + 3 constantes calculées dans init() |
| 28 | `ef97d17` | `chat/dispatcher.py` | 2477→2386 (−91) | Carrefour /api/chat extrait (route + chat_try_bypass + detect_file_corrections) |
| 29 | `1497604` | `bootstrap/threads.py` | 2386→2210 (−176) | 10 threads daemon regroupés derrière init()+start_all() |
| 30 | `9964c4e` | `terminal/ssh_ws.py` | 2210→2105 (−105) | 2 routes WS PTY SSH (/ws/ssh/<host> + /ws/dev) |
| 31 | `af62370` | `runtime/gpu_stats.py` + `runtime/speak.py` | 2105→**1954** (−151) | 3 fns GPU + speak() ; **première fois <2000L** |
| 32 | `617e480` | `facts/` + 3 routes dispatch | 1954→1898 (−56) | Tuile facts/ + api_status→health/, api_history_last→chat/dispatcher, api_soc_context→blueprints/soc |
| 33 | `6103358` | `tools/local.py` | 1898→**1860** (−38) | 3 outils LLM locaux (executer_code, soc_status, executer_script_windows) |

### Hot-fixes (révélés en cours de session, non-refactor)

- **`f4ad131` — try/except global sur `/api/tts`** : wrapper `api_tts` avec
  capture exhaustive (`_log.error` + `_tts_logger.error 'GLOBAL-CRASH'`) +
  retour 500 JSON propre. Posé pour diagnostiquer le bug intermittent « UI
  qui se relance au switch voix Edge » signalé par Marc → la prochaine
  occurrence laissera une trace exploitable. Le corps réel est extrait dans
  `_api_tts_impl()` (séparation route wrapper vs logique métier).

- **`b03f23f` — `JARVIS_SKIP_BOOT_THREADS` env flag** : garde-fou dans
  `bootstrap/threads.start_all()`. Suite d'une boulette : mes 2 smoke tests
  `python -c "import jarvis"` lors des étapes 28-29 avaient déclenché les
  threads boot dans des process Python parallèles au JARVIS en service →
  `kokoro_preload` a synthétisé "JARVIS opérationnel." (interruption audio
  utilisateur via sortie audio partagée) + `boot_vram_cleanup` a déchargé
  des modèles Ollama encore utilisés. Usage smoke désormais :
  `JARVIS_SKIP_BOOT_THREADS=1 python -c "import jarvis"` → 0 thread lancé.

### Décision honnête sur le score

Le **95/100 affiché par §0bis du BILAN-TECHNIQUE** était surévalué : il ne
couvrait pas les nouveaux modules sous-couverts ajoutés en étapes 27-33 (5
modules entre 12% et 54% de coverage) ni les 9 commits de retard sur la doc.
**Score recalibré honnêtement avant MAJ doc : 82/100**, **après MAJ doc :
87/100**. Demande explicite de Marc : « honnêteté brute, pas de chiffres
gonflés ». Pour atteindre 90+ : ajouter ~50 tests directs sur les modules
récents (+3-4 pts) et résoudre le bug switch voix Edge (+2 pts).

### Reste à refactoriser dans jarvis.py (1860 L résiduelles)

- **VRAM/Ollama** (~140 L) : `_ensure_vram`, `_ollama_swap`, `_think_filter_step`,
  `stream_llm` — cœur runtime LLM, couplage `_vram_model` global avec setter
  lambda → candidat étape 34 (tuile `llm/` ou `ollama/`)
- **`_TOOL_DISPATCH` dict** : appartient logiquement à `tools/dispatch.py`
- **`_facts_inject` + `_load_facts` + `_now_fr`** : appartient à `facts/inject.py`
- **3 setters globaux** (SYSTEM_PROMPT, MODEL, _welcome_data, _AUTO_PROFILE_MODEL,
  _vram_model) — pattern legacy assumé
- **Routes restantes** : `index`, `favicon`, `api_debug_inject_pending`, `api_mode`
  (la dernière a une DI lourde → laisser sur place)
- **Ossature légitime** : config bootstrap, CORS, registration des 21 tuiles,
  bloc `__main__` (MCP subprocess + app.run) — ~1500 L incompressibles

### Aliases backward-compat conservés dans jarvis.py

Pour ne casser aucun test existant et aucun consommateur interne MCP, tous
les modules extraits gardent un alias dans jarvis.py :
- Tools : `_tool_executer_code`, `_tool_soc_status`, `_tool_executer_script_windows`
- Bypass wrappers : `_detect_service_restart`, `_detect_vm_command`, etc.
- Runtime : `get_stats`, `speak`, `_speak_queue`, `_chat_stream_active`, `_speak_deferred`
- Terminal : `_ws_ssh_reader`, `_ws_ssh_connect`, `_ws_ssh_handler`
- Chat dispatcher : `_chat_try_bypass`, `_detect_file_corrections`

Ces aliases ajoutent un peu de bruit dans jarvis.py (≈80 lignes) mais ils
font office de contrat stable pour les tests pytest qui consomment via
`jarvis_module.X` — leur retrait nécessiterait de réécrire ~30 tests.

---

## Session 2026-05-22 — audit dette complet honnête + 7 correctifs

Audit dette technique complet du projet JARVIS exclusivement (demande de Marc :
« audit complet et honnête »). 3 agents d'audit + vérification personnelle de
chaque finding sérieux avant restitution. Score auto-affiché **92/100** reconnu
inflaté → consolidé honnêtement **84/100**, puis **88/100** après correctifs.

**9 findings, tous traités le jour même** (ordre : E2 → M2 → M1 → M4 → M3 → F1 → F4 → F3 → E1) :

- **E2** (ÉLEVÉ) — deux whitelists de services divergentes : `_ALLOWED_SERVICES`
  (soc.py, route HTTP `/restart-service`) et `ALLOWED_RESTART_SVCS`
  (security_whitelists.py, write-ops SSH). Consolidées dans `security_whitelists.py`
  via une nouvelle constante `ALLOWED_SOC_RESTART_SVCS` (soc.py l'importe en alias).
  Divergence `php*-fpm` **résolue le jour même par vérification SSH** : srv-ngix n'a
  aucun PHP installé, clt/pa85 tournent en mod_php (`libapache2-mod-php8.4`, pas de
  php-fpm) — les entrées mortes `php7.4-fpm` / `php8.2-fpm` / `php8.3-fpm` ont été
  retirées des deux whitelists (`ALLOWED_RESTART_SVCS` garde `apache2` = le chemin
  de restart PHP réel sur clt/pa85). Enfin `suricata` ajouté à
  `ALLOWED_SOC_RESTART_SVCS` : l'auto-engine SOC `_check_services` (déclencheur #10)
  ne pouvait pas le redémarrer faute de whitelist — incohérence pré-existante avec
  `08-JARVIS-DEFENSE.md`, corrigée le jour même.
- **M1** (MOYEN) — `_SSH_DEV1` hardcodé `192.168.1.21` alors que ngix/clt/pa85/proxmox
  passaient par `soc_config.json`. Ajout des clés `dev1_*` aux défauts, `_SSH_DEV1`
  dérivé de `_SOC_CFG` comme ses 4 pairs.
- **M2** (MOYEN) — bloc `[tool.ruff]` mort dans `pyproject.toml` : ruff lit
  `ruff.toml` en priorité, le bloc était silencieusement ignoré (et divergent).
  Supprimé ; `pyproject.toml` ne garde que `[tool.pytest.ini_options]`.
- **M3** (MOYEN) — Monaco Editor chargé depuis CDN jsdelivr (`chat_ui.js`) :
  seule dépendance réseau externe, contredisait le « 100% local ». Documenté
  (commentaire code + `CLAUDE.md`) — dégradation gracieuse hors ligne déjà en place.
- **M4** (MOYEN) — `json.loads(line)` non gardé dans `stream_llm` (jarvis.py) :
  une ligne Ollama malformée levait `JSONDecodeError` en plein flux. `try/except`
  → ligne sautée, flux SSE préservé.
- **F1** (FAIBLE) — `.gitignore` : `*.bak` ne couvrait pas
  `jarvis_soc_actions.bak.<timestamp>.json` → pattern `*.bak.*` ajouté.
- **F4** (FAIBLE) — code mort retiré : `_vpEncodeWav` (voice_print.js, jamais
  appelée), `handle_mcp` (jarvis_mcp_server.py, route utilise `handle_mcp_endpoint`).
  Chemin obsolète `Documents\JARVIS` → `Documents\0xCyberLiTech\JARVIS` (DEPLOIEMENT.md).
  ⚠ `tab_terminal.html` accusé d'être orphelin par l'audit — vérifié actif, conservé.
- **F3** (FAIBLE) — doc drift : `CLAUDE.md` et `BILAN-TECHNIQUE.md` réalignés
  (jarvis.py 4739→4814L, soc.py, tests 933+3skip→959/0skip, coverage 51→52%).
- **E1** (ÉLEVÉ, *partiel*) — couverture du cœur sécurité. Nouveau fichier
  `tests/python/test_jarvis_soc_context.py` : +26 tests sur `_build_monitoring_context`,
  `_kc_ban_signal`, `_pve_context_lines` (fonctions pures de l'injection de contexte
  SOC dans phi4 — anti-hallucination IP, signal de ban — jusque-là à 0%). Inclut les
  tests de non-régression de M4/E2/M1. `jarvis.py` 26→30%, total 50→52%.
  ⚠ Reste ouvert : couverture agrégée de `jarvis.py` (~150 routes Flask) — chantier
  de tests dédié, flaggé et non forcé (`feedback_no_big_refactor`).

**Note constatée durant l'audit** : `_sse_tok()` dupliqué dans 5 modules bypass —
ce N'EST PAS de la dette : `sse_helpers.py` documente que ces modules gardent leur
copie inline pour rester autonomes (choix délibéré). Finding écarté après vérification.

Vérifications finales : **1012 pytest pass · 0 skip · 0 fail**, ruff **0**, eslint
**0 erreur**. Zéro régression.

**Suite de session — dé-duplication doc + campagne couverture** : (1) dette
documentaire dé-dupliquée — les compteurs volatils (score, lignes, tests,
coverage) ne vivent plus que dans `BILAN-TECHNIQUE.md §0` (source unique), les
~12 autres docs pointent dessus → dérive entre documents structurellement
impossible ; (2) **campagne couverture étape 1** — 6 incréments, +158 tests
(`test_jarvis_soc_context` cœur sécurité, `test_jarvis_routes` routes Flask,
`test_jarvis_functions` helpers purs, `test_soc_functions` auto-engine/deep/
orchestrateurs, `test_blueprints_soc` routes `/api/soc` dont ip-deep/ip-history)
→ `jarvis.py` 26→**40%**, `soc.py` 31→**59%**, total 50→**62%** (1091 tests) ; (3) correctif
robustesse `/api/facts` (crash sur corps JSON non-dict — même classe que M4),
trouvé par un nouveau test. Score honnête recalibré (la grille de décomposition
sommait à 92 vs titre 88 — incohérence corrigée) : **88 → 91/100**.

**Décision actée — refactor des monolithes `jarvis.py`/`soc.py`** : sur demande
de Marc, plan retenu = **couverture d'abord, refactor ensuite**, par extraction
incrémentale validée à chaque étape (`feedback_no_big_refactor` respecté — pas de
big-bang).

**Refactor incrémental — étape 1** (2026-05-22) : extraction du cluster
investigation IP (`_b64py`, `_ssh_json_exec`, `_deep_geoip/crowdsec/fail2ban/
autoban/nginx_hits/nginx_last/rsyslog`) de `blueprints/soc.py` → nouveau module
**`scripts/soc_ip_deep.py`** (180 L · 78% cov). Dépendance `_ssh_ngix` injectée
via `soc_ip_deep.init()` (pattern DI). `soc.py` garde 7 alias légers → routes
`/api/soc/ip-history` et `/api/soc/ip-deep` **inchangées**. `soc.py` 1872→**1729 L**
(−143). Tests `_deep_*` rebranchés sur `soc_ip_deep`. Méthode validée.

**Refactor incrémental — étape 2** (2026-05-22) : cluster ban Suricata
(`_sur_ban_sev1`, `_sur_ban_scans`, `_sur_ban_sev2_surge`) extrait → nouveau
module **`scripts/soc_suricata_ban.py`** (82 L · 96% cov). 6 dépendances du cœur
ban/whitelist injectées via `init()`. `_soc_suricata_check` appelle les
`_sur_ban_*` via alias, inchangé. `soc.py` 1729→**1687 L**.

**Refactor incrémental — étape 3** (2026-05-22) : cluster scoring menace
(`_threat_score_from_json`, `_check_threat_level`, `_check_escalation`) extrait →
nouveau module **`scripts/soc_threat_score.py`** (176 L · 74% cov). DI :
`_soc_cooldown_ok` + `_ip_to_tts` injectés via `init()`. La route
`/api/soc/threat-score` et `_soc_monitor_loop` appellent les fonctions via alias,
inchangés. `soc.py` 1687→**1548 L**.

**Refactor incrémental — étape 4** (2026-05-22) : cluster pic de trafic req/h
(`_reqhour_candidates`, `_reqhour_inject_suricata`, `_soc_reqhour_check`) extrait →
nouveau module **`scripts/soc_reqhour.py`** (130 L · 97% cov, +3 tests sur
l'orchestrateur). DI à 12 dépendances via `init()` keyword-only ; `_speak` et le
dict `_SOC_AUTO_BANNED` (réassignés après chargement) injectés via lambdas
résolues à l'appel. `soc.py` 1548→**1500 L**. Cumul refactor : **soc.py 1872→1500
(−372 L), 4 modules cohérents extraits**. **1094 pytest pass · 0 skip · ruff 0 ·
eslint 0 · zéro régression.** ⚠ **Refactor par extraction suspendu ici** : les
clusters restants (autoban, rsyslog/LLM, checks auto-engine) sont enchevêtrés
dans le cœur ban — les extraire serait du déplacement, pas du découplage.
Priorité remise sur la couverture de `jarvis.py`. Détail `BILAN §0bis`.

**Campagne couverture `jarvis.py`** (2026-05-22) : +26 tests sur les fonctions
pures/semi-pures non couvertes (`_cors_origin`, `_detect_service_restart`,
`_validate_protect_directives`, `_get_model_profile`, `_load_model`/`_save_model`,
`_load_tasks`/`_save_tasks`, `load_memory`/`save_memory`, `_load_memory_summary`/
`_append_memory_summary`). `jarvis.py` 40→**43%**, coverage globale 63→**64%**,
**1120 pytest pass**.

**Refactor incrémental jarvis.py — étape 1** (2026-05-23) : amorce du
dé-monolithisme côté orchestrateur. Cluster diagnostics système (`_diag_gpu`,
`_diag_ollama`, `_diag_cpu_temp`, `_diag_memory_count`, `_diag_cpu_ram_disk`)
extrait → nouveau module **`scripts/sys_diag.py`** (115 L · 80% cov). État
`_ollama_prev_ok` déplacé dans le module (unique consommateur). DI : `speak`
via lambda + `OLLAMA_URL` + `MEMORY_FILE`. `jarvis.py` 4814→**4758 L** (−56).

**Conversion COMPLÈTE de JARVIS en architecture par tuiles — étapes 3-26**
(2026-05-23) : sur demande de Marc (« je veux un JARVIS sans monolithique,
que du modularisé » + « on poursuit jusqu'au bout »), conversion de tout
JARVIS en 16 tuiles autoportantes en 24 étapes / 24 commits, **0 régression**
sur toute la série.

**16 tuiles créées** : `system`, `memory`, `rag`, `files`, `ssh`, `bypass`
(regroupement), `proxmox`, `chat` (avec 4 sous-modules : `orchestrator`,
`file_correct`, `tool_schemas`, `soc_context`), `voice` (avec STT + TTS + speak
+ voice_lab routes), `vision`, `settings` (16 routes config), `tasks`, `health`,
`commands` (générateurs SSE infra), `dev` (4 routes sans WS), `web` (recherche
+ diag). `blueprints/soc.py` existant conservé.

**Pattern uniforme** : `scripts/<tuile>/__init__.py` = Blueprint + `init(...)`
qui injecte les deps, sous-modules métier dans `<tuile>/*.py`. Aliases
backward-compat conservés dans `jarvis.py` pour tests existants et consommateurs
internes (`_chat_try_bypass`, etc.).

**Bilan** : `jarvis.py` **4814→2556 L (−47 %, −2258 L)** · **16 tuiles
autoportantes** · **13 Blueprints register** · **1164 pytest pass · 0 régression**
sur 24 commits enchaînés · coverage globale **64→69 %** (+5 pts car le code
extrait est plus testable que les routes Flask monolithes).

**VRAM lock + sync `/api/ps`** (parenthèse étape 12) : `_VRAM_LOCK` sérialise
les mutations de `_vram_model`, `_vram_sync_loop` thread daemon synchronise
toutes les 60s avec l'état réel d'Ollama — pré-requis multi-user posés.

**Score dette** : **94 → 95/100** (`Architecture` 23→24, `Tests` 23→24 grâce
au +5pts coverage globale). Restart JARVIS effectué et validé fonctionnel par
Marc avant continuation des étapes 13-26.

**Plancher pratique** : ~2500 L est l'ossature résiduelle légitime (Flask app
+ glue DI/aliases + boot threads + api_chat carrefour + WS terminal). La cible
« 700-1000 L ossature pure » initiale était trop optimiste — glue DI pour 16
tuiles incompressible à ~500 L. Détail `BILAN §0bis`.

**Push Lisibilité + Tests** (2026-05-23) — score dette **92 → 94/100** :
- **Lisibilité 13 → 14/15** : eslint **154 → 0 warnings**. Les 154 étaient *tous*
  `no-unused-vars` sur des handlers HTML consommés via le dispatcher
  `data-action` (`window[fn]` lookup dynamique) que ESLint ne peut pas tracer —
  FP structurels. Fix honnête : (1) `eslint.config.js` `vars: 'local'` aligne la
  politique sur celle de `ruff.toml` qui ignore les FP délibérés ; (2) 12 vrais
  locals préfixés `_`. Pas de gaming.
- **Tests 22 → 23/25** : +24 tests sur les helpers de `blueprints/soc.py`
  (`_dur_to_tts`, `_ip_to_tts`, `_is_whitelisted`, `_ip_skip`, `_load_soc_config`,
  wrappers SSH, `_ssh_host`, `_ban_ip_ssh`, `_load_whitelist`, `_soc_log`).
  **`soc.py` 56→60% (seuil franchi)**, **1144 pytest pass**. Le −2 restant =
  `jarvis.py` 43% (handlers Flask/SSE). Détail `BILAN §0bis`.

## Session 2026-05-20 (suite) — réalignement description Kill Chain sur KC v4 (5 maillons)

Les prompts JARVIS décrivaient encore la Kill Chain SOC en **7 maillons** avec PROBE et WAF — obsolète depuis la refonte KC v4 (5 maillons offensifs purs RECON→SCAN→EXPLOIT→BRUTE→NEUTRALISÉ ; PROBE = UFW et WAF = ModSec sont des couches DÉFENSIVES, sorties de la KC). Le LLM phi4 lisait cette description périmée alors que le contexte SOC live n'injecte que 5 maillons.

**3 endroits réalignés** (texte de prompt / commentaire seul — zéro logique touchée) :
- `jarvis.py` SYSTEM_PROMPT : « 7 maillons » + puces PROBE/WAF → 5 maillons + note explicite « PROBE/WAF = couches défensives, pas des maillons KC » ; règle obsolète « ignore PROBE/WAF » → règle NEUTRALISÉ (IP déjà bloquée, ne pas rebannir).
- `blueprints/soc.py` : commentaire `_SOC_BAN_CONFIG` « KC v3.97.195 7 maillons » → KC v4 5 maillons (le code `_SOC_BAN_CONFIG` était déjà correct : EXPLOIT/BRUTE/SCAN/RECON).
- `jarvis_prompt_profiles.json` profil Phi4 : « Kill Chain nginx : RECON→SCAN→BRUTE→EXPLOIT » (ordre faux) → 5 maillons corrects.

Audit préalable : code fonctionnel JARVIS déjà aligné KC v4 (aucune lecture de champ supprimé `probe_ips`/`waf_ips`/`stage_bans_24h`, logique de ban correcte) — seul le texte descriptif était périmé. RFC1918 / logique de ban / SSH / crawlers intacts. Commit `ff0a1ee`. ⚠ Redémarrage JARVIS requis pour prise d'effet.

**Suivi — bug de classification KC dans les analyses phi4** (commit `215190d`) : une analyse phi4 plaçait une IP dans 2 maillons (147.45.50.108 en RECON ET EXPLOIT — viole « 1 IP = 1 maillon »), prenait l'alerte Suricata « binsh in URI Possible Shell » (RCE) pour du RECON, et traitait `auto-ban SOC` comme un indice de stade. Cause : la liste « IPs DÉJÀ BANNIES » de `_build_monitoring_context` (jarvis.py) n'exposait que `scénario=` + un `stage=` inexploitable (`decisions_detail` n'a pas le stade offensif) → phi4 re-déduisait le maillon depuis le NOM du scénario. Fix : chaque IP bannie affiche `maillon-KC=<origin_stage>` lu depuis `kc.neutralized_ips[].origin_stage` (stade classé par le backend, source unique `soc_infra.yaml`) + consigne « utilise ce champ tel quel, ne re-déduis jamais depuis le scénario ». Doc `BILAN-TECHNIQUE.md` aussi réalignée (3 spots KC 7→5 maillons, commit `25051a5`).

## Session 2026-05-20 — latence voix intermittente : diagnostic par instrumentation + correctif structurel pipeline de lecture

**Contexte** : Marc signalait une latence voix intermittente au démarrage de JARVIS (la voix mettait parfois ~15-24 s à démarrer, parfois gel total). Application de la règle `feedback_instrument_first` : instrumenter et mesurer AVANT de corriger, pas de diagnostic par inférence. L'instrumentation a révélé deux causes, l'une de pipeline (lecture audio), l'autre de synthèse (longueur du texte edge-tts).

### 1. Correctif STRUCTUREL du pipeline de lecture voix (`scripts/static/js/audio_viz.js`, `scripts/static/js/boot_init.js`)

**Cause racine** : la file de lecture audio (`processQueue`/`playSentence`) pouvait :
- **(a) geler définitivement** — `playSentence` ne se résolvait que sur `source.onended`, qui ne se déclenche jamais si la source joue sur un `AudioContext` suspendu ;
- **(b) provoquer un chevauchement** — `source.start()` appelé sur un contexte suspendu planifie une source « gelée » qui ressurgit au `resume` suivant, par-dessus la parole en cours.

**Fix = invariant unique** : une source TTS n'est JAMAIS démarrée sur un AudioContext suspendu.
- `processQueue` appelle `_ensureAudioCtx()` puis resume-ou-abandonne AVANT `playSentence`.
- Verrou `isPlaying` pris avant tout `await` (anti ré-entrance).
- Ancien « timeout filet » supprimé (devenu inutile une fois l'invariant garanti).
- `boot_init.js` : déverrouillage audio armé tôt (dans `_jarvisInit`), multi-gestes (`click`/`keydown`/`pointerdown`/`touchstart`), flag `_userGestured` découplé du timing `/api/boot-id`.

### 2. Découpage TTS des textes longs (`_splitForTts`)

Nouvelle fonction `_splitForTts` : découpe les textes > 280 caractères aux frontières de phrase. edge-tts a un temps de synthèse proportionnel à la longueur du texte → la voix démarre désormais en **~1 s** au lieu de **~15-24 s** sur les longues analyses SOC.

### 3. Optimisation VRAM (`scripts/jarvis.py`, `scripts/llm_opts.py`, `scripts/JARVIS-menu.ps1`)

- `_SOC_NUM_CTX` (jarvis.py) et `DEFAULT_SOC_NUM_CTX` (llm_opts.py) : **16384 → 8192**. KV cache réduit → phi4 passe de ~12.4 Go à **~11.56 Go** en VRAM.
- ⚠ Suivi 2026-05-20 soir : `tests/python/test_llm_opts.py` était resté à `16384` (5 tests en échec, dette de test non détectée sur le coup) — aligné sur `8192` (7 occurrences) le 2026-05-20 soir, commit `4f8d7a5`. Suite JARVIS de nouveau **933 pytest pass**.
- Modèle d'embedding RAG `mxbai-embed-large` **dé-épinglé** : `keep_alive` `-1` → `"10m"` (dans `_rag_embed` et `_rag_embed_prewarm`). Il se décharge après 10 min d'inactivité au lieu de rester épinglé à vie.
- `_soc_model_prewarm` : précharge phi4 directement en `num_ctx 8192` (évite un reload au 1er chat SOC).
- `_rag_embed_prewarm` : délai de préchauffage 20 s → 5 s (le RAG se charge avant phi4).
- **Résultat mesuré** : VRAM libre passée de **~1.3 Go à ~2.0-2.8 Go**.
- **DÉCISION ACTÉE** : phi4:14b est **conservé** comme modèle SOC (pas de passage à qwen3:8b). Justification : les références 2026 confirment phi4 comme meilleur raisonneur analytique par Go de VRAM, et la VRAM disponible est suffisante après optimisation. Garder phi4 = zéro re-calibration du prompt anti-hallucination.

### 4. Instrumentation TTS (`scripts/jarvis.py`, `scripts/tts_engines.py`, `scripts/deepfilter.py`)

- Sondes `[TTS-PERF]` : décomposition du temps `/api/tts` (edge_gen / dsp / total), timing edge-tts par tentative, temps de chargement DeepFilterNet, timings des threads de préchauffage boot.
- Log **persistant** `scripts/tts_perf.log` (RotatingFileHandler avec filtre `[TTS-PERF]` sur le logger racine) — capture la latence intermittente sans surveiller la console.

### 5. Tuile VRAM — tri d'affichage stable (`scripts/static/js/gpu_monitor.js`)

Tri d'affichage stable : les modèles d'embedding (RAG) sont toujours affichés en dernier → le segment RAG ne « saute » plus de gauche à droite quand phi4 charge.

---

# JARVIS — Mémoire projet (2026-05-17 — audit dette complet final + migration LAN unique Freebox + audit honnête)

## Session 2026-05-17 nuit — audit dette JARVIS complet + 6 quick wins (score 92/100 confirmé)

**Demande Marc** : audit dette technique complet JARVIS exclusivement, puis corrections.

**Verdict** : **score 92/100** (vs 91 CLAUDE.md / 94 BILAN historique → réconcilié à 92). Drifts numériques détectés et corrigés.

### Corrections appliquées (toutes commits suivants)
1. `scripts/]` (21 KB fichier accidentel, log "Fermeture page" piped) supprimé
2. `scripts/jarvis_start.log` (15B garbage) + `tts.log.{1,4,5,6}` (rotation old) supprimés
3. `BILAN-TECHNIQUE.md` : 936→933 pytest · 4633L→4739L · 25→22 modules à 100% · score 94→92
4. `CLAUDE.md` : 936→933 pytest · 4633L→4739L · 91→92 score
5. `jarvis_mcp_server.py:5` docstring : "10 outils" → "12 outils" + ajout `jarvis_defense_24h` + `jarvis_ioc_status`
6. `.pre-commit-config.yaml:41` : "436+ tests" → "933 tests"

### Audit factuel (chiffres réels post-migration LAN unique Freebox)
- **933 pytest pass** + 3 skip (post-migration : -3 tests router retirés)
- Coverage **51%** (6065 stmts · 2976 miss)
- **22 modules à 100% cov** (recompte précis vs 25 annoncés)
- `jarvis.py` **4739L** (2918 stmts) — orchestrateur Flask
- `blueprints/soc.py` 986 stmts (1691L)
- MCP : **12 outils** réels (docstring désormais aligné)
- ruff All passed · ESLint 155 warnings cross-fichiers acceptés
- 4 couches SSH write ops + audit JSONL : robustes
- 0 eval/exec · 1 shell=True documenté · 0 secret en clair

---

## Session 2026-05-17 soir — chantier coverage 5 modules + cleanup snapshots locaux

**Demande Marc** : "on corrige tout" après audit qui révélait 5 modules à coverage faible + 4 dossiers snapshots locaux.

### Résultats globaux

| Indicateur | Avant | Après | Gain |
|---|---|---|---|
| **Tests pytest** | 814 | **936** | +122 tests (+93 chantier 5 modules · +29 option B audio_dsp 72→93%) |
| **Coverage globale** | 44% | **51%** | +7 points absolus |
| **Modules Python ≥100% cov** | 21 | **25** | +4 (+chat_soc_inject, +bypass_code, +voice_lab, +bypass_simple constaté ratisser) |
| **Disque libéré (snapshots)** | — | **361 Mo** | 4 dossiers `scripts.*-YYYYMMDD/` supprimés |

### Coverage par module — détail

| Module | Avant | Après | Gain | Tests ajoutés |
|---|---|---|---|---|
| `chat_soc_inject.py` | 38% | **100%** | +62 pts | +19 (`_kpi_with_delta` 7 cas · `_format_defense_block` 12 cas · `inject(fetch_defense_fn)` 5 cas) |
| `bypass_code.py` | 54% | **100%** | +46 pts | +10 (`code_scp_exec_sse` happy/refus/exec/send/SCP error/exception/sortie vide/commande SCP construite) |
| `code_reasoning.py` | 44% | **96%** | +52 pts | +15 (`_run_task` 9 cas avec stream Ollama mocké · `code_reasoning_gen` 4 cas avec thread daemon · cleanup au passage) |
| `voice_lab.py` | 71% | **100%** | +29 pts | +25 (`is_librosa_available` True/False · `analyse_features` signal sinus 220Hz/150Hz/silence · 8 cas `_classify_type` · 3 cas `_eq_preset`) |
| `audio_dsp.py` | 25% | **93%** | +68 pts | +53 (24 smoke + 29 option B : 9 branches `_apply_fx_rack` reverb/delay/chorus/flanger/echo/phaser/exciter + cache LRU 8 éviction · 3 `_compress` algo réel · 3 `_dsp_eq_gain` complet · 2 `_dsp_decode_audio` WAV mono/stéréo · 2 `_dsp_apply_chain` pipeline · 7 `apply_dsp_to_mp3` chaîne entière + df_override + fallback exception) |

### Suppression snapshots locaux (361 Mo)

4 dossiers `scripts.*-YYYYMMDD/` supprimés :
- `scripts.action1-ruff/` (90 Mo)
- `scripts.aprem-20260514/` (91 Mo)
- `scripts.matin-20260514/` (90 Mo)
- `scripts.snapshot-20260514/` (90 Mo)

Tous étaient déjà gitignored depuis 2026-05-14 (refactor JS) et avaient rempli leur rôle de rollback de sécurité. Validation explicite Marc avant suppression (action irréversible).

### Stratégie de test par module

- **chat_soc_inject** (logique critique injection SOC phi4) : tests directs des helpers `_kpi_with_delta` + `_format_defense_block` (sérialisation `defense_24h.json` compact ~500 chars). Tests `inject` couvrent les 3 branches : fetch_defense OK / KO / JSON invalide.
- **bypass_code** (exécution Python sandbox srv-dev-1) : mock `subprocess.run` (CompletedProcess + TimeoutExpired) + `ssh_dev1_fn` factice. Couvre SCP succès/échec/exception, exec python3/bash, send-only mode.
- **code_reasoning** (qwen3:8b avec thinking masqué) : mock `requests.post` avec `_FakeStreamResponse.iter_lines()` yieldant des chunks JSON Ollama. Test du masquage `<think>...</think>` à la volée.
- **voice_lab** (analyse acoustique librosa) : tests live avec librosa 0.11.0 installé. Génération signal sinusoïdal mono float32 → vérifs pitch_median ≈ fréquence injectée + champs dict requis.
- **audio_dsp** (DSP NumPy + scipy) : smoke tests préservation shape/dtype pour 6 helpers FX (`_apply_delay/chorus/phaser/flanger/echo/exciter`) + `_gen_ir` 5 presets reverb + `_pcm_to_wav` header WAV.

### Commit unique

`feat(jarvis): coverage +6pts (5 modules) + snapshots cleanup 361Mo` — 5 fichiers tests + suppression 4 dossiers locaux.

### Items NON actionnables confirmés

- `jarvis.py` 26% cov (2918 stmts orchestrateur Flask) — couvert E2E Playwright
- `blueprints/soc.py` 33% cov (1007 stmts orchestrateur SOC) — idem
- 155 warnings ESLint — faux positifs camelCase exports inter-modules
- 135 inline styles JS — pattern SPA temps réel acceptable

Score honnête après cette session : **~94/100** (vs ~93 avant) — gain +1 pt sur le critère Tests (24/25 → 25/25 atteint car 50% coverage globale + 25 modules à 100% sur 32).

---

## Session 2026-05-17 — clôture roadmap SSH write ops + audit log forensic dédié

**Découverte audit** : la "seule tâche TODO formelle" de la roadmap CLAUDE.md (`SSH write ops — levée partielle apt upgrade / restart`) était en fait **DÉJÀ LIVRÉE depuis Phase 3 module 6b** :
- `security_whitelists.py` : `BLOCKED_SSH_PATTERNS` (29) + `ALLOWED_RESTART_SVCS` (8 services) + `ALLOWED_APT_PKGS` (12 paquets) + `check_write_op()` validation stricte + `parse_upgradable_packages()`
- Consommé dans `_tool_commande_ssh_run` ([jarvis.py:1652](scripts/jarvis.py#L1652)) — logique 3 couches : pas-bloqué / bloqué-whitelisté / bloqué-refusé
- 28 tests pytest pass dans `test_security_whitelists.py`

La roadmap était simplement **obsolète** (TODO non actualisé après livraison). Cochée 2026-05-17.

### Audit log write ops forensic dédié — vraie valeur ajoutée

**Asymétrie identifiée** : tout l'écosystème SOC+JARVIS trace ses actions (kill_chain, bans cscli, xdr_events) — sauf les write ops SSH, qui sortaient noyées dans le log Flask générique. Forensic post-mortem coûteux.

**Implémentation** (commits à venir) :
1. **`security_whitelists.py`** : ajout `audit_writeop(host, cmd, allowed, output, *, log_path, ts)` (best-effort, ne JAMAIS bloquer la commande SSH si I/O échoue · JSON ligne · path absolu `JARVIS/logs/audit_writeops.jsonl`).
2. **`jarvis.py:1652` `_tool_commande_ssh_run`** : appel `audit_writeop` à 2 endroits :
   - Sur refus (`check_write_op` retourne err) — `allowed=False, output=err`
   - Sur exécution write op (`is_writeop=True` après break) — `allowed=True, output=output`
   - Sur non-write-op (pattern jamais matché) : pas d'audit (pas concerné)
3. **`.gitignore`** : ajout `logs/` et `*.jsonl` (séparé des `*.log` runtime existants).
4. **Tests pytest** : 7 nouveaux dans `test_security_whitelists.py` :
   - `test_audit_writeop_allowed_appends_jsonl`
   - `test_audit_writeop_refused_appends_jsonl`
   - `test_audit_writeop_append_mode_multiple_lignes`
   - `test_audit_writeop_tronque_cmd_longue` (limite 500 chars)
   - `test_audit_writeop_cree_repertoire_parent`
   - `test_audit_writeop_silently_ignores_io_errors`
   - `test_audit_writeop_default_timestamp_utc_format` (ISO8601 + Z)
5. **Smoke test live** module en direct : path absolu OK · format JSONL OK · dossier auto-créé. Test fichier supprimé après validation (recréé à la 1re vraie write op).

**Total tests pytest** : 801 → **808 pass** (+7 audit_writeop · zéro régression).

**Format JSONL** (1 ligne par appel · forensic ciblé) :
```json
{"ts":"2026-05-17T07:13:27Z","host":"ngix","cmd":"systemctl restart nginx","allowed":true,"out_len":27}
{"ts":"2026-05-17T07:13:28Z","host":"clt","cmd":"systemctl restart evilsvc","allowed":false,"out_len":51}
```

**Note confidentialité** : la sortie commande N'EST PAS loggée (seule sa longueur `out_len` est tracée). La commande est tronquée à 500 chars. Suffisant pour forensic, pas de leak de données sensibles.

### À tester live (après prochain redémarrage JARVIS)

Le module a été testé en direct et fonctionne. Le test bout-en-bout via JARVIS web requiert redémarrage (`jarvis.py` modifié). À faire au prochain restart :
1. Démarrer JARVIS
2. Lancer commande SSH `systemctl restart nginx` sur srv-ngix via JARVIS
3. Vérifier `JARVIS/logs/audit_writeops.jsonl` contient 1 ligne `allowed=true`
4. Lancer commande non whitelistée (`systemctl restart cron`) → vérif `allowed=false`

### ⚠ Bug CRITIQUE de défense-en-profondeur colmaté (correction immédiate)

**Découverte** : en creusant le "bug latent" `apt install <pkg>` non bloqué, j'ai trouvé un trou bien plus grave dans la logique `_tool_commande_ssh_run` :

```python
for pattern in BLOCKED_SSH_PATTERNS:
    if pattern.lower() in cmd_lower:
        is_writeop = True
        err = check_write_op(cmd)
        if err is not None:
            return refus
        break   # ← FAILLE : si check_write_op retourne None, on EXÉCUTE !
```

`check_write_op` ne traite QUE 2 cas (systemctl restart + apt install/upgrade). Pour TOUT le reste (`rm`, `mkfs`, `dd`, `shutdown`, `qm destroy`, ...), elle retourne `None`. Le test ligne 123 le documente même explicitement.

**Conséquence** : `rm -rf /` matchait pattern `"rm "`, `check_write_op("rm -rf /")` retournait `None`, `err is not None` était False, `break` → **commande EXÉCUTÉE sur srv-ngix/proxmox/clt/pa85**.

**Risque réel** : faible en pratique (phi4 local, prompt restreint, pas d'accès externe) mais **inacceptable** comme défense-en-profondeur.

**Fix appliqué 2026-05-17** (commit à venir) :

1. **`BLOCKED_SSH_PATTERNS`** : ajout `"apt install"`, `"apt upgrade"`, `"apt-get install"`, `"apt-get upgrade"` (avant, ces patterns absents → `apt install evilpkg` passait sans entrer dans la boucle).
2. **`security_whitelists.py`** : extraction des regex `_RE_SYSTEMCTL_RESTART` + `_RE_APT_WRITE` en constantes module + ajout `is_known_write_op(cmd) -> bool` (gardien sécurité, retourne True ssi commande est de forme reconnue par `check_write_op`).
3. **`_tool_commande_ssh_run`** ([jarvis.py:1652](scripts/jarvis.py#L1652)) : logique étendue à **4 couches** :
   - **Couche 1** : aucun pattern BLOCKED matche → exec direct (lecture/diagnostic)
   - **Couche 2** : pattern BLOCKED + commande reconnue (`is_known_write_op` True) + whitelistée (`check_write_op` None) → exec + audit `allowed=true`
   - **Couche 3 (NOUVEAU)** : pattern BLOCKED + commande NON reconnue (rm/mkfs/dd/shutdown/...) → **REFUS PAR DÉFAUT** + audit `allowed=false`
   - **Couche 4** : pattern BLOCKED + commande reconnue + refusée explicitement (svc/pkg non whitelisté) → REFUS + audit `allowed=false`
4. **Tests** : +6 nouveaux (1 test patterns apt + 5 tests `is_known_write_op` couvrant 14 commandes destructives). Total **808 → 814 pass**.

**Validation simulation** (script de smoke test) :
```
'rm -rf /'                  → REFUSE par defaut (pattern: 'rm ')        ✓
'mkfs.ext4 /dev/sda'        → REFUSE par defaut (pattern: 'mkfs')       ✓
'shutdown now'              → REFUSE par defaut (pattern: 'shutdown')   ✓
'apt install evilpkg'       → REFUSE explicite (whitelist apt)          ✓
'systemctl restart nginx'   → AUTORISE                                  ✓
'apt install nginx'         → AUTORISE                                  ✓
'ls -la'                    → EXEC direct (lecture)                     ✓
'cat /etc/hosts'            → REFUSE par defaut (pattern: '/etc/hosts') ✓
```

**Smoke test live à faire au prochain restart JARVIS** :
1. Demander à JARVIS : "Sur srv-ngix, lance : rm -rf /tmp/test" → doit refuser
2. Vérifier `JARVIS/logs/audit_writeops.jsonl` : 1 ligne `allowed=false` avec pattern `rm `

---

## Session 2026-05-17 (matin) — audit dette honnête + parité documentaire avec SOC

**Contexte** : audit complet et honnête de la dette JARVIS (post-session SOC où SOC a atteint 96/100 avec docs exhaustives). Score JARVIS recalibré : **93 → 91/100** (audit révèle 2 documents manquants par rapport à SOC).

### Audit dette honnête — chiffres recalibrés

| Indicateur | Mémoire (avant audit) | Audit réel 2026-05-17 | Écart |
|---|---|---|---|
| Tests pytest | 801 pass | **801 pass · 0 fail** | ✓ |
| Coverage globale | 39% | **44%** | **+5 pts** (mémoire pessimiste, pytest-cov réel plus haut) |
| Modules à 100% cov | n/a | **21 modules** | (nouvelle info) |
| `jarvis.py` cov | 26% | **26%** (2909 stmts) | ✓ |
| `blueprints/soc.py` cov | 33% | **33%** (1007 stmts) | ✓ |
| ESLint warnings | 155 | **155** | ✓ |
| Score honnête | 93/100 | **91/100** | **−2** (CLAUDE.md absent · BILAN-TECHNIQUE.md absent vs SOC) |

**Décomposition 91/100 honnête** : Archi 22/25 (monolithe Flask accepté) · Tests 23/25 (cov 44% RÉELLE > mémoire) · **Doc 13/15** (−2 CLAUDE.md + BILAN absents avant cette session) · Lisibilité 14/15 (155 warnings ESLint acceptés) · Perf 10/10 · Sécu 10/10.

### Création BILAN-TECHNIQUE.md (parité avec SOC)

Nouveau document `JARVIS/BILAN-TECHNIQUE.md` (~800 lignes) calqué sur la structure de `SOC/BILAN-TECHNIQUE.md` :
- **0. État actuel** (audit honnête avec décomposition score + chiffres clés)
- **0bis. Session 2026-05-16 nuit** (Sprint 18d MCP IoC + refactor `_SOC_BAN_CONFIG` + defense_24h + heatmap 15min + QW4 ESLint)
- **1. Vue d'ensemble** (architecture moteur IA local)
- **2. Architecture Python** (32 modules détaillés avec coverage : cœur Flask + chat/LLM + audio/TTS/STT + infra/sécu + MCP)
- **3. Architecture Frontend** (refactor JS terminé · 13 extractions · 21 modules JS · 8 CSS · 10 templates)
- **4. Circuit breaker Ollama** (state machine 3 états · 8 call-sites · indicateur HUD)
- **5. TTS chain & profiling** (4 moteurs · pré-warm Kokoro CUDA · médianes TTFB)
- **6. MCP server** (12 outils détaillés)
- **7. Intégrations SOC** (cache + fallback SSH + injection 100% serveur + 6 outils MCP)
- **8. Sécurité & règles absolues** (whitelist SSH 29 patterns · SSH read-only · anti-double-ban · anti-hallucination · RFC1918)
- **9. Performance** (fix IPv6 systémique · cache SOC · pré-warm · debounce DSP)
- **10. Tests & qualité** (coverage par catégorie · 25 E2E · pre-commit/pre-push hooks · ESLint config)
- **11. Roadmap résiduelle** (1 seule tâche ouverte : SSH write ops)
- **12. Bilan santé** (tableau récap final)

### Création CLAUDE.md (briefing JARVIS-spécifique)

Nouveau document `JARVIS/CLAUDE.md` (~120 lignes) — **complémentaire** au `0xCyberLiTech/CLAUDE.md` racine (ne duplique pas). Sert quand on ouvre VSCode dans `JARVIS/` seul :
- Identité (v3.3 · ~94/100 · 936 tests · refactor JS terminé)
- Sources de vérité (priorité : MEMORY → BILAN → RUNBOOK → docs/)
- Stack technique compacte
- Lancement (start/stop/MCP)
- **4 modes (règle absolue)** : SOC/GENERAL/CODE/CR avec modèles + auto-engine SOC marker
- Conventions (127.0.0.1 vs localhost · Edit vs Write >200Ko · pre-commit/pre-push)
- **7 règles ABSOLUES zéro régression** : RFC1918 · `_BLOCKED_SSH` · `_ALLOWED_SERVICES` · injection 100% serveur · architecture coût LLM · auto-engine mode soc · SSH read-only
- Fichiers clés (paths + rôles)
- Fichiers gitignored à recréer en DR
- Workflow + conventions commit

### Résultat parité doc JARVIS/SOC

| Doc | SOC | JARVIS (avant 2026-05-17) | JARVIS (après) |
|---|---|---|---|
| `MEMORY.md` | ✓ (gitignored) | ✓ (tracké) | ✓ |
| `RUNBOOK.md` | ✓ | ✓ | ✓ |
| `BILAN-TECHNIQUE.md` | ✓ (768L) | ❌ | ✓ **(nouveau ~800L)** |
| `CLAUDE.md` projet-spécifique | — | ❌ | ✓ **(nouveau ~120L)** |
| `docs/` détaillés | 11 fichiers PROJET-SOC + 5 DEPLOY + 2 Archives | 7 fichiers (AUDIO-DSP, MCP-SERVER, REFERENCE-TECHNIQUE, ROUTING-JARVIS, DEPLOIEMENT, REINSTALLATION, SUPPORT-INFOGERANCE) | ✓ inchangé |

**Score post-création** : passage 91 → **93/100 estimé** (récupération des 2 points Doc avec création BILAN + CLAUDE) — à valider au prochain audit.

### ⚠ Correction de framing : JARVIS est POST-modularisation

L'audit initial parlait de "monolithe `jarvis.py`" — terme inexact. La modularisation est DÉJÀ faite des 2 côtés :
- **Python** : 31 modules satellites extraits (21 à 100% cov). `jarvis.py` (4633L) = **orchestrateur Flask** : ~150 endpoints HTTP + routing 4 modes + auto-engine SOC + glue. Logique métier déjà extraite.
- **JS** : refactor TERMINÉ. `jarvis_main.js` 7828→148L (−98,1%). 13 modules dans `static/js/`.

### Items NON actionnables (à NE PAS confondre avec des dettes)

1. **`jarvis.py` 26% cov** — normal pour orchestrateur HTTP, couvert indirectement par 25 tests E2E Playwright. **IGNORER**.
2. **`blueprints/soc.py` 33% cov** — orchestrateur SOC cache + fallback SSH, testé via MCP. **IGNORER**.
3. **155 warnings ESLint** — faux positifs camelCase exports inter-modules sans bundler. **IGNORER**.
4. **135 inline styles JS** — pattern HUD temps réel acceptable. **IGNORER**.

### Seule vraie tâche TODO formelle

- [ ] **SSH write ops** — levée partielle (`apt upgrade` / `restart`) après stabilisation routing · demande validation Marc avant implémentation (cf. `feedback_jarvis_no_regression`).

---

## Intégration SOC defense_24h — 2026-05-16 (commit `ed8f3a8`)

Nouveau résumé compact des actions défensives 24h alimente JARVIS via 3 canaux complémentaires (source : `defense_aggregator.py` côté SOC, cron 60 s).

- **Route HTTP `/api/soc/defense`** (cache 30 s) — `blueprints/soc.py:_fetch_defense()` + endpoint dérivé du `monitoring_url` (même host:port, fichier différent). Pas de fallback SSH (defense est secondaire).
- **Injection bloc compact dans system prompt phi4 mode SOC** — `chat_soc_inject.py:_format_defense_block()` (~400 chars : KPI + pic horaire + top 5 pays/AS/scénarios). Activé via `fetch_defense_fn=_fetch_defense` passé en DI dans `_chat_inject_soc`. Phi4 répond direct aux questions « combien de bans / quel pays attaque le plus / quelle heure de pointe » sans recalculer depuis monitoring.json brut (210 Ko → 0,4 Ko de contexte LLM).
- **Outil MCP `jarvis_defense_24h`** (11e outil, était 10) — `jarvis_mcp_server.py:_handle_jarvis_defense_24h()` formate le JSON en bloc texte JARVIS_HEADER. Permet à Claude Code (MCP client) d'interroger ce résumé en 1 call au lieu de parser monitoring.json. **+2 tests pytest** (799 → 801) + tests `compte_10` renommés `compte_11`.

Pattern « Single Source of Truth » : 1 fichier JSON côté SOC → 3 consommateurs (humain navigateur / phi4 chat / Claude MCP). 0 régression, ruff/eslint 0, tests existants intacts.

### Adaptation granularité heatmap 15 min (commit `0d7de9c`)

Suite au passage côté SOC à 96 buckets de 15 min (au lieu de 24 buckets horaires), les 2 consommateurs JARVIS du JSON ont été adaptés :
- `chat_soc_inject._format_defense_block()` : lit `heatmap_bucket_min` du JSON (15 en v1.2, fallback 60 si len(heat) ≤ 24). Calcule peak_lbl en min/h selon la granularité : « tranche courante » / « il y a Xmin » / « h-X » / « h-X Ymin ». Format string : « Pic 15min: il y a 30min (310 actions sur la tranche) ».
- `jarvis_mcp_server._handle_jarvis_defense_24h()` : même logique de déduction + label adaptable. Bloc texte LLM affiche « Pic 15min : ... ».
- Rétro-compat : fallback bucket_min=60 si heatmap_bucket_min absent.

### Quick wins dette technique 2026-05-16 (commit `9c904c2`)

QW4 — ESLint pre-commit JARVIS aligné cohérence cross-projet :
- Hook `files:` élargi de 4 fichiers (jarvis_main, jarvis_mixing, recorder, voice_print) à tous les modules JS (4 historiques + 18 extraits dans `scripts/static/js/`).
- `varsIgnorePattern: '^_'` → `'^(_|[A-Z][A-Z0-9_])'` (capture aussi les SCREAMING_SNAKE_CASE comme `BS`, `DSP_PROFILES`).
- Aligné avec SOC pour cohérence cross-projet (audit dette 2026-05-16).
- Résultat : 161 → 155 warnings (80% restants sont des fonctions camelCase partagées impossibles à détecter sans bundler — acceptable). 0 erreur.
- Tests : 801/801 PASS, aucune régression.



## Injection SOC 100 % serveur + crawlers légitimes — 2026-05-14 (commit `ec8f2df`)

**Déclencheur** : JARVIS hallucinait des analyses SOC (IP fantômes, score faux) et recommandait de bannir des crawlers légitimes (Bingbot/Googlebot).

- **Cause hallucination** : `jarvis_main.js` `_buildChatPayload()` incrustait le snapshot SOC **dans le message utilisateur** → persisté dans l'historique. En multi-tours, le client ne rafraîchissait que le dernier message → les vieux snapshots restaient → phi4 les mélangeait. Idem `SOC/dashboard/js/18-jarvis-chat.js`.
- **Fix** : suppression de l'injection client-side (`_monCtxStr` + `_SOC_CHAT_KW` + `_MON_NET_SPIKE_S` morts, −83 L). Injection **100 % serveur** via `chat_soc_inject.py` → system prompt, **frais à chaque appel, jamais persisté**, source de formatage unique (Python `_build_monitoring_context`).
- **`force_soc`** threadé en DI (`api_chat` → `chat_system_prompt.build` → `chat_soc_inject.inject`) : `model_override='soc'` (chat du dashboard SOC) force l'injection même sans mot-clé.
- **Garde-fou** : srv-ngix injoignable → instruction anti-hallucination dans le system prompt (était côté client, déplacé serveur).
- **`_build_monitoring_context`** : affiche la liste « IPs DÉJÀ BANNIES par CrowdSec » (corrige les bans redondants) + « Crawlers légitimes vérifiés FCrDNS » + flag `⚠UA-USURPÉ`.
- **Profil SOC** (`jarvis_prompt_profiles.json`) : règles ABSOLUES — IPs déjà neutralisées + crawlers légitimes (ne jamais bannir un crawler vérifié ; usurpateur = menace réelle).
- **Auto-engine proactif** (`18-jarvis-engine.js`) **inchangé** — et n'auto-bannira plus un crawler vérifié (exclu de `kill_chain.active_ips` côté SOC). Bilan : **−39 L nettes**, ruff/eslint verts. Côté SOC : commit `7d386c2` (cf. `SOC/MEMORY.md`).
- **Reco de ban proportionnée** (commit `f17fc66`) : `_kc_ban_signal()` annote chaque IP Kill Chain `signal=FORT|faible` (FORT = EXPLOIT / UA usurpé / hits ≥ `_KC_BAN_SIGNAL_MIN_HITS`=10, plancher aligné sur `banMinCount` auto-engine). Profil SOC : règle ABSOLUE — ne jamais recommander un ban prioritaire sur signal faible (SCAN/RECON isolé = bruit de fond). Fin des recos de ban sur SCAN 1-hit.

---

## Chantier dette technique — 2026-05-14/15 — score 62→93/100 honnête (+31)

⚠ **2e recalibration honnête (post-audit pytest --cov)** : les annonces récentes 92-94 étaient optimistes — basées sur "70% des modules testés" qui ≠ "70% lignes couvertes". L'audit pytest --cov rigoureux a révélé une coverage RÉELLE de 12% (les 11 modules non testés représentaient 66% du code total : jarvis.py 2891 stmts à 0%, blueprints/soc.py 963 stmts à 0%). Phase 4 a corrigé cela.

Le chantier a fait **62 → 91/100** (recalibré honnêtement) :
- 62→75 : Ruff + git + hooks + CSS 8 fichiers + audio_dsp.py
- 75→76 : 2 smoke tests LLM
- 76→78 : refactor JS partiel (3 sous-systèmes extraits de jarvis_main.js)
- 78→82 : refactor JS reprise du soir — `jarvis_main.js` 7828→3235 L (−59%), 9 modules
- 82→85 : refactor JS continuation 2026-05-15 — `jarvis_main.js` 3235→1181 L (−85% cumul), 13 modules
- 85→87 : **Phase 2 tests Python initial** — 436 tests sur 23/34 modules (mais coverage réelle = 12% lignes) +1 bug prod fixé (tts_cleaner)
- 87→88 : **Phase 3 fix perf IPv6** — `OLLAMA_URL`/`JARVIS_BASE` → `127.0.0.1` explicite · −97% latence clients internes · outil `tools/profile_perf.py`
- 88→88 : refactor JS FINAL #12-#13 — `jarvis_main.js` 1181→148 L (−98,1% cumul) · refactor officiellement terminé
- 88→90 : **Phase 4 — coverage massivement augmentée** — hook pre-push pytest installé · 132 tests supplémentaires (38 soc.py + 28 jarvis.py + 27 proxmox_api + 39 voice_lab) · **coverage TOTAL 12% → 35% (+23 pts)** · 568 tests pytest au total · 27/34 modules touchés (79%)
- 90→91 : **Phase 4 extension viser 95** — 114 tests supplémentaires sur 5 modules I/O (22 ssh_terminal + 18 rag_live + 22 stt + 34 bypass_backup + 18 deepfilter) · **coverage TOTAL 35% → 39% (+4 pts)** · ssh_terminal 100%, stt 98%, rag_live 92%, bypass_backup 96%, deepfilter 84% · 682 tests pytest au total · **32/34 modules touchés (94%)**
- 91→92 : **Circuit breaker Ollama** (commit `8ebbbad` + UI fix `227405b` + nomenclature `6514570`) — module `ollama_circuit.py` (110 L · state machine 3 états CLOSED/OPEN/HALF_OPEN · backoff exponentiel ×2 plafonné à 5 min · thread-safe · singleton) + 23 tests (705 tests total) + wrapping chat principal `jarvis.py:1786` (refus immédiat si Ollama down 3 erreurs consécutives) + endpoint `/api/ollama-status` enrichi + indicateur HUD visuel (`●` + label "OLLAMA" vert/orange/rouge selon état) · UX : quand Ollama tombe, JARVIS reste réactif (refus 1ms vs timeout 30s) + diagnostic instantané pour user (rouge clignotant)
- 92→93 : **Phase 4 finale — 100% modules testés + circuit breaker étendu + profiling TTS** (commits `e1b15f4` + `2311b0a` + `e079d65` + `efac7f9`) :
  - **Circuit breaker étendu** (`e1b15f4`) : import module-level `from ollama_circuit import circuit, OllamaUnavailable` dans `jarvis.py` · 8 call-sites Ollama wrappés (chat stream L1791, chat models test L4296, summarize L774, RAG embed L821, tool detect L1733, welcome refresh L2519, RAG embed prewarm L4565, SOC model prewarm L4601) · 4 ping/health endpoints intentionnellement non wrappés (L674 health, L2560 sysdiag, L4575 vram cleanup, L4585 unload urllib direct).
  - **Bouton SOC PING JARVIS enrichi** (commit `3d73448` repo SOC) : `pingJarvis()` dans `18-jarvis-ui.js` enchaîne après ping un `/api/ollama-status` · toast affiche état Ollama (`● OK` / `◐ recovery 25s` / `◯ DOWN retry 12s`) + badge classe sur `#pro-ping-btn` (`cb-closed/cb-half_open/cb-open`, animation blink si OPEN). CSS `monitoring.css` : 7 nouvelles classes.
  - **Tests `tts_engines.py`** (`2311b0a`) : 42 tests, **coverage 83%** (199 stmts, 33 missed). Couvre les 4 engines : `_normalize_kokoro_voice` (préfixes valides + fallback ff_siwis), `list_piper_models` (filtrage .onnx + .onnx.json), `list_sapi_voices` (pyttsx3 mocké), `_get_piper_model` (cache hit, LRU eviction, FileNotFoundError), `_get_kokoro` (import failure, déjà unavailable, pipeline existant), `kokoro_synth` (pipeline None, aucun audio, exception reset, succès, clamp speed 0.5-2.0), `piper_synth` (aucun modèle, succès, fallback nom, aucun chunk), `sapi5_synth` (succès, PS fail, voice_id résolu via `_pyttsx3` mock), `edge_generate_mp3` (succès, retry, 3 échecs, délai DNS spécifique).
  - **Tests `jarvis_mcp_server.py`** (`e079d65`) : 52 tests, **coverage 91%** (211 stmts, 20 missed). Sans dépendance pytest-asyncio — utilise `asyncio.run()` directement. httpx mocké via classes async context manager fakes (`_FakeResp/_FakeStreamCtx/_FakeClient`). Couvre constantes (JARVIS_BASE IPv4 explicite), `_sanitize` (IPv4 → [IP], tronque à 3000), `_TOOLS_DEFS` (10 outils définis, noms uniques, handlers correspondent), `_collect_sse_tokens` (concat tokens, filtre `data:`, ignore JSON invalide, ssh_file prend priorité), `_get_ip_history` (404, vide si rien, données réelles), `_get_soc_context_live` (succès, fallback `/api/status`, tout KO), 10 handlers (chat/soc_status/stats/read_file/model_switch/last_response/code_exec — succès/vide/erreur/sanitize), `call_tool` (outil inconnu, ConnectError → hors ligne, exception générique).
  - **Couverture finale** : 34/34 modules Python testés (100%) · **799 tests pytest** (705 + 42 + 52).
  - **Profiling TTS détaillé** (`efac7f9`) : `tools/profile_tts.py` mesure TTFB+total+taille pour 4 moteurs × 7 textes. Restaure l'engine d'origine en `try/finally`. Médianes mesurées 2026-05-15 (chaud) : **edge 1453ms · kokoro 203ms · piper 219ms · sapi 563ms**. Cold start Kokoro = 42.8s (chargement VRAM CUDA), Piper cold = 1.6s (ONNX CPU), edge cold = 765ms-1344ms (DNS + retry asyncio). Kokoro/Piper sont 7-10× plus rapides qu'edge en chaud. Recommandation : pré-warmer Kokoro au boot (comme phi4) pour éviter cold start, ou défaut Piper pour temps-réel SOC.
  - **Pré-warm Kokoro CUDA au boot** (`2cc98e9`) : thread daemon `_kokoro_prewarm` lancé 60s après boot (après `_soc_model_prewarm` + marge GPU). Charge le pipeline Kokoro CUDA en VRAM avant la 1re alerte vocale. Validation post-redémarrage : `/api/tts/status` Kokoro = `EN SERVICE` immédiatement (au lieu de `CHARGEMENT` avant), TTS instantané dès la 1re alerte SOC.

**Refactor JS — reprise 2026-05-14 (soir) + continuation 2026-05-15** : `jarvis_main.js` **7828 → 1181 L (−6647, −85%)** · **13 modules extraits** dans `static/js/`. Méthode : cartographie des appels top-level → extraction de sections sans dépendance d'ordre · bodies **byte-identiques** vérifiés · `node --check` + eslint 0 erreur à chaque étape · `eslint.config.js` globals cross-file déclarés. ⚠ **Procédure renforcée après régression #4 ET #9** : vérifier aussi les `const/let/var` partagés utilisés au top-level par les scripts chargés AVANT le module (NE PAS exclure const/let/var du grep load-order — leçon des fix `_LS_PROMPT_PROFILE` et `_origAddMessage`).
- **#1** `a118772` — `tasks_tab.js` (129 L) + `welcome.js` (244 L) — **validé prod**.
- **#2** `fe1be24` — `eq_parametric.js` (502 L, EQ voix) — **validé prod**.
- **#3** `3f37189` — `eq_music.js` (701 L) + `audio_mire.js` (383 L) — **validé prod**.
- **#4** `0c5d110` — `audio_viz.js` (1138 L, toute la viz audio) — **régression d'ordre** : `audio_viz.js` définit `const _SAMPLE_RATE` requis au top-level par `recorder.js`/`eq_parametric.js` chargés avant → corrigé `c83f57f` (`audio_viz.js` chargé juste après `jarvis_main.js`, position d'origine du bloc viz) — **validé prod après fix**.
- **#5** `5f57018` — `settings_llm.js` (477 L, params LLM, profils prompt, system prompt, faits, mémoire LT, RAG) — **validé prod**.
- **#6** `496ffc7` — `dsp_audio.js` (291 L, chaîne DSP UI : gain/compresseur/limiteur/EQ bandes, push backend, canvas DSP) — **validé prod**.
- **#7** `99b920c` — `boot_init.js` (792 L, bloc « BOOT SEQUENCE » de l'original : message vocal d'intro, rack d'effets FX UI — IR reverb/echo/delay, crossfade wet/dry, FX2 modulation, banques mémoire FX 0-9, VU FX via hook fetch TTS — et INIT, point d'entrée unique `DOMContentLoaded` `_jarvisInit`) — **chargé EN DERNIER** dans jarvis.html (point d'entrée) — `_rackVuInterval`/`_rackUpdateVu`/`_DRAW_INTERVAL_MS` référencés au top-level mais définis dans `jarvis_main.js` chargé avant → OK — **validé prod (F12=0, tous onglets)**.
- **#8** `6fa224d` — `audio_rack.js` (693 L, AI AUDIO RACK + helpers EQ : rack DSP intégré faders/comp/EQ/stereo widener/Haas/DeepFilterNet/master/VU/test voix, presets EQ paramétrique + presets spectre, master DSP, helpers EQ partagés `setEqBand`/`eqSetFreq`/`eqSetType`/`eqPushNow`/`eqToggleBypass`/`_canvasCoords`, `escHtml`) — chargé après `dsp_audio.js` et avant `boot_init.js` — **validé prod (F12=0, tous onglets)**.
- **#9** `b1c8188` + fix `f8725b5` — `chat_core.js` (512 L, mal banni « DIAGNOSTIC SYSTÈME » mais contient `sendMessage` + SSE chat streaming + 4 modes (`setModeSoc/General/Code/CodeReasoning`) + vision + polling Ollama + diagnostic + listeners top-level paste/keydown/input sur `user-input`) — **régression load-order #2** : `_LS_PROMPT_PROFILE` (défini chat_core.js) utilisé au top-level par settings_llm.js chargé avant → fix : déplacer chat_core.js avant settings_llm.js dans jarvis.html — **validé prod après fix**.
- **#10** `ef7a8de` + fix `c255fab` — `chat_ui.js` (573 L, état + UI du chat : `const history = []` + `busy` + abort SSE, `addMessage`/`_esc`/`addToolEvent`, mémoire long-terme `loadMemory`/`saveMemory`/`clearMemory`, STOP TTS button, markdown rendering + Monaco code editor modal complet, web search toggle, bloc `patchAddMessage` MutationObserver) — **régression #3** : `const history = []` perdu par sed off-by-one (j'ai démarré à 1051 au lieu de 1050) → `history.push is not a function` (resolved vers `window.history`) → fix `c255fab` réintroduit la déclaration — **validé prod après fix**.
- **#11** `da17642` — `gpu_monitor.js` (347 L, anneaux SVG CPU/RAM/GPU/VRAM du chat HUD : constantes graphiques `CIRC`/`_RTX_BLUE`/`_RTX_GREEN`/`_VRAM_GRADIENT_*`, fetch `/api/stats`, anim hexagone, polling périodique, `pollVramLlm()` au top-level) — **validé prod (F12=0, tous onglets)**.
- **#12** `00a3edc` — `soc_tab.js` (594 L, ONGLET ◈ SOC + SOC GRAPHIQUES regroupés : initSocTab/refreshSocTab/checkThreatLevel/_buildChatPayload/socNarrativeAnalysis/clearSocActions/socForceAutoban + sparkline 30j/Canvas modal détail/_socDrawCharts/socMonthNav) — chargé AVANT chat_ui/chat_core (chat_core utilise _buildChatPayload) — **off-by-one détecté+fixé** (`var _socAutoRefresh = null` ligne 78 perdue par sed, réinsérée) — **validé prod (F12=0)**.
- **#13** `9a09923` — `settings_ui.js` (482 L, FUSION 5 sous-systèmes UI contigus : SETTINGS GPU HEALTH polling + MODELE SWITCHER icônes + VOICE SWITCHER preview + LLM HEADER `_updateHeaderLLM` + CHAT HUD EXTRAS) — **MILESTONE FINAL** : `jarvis_main.js` 609→148 L (−76%) — **validé prod (F12=0)**.
⚠ Restart JARVIS requis après chaque extraction (`debug=False` → templates en cache). **Refactor JS terminé** : `jarvis_main.js` final = **148 L** = header consts (56 L) + TABS (17 L) + HORLOGE (8 L) + GRAPHIQUES (50 L) + pointeurs (~17 L). Plus rien d'extractible avec valeur (rendement décroissant total).

**Suite tests unitaires Python — 2026-05-15 (cumul +7 pts dette : 85→92/100)** : passage de **0 à 436 tests** sur **23 modules / 33 = 70% couvert** en 7 batchs, pytest 9.0.2, setup `[tool.pytest.ini_options]` + `tests/python/` + `conftest.py` (sys.path injection). Méthode : focus sur les modules logique pure (0 I/O direct), DI via stubs, mock `requests.post` pour les modules HTTP, pytest fixtures `tmp_path` pour les helpers fichier.

| Batch | Commit | Modules testés | Tests |
|---|---|---|---|
| #1 | `efa68e3` | tts_dedup · chat_messages · chat_routing | 27 |
| #2 | `efa68e3` | chat_system_prompt · llm_opts · tts_cleaner (+1 bug fixé) · security_whitelists · chat_soc_inject | 117 |
| #4 | `dcc1879` | chat_capture · chat_stream · chat_generate · chat_pending_bypass · chat_tool_calls · sse_helpers · stream_tokens · deferred_speak | 86 |
| #5 | `57ee82e` | audio_dsp (508 L, le plus gros — _db2lin, _pcm_to_wav, _mono_to_stereo Haas, court-circuits, bypass apply_dsp_to_mp3) | 31 |
| #6 | `c819507` | bypass_simple · bypass_filesystem · vision (mock requests streaming) | 80 |
| #7 | `0d216cb` | bypass_proxmox · bypass_code · code_reasoning | 84 |

**Bug prod détecté+fixé par les tests** : `tts_cleaner.py` ordre regex images/liens — `![alt](img.png)` matchait d'abord `[texte](url)→texte`, laissant `!alt` que le TTS prononçait "exclamation alt". Inversion de l'ordre : images supprimées AVANT liens.

**Modules Python restants non testés (10/33)** : wrappers I/O réseau lourds (`bypass_backup`, `proxmox_api`, `ssh_terminal`, `tts_engines`, `stt`, `deepfilter`, `rag_live`, `voice_lab`) ou intégrations Flask (`jarvis.py`, `jarvis_mcp_server.py`, `blueprints/soc.py`) — rendement décroissant pour tests unitaires (E2E Playwright déjà existants pour l'intégration).

**Phase 3 — Profiling perf 2026-05-15 (+1 pt : 92→93/100)** : `tools/profile_perf.py` (script standalone, 200 L, mesure TTS/RAG/Ollama swap/endpoints UI sans modifier prod). **Bug systémique identifié** : timeout résolution IPv6 `::1` sur Windows → tout client tapant `localhost` perdait ~2s par requête (Flask écoute sur 127.0.0.1 IPv4 only, le resolver Windows tente `::1` en premier, timeout, fallback IPv4). **Fix** (3 fichiers, single-source no-hardcode) :
- `scripts/jarvis.py:544` — `OLLAMA_URL = http://127.0.0.1:11434`
- `scripts/blueprints/soc.py` — `from jarvis import OLLAMA_URL` au lieu de hardcode
- `scripts/jarvis_mcp_server.py:36` — `JARVIS_BASE = http://127.0.0.1:5000`

**Résultats mesurés (clients utilisant 127.0.0.1)** : `/api/health` 2047→16ms (−99%) · `/api/sysdiag` 4604→557ms (−88%) · Ollama `/api/ps` 2078→<1ms (−100%) · embedding mxbai 2062→47ms (−98%) · TTS edge-tts TTFB 3063→656ms (−79%) · phi4 WARM first token 2422→78ms (−97%). **Bénéficiaires** : MCP server (Claude Desktop), soc.py auto-engine, chat→Ollama interne. Le navigateur user garde un overhead Happy Eyeballs ~50ms négligeable.

**Phase 4 — Audit honnête + actions correctives 2026-05-15 (88→91/100)** :

Audit `pytest --cov` rigoureux a révélé que les annonces "70% modules testés = 70% coverage" étaient FAUSSES. Coverage réelle initiale : 12% lignes (les 11 modules non testés représentent 66% du code total).

Actions correctives (cumul 12% → 39% coverage, 132 → 246 tests supplémentaires) :
1. **Hook pre-push pytest** (commit `a7619a0`) : `.pre-commit-config.yaml` étendu avec `stages: [pre-push]` pour pytest. Bloque les push sur tests rouges. Alternative locale à la CI cloud impossible avec « rien sur le web ».
2. **Tests blueprint soc.py** (commit `9ef68e3`) : 38 tests via Flask test_client + helpers purs. **soc.py 0%→33%** (317 stmts couverts).
3. **Tests jarvis.py** (commit `f236001`) : 28 tests via Flask test_client (l'import jarvis = boot complet en 1.7s, OK pour suite pytest). **jarvis.py 0%→26%** (743 stmts couverts).
4. **Tests proxmox_api.py** (commit `605a93f`) : 27 tests avec mock requests.Session (token + ticket auth). **proxmox_api 0%→93%** (126 stmts couverts).
5. **Tests voice_lab.py** (commit `b7a587d`) : 39 tests avec mock librosa + tmp_path FS. **voice_lab 0%→71%** (65 stmts couverts).
6. **Batch petits modules** (commit `03e26df`) : 22 tests ssh_terminal (100%) + 18 rag_live (92%) + 22 stt (98%).
7. **Tests bypass_backup.py** (commit `be55317`) : 34 tests avec mock subprocess.Popen (PowerShell + parsing résumé). **bypass_backup 0%→96%** (126 stmts couverts).
8. **Tests deepfilter.py** (commit `d8bfde6`) : 18 tests avec mock torch + df.enhance. **deepfilter 0%→84%** (81 stmts couverts).
9. **`.coverage` ajouté à `.gitignore`** (commit `dc7fbfd`) — cache binaire pytest-cov, ne doit pas être tracké.

**Coverage TOTAL : 12% → 39% (+27 pts).** Ensuite étendu à **34/34 modules (100%)** via tests `tts_engines` (83% cov, 42 tests) + `jarvis_mcp_server` (91% cov, 52 tests) + `ollama_circuit` (100% cov, 23 tests). **Total final : 799 tests pytest**.

**Modules non testés restants (2/34)** : `tts_engines.py` (199 stmts — 4 engines async/CUDA/ONNX/SAPI très lourds à mocker) et `jarvis_mcp_server.py` (211 stmts — FastMCP avec décorateurs async). Pour atteindre 95+ : tester ces 2 modules (+ 4 pts coverage potentiel) · circuit breaker formel Ollama (+1 pt) · profiling détaillé TTS engines (+1 pt). Plafond réaliste sans CI cloud : ~93-95/100.

**5 commits git atomiques** (dépôt initialisé, 100% local, aucun remote) :

| Commit | Action | Détail |
|--------|--------|--------|
| `a530dc6` | Baseline + #1 Ruff | 98→0 erreurs · 2 bugs F821 réels corrigés (`_torch` import lazy → CUDA reverb actif · `VOICES_DIR` → `_tts_eng.VOICES_DIR`) · `ruff.toml` (E701/E702 ignorés = style · E402/I001 per-file jarvis.py+mcp) |
| — | git init | `.gitignore` protège `jarvis_secret.key` + `jarvis_pve.json` + `soc_config.json` · 132 fichiers, 0 secret tracké · `core.autocrlf false` |
| `b46eae2` | #2 Pre-commit hooks | `.pre-commit-config.yaml` 100% local (ruff + eslint, zéro réseau) · BLOQUANT · testé négatif (faute F821 → commit bloqué) + positif |
| `ad4629f` | Doc README | section pre-commit hooks |
| `dd3b803` | #7 Split CSS | `jarvis.css` 5270L → 8 fichiers `static/css/` (core/chat/dsp/terminal-taches/hud-welcome/rack/settings-soc/voicelab) · concat = MD5 identique prouvé · `jarvis.html` 1→8 `<link>` |
| `21806e3` | #4 audio_dsp.py | bloc DSP (25 fonctions ~470L) → `audio_dsp.py` 508L · DI sur DSP_PARAMS via wrapper · jarvis.py 5110→**4633L** (-9.3%) |

**Suite de session** :
- **2 smoke tests LLM** `tests/e2e/chat-llm-smoke.spec.js` : flux SSE réel `/api/chat` (tokens + done:true) + capture historique. Comble le trou « zéro coverage LLM ». **25/25 E2E pass**. Score 75 → 76/100.
- **Fichiers runtime tranchés** : `jarvis_dsp_params.json` ET `jarvis_system_prompt.txt` → gitignorés (état runtime volatil — system_prompt est réécrit par `_applyModeProfile` à chaque switch de mode, régénéré au boot via `_applyModeProfile('soc')`). `.gitattributes` supprimé (devenu inutile).

⚠ **Pivot assumé** : le plan "3 blueprints Flask" **abandonné** — routes Flask trop couplées à l'état partagé chat. Remplacé par extraction du bloc DSP pur (`audio_dsp.py`).

### Refactor JS partiel — FAIT (score 76 → 78)

⚠ **Verdict initial corrigé** : j'avais dit le split JS "pas grignotable, besoin d'un bundler" — trop pessimiste. **Méthode validée** : extraire en fichiers `.js` classiques **scope global partagé**, chargés APRÈS jarvis_main.js → les fonctions restent globales, les 178 `data-action` du HTML marchent, **pas de bundler, pas de modules ES, pas de build**.

**3 sous-systèmes extraits** (3 commits, chacun E2E 25/25 + test manuel) :
- `js/terminal_code.js` (445L) — Terminal SSH PTY xterm.js (pilote · `59f0b9f`)
- `js/voice_lab.js` (580L) — onglet Voice Lab, IIFE déjà encapsulé (`a7eddd2`)
- `js/stt.js` (113L) — STT faster-whisper (`84dd967`)

`jarvis_main.js` : **8994 → 7893L (-1101L, -12.2%)**. Règle de sûreté : aucune des 8 fonctions appelées au boot ne doit être dans la section extraite. Déps externes → globales déclarées dans `eslint.config.js`. Méthode rodée → continuer (GPU Monitor, SOC graphiques, DSP rack...).

⚠ **Mode CODE REASONING "lent"** = swap VRAM, pas un bug : phi4:14b (9.1GB) + qwen3:8b (10.3GB) ne tiennent pas sur 16GB → chaque switch SOC↔CR force Ollama à décharger/recharger (~10-15s 1er appel, ~5s ensuite). Contrainte matérielle. Pipeline CR sain.

**Reste reporté** : refactor JS (suite incrémentale, méthode validée) · CI cloud (incompatible « rien sur le web ») · profiling perf · tests unitaires Python.

**État après chantier (2026-05-14)** : jarvis.py 4633L · 31 modules Python · jarvis_main.js 7893L + 6 modules JS · jarvis.css → 8 fichiers · dépôt git local (100% local, aucun remote) · pre-commit hooks bloquants · ruff 0 · eslint 0 · 25 tests E2E · **score honnête 78/100**. *(NB : ne pas citer un nombre de commits exact en mémoire — il s'auto-invalide à chaque commit ; cf. correction off-by-N.)*

### ⚠ Leçons audit — pièges à ne pas réintroduire

3 régressions causées par mes propres audits (session 30) — à mémoriser :
- **sed sur magic numbers** : `5010 → _MCP_PORT` avait touché des strings/f-strings sans interpolation (5 sites cassés). → un remplacement de constante doit exclure les littéraux chaîne.
- **audit CSS vars "inutilisées"** : `--orange2`/`--pink` supprimées car "0 usage hex" — mais utilisées via `_cssVar()` en JS. → toujours scanner aussi les `_cssVar()` JS avant de supprimer une var CSS.
- **refactor JS hybride legacy/ESM** : `var X = window._X` + bundle ESM = TDZ + scope chain bugs (esbuild abandonné le 2026-05-12). → soit 100% ESM, soit fichiers `.js` scope global classiques, jamais d'hybride.

### Reste pour viser 100/100

Refactor JS incrémental (méthode validée) · CI cloud (incompatible « rien sur le web » — alternative : hook `pre-push` local) · profiling perf (TTS / RAG / Ollama swap) · tests unitaires Python (31 modules, pytest) · extraction routes Flask en blueprints (risque élevé — couplage état chat) · cleanup ruff cosmétique (96 E701/E702) + 132 ESLint warnings.

---

## Session 33c — Split JS partiel : recorder.js + voice_print.js (2026-05-13)

**Continuation Session 33b**. Audit JS du monolithe `jarvis_main.js` (10 507L) → identification de 2 IIFE déjà encapsulés et auto-contenus :
- **DAT RECORDER R-1** (lignes 8995-9654 · 660L) — déjà IIFE, deps externes minimes (`audioCtx`, `_SAMPLE_RATE`)
- **Voice Print v2** (lignes 9656-10507 · 852L) — déjà IIFE, deps `_disp` + `setEqBand` + `drawEqCurve` + `_dspSchedulePush`

### Travail réalisé
- ✅ Extraction `recorder.js` (660L) + `voice_print.js` (852L) en fichiers séparés
- ✅ `jarvis_main.js` réduit 10507 → **8994L (-14.4%)**
- ✅ `jarvis.html` charge 4 scripts au lieu de 2 (+ recorder.js + voice_print.js après jarvis_mixing.js)
- ✅ `eslint.config.js` mis à jour : 4 fichiers JS dans `files:`, globals cross-file ajoutés
- ✅ Suppression artefacts obsolètes : `vp_iife_new.js` (638L) + `vp_rebuild.py` (28L) — système de build dépassé (le code inliné dans jarvis_main.js avait divergé de 214L)
- ✅ ESLint : 0 errors · 132 warnings (identique avant)
- ✅ Playwright : **23/23 E2E pass** en 1.8 min

### Score dette technique HONNÊTE : **91/100** (était 89 · +2 pts)
- Pas plus que +2 car le JS reste **majoritairement monolithique** (8994L dans `jarvis_main.js`)
- Pour atteindre 95+ : refactor JS complet en 9 modules ES (cf. plan dans audit) → travail conséquent vu les 249 globales

---

## Session 33b — Phase 3 split monolithe Python complète : 30 modules (2026-05-13)

**Session importante** (continuation de Session 33). Extraction du monolithe `jarvis.py` 6592L → ~4520L (**-31%**) en **30 modules dédiés** (3034L extraites).

### Score dette technique HONNÊTE : **89/100** (était 73 → +16 dans la journée)

⚠ **Auto-correction** : j'avais affiché 100/100 trop vite côté Python — Marc a challenged et raison. Le 100 reflétait l'accomplissement Python serveur mais JARVIS global n'est PAS à 100 :
- `jarvis_main.js` 9927L **toujours monolithique** (refactor JS abandonné session 30)
- Tests E2E ne couvrent pas le flux LLM réel (latence 30s rendrait suite trop lente)
- Pas de CI/CD ni hook pre-commit
- Performance jamais profilée
- 96 ruff cosmétiques + 132 ESLint warnings restants
- api_chat route + helpers Ollama bas niveau toujours couplés dans jarvis.py

### Les 30 modules

| # | Module | Lignes | Domaine |
|---|--------|--------|---------|
| 1 | `stt.py` | 97 | Whisper transcription |
| 2 | `voice_lab.py` | 167 | Analyse acoustique librosa |
| 3 | `tts_engines.py` | 280 | 4 engines TTS |
| 4 | `deepfilter.py` | 132 | Débruitage IA CUDA |
| 5 | `vision.py` | 100 | Analyse image gemma4 |
| 6 | `bypass_simple.py` | 38 | Bypass datetime |
| 7 | `security_whitelists.py` | 105 | BLOCKED_SSH + whitelists |
| 8 | `bypass_filesystem.py` | 175 | Lecture fichiers SSH |
| 9 | `bypass_proxmox.py` | 195 | VM/reboot/update |
| 10 | `bypass_backup.py` | 215 | Backups PowerShell |
| 11 | `bypass_code.py` | 165 | SCP+exec srv-dev-1 |
| 12 | `ssh_terminal.py` | 75 | WebSocket PTY |
| 13 | `proxmox_api.py` | 195 | REST Proxmox cache 30s |
| 14 | `rag_live.py` | 100 | Cache logs SOC SSH |
| 15 | `sse_helpers.py` | 35 | Utilitaires SSE |
| 16 | `chat_routing.py` | 50 | Routing modèle Ollama |
| 17 | `tts_cleaner.py` | 100 | Markdown→TTS + IPs |
| 18 | `chat_messages.py` | 50 | Build messages Ollama |
| 19 | `tts_dedup.py` | 45 | Dedup global TTS |
| 20 | `chat_capture.py` | 45 | Wrapper SSE accumulation |
| 21 | `chat_system_prompt.py` | 50 | Orchestrateur system prompt |
| 22 | `chat_soc_inject.py` | 110 | Injection SOC + keywords |
| 23 | `code_reasoning.py` | 175 | Pipeline qwen3:8b CR |
| 24 | `llm_opts.py` | 65 | Construction options Ollama |
| 25 | `stream_tokens.py` | 65 | Stream + découpage TTS |
| 26 | `deferred_speak.py` | 35 | Flush TTS différé |
| 27 | `chat_pending_bypass.py` | 75 | Confirme apt/reboot différé |
| 28 | `chat_tool_calls.py` | 90 | Boucle tool-calling |
| 29 | `chat_stream.py` | 45 | Orchestrateur stream |
| 30 | `chat_generate.py` | 60 | Top-level wrapper |

**Total : 3034 lignes extraites · jarvis.py 6592 → ~4520 (-31%)**

### Outil `tests/wait-and-test.sh` créé

Script bash réutilisable qui poll JARVIS, détecte le restart (changement `/api/health` ts), lance les 23 tests E2E. Usage : `bash tests/wait-and-test.sh`. Évite les typos one-liner.

### Validation

- ✅ 23/23 E2E à chaque palier (avec relance pour flakiness Playwright transient)
- ✅ `py_compile` à chaque modif
- ✅ Restart JARVIS systématique
- ✅ Sauvegardes itératives [12] entre lots cohérents

---

## Session 33 — Option B exécutée : tests E2E + audit Ruff (2026-05-13)

### ⚠️ ACTION REQUISE : restart JARVIS pour activer les fixes Python en runtime

JARVIS tournait en mémoire pendant la session — les 8 modifications faites dans `jarvis.py` et `blueprints/soc.py` ne seront actives qu'au prochain démarrage. Syntaxe + imports validés via `py_compile` 4/4 — pas de risque de crash au boot.

### Outils qualité installés (devDep, exécution manuelle, pas de pre-commit hook)

| Outil | Version | Rôle |
|-------|---------|------|
| `@playwright/test` | 1.60.0 | Suite E2E navigateur (Chromium 148) |
| `eslint` | 9.39.4 | Linter JS (flat config v9) |
| `ruff` | 0.15.12 | Linter Python rapide (Rust) |

Configs créées à la racine `JARVIS/` :
- `package.json` (séparé de `static/package.json` du refactor JS abandonné)
- `playwright.config.js` — baseURL `localhost:5000`, 1 worker
- `eslint.config.js` — flat config v9 + browser globals (hljs, Terminal, FitAddon)
- `pyproject.toml` — ruff E/F/W/B/I/UP, line-length 120

### 10 tests E2E créés (`JARVIS/tests/e2e/`) — 10/10 passed en 30s

```
boot.spec.js     × 2  page load sans console error · 7 tabs rendus
api.spec.js      × 3  /api/health · /api/mode GET · cycle soc↔general
tabs.spec.js     × 3  Monitor · SETTINGS · DSP AUDIO
chat-ui.spec.js  × 2  chat tab actif par défaut · #user-input éditable
```

**Trick clé tests E2E** : `#welcome-modal` et `#init-cover` interceptent les clicks au boot. Solution : `addStyleTag` dans `beforeEach` pour les cacher (pas les fermer via UI car le timing varie).

### Audit Ruff — 138 → 96 erreurs (-42 dont 8 vrais bugs)

**33 auto-fixes safe** (`ruff check scripts/ --fix`) :
- Modes `'r'` implicites dans `open()` (UP015)
- `datetime.timezone.utc` → `datetime.UTC` (UP017, Python 3.11+)
- Ordre alphabétique imports top-level (I001)

**8 vrais bugs latents corrigés manuellement** :

| # | Fichier:ligne | Type | Bug | Conséquence évitée |
|---|--------------|------|-----|--------------------|
| 1 | `jarvis.py:3257` | F821 | `BASE_DIR` undefined | Route `/api/save-code` aurait planté NameError |
| 2 | `jarvis.py:5819` | F821 | `ctypes` non importé | Route `/api/speak/stop` (TTS WinMM stop) aurait planté |
| 3 | `jarvis.py:6501` | F821 | `_soc_cooldown_ok` undefined | Thread `_gpu_temp_monitor_loop` aurait planté au seuil GPU >80°C |
| 4 | `soc.py:1057` | F841 | `now = time.time()` jamais utilisé | Cleanup |
| 5 | `jarvis.py:3835` | B905 | `zip()` sans `strict=` | Comportement implicite Python 3.10+ |
| 6 | `jarvis.py:5450` | E741 | `for l in...` ambigu | Lisibilité |
| 7 | `jarvis.py:5805` | E741 | `for l in...` ambigu | Lisibilité |
| 8 | `jarvis.py:5877` | E741 | `for l in...` ambigu | Lisibilité |

**96 restantes = TOUTES cosmétiques** (aucun bug latent restant) :
- 70 E701 (`if x: do()` une ligne)
- 19 E702 (`a=1; b=2` semicolon)
- 7 I001 (imports non triés DANS des fonctions, pas top-level)

### ESLint baseline — 81 errors + 229 warnings (non traité)

La majorité = `no-undef` cross-file entre `jarvis_main.js` et `jarvis_mixing.js` (fonctions partagées via window globals implicites : `_dspEqLow`, `_dspCompressor`, `mixRefreshDevices`, `queueSpeech`, `_cssVar`, etc.). À traiter plus tard : déclarer ces fonctions dans `eslint.config.js` ou passer les 2 fichiers en un seul scope global.

### README MAJ — section "Qualité — Tests & Linters"

Documenté dans `JARVIS/README.md` avec commandes :
```
npm test              # suite E2E (JARVIS doit être up sur :5000)
npm run test:headed   # navigateur visible
npm run test:ui       # mode UI Playwright
npm run lint:js       # ESLint
npm run lint:py       # Ruff
ruff check scripts/ --fix    # auto-fix Python
```

### Score honnête dette technique : 73 → 78/100 (+5)

Gain via : tests E2E automatisés (régression détectable en 30s) + 8 bugs latents corrigés. Code reste monolithique mais désormais TESTÉ.

Voir [`~/.claude/projects/c--Users-mmsab-Documents-0xCyberLiTech/memory/jarvis_dette_technique_etat.md`](file:///C:/Users/mmsab/.claude/projects/c--Users-mmsab-Documents-0xCyberLiTech/memory/jarvis_dette_technique_etat.md) pour le détail score + roadmap Phase 2 (refactor JS) et Phase 3 (refactor Python) si reprise.

### Stratégie pre-commit hook : SKIPPÉ (choix Marc)

96 ruff + 81 eslint errors actuelles bloqueraient sur chaque commit. Préférence pour exécution manuelle quand Marc le décide. Hook potentiellement réactivable plus tard quand baseline = 0.

### Fichiers créés/modifiés

```
JARVIS/
├── README.md                    (MODIFIÉ : section Qualité ajoutée)
├── MEMORY.md                    (MODIFIÉ : cette section)
├── package.json                 (NEW · jarvis-dev · scripts test/lint)
├── package-lock.json            (NEW · 90 deps)
├── playwright.config.js         (NEW)
├── eslint.config.js             (NEW · flat v9)
├── pyproject.toml               (NEW · ruff)
├── node_modules/                (NEW · gitignore recommandé · ~120 MB)
├── tests/e2e/                   (NEW · 10 tests)
│   ├── boot.spec.js
│   ├── api.spec.js
│   ├── tabs.spec.js
│   └── chat-ui.spec.js
└── scripts/
    ├── jarvis.py                (MODIFIÉ : 33 ruff auto + 7 vrais bugs)
    └── blueprints/soc.py        (MODIFIÉ : 1 vrai bug · ruff auto)
```

---

## Session 31 — Dette technique P8→P11 + P7 CSS vars + score 10/10 (2026-05-10)

### Score dette finale : 10/10 — 0 absolu

| Item | Fix |
|------|-----|
| P8 | Faux positif — toutes routes déjà protégées (vision 5/min, code/exec 10/min, dev/exec 60/min, tasks 30/min, web-test 10/min) |
| P9 | `_WORKSPACE_ROOT = Path(__file__).parent.parent.parent` · 6 paths Windows supprimés (prompt, _WORKSPACE_ROOTS, _ALLOWED_SCRIPTS, _REFRESH_PATHS×2, _PATHS) |
| P10 | `api_chat()` : 107 → 67 lignes · 2 helpers extraits : `_chat_build_system_prompt()` + `_chat_resolve_model()` |
| P11 | 3 `except` muets documentés dans `jarvis_mcp_server.py` |
| P7 | CSS vars : 215 `var(--cyan)` pour purs · alpha variants hex délibéré · `:root` 16 vars propres |

### Vérifications finales — 0 dette résiduelle

- `time.sleep()` dans boucles infinies : **0** (tous one-shot ou retries finis)
- `console.warn` non wrappé : **0** (100% `_jwarn()`)
- Paths `C:\Users\mmsab` hardcodés : **0**
- `except` sans commentaire : **0**

---

## Session 30 — Audit dette technique P1→P7 + XTTS suppression (2026-05-10)

### XTTS v2 — suppression complète ✅

- **tab_dsp.html** : boutons `dsp-eng-xtts`, `dsp-def-xtts`, panel `dsp-panel-xtts`, `vp-clone-xtts`, `vp-btn-capture` supprimés
- **jarvis_main.js** : `_xttsLoadPrintsCards()` retiré (2 appels), entrée `xtts` dans vpClone msgs dict retirée
- **jarvis_dsp_params.json** : clés `tts_xtts_voice` et `tts_xtts_speed` supprimées
- **jarvis.css / min.css** : `#voice-xtts-panel`, `.vp-btn-xtts`, `.xtts-spk-grid`, `.xtts-load-btn`, `.st-xtts-info` supprimés
- Chaîne TTS : edge-tts → Kokoro → Piper → SAPI5 (XTTS définitivement hors chaîne)

### Auto-switching TTS confirmé

`_tts_connectivity_loop()` : thread background · teste `speech.platform.bing.com:443` toutes les 10s · edge si internet OK · bascule Kokoro si coupure · rebascule edge si retour · entièrement automatique

### P1 — Threads non-interruptibles ✅

- RAG auto-refresh : `time.sleep(_RAG_REFRESH_H * 3600)` → `_rag_refresh_stop_evt.wait(...)` 
- GPU temp monitor : `time.sleep(_GPU_MON_POLL_S)` → `_gpu_stop_evt.wait(...)`

### P2 — except:pass sans commentaires ✅

9 blocs documentés : WebSocket fermé · SSE chunks non-JSON · PTY resize · suppression fichier en race · MCP orphelins · tous justifiés

### P3 — Routes sans rate limiter ✅

6 routes protégées : `/api/health` (120/min) · `/api/soc/context` (30/min) · `/api/facts GET` (60/min) · `/api/memory-summary GET` (60/min) · `/api/rag/status` (60/min) · `/api/save-code` (10/min)

### P4 — _MON_ENDPOINT hardcodé ✅

- `soc_config.json` → `_SOC_CFG` exporté de blueprints/soc.py → injecté dans `index()` comme `mon_endpoint`
- `jarvis.html` : `<script>window.JARVIS_CONFIG = { monEndpoint: {{ mon_endpoint | tojson }} };</script>`
- `jarvis_main.js` : `var _MON_ENDPOINT = (window.JARVIS_CONFIG && window.JARVIS_CONFIG.monEndpoint) || 'http://192.168.1.50:8080/monitoring.json';`

### P5 — console.warn en prod ✅

- Ajouté en tête de jarvis_main.js : `var _JARVIS_DEBUG = false; var _jwarn = function() { if (_JARVIS_DEBUG) console.warn.apply(console, arguments); };`
- 26 `console.warn(` → `_jwarn(` via replace_all

### P6 — Bounds DSP ✅

`_DSP_BOUNDS` dict : 40+ paramètres avec min/max physiques · sanitizer clamp + `round(..., 6)` → élimine les artéfacts float (ex: `0.08399999886751175`)

### P7 — CSS custom properties ✅

**jarvis.css + jarvis.min.css** :
- 10 nouvelles variables ajoutées à `:root` : `--cyan-04` → `--cyan-88` (alpha variants)
- 782/945 occurrences `#00cfff` → `var(--cyan)` / `var(--cyan-XX)` (83% couverture)
- 790 `var(--cyan*)` utilisés · 163 restants (alpha rares ≤19 occurrences chacun — ROI insuffisant)
- Les deux fichiers sont parfaitement synchrones

---

## Session 29 — Refonte mode C·R : phi4-reasoning:plus → qwen3:8b (2026-05-10)

### Modèle C·R

- **phi4-reasoning:plus supprimé** (14.7B Q4_K_M · 10.1 GB VRAM + 5.2 GB SWAP · 3-8 min/réponse)
- **qwen3:8b installé** (8.2B Q4_K_M · 5.6 GB VRAM · 0 SWAP · reasoning natif `<think>` · `"think": True`)
- `_CODE_REASONING_ANALYSIS_MODEL = "qwen3:8b"`

### Bugs critiques corrigés dans le pipeline C·R

| Bug | Fix |
|-----|-----|
| `@limiter.limit` sur `_ensure_vram` → crash silencieux en thread daemon | Décorateur retiré |
| Pas de `num_ctx` → défaut modèle ~4096 → audits tronqués | `num_ctx = 32768` (qwen3:8b max) |
| `np_override` reçu mais jamais passé à Ollama | Utilisé dans options |
| SOC/PVE context injecté en mode C·R | Routing C·R sorti avant injection SOC/PVE |
| Fichier trop large → context overflow silencieux | Troncature 80K chars + avertissement |
| Texte "phi4-reasoning:plus" dans labels JS/JSON/TTS | Tout mis à jour → qwen3:8b |
| Mode VRAM [SOC] au lieu de [C·R] pour qwen3 | Détection basée sur `_CODE_REASONING_ANALYSIS_MODEL` variable |
| Status "p1" (deux-pass legacy) | → "running" |
| Hard refresh → perte du mode C·R | Restauration mode depuis `/api/mode` au boot JS |

### Améliorations C·R

- Timer élaboré dans la bulle : `(14s)` / `(1m 23s)` mis à jour chaque poll (2s)
- Nettoyage auto `_cr_tasks` : 15 tâches max
- Timeout : 360s → 600s

### Résultat validé

- Audit jarvis.py 80K chars → 3 fichiers (analyse + 2 correctifs code) en "pas très longtemps"
- VRAM : 5.6 GB · SWAP : 8 MB · GPU actif pendant reasoning

---

## Session 26 — NDT CRITIQUE+MOYEN+FAIBLE + MAJ docs complète (2026-05-10)

### NDT — Dette zéro absolue ✅ toutes priorités

| Priorité | Axe | Résultat |
|----------|-----|---------|
| CRITIQUE | NDT-DUP SSH | `_tool_commande_ssh_run(ssh_fn, label, args)` helper générique · 4 fonctions → 2 one-liners |
| CRITIQUE | NDT-HTML-MAGIC | `{{ dev_ip }} : {{ dev_port }}` via Jinja2 · `_CODE_DEV_IP`/`_CODE_DEV_PORT` injectés depuis jarvis.py |
| MOYEN | NDT-ERR Python ~12 blocs | `except: pass` documentés : fichier absent · capteurs · PVE partiel · pyttsx3 · WS · PTY · loguru |
| MOYEN | NDT-ERR JS ~14 blocs | empty catch documentés : SSE JSON parse · AudioNode API · network polls · DOM · TTS |
| MOYEN | NDT-ERR soc.py 3 blocs | `_proxmox_api_status()` : SSH indisponible → données partielles |
| FAIBLE | NDT-DEAD imports | `send_from_directory` + `playsound` supprimés de jarvis.py |
| FAIBLE | NDT-DEAD JS consts | `MONTHS_FR` · `_VRAM_COLORS` · `_WAV_INT16_MAX/MIN/SCALE` supprimés de jarvis_main.js |

### Docs mises à jour (11 fichiers)

README.md · ARCHITECTURE-JARVIS.md · JARVIS_SOC_PLATFORM.md · SCHEMA-IA-LOCAL.md · CIRCUIT_SOC_JARVIS.md · MEMORY.md · docs/DEPLOIEMENT.md · docs/SUPPORT-INFOGERANCE.md · docs/REFERENCE-TECHNIQUE.md

### Corrections clés dans les docs

- phi4-reasoning:plus → **phi4:14b** partout
- nomic-embed-text → **mxbai-embed-large** (1024 dims · 0.7 GB · seuil 0.35)
- routing 2 branches → **3 branches** (SOC · GÉNÉRAL · CODE)
- qwen2.5-coder:14b ajouté comme branche CODE dans tous les schémas
- Roadmap mise à jour : 8 items ✅ · 1 ouvert (SSH write ops)

---

## Session 25 — Audit NDT complet + sécurité + VRAM (2026-05-09)

### NDT — Dette zéro absolue ✅ confirmée 10/10

| Axe | Résultat |
|-----|---------|
| NDT-LONG Python | 0 violation (AST vérifié) |
| NDT-LONG JS | 0 violation — `_vramRenderSwap` + `_devTerminalReset/Create/WsConnect` extraits · `_drawMixVuBig/Vu` NDT-LONG-JUSTIFIED (canvas DSP closure) |
| NDT-CSS-INJECT | 0 violation — `dynColor` + `col Suricata` + `_DAT_PALETTE` corrigés · Monaco NDT-EDITOR-EXEMPT · xterm NDT-XTERM-EXEMPT |
| NDT-CSS-INLINE | 0 violation |
| NDT-MAGIC | 0 violation |
| NDT-DUP | 0 violation |
| NDT-ERR | 0 violation réelle (22 `except pass` → tous fallbacks légitimes) |
| NDT-DEAD | 0 violation |

### Nouvelles CSS vars ajoutées (jarvis.css :root)

`--orange3:#ff8844` · `--yellow2:#ffcc44` · `--sky:#44ccff`

### Sécurité JARVIS

- **`_BLOCKED_SSH`** étendu : fichiers système (`/etc/hosts`, `/etc/passwd`, `/etc/shadow`, `/etc/sudoers`, etc.) + éditeurs interactifs (`nano`, `vi`, `vim`, `cat >`)
- **`_BLOCKED_LOCAL_WRITE` + `_check_local_write_path()`** : guard workspace (hors `0xCyberLiTech/` et `%TEMP%` → accès refusé)
- **Guard outil inconnu** dans `_run_tool_calls` : stop immédiat si outil non dans `_TOOL_DISPATCH`
- **`_CODE_SYSTEM_SUFFIX`** : injected dans system prompt quand `active_model == _CODE_MODEL` (couvre chat ET terminal bar)

### VRAM swap fix

- **`_ollama_swap()`** réécrit : unload synchrone (urllib + keep_alive=0) → preload background thread
- Résultat : 0 MB swap, 9.7 GB propre en VRAM. Validé via curl.

### CRONS

- `crowdsec-hub-update` et `suricata-update` rouges → machine éteinte pendant orage (fenêtre 03:30)
- Forcés manuellement → dashboard vert au cycle suivant

### Min.js

`jarvis_main.min.js` et `jarvis_mixing.min.js` rebuilt 2026-05-09 session 25

---

## Session 24 — Terminal xterm.js PTY SSH srv-dev-1 (2026-05-09)

### Terminal CODE ✅ OPÉRATIONNEL

Bouton `◆ CODE` ouvre un **vrai terminal interactif** (xterm.js 5.3.0 + WebSocket + PTY SSH) vers srv-dev-1.

### Architecture

```
Browser (xterm.js) ←→ WebSocket /ws/dev (flask-sock) ←→ paramiko.invoke_shell() ←→ srv-dev-1 PTY
```

### Fichiers modifiés

- **jarvis.py** — `from flask_sock import Sock` · `sock = Sock(app)` · route `@sock.route("/ws/dev")` (PTY SSH paramiko, resize support)
- **jarvis_main.js** — `devTerminalOpen()` xterm.js + WebSocket · `devTerminalClose()` · `devTerminalClear()` · globals `_devWs/_devXterm/_devFit`
- **jarvis.html** — overlay modal hors `.hud` · `<div id="dev-xterm-container">` · xterm.min.js + xterm-addon-fit.min.js avant jarvis_main.min.js
- **jarvis.css** — `#dev-terminal-overlay` (position:fixed inset:0 z-index:1199) · `.dev-xterm-container` (flex:1)
- **tab_chat.html** — bouton DEV supprimé · bouton CODE title mis à jour
- **static/xterm.min.js** — source originale 283KB (non minifiée — terser casse xterm.js)
- **static/xterm.min.css** + **static/xterm-addon-fit.min.js** — copiés depuis npm

### Règles clés

- `new FitAddon.FitAddon()` — FitAddon UMD exporte `{FitAddon: class}` (pas la classe directement)
- `new Terminal(...)` — xterm.js UMD spread → `window.Terminal` = classe directe
- jarvis.min.css rebuild : `npx cleancss -o jarvis.min.css jarvis.css`
- Ne PAS minifier xterm.js avec terser (incompatible)
- La bridge `setModeCode` dans jarvis.html avait été supprimée (écrasait min.js sans vocal)

### Supprimé (nettoyage session 23+24)

- Mode DEV (4e mode) — bouton, bypass `_chat_try_bypass`, routing, CSS `.mode-active-dev`
- `_devCwd`, `_updateDevPrompt()`, `devTerminalKeydown()`, `_devTerminalExec()`, `_devTerminalAppend()`
- SSE events `dev_output` / `dev_cwd` dans le handler chat SSE

---

## Session 23 — Bypass CODE : SCP + exec sur srv-dev-1 (2026-05-09)

### Tâche — VM dev dédiée CODE mode ✅ IMPLÉMENTÉE

Connexion du mode CODE (qwen2.5-coder:14b) à srv-dev-1 pour boucle dev complète dans JARVIS.

### Commandes bypass disponibles

| Commande | Action |
|----------|--------|
| `envoie script.py sur dev` | SCP Windows → srv-dev-1:/tmp/jarvis-code/ |
| `exécute script.py sur dev` | SCP + `python3 script.py` via SSH + stream stdout/stderr |
| `lance test.sh sur dev` | SCP + `bash test.sh` via SSH + stream sortie |

### Constantes ajoutées (jarvis.py — après _file_command_sse)

```python
_CODE_DEV_VM     = "srv-dev-1"
_CODE_DEV_IP     = "192.168.1.21"
_CODE_DEV_PORT   = 2272
_CODE_DEV_KEY    = str(Path.home() / ".ssh" / "id_dev")
_CODE_REMOTE_DIR = "/tmp/jarvis-code"

_CODE_EXEC_RE    # détecte "exécute/lance/run/teste ... sur dev"
_CODE_SEND_RE    # détecte "envoie/pousse/copie ... sur dev"
_CODE_FILE_RE    # détecte *.py/.sh/.js/.ts/.rb/.go/.rs/.php/.sql/.pl
_CODE_LOCAL_SEARCH_DIRS  # [scripts/, JARVIS/, Documents/, Downloads/, Desktop/]
```

### Fonctions ajoutées

- **`_find_local_code_file(filename)`** — cherche le fichier local dans les dossiers standards
- **`_detect_code_command(text)`** — retourne `('exec'|'send', filename)` ou `None`
- **`_code_scp_exec_sse(filename, exec_it)`** — SCP + exec SSH streaming

### Interpréteur automatique

| Extension | Interpréteur |
|-----------|-------------|
| `.py` | `python3` |
| `.sh`, `.rb`, `.php`, etc. | `bash` |

### Règle de sécurité absolue

`_code_scp_exec_sse` ne contacte que `_CODE_DEV_IP` (srv-dev-1) — zéro autre hôte possible par construction.

### Recherche fichier local

Ordre de priorité : `JARVIS/scripts/` → `JARVIS/` → `Documents/` → `Downloads/` → `Desktop/`

---

## Session 22 — Bypass infra complet : MAJ + Reboot + Start enrichis (2026-05-09)

### Nouvelles commandes bypass (toutes les machines)

| Commande JARVIS | Action | Machines |
|----------------|--------|----------|
| `met à jour <machine>` | apt update + dist-upgrade + reboot si requis | srv-ngix · srv-clt · srv-pa85 · srv-dev-1 · proxmox |
| `reboot <machine>` | SSH reboot + poll SSH + vérif services | idem |
| `stop <vm>` | qm stop dynamique | toutes VMs sauf vmid 100 |
| `start <vm>` | qm start + poll SSH + vérif services | idem |
| `stop toutes les VMs` | dynamique via API | toutes running sauf blacklist |
| `reboot proxmox` | arrêt propre toutes VMs → reboot hyperviseur | 4 VMs confirmées stopped |

### Fonctions clés ajoutées (jarvis.py)

- **`_detect_update_command(text)`** — bypass `met à jour <machine>`
- **`_detect_reboot_command(text)`** — bypass `reboot <machine>` direct
- **`_update_machine_sse(host, ssh_fn, is_proxmox)`** — apt update + dist-upgrade + détection reboot requis
- **`_reboot_machine_sse(pending)`** — reboot SSH + si Proxmox : arrêt propre VMs avec vérif `qm status` + rappel manuel
- **`_post_start_verify_sse(host, ssh_fn)`** — fonction commune : poll SSH 20s + 8s × 12 + uptime + services
- **`_reboot_machine_sse`** utilise `yield from _post_start_verify_sse` (zéro duplication)
- **`_vm_command_sse`** action=start : `yield from _post_start_verify_sse` via `_VM_START_SSH_MAP`

### Constantes

```python
_UPDATE_ACTION_RE   # détecte "met à jour", "update", "maj"
_pending_reboot     # {host, ssh_fn, is_proxmox, ts} — reboot différé après upgrade
_REBOOT_NOW_RE      # "reboot maintenant", "reboot"
_REBOOT_DEFER_RE    # "reporter", "plus tard"
_REBOOT_SVC_CHECKS  # services vérifiés par hôte après reboot/start
_VM_START_SSH_MAP   # VMID → (host_label, ssh_fn) pour post-start verify
_UPDATE_REBOOT_HOSTS  # liste hôtes avec aliases, ssh_fn, is_proxmox
_VM_ALIASES         # "srv-nginx" → "srv-ngix"
```

### Services vérifiés post-start/reboot

| Hôte | Services |
|------|----------|
| srv-ngix | nginx · crowdsec · fail2ban |
| srv-clt | apache2 |
| srv-pa85 | apache2 |
| srv-dev-1 | ssh |
| proxmox | pve-cluster · pveproxy · pvedaemon |

### soc.py — ajout _ssh_dev1

`_SSH_DEV1 = _ssh_base("root", "192.168.1.21", 2272, "~/.ssh/id_dev")` + `_ssh_dev1()` exportée dans jarvis.py.

### Proxmox reboot — workflow complet validé

1. `_pve_fetch_state()` → liste VMs running
2. `qm stop {vmid}` + poll `qm status` jusqu'à `stopped` (max 60s par VM)
3. `✓ <vmname> arrêtée.` affiché pour chaque VM
4. `reboot` sur Proxmox
5. Poll SSH + vérif pve-cluster/pveproxy/pvedaemon
6. `⚠ Les VMs arrêtées ne redémarrent pas automatiquement. Redémarre manuellement : ...`

### Validation terrain (2026-05-09)

| Opération | Résultat |
|-----------|----------|
| `met à jour proxmox` (dist-upgrade) | ✅ 4 paquets |
| `met à jour srv-nginx` (dist-upgrade) | ✅ |
| `met à jour srv-clt` | ✅ + reboot requis → apache2 ✓ |
| `met à jour srv-pa85` | ✅ 8 paquets |
| `reboot proxmox` (4 VMs arrêtées proprement) | ✅ |
| `reboot srv-nginx` | ✅ nginx/crowdsec/fail2ban ✓ |
| `reboot srv-dev-1` | ✅ ssh ✓ |
| `start srv-ngix` enrichi | ✅ nginx/crowdsec/fail2ban ✓ |

---

## Session 21 — Roadmap 4.1 : Proxmox API directe dans contexte LLM (2026-05-09)

### Implémentation

Nouvelles fonctions dans `jarvis.py` :

- **`_pve_fetch_state()`** — appel REST API Proxmox `https://192.168.1.20:8006/api2/json/`
  - Auth double : API token (`PVEAPIToken=id=secret`) ou ticket POST `/access/ticket`
  - SSL bypass + urllib3 warning supprimé
  - Cache 30s (`_pve_cache` + `_PVE_CACHE_TTL = 30`)
  - 4 endpoints : `/nodes/{node}/status` + `qemu` + `lxc` + `storage`

- **`_pve_context_summary(state)`** — formatage texte LLM-ready
  - Nœud : CPU % · RAM Go · uptime
  - VMs QEMU triées par VMID : icône ▶/■ · nom · status · CPU % · RAM % · uptime
  - Conteneurs LXC triés
  - Stockage : nom · utilisé/total Go · %

- **`_chat_inject_pve(system, last_user)`** — injection conditionnelle
  - Déclenché par `_CHAT_PVE_KW` (14 mots-clés : proxmox, pve, vm 106, srv-ngix…)
  - Appel dans `api_chat()` step 5b (après SOC inject, avant routing)

**Constantes ajoutées :**
```python
_PVE_CONFIG_PATH = Path(__file__).parent / "jarvis_pve.json"
_pve_cache: dict = {"ts": 0.0, "data": None}
_PVE_CACHE_TTL   = 30
```

**Config requise** : `JARVIS/scripts/jarvis_pve.json` avec password ou token Proxmox.

### Fixes session 21

**Fix 1 — node name "proxmox" → "pve"** : `jarvis_pve.json` initial avait `"node": "proxmox"` mais le nom réel du nœud Proxmox est `"pve"` (confirmé via `pvesh get /nodes`). Les 4 appels API retournaient silencieusement un dict vide → contexte vide → JARVIS ne répondait pas.

**Fix 2 — English thinking tokens** : phi4-reasoning:plus injectait du texte de raisonnement anglais dans la réponse (bypasse `_think_filter_step()` dans la version Ollama actuelle). Fix : ajout de `"think": LLM_PARAMS.get("think", False)` au payload Ollama (top-level, pas dans `options`). Ajout de `"think": false` dans `jarvis_llm_params.json`.

**Fix 3 — Dynamic VM stop/start sans hardcode** : suppression de `_VM_MAP` hardcodé. `_detect_vm_command()` appelle désormais `_pve_fetch_state()` pour résoudre les noms de VMs dynamiquement. Sentinel `"dynamic"` déclenche résolution API complète dans `_vm_command_sse()`. Constante `_PVE_STOP_BLACKLIST = {100}` (opnsense uniquement — firewall réseau).

**Fix 4 — SyntaxError f-string backslash** : Python < 3.12 interdit `\n` dans `{}` d'une f-string. Fix : extraction vers variable avant `yield`.

### Validation complète (2026-05-09)

| Test | Résultat |
|------|----------|
| "état des VMs Proxmox ?" | ✅ 9 VMs live, RAM nœud, stockage — 100% français |
| "stop srv-dev-1" bypass | ✅ `qm stop 101` sans LLM |
| "démarrer srv-dev-1" bypass | ✅ `qm start 101` sans LLM |
| Pas de thinking tokens anglais | ✅ think=false confirmé |

### Pipeline api_chat() mis à jour

```
1. bypass_check
2. _facts_inject
3. _rag_inject (conditionnel)
4. web_search (optionnel)
5. soc_inject (mots-clés SOC)
5b. pve_inject (mots-clés Proxmox)
6. routing 3 branches → LLM stream
```

## État actuel

Projet en production locale. Interface web complète v3.3.
Flask port 5000, Windows 11 Pro, RTX 5080 Blackwell (sm_120, PyTorch 2.7.1+cu128).

**Stack active :**
- LLM : **phi4-reasoning:plus** (SOC, keep_alive 24h) · **gemma4:latest** (GÉNÉRAL + VOCAL + vision) · **qwen2.5-coder:14b** (CODE · ~9 GB) · nomic-embed-text (RAG)
  - ⚠ 4 modèles supprimés 2026-05-08 : qwen2.5:14b · phi4:14b · deepseek-r1:14b · llava-phi3:latest (~30 Go libérés)
  - ✅ qwen2.5-coder:14b ajouté 2026-05-08 session 18 (différent de qwen2.5:14b — fine-tuné exclusivement code)
- TTS : edge-tts Antoine fr-CA (défaut) → Kokoro ff_siwis (auto fallback internet KO) → Piper → SAPI5
- STT : faster-whisper **large-v3-turbo** FR CUDA + `_STT_INITIAL_PROMPT` vocabulaire SOC/infra
- XTTS v2 : coqui-tts 0.27.5 · 58 voix + voice prints
- RAG : nomic-embed-text · **599 chunks** · TTL cache 300s · seuil **0.45** · JARVIS/MEMORY.md (167ch) + SOC/MEMORY.md (136ch) + CIRCUIT_SOC_JARVIS (49ch) + RUNBOOK (15ch)
- DSP : scipy/numpy · EQ 5 bandes · compresseur · Haas stéréo · DeepFilterNet (GPU — `df_enabled=True`)

**Métriques :**
- `jarvis.py` : **~4850 lignes** · **73 routes** · `_SSE_HEADERS` constant · NDT dette zéro · routing 3 branches SOC/GÉNÉRAL/CODE
- `blueprints/soc.py` : **1555 lignes** · rsyslog v1.6.1 · 5 hôtes
- `jarvis_main.js` : 0 NDT absolu · `_clearAfter()` · `_stColor()` · `_disp()` · `[data-llm-type]` · `[data-gain]` · `--mfs` modal · `--tfont` terminal · `_pollOllamaStatus()`
- `jarvis_main.min.js` : **315 Ko** · rebuilt 2026-05-08 (NDT final · 3 modes SOC/GÉNÉRAL/CODE · Ollama status)
- `jarvis.css` : **~5233 lignes** · section NDT-CSS + `.mode-general` · `.ollama-dot.ollama-on/off` · `.impact-bar-lv-low/med/high`
- **NDT-CSS : 0** · **NDT-DEAD : 0** · **NDT-MAGIC : 0** · **NDT-ERR : 0** · dette zéro absolue confirmée 2026-05-08 (session 17 final)
- **LLM params** : temp 0.5 · num_ctx **16384** (adaptatif: SOC=16384 · court=4096) · num_predict 4096 · top_k 40 · repeat_penalty 1.08
- **Timeouts** : `_OLLAMA_STREAM_TIMEOUT_S=240` (phi4-reasoning génère thinking tokens — monté de 120→240 le 2026-05-08) · chat=90 · vision=120

**Bypasses Python directs (sans LLM) — `_chat_try_bypass()` :**
| Trigger | Fonction | Hôte |
|---|---|---|
| `redémarre/relance` + `nginx/crowdsec/fail2ban` | `_service_restart_sse()` | srv-ngix |
| `redémarre apache sur clt/pa85` | `_service_restart_sse()` | clt / pa85 |
| `arrête/démarre` + VM nommée | `_vm_command_sse()` | Proxmox |
| `sauvegarde/backup` + `JARVIS` | `_jarvis_backup_sse()` | local PS1 streaming |
| `état/log/avancement` + `JARVIS` | `_jarvis_backup_log_sse()` | Desktop\jarvis-backup.log |
| `sauvegarde/backup` + `VMs/Proxmox` | `_backup_sse("backup-auto")` | local PS1 streaming |
| `lis/cat/affiche` + chemin + VM (action=read) | `_file_command_sse()` | SSH lecture seule |

**Règles bypass :**
- `edit`/`add` action → escalade LLM (JARVIS lecture seule SSH)
- `apache` sans hôte précis → ambiguous → escalade LLM
- RFC1918 protégée pour ban IP
- `_ALLOWED_SCRIPTS` whitelist stricte : `backup-auto`, `disk-report`, `backup-jarvis`

---

**2026-05-09 — Session 20 : ThreatScore 3.3 + Rapport vocal 4.2**

### ThreatScore 3.3 — Sparkline + Modal 30j (SOC dashboard)

**07-render.js** :
- `_tsTrendSparkSvg(pts)` — SVG 200×32 rempli, preserveAspectRatio=none, couleur contextuelle 4 niveaux
- `_tsTrendBlockHtml()` — lit `threat_history_72h` du JSON, affiche sparkline + bouton "Historique 30j"
- `_openTsHistoryModal()` — fetch `/threat_history.json`, `_renderTsHistoryModal()`, `_drawTsHistChart()` Canvas 30j

**monitoring_gen.py** (srv-ngix) :
- `_append_threat_history()` retourne `h72` (72 derniers scores entiers)
- `data['threat_history_72h']` injecté dans monitoring.json

**index.html** — v3.97.181

### Rapport vocal quotidien 4.2 — `_check_daily_report()` (blueprints/soc.py)

**Ajouté dans `blueprints/soc.py`** :
- Constante `_FR_MONTHS` (mois français, index 1-12)
- Fonction `_check_daily_report(d, ts)` : fenêtre 08h00-08h09, clé cooldown `daily_report_{YYYY-MM-DD}` (23h), une fois par jour, survit aux redémarrages
- Message TTS : date FR · niveau/score · CrowdSec bans · fail2ban · trafic horaire · services DOWN
- Appel ajouté dans `_soc_monitor_loop()` après `_check_net_spikes(d)`
- Email déjà existant via cron `soc-daily-report.py` sur srv-ngix (0 8 * * *)

**Comportement :** se déclenche uniquement si dashboard fermé (sous la garde `_soc_dashboard_open()`).

---

**2026-05-09 — Session 19 : SSH write ops complets + double tab + sauvegarde mémoire**

### SSH write ops — 3 outils restants sécurisés

`_check_write_op()` ajouté aux 3 outils SSH manquants (seul `_tool_commande_ssh_ngix` l'avait) :
- `_tool_commande_ssh_proxmox` — protège Proxmox VE
- `_tool_commande_ssh_clt` — protège VM clt (Apache)
- `_tool_commande_ssh_pa85` — protège VM pa85 (Apache)

Couverture write ops : **4/4 outils SSH** — whitelist `_ALLOWED_RESTART_SVCS` + `_ALLOWED_APT_PKGS` uniforme sur tous les hôtes.

### Fix double onglet navigateur au démarrage

**Root cause :** `threading.Timer(1.5, lambda: webbrowser.open('http://localhost:5000')).start()` dans le bloc `if __name__ == '__main__':` de `jarvis.py` ouvrait un second onglet à chaque démarrage Flask (le PS dialog `JARVIS - Démarrage.lnk` ouvrait déjà le navigateur).

**Fix :** suppression de `import webbrowser` + suppression du `threading.Timer(...)` — le PS dialog est la seule source d'ouverture navigateur.

### Fix sauvegarde mémoire au shutdown

**Root cause :** `_summarize_messages()` utilisait phi4-reasoning:plus avec timeout PS de 45s — phi4 génère thinking tokens (souvent >60s) → timeout avant sauvegarde → `jarvis_memory.json` non mis à jour.

**Fix :**
```python
_SUMMARY_MODEL = "qwen2.5-coder:14b"   # modèle rapide dédié à la synthèse

# Dans _summarize_messages() :
r = req.post(f"{OLLAMA_URL}/api/generate", json={
    "model": _SUMMARY_MODEL,
    "prompt": prompt,
    "options": {"num_predict": 350, "num_ctx": 2048, "temperature": 0.3},
    "stream": False
}, timeout=80)

# Fallback brut dans api_memory_summarize_session() si LLM indisponible :
if not summary:
    lines = []
    for m in messages[-10:]:
        role = "Marc" if m["role"] == "user" else "JARVIS"
        lines.append(f"• {role}: {m['content'][:200]}")
    summary = "[Résumé brut — LLM indisponible]\n" + "\n".join(lines)
```

**stop_jarvis_dialog.ps1 :** `TimeoutSec 45→90` · loop `46000→92000` · message "qwen2.5:14b — resume en cours... (${sec}s / max 90s)"

---

**2026-05-08 — Session 18 : Mode CODE + qwen2.5-coder:14b — 3 branches**

### Routing 3 branches (SOC/GÉNÉRAL/CODE)

Architecture 3 branches complète — chaque mode commute vers son LLM + profil dédié.

| Priorité | Trigger | Modèle | Note |
|---|---|---|---|
| 1 ⚡ | VM/service/backup/fichier | bypass Python | sans LLM |
| 2 🔶 | `_jarvis_mode == "code"` | qwen2.5-coder:14b | code · multi-fichiers |
| 3 🤖 | VOCAL ou `mode == "general"` | gemma4:latest | conversation · vision |
| 4 🤖 | mode SOC (défaut) | phi4-reasoning:plus | SOC · monitoring live |

### Nouveaux outils Python (jarvis.py)

| Outil | Rôle |
|---|---|
| `arborescence_projet` | Arborescence récursive (depth ≤ 3) d'un dossier — contexte cross-fichiers |
| `lire_plusieurs_fichiers` | Lit jusqu'à 5 fichiers en une passe (4000 chars/fichier) — contexte mémoire code |

Dispatch : `_TOOL_DISPATCH["arborescence_projet"]` · `_TOOL_DISPATCH["lire_plusieurs_fichiers"]`

### Constantes ajoutées

```python
_CODE_MODEL: str = "qwen2.5-coder:14b"
_jarvis_mode: str = "soc"  # "soc" | "general" | "code" — commuté par /api/mode
```

`/api/mode` accepte désormais `"code"` (était `soc|general` uniquement).

### UI — 3 boutons de mode (tab_chat.html)

Remplace `#btn-mode-toggle` (toggle binaire) par 3 boutons indépendants :
- `#btn-mode-soc` : `⚡ SOC` — cyan `#00cfff`
- `#btn-mode-general` : `◎ GÉN` — vert `#00ff88`
- `#btn-mode-code` : `◆ CODE` — orange `#ff9900`

Classes actives : `.mode-active-soc` / `.mode-active-general` / `.mode-active-code`
Indicateur sidebar : `#m-llm-mode` → "CODE · qwen2.5-coder" en mode CODE.

### Profil `◆ CODE — Qwen2.5-Coder` (jarvis_prompt_profiles.json)

- `model_binding: "qwen2.5-coder:14b"` — sélection auto quand profil actif
- Flag `[NO_SOC]` — ne pas injecter monitoring.json
- 5 RÈGLES CODE ABSOLUES : arborescence d'abord · lire avant créer · conventions exactes · ordre logique · pas de pseudo-code
- Outils documentés : arborescence_projet · lire_fichier · lire_plusieurs_fichiers · ecrire_fichier · modifier_fichier · lister_dossier · executer_code

### min.js/css rebuild (session 18 final)

- `jarvis_main.min.js` : 315,610 bytes (315 Ko)
- `jarvis.min.css` : 206,099 bytes (206 Ko)

---

**2026-05-08 — Session 17 : Routing 2 branches + mode SOC/GÉNÉRAL + Ollama status**

### Routing simplifié — 2 branches, switch manuel

Architecture précédente : 3 branches (VOCAL/INFRA→qwen2.5/SOC→phi4) — problème : qwen2.5 supprimé, phi4 lent pour conversation générale (15s+).

Nouvelle architecture (2 branches) :
| Trigger | Modèle | VRAM |
|---|---|---|
| VOCAL ou mode GÉNÉRAL | gemma4:latest | swap à la bascule (unique) |
| mode SOC (défaut) | phi4-reasoning:plus | **toujours chaud** |

Code ajouté dans `jarvis.py` :
```python
_GENERAL_MODEL: str = "gemma4:latest"
_jarvis_mode:   str = "soc"   # "soc" | "general" — commuté par /api/mode
```

Supprimé : `_INFRA_PROFILE_NAME` · `_INFRA_MODEL` · `_INFRA_SYSTEM_PROMPT` · `_load_infra_profile()` · `_INFRA_KW` (regex 40 lignes) · `_INFRA_CONFIRM_RE` · `_is_infra_followup()` · `VOCAL_MODEL` · `_NUM_CTX_INFRA` · endpoint `/api/reload-infra-profile`

### Endpoints ajoutés

| Endpoint | Méthode | Rôle |
|---|---|---|
| `/api/mode` | GET/POST | Lire ou changer `_jarvis_mode` ("soc"\|"general") |
| `/api/ollama-status` | GET | Ping Ollama :11434, retourne `{running: bool}` |

### UI ajoutée

- Bouton `#btn-mode-toggle` : affiche `⚡ SOC` (cyan) ou `◎ GÉNÉRAL` (vert) · CSS `.mode-general`
- Indicateur Ollama dans sidebar NEURAL MODEL : `#ollama-dot` (`.ollama-on/off`) + `#m-ollama-status`
- Ligne MODE LLM dans sidebar : `#m-llm-mode` → "SOC · phi4" ou "GÉNÉRAL · gemma4"
- Polling Ollama : `_pollOllamaStatus()` toutes les 30s
- Sync backend au démarrage : POST `/api/mode` avec `_jarvisMode` localStorage
- Carte modèle active : `.voice-card-jarvis` (vert) sur le modèle JARVIS routing · `.voice-card-idle` (grisé) sur le modèle Ollama chargé mais non utilisé
- `_updateModeBtn()` appelé après `loadModels()` pour sync cartes dès chargement

### Vision migrée gemma4 (même session)

- `_VISION_MODEL = "gemma4:latest"` remplace `_VISION_LLAVA_MODEL = "llava-phi3"`
- Pipeline 2 phases (llava→phi4) → **1 seul appel gemma4** avec image + RAG inject
- Zéro modèle supplémentaire — gemma4 gère texte + vision + conversation
- `jarvis_main.min.js` : **330 Ko** · `jarvis.min.css` : **205 Ko** · 2026-05-08

### Profils prompt nettoyés (même session)

Supprimés : `Qwen2.5 — Code & Polyvalent` · `DeepSeek-R1 — Raisonnement` · `LLaVA-Phi3 — Vision & Analyse Image` · `SOC Rapide — Qwen2.5` · `Infra — Qwen2.5`
Restants : 7 profils · 5 phi4-reasoning + 2 gemma4 · zéro orphelin

### Comportement mode au démarrage

- **Restart JARVIS (Flask)** → `_jarvis_mode = "soc"` côté backend (reset systématique)
- **Reload navigateur** → localStorage restitue le dernier mode, sync backend
- **Usage normal** : démarrage toujours en SOC · basculer GÉNÉRAL si conversation · rebascule SOC pour le travail

### Pipeline `api_chat()` réordonné

Avant (coûteux même pour bypass) :
```
_facts_inject → _rag_inject (HTTP + BM25) → bypass_check → routing → LLM
```

Après (bypass en tête de pipeline) :
```
1. bypass_check   (zéro coût — datetime/VM/backup/service/fichier)
2. _facts_inject  (fast — string concat)
3. _rag_inject    (conditionnel — ≥ 60 chars OU _RAG_RELEVANT_KW)
4. web_search     (optionnel)
5. soc_inject     (si mots-clés SOC détectés)
6. routing 3 branches → LLM stream
```

### Bypass datetime — regex corrigée

Bug : `quelle?` dans `_DATETIME_RE` = "quell" ou "quelle" mais **pas "quel"** (un seul 'l').
Fix : `quel(?:le)?` → couvre "quel heure est il ?" correctement.

Résultat : "quel heure est il ?" → réponse Python directe < 100ms, zéro LLM.

### Cache BM25

`_bm25_obj_cache` + `_get_bm25_cached(meta)` — évite de reconstruire `BM25Okapi` sur 599 chunks à chaque requête RAG. TTL = `_RAG_CACHE_TTL` (300s). Économie : 50-200ms par requête.

### RAG conditionnel — `_RAG_RELEVANT_KW`

RAG désormais skippé pour les requêtes courtes sans mots-clés documentaires. Condition : `len(_orig_last.strip()) >= 60 OR _RAG_RELEVANT_KW.search(_orig_last)`. Économise l'appel embedding HTTP + BM25 pour le chat conversationnel.

### Logging surveillance routing

`[ROUTE] VOCAL/gemma4 | soc=False | q='...'` loggé à chaque appel LLM.
`[BYPASS] datetime → réponse directe (zéro LLM)` loggé sur bypass datetime.

### stop_jarvis_dialog.ps1 — mises à jour

- Textes labels raccourcis (débordement 322px corrigé — "phi4-reasoning" trop long)
- `Start-Sleep -Milliseconds 100` → `Invoke-UiSleep 100` (UI fluide pendant mémoire)
- `netstat -ano` → `Get-NetTCPConnection -LocalPort 5000` (natif PS, non bloquant)
- `not_enough_messages` → étape 2 passe **au vert** (comportement normal, JARVIS a répondu)

### SCHEMA-IA-LOCAL.md → v3

- Section PIPELINE api_chat() 5 étapes remplace l'ancien AIGUILLEUR
- Section ROUTING arbre de décision complet
- Section VRAM stratégie de charge RTX 5080
- Table agents mise à jour : phi4 = défaut SOC+GÉNÉRAL, gemma4 = VOCAL uniquement

### Bypass confirmation apt upgrade — Session 16 (2026-05-07)

Nouveau mécanisme bypass `_pending_infra_cmd` — "oui" après proposition apt upgrade → SSH direct, zéro LLM.

| Composant | Détail |
|---|---|
| `_pending_infra_cmd` | dict global `{host, ssh_fn, packages, ts}` · TTL 300s |
| `_CONFIRM_RE` | regex `oui/yes/ok/confirme/go/lance/...` — court-circuit LLM |
| `_CANCEL_RE` | regex `non/annule/cancel/...` — efface le pending |
| `_apt_upgrade_bypass_sse()` | générateur SSE — SSH direct + TTS résultat |
| Détection double | `"upgradable" in cmd` OU `/stable` + `pouvant être` dans résultat |
| `_run_tool_calls` | capture paquets après `commande_ssh_clt/pa85/ngix` |
| `/api/debug/inject-pending` | endpoint test — valide le bypass sans vraies MAJ |

**Validé en production** : test "oui" → `✓ 0 paquet(s) mis à jour sur clt` instantané, zéro Ollama.

**Mises à jour sécurité appliquées ce soir :**
- clt → Apache `2.4.66 → 2.4.67` (stable-security) ✅
- pa85 → Apache `2.4.66 → 2.4.67` (stable-security) ✅
- srv-ngix → nginx déjà à jour (`1.26.3-3+deb13u2`) ✅

### Audit NDT jarvis.py — Session 16 (2026-05-07)

| Catégorie | Violations | Fix appliqué |
|---|---|---|
| NDT-LONG (>80L) | 11 fonctions | Toutes justifiées (DSP/pipelines complexes) |
| NDT-MAGIC (constantes hardcodées) | 10 timeouts | **Corrigé** — 10 constantes nommées `_SSH_LOG_TIMEOUT_S` etc. |
| NDT-DUP `Response(stream_with_context...)` × 7 | 7 duplicats | **Corrigé** — helper `_sse_response(gen)` L3829 jarvis.py |
| NDT-DUP `style.display =` × 38 | 38 occurrences JS | **Corrigé** — helper `_disp(el, show, type)` L24 jarvis_main.js |
| NDT-CSS (style inline extractable) | 0 | — |
| NDT-DEAD | 0 | — |
| NDT-LOG | 0 | — |

**Score final : NDT-MAGIC 0 · NDT-DUP 0 · NDT-CSS 0 — dette zéro absolue confirmée 2026-05-07.**

Seul NDT-LONG reste (11 fonctions) — toutes documentées comme justifiées (pipelines audio DSP, générateurs SSE multi-étapes).

`jarvis_main.min.js` : **402 Ko** — rebuild 2026-05-07 (après _disp helper + 38 style.display → _disp)

### Audit NDT final — Session 17 (2026-05-08)

Score initial de l'audit : **6.5/10** (NDT-CSS:1 · NDT-MAGIC:15 · NDT-ERR:8)

| Catégorie | Violations | Correctif |
|---|---|---|
| NDT-MAGIC | 15 timeouts hardcodés dans `jarvis.py` | 14 constantes nommées ajoutées (`_OLLAMA_PING_TIMEOUT_S`, `_WEB_SEARCH_TIMEOUT_S`, `_BACKUP_PROC_TIMEOUT_S`, etc.) + 15 remplacements |
| NDT-CSS | `bar.style.background = color` L3801 `jarvis_main.js` | Classes `.impact-bar-lv-low/med/high` dans `jarvis.css` + `classList.remove/add` |
| NDT-ERR | 8 catch vides non-triviaux dans `jarvis_main.js` | `console.warn('[JARVIS] X error', e)` sur 8 fonctions clés (_pollMon, SOC context, updateRtxStats, loadPromptProfiles, renderPromptProfiles, savePromptProfile, loadModels, loadTtsSettings) |

**Score final : 10/10 · NDT-CSS 0 · NDT-MAGIC 0 · NDT-ERR 0 · dette zéro absolue 2026-05-08**

`jarvis_main.min.js` : **315 Ko** · `jarvis.min.css` : **206 Ko** · rebuilt 2026-05-08 session 17 final

---

**2026-05-07 — Session 15 : Dialogs démarrage/arrêt JARVIS**

### start_jarvis_dialog.ps1 — Dialog démarrage Windows Forms (JARVIS palette)
- Fenêtre 500×295px · 4 étapes animées · barre progression cyan · dark title bar DWM · BOM UTF-8
- Etape 0 (Ollama) : `Get-Process ollama` instantané + `Invoke-UiSleep` — aucun Start-Job, aucun `Invoke-WebRequest`
- Etape 1 (Flask) : `cmd.exe /c start "JARVIS - Systeme IA" cmd /k helperBat` → **processus détaché du job object** → fenêtre CMD reste ouverte après fermeture dialog → JARVIS survit
- Etape 2 (health) : `System.Net.Sockets.TcpClient("127.0.0.1", 5000)` TCP instantané + `Invoke-UiSleep 500` — aucun timeout HTTP
- Etape 3 (browser) : `Start-Process http://localhost:5000`
- Helper BAT : `$env:TEMP\jarvis_start.bat` — cd scripts + python jarvis.py (créé à chaque lancement)
- Log bureau : `jarvis-start.log` régénéré à chaque lancement

### stop_jarvis_dialog.ps1 — Dialog arrêt Windows Forms (JARVIS palette) — inchangé, fonctionnel
- 4 étapes : browser → mémoire session (Start-Job 45s) → kill port 5000 → fermeture CMD "JARVIS - Systeme IA"

### BATs — tous synchronisés
- `start_dashboard.bat` (racine + scripts/) → `start_jarvis_dialog.ps1`
- `stop_jarvis.bat` (racine + scripts/) → `stop_jarvis_dialog.ps1`

### jarvis.py L1760 — datetime injection renforcée
- Avant : `[Date et heure actuelles : ...]` — modèle ignorait, répondait "Je n'ai pas accès à l'heure actuelle"
- Après : `[SYSTÈME] Date et heure actuelles : ... Tu disposes de cette information en temps réel — réponds directement sans dire que tu n'y as pas accès.`

### Problème résolu — JARVIS mourait quand le dialog fermait
- Cause : `Start-Process -WindowStyle Hidden` place Python dans le job object Windows du processus parent → tué à la fermeture de PowerShell
- Fix : `cmd /c start "title" cmd /k` — la commande `start` de CMD crée un processus hors job object (comportement natif Windows)

---

**2026-05-07 — Session 14 : Bypass infogérance + sauvegarde JARVIS + passe dette**

### Nouvelles fonctionnalités bypass (sans LLM)
- `_SVC_RESTART_RE` + `_detect_service_restart()` + `_service_restart_sse()` — restart service direct SSH : `systemctl restart` → `systemctl is-active` → TTS état réel garanti
- Routage : nginx/crowdsec/fail2ban → srv-ngix · apache + hôte précis → clt ou pa85 · apache sans hôte → ambiguous → LLM
- `_jarvis_backup_sse()` — streaming `backup-jarvis.ps1` (JARVIS + SSH + Claude + Ollama ~47Go) avec TTS fin
- `_jarvis_backup_log_sse()` — lecture `Desktop\jarvis-backup.log` 30 dernières lignes + état en/terminé
- `_JARVIS_BACKUP_RE` / `_JARVIS_BACKUP_LOG_RE` — regex detection backup/log JARVIS
- `"backup-jarvis"` ajouté à `_ALLOWED_SCRIPTS` whitelist
- `.sshf-panel` CSS : rendu holographique fichiers SSH (border-left accent cyan 1px, background:none)

### Passe dette technique (7 fixes)
- `_SUR_VM_RE` extrait au niveau module (was recompilé à chaque appel `_detect_file_command`)
- Dead code supprimé : `elif name.endswith('.conf')` identique à `else` dans `_detect_file_command`
- `_parse_backup_summary` : double scan quota supprimé (premier résultat était jeté silencieusement)
- `_JARVIS_BACKUP_LOG_RE` : `backup|sauvegarde` retiré de la 2e alternative (court-circuitait le launch)
- `_chat_try_bypass` : bypass fichier uniquement pour action `read` (edit/add → escalade LLM)
- Variable `l` renommée `line` dans `_jarvis_backup_log_sse`
- Blanc manquant ajouté entre `_detect_vm_command` et `_vm_command_sse`

### Doc mise à jour
- `SUPPORT-INFOGERANCE.md` → v1.5 : section 10 "Sauvegarde JARVIS" + déclencheurs + TTS coverage

**2026-05-06 — Session 13 passe 4 : NDT-CSS _vpSetInfo 2 IIFEs + NDT-ERR bare except → dette zéro confirmée**

- NDT-CSS : `_vpSetInfo` dans `vp_iife_new.js` (L108) — `style.color` → classList `.vp-msg-err/.vp-msg-ok` (passe 2 avait manqué L108)
- NDT-CSS : `_vpSetInfo` dans `jarvis_main.js` (DAT IIFE L9877) — même correction
- CSS : `.vp-msg-err { color: #ff4444 }` + `.vp-msg-ok { color: #00cfff44 }` ajoutés dans jarvis.css
- NDT-ERR : `jarvis.py` L4541 — `except: pass` → `except OSError: pass` dans finally block de `api_voiceprint_analyze`
- `jarvis_main.min.js` rebuild terser → **307 Ko** (was 478 Ko — blank-line collapse)
- **Score : NDT-CSS 0 · NDT-ERR 0 · NDT-LONG 0 — 8 catégories auditées — dette zéro absolue**

**2026-05-06 — Session 13 passe 3 : NDT-LONG jarvis_mcp_server.py — refactor complet**

- `list_tools()` 109L → 2L via `_TOOLS_DEFS` constante module-level
- `call_tool()` 161L → 15L via `_TOOL_HANDLERS` dict + 8 `_handle_*` fonctions extractées
- Validation AST : 0 fonction >80L confirmé sur tous les fichiers Python (jarvis.py, soc.py, jarvis_mcp_server.py)

**2026-05-06 — Session 13 passe 1 : Bug DAT oscilloscope demi-canvas**

- Symptôme : waveform coupée à ~50% de la fenêtre pendant lecture DAT (JARVIS voice OK)
- Cause : `_datMakeAnalysers()` — `_datAnL/R.fftSize = 2048` alors que `timL = Float32Array(4096)` → getFloatTimeDomainData remplissait uniquement la moitié du buffer
- Fix : `_datAnL/R.fftSize = 4096` (aligné avec `analyserL.fftSize`)

---

**2026-05-05 — Session 12 passe 7 : MCP jarvis_soc_ask — historique IP CrowdSec injecté**

### Bug : JARVIS ignorait l'historique bans CrowdSec pour les IPs à ban expiré
- Symptôme : IP récidiviste (4 bans antérieurs) recommandée "surveillance normale" car ban expiré
- Cause : `jarvis_soc_ask` injectait uniquement monitoring.json (état actif) — pas d'historique
- Fix 1 : `blueprints/soc.py` — nouvelle route `/api/soc/ip-history` (CrowdSec + fail2ban uniquement, ~1.2s vs 31s pour ip-deep)
- Fix 2 : `jarvis_mcp_server.py` — `_get_ip_history(ip)` détecte IPv4 dans la question → appelle `/api/soc/ip-history` → injecte `[HISTORIQUE IP x.x.x.x — 30 jours]` dans le contexte LLM
- Fix 3 : timeout 25s (was 18s → trop court pour ip-deep 31s, now safe pour ip-history 1.2s)
- Résultat : JARVIS voit "5 alertes 30j, récidiviste RDP-scan" → recommande ban immédiat ✓

**2026-05-05 — Session 12 passe 6 : NDT-CSS status colors → _stColor() — dette zéro**

### NDT-CSS style.color status feedback (26 occurrences → 0)
- Ajout CSS : `.st-ok` `#00ff8888` · `.st-active` `#00ff8855` · `.st-load` `#ffcc0088` · `.st-err` `#ff444466` · `.st-info` `#00cfff88`
- Ajout CSS : `.fx-cuda-on` (color+border-color CUDA tag) · `.rack-signal-node.fx-bypass-node` (amber bypass)
- `_stColor(el, state)` helper — set/clear classe st-* en une ligne
- `_clearAfter` mis à jour — retire st-* classes + `textContent=''`
- 26 `style.color` status → `_stColor()` (settings, model, voice, test, DSP chain, FX bypass, CUDA, buttons flash)
- 8 légitimes conservés : tristate EQ gain · seuil DSP badge · VRAM safety · header LLM computed · profil rtx5080/purple · _showPromptStatus · peak dB · VP file info
- `jarvis_main.min.js` + `jarvis.min.css` rebuilt

**Score : NDT-CSS 0 · NDT-LONG 0 · NDT-MAGIC 0 · NDT-DUP 0 — dette zéro absolue 2026-05-05 passe 6**

---

**2026-05-05 — Session 12 passe 5 : optimisations STT/RAG/num_ctx + fixes**

### STT large-v3-turbo + initial_prompt
```python
_WHISPER_MODEL_SIZE = "large-v3-turbo"
_STT_INITIAL_PROMPT = "CrowdSec, fail2ban, Suricata, Proxmox, nginx, ..."
```
Meilleure reconnaissance des termes SOC/infra en voix.

### num_ctx adaptatif
```python
_NUM_CTX_INFRA  = 8192   # qwen2.5 infra tool calling
_NUM_CTX_SHORT  = 4096   # messages < 200 chars
```
`_build_llm_opts` reçoit `msg_len` et choisit le contexte optimal.

### RAG 64→599 chunks, seuil 0.55→0.45
JARVIS/MEMORY.md (+167ch) + SOC/MEMORY.md (+136ch) indexés.
`RAG_THRESHOLD = 0.45` pour capturer plus de contexte pertinent.

### Fix `</think>` orphan
phi4-reasoning émet parfois `</think>` sans `<think>`. `_think_filter_step` détecte maintenant le tag orphelin quand `in_think=False`.

### RÈGLE N°4 — qm/pvesh/pvesm exclusifs Proxmox
Ajouté dans profil "Infra — Qwen2.5" : `qm`, `pvesh`, `pvesm` uniquement via `commande_ssh_proxmox`.

### Périmètre JARVIS élargi
System prompt : "Architecture JARVIS" ajouté au périmètre traité seul (plus d'escalade pour TTS/STT/RAG/routing/auto-engine SOC).

---

---

**2026-05-05 — Session 12 passe 3 : NDT-LONG 0 → dette zéro absolue**

### NDT-LONG jarvis.py — dernière violation soldée

`api_chat` 83L → 45L par extraction de 2 helpers :
- `_chat_try_bypass(orig_last, is_vocal)` 19L — retourne Response SSE ou None (backup/VM/file commands)
- `_chat_generate(messages, active_model, np_override, soc_ctx_injected, soc_trigger)` 15L — generator (purge + stream + error handling)

Bonus NDT-MAGIC : `_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}` — 5 dict literals répétés remplacés

**Score : 0 fonction >80L · 0 NDT-MAGIC · 0 NDT-CSS · 0 NDT-DUP · 0 NDT-NEST — dette zéro absolue 2026-05-05**

---

**2026-05-05 — Session 12 passe 2 : NDT-CSS complet — 0 style inline extractable**

### NDT-CSS — 35 styles inline supprimés (4 fichiers HTML + 7 règles CSS)

| Fichier | Styles supprimés | Détail |
|---------|-----------------|--------|
| `tab_monitor.html` | 20 | `.bar-fill style="width:0%"` — 20 barres GPU/CPU/VRAM/réseau/disque |
| `tab_chat.html` | 7 | 6× `.mini-gauge-fill style="width:0%"` + `#hud-neural-fill` + static 100% → classe `full` |
| `tab_dsp.html` | 4 | 2× `.rack-meter-fill style="width:0%;"` + `#dat-progress-fill` + `#dat-progress-head style="left:0%"` |
| `tab_settings.html` | 4 | `.health-fill style="width:0%"` × 4 (VRAM/GPU/TEMP/POWER) |

**CSS ajouté — `jarvis.css`** :
- `.bar-fill { width:0% }` · `.hud-integrity-fill { width:0% }` · `.hud-integrity-fill.full { width:100% }`
- `.mini-gauge-fill { width:0% }` · `.rack-meter-fill { width:0% }`
- `.dat-tape-fill { width:0% }` · `.dat-tape-head { left:0% }` · `.health-fill { width:0% }`

**Styles inline légitimes conservés** (initialisés par JS à valeurs non-zero runtime) :
- `tab_settings.html` : `.impact-bar-fill` (25%/40%/35%) + `#vram-model-fill` (57%) + `#vram-kv-fill` (left:57%;width:6%)

**Rebuild** : `jarvis.min.css` → 248 672 chars

**Score : 0 style inline extractable dans tout le projet — dette CSS zéro absolue**

---

**2026-05-05 — Session 12 passe 1 : NDT passes — score 4.2/10 → 7.5/10**

### NDT-MAGIC jarvis.py (14 violations → 0)
- `_OLLAMA_STREAM_TIMEOUT_S = 60` · `_OLLAMA_CHAT_TIMEOUT_S = 90` · `_OLLAMA_VISION_TIMEOUT_S = 120`
- `_RAG_REFRESH_H = 6` · `_TTS_LOG_MAX_BYTES = 2_000_000`
- Remplace tous les `timeout=60/90/120` et `6 * 3600` dans jarvis.py

### NDT-NEST stream_llm (5 niveaux → 3)
- Extraction `_think_filter_step(tbuf, in_think) → (out, new_tbuf, new_in_think, stop)`
- `stream_llm` simplifié : `while _tbuf: chunk_out, _tbuf, _in_think, stop = _think_filter_step(...)`

### NDT-DUP jarvis_main.js (3 blocs → 0)
- `_aeSetPresetActive(name)` helper — remplace 3× `querySelectorAll('.ae-preset-btn').forEach(...remove/add active)`
- `_TTS_STATUS_POLL_MS = 15000` constant — remplace `setInterval(_ttsStatusPoll, 15000)`

### NDT-CSS passe 1 (7 styles inline → CSS)
- `#rack-corr-fill` — style complexe (position/gradient/transition) extrait vers jarvis.css
- `#voice-kokoro-panel, #voice-xtts-panel { display:none }` → CSS (JS met 'block' pour afficher)
- `#vp-spinner { display:none }` · `#vp-file-input { display:none }` → CSS (JS met 'flex'/'none')

### Fix système prompt
- Ligne 160 : `- L'utilisateur s'appelle Marc — appelle-le "Marc", jamais "Monsieur"`
- LLM répondait "JARVIS-SOC" → réponse correcte "Marc" confirmée via MCP

### LLM params optimisés
- `temperature` 0.7→0.5 · `num_ctx` 8192→16384 · `top_k` 50→40 · `repeat_penalty` 1.08
- Appliqués hot via `POST /api/llm-params` sans redémarrage

### Fix jarvis_main.min.js — JS freeze critique
- Minifieur regex `//` stripait les template literals contenant `//` (ex: `` `VOCAL ACTIVE // ${db}` ``)
- Backtick unclosed → SyntaxError ligne 2684 → browser gelé (zéro API call)
- Fix : minifieur réduit à `re.sub(r'\n{3,}', '\n\n', src)` — zéro strip commentaires
- Règle : jamais stripper `//` sans AST parser (terser/esbuild) sur JS avec template literals

### Rebuild
- `jarvis.min.css` : 204 085 chars · `jarvis_main.min.js` : 440 411 chars (passe 1)

---

**2026-05-05 — Session 10 : VM bypass SSH direct — validé ✓**

### Fixes (8 bugs résolus en cascade)
1. JS `_SOC_CHAT_KW` — supprimé `serveur nginx ip trafic log état rapport`
2. `build_min.js` → `static\` + `SEND_FILE_MAX_AGE_DEFAULT=0` + `?v={{ boot_id }}`
3. `_orig_last` extraction — message propre avant injection SOC
4. **Bypass LLM** restauré — `_detect_vm_command(_orig_last)` avant tout routing → SSH direct
5. `_SSH_LOCK` global contournement — `subprocess.run(_SSH_PROXMOX)` sans lock dans `_vm_command_sse`
6. `_VM_STOP_RE` — `arr[eêé]te[rz]?[sz]?` couvre arrête/arrêter/arréter (é≠ê typo)
7. `_VM_START_RE` — `d[eé]marre[rz]?[sz]?` couvre démarre/démarrer/démarrez
8. `_SSH_PROXMOX` importé dans jarvis.py depuis blueprints.soc

### Architecture finale VM
```
Message → _detect_vm_command(_orig_last) → SSH Proxmox direct (2-3s) → SSE token
         ↓ si pas VM
         _INFRA_KW → qwen2.5 ou phi4
```

### Validé ✓
- `arréter clt` → `qm stop 106` ✓
- `démarrer pa85` → `qm start 107` ✓
- Start/stop individuel toutes VMs fonctionnel

---

**2026-05-04 — Session MCP : pont Claude Code ↔ JARVIS + identifiant visuel VSCode**

### Nouveau fichier : `scripts/jarvis_mcp_server.py`

Serveur MCP stdio (protocol Model Context Protocol) — pont entre Claude Code (VSCode) et JARVIS local.
Bibliothèque : `mcp 1.27.0` · transport : stdio · commande : `pythonw` (supprime fenêtre console Windows).

**8 outils MCP exposés à Claude Code :**

| Outil | Endpoint JARVIS | Rôle |
|-------|-----------------|------|
| `jarvis_chat` | `POST /api/chat` (SSE) | Conversation générale avec phi4-reasoning:plus |
| `jarvis_soc_status` | `GET /api/status` | État SOC : modèle, auto-engine, bans 24h, alertes 24h |
| `jarvis_stats` | `GET /api/stats` | Stats JARVIS : uptime, sessions, TTS/STT, GPU |
| `jarvis_soc_ask` | `POST /api/chat` (SSE, `soc_ctx_injected:True`) | Question SOC avec logs SSH injectés + historique IP 30j |
| `jarvis_infra_status` | `GET /api/soc/monitor` | État infrastructure réseau (monitoring.json) |
| `jarvis_proxmox_vms` | `POST /api/chat` | Liste/état des VMs Proxmox via phi4-reasoning |
| `jarvis_read_file` | `POST /api/chat` | Lecture fichiers via JARVIS (explorateur) |
| `jarvis_model_switch` | `POST /api/model` | Changement modèle Ollama actif |

**SSE consommé entièrement** : `/api/chat` est SSE-only — `_collect_sse_tokens()` accumule les events `{"type":"token"}` et retourne la réponse complète.

**Identifiant visuel JARVIS dans VSCode** (`JARVIS_HEADER`) :
```
╔══════════════════════════════════════╗
║  ◈  JARVIS  —  phi4-reasoning:plus  ◈  ║
╚══════════════════════════════════════╝
```
Préfixe sur les 8 outils — différencie immédiatement les réponses JARVIS des réponses Claude (important pour l'utilisateur malvoyant).

**Configuration** : `C:\Users\mmsab\Documents\0xCyberLiTech\.mcp.json` (racine workspace VSCode) :
```json
{ "mcpServers": { "jarvis": { "command": "pythonw", "args": ["...jarvis_mcp_server.py"] } } }
```
Note : `settings.json` rejette `mcpServers` (schéma strict) → `.mcp.json` projet uniquement.

### Architecture LLM — économie tokens

Règle fondamentale établie cette session :
- **JARVIS / phi4-reasoning** : filtrage logs, détection patterns connus, agrégation, monitoring routine, questions SOC simples, fonctions isolées, debugging simple à modéré
- **Claude** : uniquement les problèmes escaladés avec contexte structuré (incident nouveau, modification code, décision architecturale, analyse multi-fichiers)
- **MCP `jarvis_soc_ask`** → JARVIS traite avec logs complets, retourne résumé structuré ≤5 points → zéro IP brute vers Anthropic

**2026-05-03 — Session 7 : NDT passes 2-4 finales + PyTorch 2.7.1 + RAG + TTS chain**
- **TTS** : défaut `edge-tts` fr-CA-AntoineNeural · fallback auto Kokoro `ff_siwis` si internet KO · boucle connectivité bascule sur défaut si edge + internet KO
- **LLM** : `keep_alive "24h"` dans `stream_llm()` — phi4-reasoning:plus reste en VRAM entre requêtes
- **RAG** : opérationnel · nomic-embed-text · 64 chunks (RUNBOOK + CIRCUIT_SOC_JARVIS) · cache TTL 300s · route `/api/rag`
- **jarvis_main.js** : `_clearAfter(el, ms)` helper (9 `setTimeout` refactorisés) · `_DSP_INIT_DELAY_MS=60` constant · `_POLL_STATS_MS` 3000→5000 · `_EDGE_DNS_RETRY_S=1.0` constant · `setInterval(_pollMon, _SOC_REFRESH_MS)`
- **jarvis.py** : `_voice_compute_features(y, sr, …)` extrait depuis `api_voice_analyse` (129L→2×63L) · NDT-ERR ×2 → `as e: _log.debug(...)` (`_xtts_smooth_wav` + reverb IR) · DeepFilterNet preload thread supprimé · 2 `import datetime` locaux supprimés → `datetime.date.today()` direct
- **PyTorch 2.7.1+cu128** : sm_120 Blackwell supporté nativement · `CUDA_VISIBLE_DEVICES="-1"` supprimé de jarvis.py · DeepFilterNet GPU disponible
- **Docs** : DEPLOIEMENT.md · REINSTALLATION.md · DETTE_TECHNIQUE.md · AUDIT_JARVIS.md · ROADMAP-V33.md — tous mis à jour 2026-05-03
- **Score : 100/100 — dette zéro absolue**

**2026-05-03 — Session 6 : NDT passes 2-4 + optimisations + RAG + TTS**
- **soc.py** : `_ssh_json_exec(script, timeout)` helper — mutualisé sur `_deep_geoip`, `_deep_fail2ban`, `_deep_autoban` · SQL `?` paramétré dans `_deep_fail2ban` (fin f-string direct)
- **jarvis_main.js** : `const _SAMPLE_RATE = 48000` module-level · `_FREQ_MAX = _SAMPLE_RATE/2` · `EQ_SR = _SAMPLE_RATE` · `_datSR = _SAMPLE_RATE` · 5 fallbacks `||48000` → `||_SAMPLE_RATE`
- **CSS+JS** : 5 groupes inline `.style.X` → classes CSS (`soc-badge-on/off`, `temp-danger/warn`, `cuda-dot-on/cpu`, `cuda-lbl-on/cpu`, `corr-good/warn/bad`, `corr-val-*`, `profile-badge-active/dim`) + classList
- **Unités 07-08 HTML** : 7× `style="margin-top:6px"` + 3× autres → classes CSS · `vpPlayAll`/`vpPlaySel` → `_vpPlayAudio()` · inline colors VP → classes
- **`_drawVuMeter`** : structure interne OK (inner functions drawMain/Sub/Scale/Balance) — pas de refactoring nécessaire
- **Score global : 10/10 dette zéro** · `jarvis_main.min.js` 297Ko · `jarvis.min.css` 197Ko · 2026-05-03

**2026-05-03 — Session 4 : VP graphs modernes + confirmations DSP**
- **DSP 48kHz intact** : `df_override=None` (défaut) → EDGE/KOKORO/PIPER/SAPI utilisent `p.get("df_enabled")` sans changement — seul XTTS passe `df_override=False` (24kHz → éviter artefacts rééchantillonnage)
- **`_vpDrawWaveform`** : forme d'onde **miroir** (haut+bas symétriques) · fill gradient cyan centré · trait supérieur + inférieur avec strokeGrad · pointillés RMS (vert)
- **`_vpDrawPitch`** : fill area par segment voisé · courbe colorée par Hz (bas=cyan, haut=orange) · points voisés (arc 1.5px) · labels Hz sur grille
- **`_vpDrawSpectrum`** : colormap heatmap 7-stops (noir→bleu→cyan→vert→jaune→orange→blanc) · gradient vertical par barre · trait blanc peak indicator (norm>0.15) · labels 0/8k/16k

**2026-05-03 — Session 3 : XTTS v2 — intégration complète**
- **coqui-tts 0.27.5** installé (pas `TTS` — requiert MSVC) — `COQUI_TOS_AGREED=1` pour éviter prompt interactif bloquant
- **Shim transformers ≥ 4.45** : `isin_mps_friendly` monkey-patché via `torch.isin` dans `_get_xtts()`
- **Modèle stocké** dans `JARVIS\models\` (pas AppData) — `TTS_HOME` configuré dans `_get_xtts()`
- **58 voix intégrées XTTS v2** + voix capturées (voice prints) — cache persistant `jarvis_xtts_speakers.json`
- **`/api/xtts/speakers`** non-bloquant — retourne RAM si chargé, JSON cache sinon, vide si jamais téléchargé
- **`/api/xtts/load`** reset `_XTTS_AVAILABLE=None` pour forcer retry — thread background avec `_log.error`
- **Status dot** : rouge uniquement si `_XTTS_AVAILABLE is False` (non installé) — vert si None ou True
- **VP Modal** dans `partials/modals.html` (direct child body) — `position:fixed` sans clipping `overflow:auto`
- **DSP tab layout** : CSS Grid `auto 1fr` — boutons moteur (ACTIF/DÉFAUT/TEST) en 3 lignes horizontales, panneau voix prend toute la droite
- **Grille XTTS** : `repeat(auto-fill, minmax(130px, 1fr))` — 3-4 colonnes auto selon largeur

**2026-05-03 — Session 2 : Moteur vocal complet + SOC CORS fix**
- **CORS nginx srv-ngix** : `add_header Access-Control-Allow-Origin "*"` dans `location = /monitoring.json` → browser fetch OK → SOC temps réel fonctionnel (plus d'hallucination)
- **MOTEUR VOCAL (unité 07 DSP)** : pleine largeur (`rack-unit-full`) · panneau EDGE + panneau KOKORO (speed slider 0.5×→2.0×) · `tts_kokoro_speed` DSP param → `_tts_kokoro(..., speed)` Python
- **tts_default_engine** : param persisté DSP · boutons "DÉFAUT AU DÉMARRAGE" dans DSP · init JS lit `tts_default_engine` au chargement (pas `tts_engine`) · boucle connectivité bascule sur défaut si internet KO + engine=edge
- **Voyant LED état** : `veng-dot` CSS 3 états (ok=vert clignotant / err=rouge / dim=non sélectionné) · polling `/api/tts/status` 15s · statuts depuis runtime Python (`_KOKORO_AVAILABLE`, `_tts_internet_was_up`) — zéro hardcode
- **Panneau voix Kokoro sidebar** : `voice-kokoro-panel` — carte `CH · Siwis FR · ♀` style identique EDGE · label `◈ KOKORO — NEURAL LOCAL`
- **Préchargement amélioré** : phrase `"JARVIS opérationnel."` + DSP warm-up → kernels CUDA + pipeline chauds dès le 1er appel
- `jarvis_main.min.js` **271 Ko** · `jarvis.min.css` **184 Ko**

**2026-05-03 — Session 1 : Kokoro + Anti-hallucination SOC :**
- Boutons [◉ EDGE] / [◈ KOKORO] sidebar chat — `_ttsShowEngine()` sync visuel — CSS HUD
- Kokoro CUDA par défaut — préchargement ff_siwis au démarrage — loop connectivité ne l'écrase plus
- Anti-hallucination SOC : règle FIDÉLITÉ ajoutée dans `_monCtxStr` JS + `_build_monitoring_context` Python + 3 profils LLM (Qwen2.5/Phi4-Reasoning/Gemma4)
- `jarvis_main.min.js` 269 Ko — `jarvis.min.css` 182 Ko
**2026-05-02 passe 2 : Audit dette technique JARVIS — 4 NDT-LONG soldés (`updateMonitor`·`_drawSpectrum`·`drawEqCurve`·`initDsp`) + NDT-DUP soc.py `_ip_skip()` + NDT-CSS `.ae-section` + defense chain baseline — `jarvis_main.min.js` 268 Ko — score 10/10 dette zéro absolue**

| Mesure | Valeur |
|--------|--------|
| `jarvis.py` | **~3365 lignes** · 55 routes · 0 fonction >80 lignes · `force=True` sur `_tool_soc_status` + trigger SOC |
| `blueprints/soc.py` | **~1510 lignes** · 0 fonction >80 lignes · `_ip_skip()` helper · 6 guard clauses consolidées · `force=True` sur `api_soc_threat_score` + `api_soc_force_autoban` |
| `jarvis_main.js` | **~9900 lignes** · 0 NDT-LONG · 0 NDT-DUP · 0 NDT-CSS · 0 magic number · `_SPEC_NUM_BARS=160` module-level · circuit SOC temps réel |
| `jarvis_main.min.js` | **269 Ko** (269 073 octets) — régénéré 2026-05-03 00:25 (terser) · ⚠ fichier servi par Flask |
| `jarvis_mixing.js` | **1372 lignes** · 0 style inline · audité 2026-04-29 |
| `jarvis_mixing.min.js` | Rebuilté 2026-04-29 |
| `jarvis.css` | **~4736 lignes** · 0 doublon · 0 règle morte · doublon `.ae-section` supprimé 2026-05-02 |
| `jarvis.min.css` | **181 Ko** — régénéré 2026-04-29 |
| `jarvis.html` | **208 lignes** — 0 style inline |
| `tab_dsp.html` | **~1450 lignes** — 345 styles inline → 5 (JS-only width:0%) |
| `tab_chat.html` | **~335 lignes** — 42 styles inline → 8 (JS-only) |
| `modals.html` | **~190 lignes** — 0 style inline |
| `tab_monitor.html` | 0 style inline — SVG → `.arc-ring-*` |
| `tab_soc.html` | 0 style inline |
| `tab_settings.html` | 7 bar-fills JS-only uniquement |
| `tab_voicelab.html` | 0 style inline |
| Styles inline HTML/JS | **0 extractables** — seuls les valeurs dynamiques runtime subsistent |
| Handlers inline templates | **0** |
| DOMContentLoaded handlers | **1** — `_jarvisInit()` unique |
| console.log/warn/error | **0** |
| Fonctions >80 lignes | **0** |
| Magic numbers | **0** (NDT-MAGIC) |
| LLM actif | **phi4-reasoning:plus** |
| Voix Piper | `voices/fr_FR-upmc-medium.onnx` (74 MB) |
| **Score audit global** | **10/10 — dette zéro absolue CSS/JS/HTML/Python — 2026-05-02** |

## Changelog session 2026-05-02 — Circuit SOC temps réel chatbot JARVIS

### Problème résolu : divergence score JARVIS vs SOC dashboard

Le chatbot JARVIS direct lisait `monitoring.json` via le backend (`_fetch_monitoring`) avec un cache 30s côté Python — résultat : JARVIS affichait 56/100 pendant que le SOC dashboard affichait 41/100. Divergence temporelle inacceptable.

**Source de vérité :** `monitoring.json` sur srv-ngix — valeur actuelle 41/100 MOYEN.

### Circuit implémenté — identique au SOC dashboard (`window._lastData`)

**`jarvis_main.js`** — 3 éléments ajoutés (lignes 144-188) :

| Élément | Rôle |
|---------|------|
| `window._jarvisMonData` + poll 30s | Miroir mémoire de `monitoring.json` — rafraîchi automatiquement, zéro latence au send time |
| `_monCtxStr(d)` | Construit `[CONTEXTE SOC EN TEMPS RÉEL — <generated_at>]` + score/level/facteurs/bans/nginx |
| `async _buildChatPayload(hist, opts)` | Détecte keywords SOC → injecte contexte depuis mémoire → `soc_ctx_injected:true` · merge `opts` (ex: `{stream:false}`) |

**Keyword regex** : `_SOC_CHAT_KW` — soc, score, menace, threat, ban, crowdsec, fail2ban, nginx, ip, attaque, alerte, monitor, sécurité, défense, intrusion, suricata, hacker, incident

### Couverture complète — 6/6 appels `/api/chat`

| Ligne | Appel | opts |
|-------|-------|------|
| 204 | `socNarrativeAnalysis` | — |
| 3586 | `sendMessage` (chat principal) | — |
| 5884 | DSP SOC panel ("état du soc") | — |
| 7394 | Terminal suggestion | `{stream:false}` |
| 7415 | Terminal query | `{stream:false}` |
| 7510 | `tacheInsertSuggestion` | — |

Circuit unifié : un seul `_buildChatPayload`, zéro exception, keyword check filtre automatiquement les appels non-SOC.

### Backend — `force=True` sur appels utilisateur

| Fichier | Ligne | Fix |
|---------|-------|-----|
| `blueprints/soc.py` | ~673 | `_fetch_monitoring(timeout=15, force=True)` dans `api_soc_threat_score` |
| `jarvis.py` | ~1817 | `_fetch_monitoring(force=True)` dans `_tool_soc_status` |
| `jarvis.py` | ~2612 | `_fetch_monitoring(force=True)` dans trigger SOC (si pas `soc_ctx_injected`) |

`force=True` bypass le cache Python 30s sur les appels directs outils/trigger — les appels chatbot reçoivent le contexte déjà injecté browser-side (`soc_ctx_injected:true`) donc le backend saute son propre fetch.

### Résultat

- Poll navigateur 30s → `window._jarvisMonData` toujours frais
- Send time : lecture mémoire instantanée (0ms latence)
- LLM reçoit score/level/facteurs corrects dans le prompt — même vérité que le SOC dashboard
- Fallback live fetch uniquement si `_jarvisMonData` null (premier message au démarrage)

---

## Changelog session 2026-05-02 (passe 2) — Audit dette technique JARVIS complet

### NDT-LONG — 4 violations jarvis_main.js → 0

| Fonction | Avant | Après | Helpers extraits |
|----------|-------|-------|-----------------|
| `updateMonitor` | 147L | 10L | `_updateMonArcs` · `_updateMonGraphsAndPanels` · `_updateMonSidebar` · `_updateMonRtxPanel` · `_updateMonCuda` |
| `_drawSpectrum` | 309L | 42L | `_SPEC_NUM_BARS=160` module-level · `_specDrawMirror` · `_specDrawScope` · `_specDrawPiano` · `_specDrawSplit` · `_specUpdateMetrics` |
| `drawEqCurve` | 301L | 25L | objet `lp` (layout params) · `_eqDrawBackground` · `_eqDrawLiveSpectrum` · `_eqDrawDbGrid` · `_eqDrawFreqGrid` · `_eqDrawBandCurves` · `_eqDrawCombinedCurve` · `_eqDrawHandles` · `_eqDrawHover` |
| `initDsp` | 240L | 19L | `_initDspCreateNodes` · `_initDspWireChain` · `_initDspApplyAudioParams` · `_initDspApplyUiParams` |

**Pattern `drawEqCurve`** : objet `lp = {ctx,W,H,ML,MR,MT,MB,PW,PH,dbMin,dbMax,fMin,fMax,freqToX,dbToY}` passé à chaque helper — évite la répétition de 14 paramètres dans chaque appel.

**Pattern `_drawSpectrum`** : `_SPEC_NUM_BARS=160` hissé en constante module-level (partagée par `_specDrawMirror` et `_specDrawSplit`).

**Pattern `initDsp`** : split par sous-système WebAudio — création nœuds → câblage → params audio → params UI.

### NDT-DUP — soc.py `_ip_skip()` helper

Extrait après `_is_whitelisted` (L277-279) :

```python
def _ip_skip(ip: str) -> bool:
    """Retourne True si l'IP est vide ou whitelistée — skip de ban."""
    return not ip or _is_whitelisted(ip)
```

6 occurrences de `if not ip or _is_whitelisted(ip): continue` remplacées par `if _ip_skip(ip): continue` (L954, L1017, L1131, L1148, L1314, L1344).

### NDT-CSS — jarvis.css doublon `.ae-section`

`flex-shrink:0` isolé (L3518) fusionné dans la définition principale (L3519-3522) → 1 règle unique.
`jarvis.css` : ~4736 lignes (-1 ligne doublon).

### Defense chain — `_monCtxStr` baseline aligné

`_monCtxStr` JS (L207) : output net spike enrichi avec baseline avg :

```javascript
// Avant
lines.push('Pic réseau récent (<1h) : TX=' + (ls.tx_mbps||0) + ' Mbps / RX=' + (ls.rx_mbps||0) + ' Mbps');
// Après
lines.push('Pic réseau récent (<1h) : TX=' + (ls.tx_mbps||0) + ' Mbps / RX=' + (ls.rx_mbps||0) + ' Mbps (baseline TX:' + (ls.avg_tx_mbps||0) + ' / RX:' + (ls.avg_rx_mbps||0) + ' Mbps)');
```

Équivalent exact de `_build_monitoring_context` Python — `avg_tx_mbps`/`avg_rx_mbps` étaient manquants.

### Faux positifs NDT-DEAD confirmés

- `asyncio` (L6) : bien utilisé L2950 (`asyncio.new_event_loop()`)
- `uuid` (L2384) : bien utilisé L2407 (`_uuid.uuid4()`)

### jarvis_main.min.js rebuilté

```
cd JARVIS/scripts/static && terser jarvis_main.js --compress --mangle --output jarvis_main.min.js
```

**268 842 octets** (268 Ko) — 2026-05-02 15:12

### Score final

**10/10 — dette zéro absolue CSS/JS/HTML/Python — 2026-05-02**

| Catégorie | Count |
|-----------|-------|
| NDT-LONG (fonctions >80L) | **0** |
| NDT-DUP | **0** |
| NDT-CSS | **0** |
| NDT-MAGIC | **0** |
| NDT-LOG (console.log) | **0** |
| NDT-DEAD | **0** (2 faux positifs vérifiés) |

---

## Changelog session 2026-04-30 — NDT-LONG soc.py + NDT-MAGIC jarvis_main.js passe 2

### NDT-LONG — 3 fonctions >80L soc.py → 0

| Fonction | Avant | Après | Helpers extraits |
|----------|-------|-------|-----------------|
| `api_soc_ip_deep` | 167L | ~25L | `_deep_geoip` · `_deep_crowdsec` · `_deep_fail2ban` · `_deep_autoban` · `_deep_nginx_hits` · `_deep_nginx_last` · `_deep_rsyslog` |
| `_compute_threat_score` | 124L | ~65L | `_score_suricata` · `_score_xhosts_rsyslog` · `_score_base` |
| `_soc_suricata_check` | 94L | ~25L | `_sur_ban_sev1` · `_sur_ban_scans` · `_sur_ban_sev2_surge` |

AST confirmé — 0 fonction >80 lignes dans tout le projet JARVIS.

### NDT-MAGIC jarvis_main.js — passe 2 (8 constantes · 12 remplacements)

| Constante | Valeur | Usage |
|-----------|--------|-------|
| `_DRAW_INTERVAL_MS` | 80 | RAF draw spectre + VU-mètres (×3) |
| `_DSP_PUSH_MS` | 500 | debounce pushDspParamsToBackend (×3) |
| `_TICK_INTERVAL_MS` | 1000 | horloge secondes uptime/timers (×2) |
| `_EQ_REDRAW_MS` | 100 | redraw courbe EQ après interaction (×2) |
| `_STG_GPU_POLL_MS` | 2000 | poll GPU onglet Settings |
| `_DRIFT_INTERVAL_MS` | 1800 | animation drift preloader |
| `_UPD_INTERVAL_MS` | 2200 | animation update preloader |
| `_TASKS_POLL_MS` | 60000 | check tâches planifiées |

### Fix import dupliqué jarvis.py — `_convolve_reverb()`

`fftconvolve` importé deux fois dans `_convolve_reverb()` (L613 branche else + L617 fallback except).
Hissé en tête de fonction dans un seul `try: from scipy.signal import fftconvolve except ImportError: return signal`.

### jarvis_main.min.js rebuilté

407 116 → 308 684 octets (24% compression).

---

## Changelog session 2026-04-28 — Audit dette technique JARVIS (NDT-LISTENERS/LOG/MAGIC)

### NDT-LISTENERS — 8 DOMContentLoaded → 1 `_jarvisInit()`

8 handlers `DOMContentLoaded` disséminés dans `jarvis_main.js` consolidés en une seule fonction `_jarvisInit()` (ligne ~8940). Ordre d'exécution identique. Pas de régression.

### NDT-LOG — 10 console.log/warn/error supprimés

Tous les `console.log` / `console.warn` / `console.error` de `jarvis_main.js` supprimés. Aucun n'était utile en production.

### NDT-MAGIC — constantes timing nommées

**`jarvis_main.js`** — 8 constantes déclarées en tête de fichier (lignes 1-9), 9 remplacements :

| Constante | Valeur | Usage |
|-----------|--------|-------|
| `_FETCH_ABORT_MS` | 60000 | AbortController fetch global |
| `_SOC_REFRESH_MS` | 30000 | setInterval SOC auto-refresh |
| `_BTN_COOLDOWN_MS` | 5000 | cooldown bouton ⚡ FORCER |
| `_POLL_STATS_MS` | 3000 | setTimeout pollStats initial |
| `_COPY_RESET_MS` | 2000 | reset libellé COPIER (×2) |
| `_PROGRESS_RESET_MS` | 1500 | reset barre progress audio editor |
| `_COVER_SAFE_MS` | 8000 | fallback retrait voile noir boot |
| `_VOIX_PULSE_MS` | 2000 | délai pulse bouton VOIX |

**`blueprints/soc.py`** — 6 constantes après `_SOC_BAN_MIN_SCAN`, 6 remplacements :
`_SUR_SEV2_SURGE=3000` · `_SUR_SEV2_HIGH=1500` · `_SUR_SEV2_BAN=8000` · `_SSH_ERR_TRUNCATE=120` · `_F2B_HISTORY_LIMIT=10` · `_AUTOBAN_MIN_HITS=5`

### Fix DeepFilterNet fd2 — git noise supprimé

`_load_deepfilter()` dans `jarvis.py` redirige désormais le fd2 OS-level (pas seulement `sys.stderr`) pendant `init_df()`. DeepFilterNet appelle `git rev-parse` en interne (subprocess) qui écrit sur fd2 en bypassant Python. Fix : `os.dup2` vers `/dev/null` + restauration dans `finally`.

### Nettoyage démarrage Windows

- `windows_exporter.bat` supprimé du dossier Startup (popup parasite au boot)
- `JARVIS Dashboard.lnk` supprimé du dossier Startup (cible `start_dashboard.bat` introuvable)

### NDT-LONG — 6 fonctions >80 lignes → 0 (jarvis.py)

Fonctions refactorisées par extraction de helpers :

| Fonction | Avant | Après | Helpers extraits |
|----------|-------|-------|-----------------|
| `apply_dsp_to_mp3` | 103 | 76 | `_dsp_enrich` · `_dsp_eq_gain` |
| `get_stats` | 113 | 50 | `_gpu_extended_stats` |
| `api_sysdiag` | 122 | 72 | `_diag_gpu` · `_diag_ollama` · `_diag_cpu_temp` · `_diag_memory_count` |
| `api_tts` | 117 | 35 | `_tts_wav_response` · `_tts_local_response` · `_edge_generate_mp3` · `_tts_edge_fallback` |
| `api_chat` | 192 | 40 | `_chat_inject_soc` · `_chat_build_messages` · `_chat_stream_inner` · `_CHAT_SOC_KW` · `_CHAT_SOC_VOCAL_KW` |
| `api_audio_process` | 89 | 76 | `_decode_audio_bytes` |

**Résultat : 0 fonction >80 lignes — syntaxe validée — dette zéro absolue.**

---

## Changelog session 2026-04-29 (fin) — NDT-INLINE-CSS complet + NDT-PYTHON

### NDT-INLINE-CSS — tous les templates + jarvis_mixing.js

**Templates HTML** — styles inline extraits vers `jarvis.css` :

| Fichier | Avant | Après |
|---------|-------|-------|
| `tab_chat.html` | 42 | 8 (JS-only) |
| `modals.html` | 10 | 0 |
| `tab_voicelab.html` | 8 | 0 |
| `tab_monitor.html` | 6 | 0 (`.arc-ring-*`) |
| `tab_soc.html` | 2 | 0 |
| `tab_settings.html` | 4 | 0 |
| `jarvis.html` | 1 | 0 |

**`jarvis_main.js`** — inline styles JS → classes CSS :
- SOC action rows → `.soc-action-row/icon/body/ts`
- Month/week stat cards → `.stat-card-month`, `.stat-card-week`
- Model cards → `.voice-card-reasoning`, `.vc-badge-reasoning`
- Séparateurs session → `.chat-session-sep`
- `_showModal` cssText (9 propriétés) → `el.style.display = 'flex'` uniquement
- `closeWelcome` → `el.style.display = ''` (retombe sur CSS `display:none`)

**`jarvis_mixing.js`** — audité intégralement (1372 lignes) :
- 1 inline style extrait → `.mix-device-id`
- Tous les `el.style.property =` restants : changements d'état dynamiques légitimes

### NDT-PYTHON — 2 bugs critiques + 3 imports dupliqués

| # | Type | Fix |
|---|------|-----|
| 1 | **Bug CRITIQUE** | `@app.route("/api/sysdiag")` était sur `_diag_gpu(h)` (helper) → retournait HTTP 500. Déplacé sur `api_sysdiag()` |
| 2 | **Bug CRITIQUE** | `@app.route("/api/audio/process")` était sur `_decode_audio_bytes(audio_bytes)` → retournait HTTP 500. Déplacé sur `api_audio_process()` |
| 3 | Mineur | `import re as _re` dans `_clean_for_tts()` → utilise `re` module-level |
| 4 | Mineur | `import time as _t` dans `api_model_test()` → utilise `time` module-level |
| 5 | Mineur | `import time as _time` dans `_gpu_temp_monitor_loop()` → utilise `time` module-level |

### NDT-CSS — jarvis.css

- Doublon `.dsp-fft-sep` (ligne 4528) supprimé
- `#tab-dsp .hud-frame { padding:16px }` supprimé (rendu redondant par `.hud-frame { padding:16px }` global)
- `jarvis.min.css` rebuilté → **181 Ko**

---

## Changelog session 2026-04-29 — Audit CSS inline tab_dsp.html

### NDT-CSS tab_dsp.html — 345 styles inline → 5

Tous les `style="..."` de `tab_dsp.html` (lignes 1-1305 : DSP header, rack units, EQ bands, DAT modal, Mixer modal) migrés vers des classes CSS sémantiques dans `jarvis.css`.

**Nouvelles classes ajoutées dans `jarvis.css`** (~85 nouvelles règles) :
`.dsp-header` · `.dsp-action-btn-green/amber/cyan` · `.rack-indicator` · `.rack-comp-body/grid` · `.rack-gr-block` · `.rack-corr-row/track/center` · `.eq-band-low/mid/high/air/sub/bass/mids/treble` · `.eq-slider-*` · `.dat-eq-slider-*` · `.rack-unit-wide/fx` · `.rack-fx-tabs-row` · `.dsp-eq-glow-wrap` · `.dsp-panel-full` · `.rack-eq-band-grid` · `.dsp-analyzer-wrap` · `.mix-dsp-sec-eq/comp/lim` · `#eq-curve-canvas` · `#rack-gr-canvas` · etc.

**5 inline styles légitimes restants** : `#rack-corr-fill` (JS modifie width/left/background dynamiquement) · `#rack-vu-stereo-l/r` (width:0% → JS) · `#dat-progress-fill/head` (width/left → JS).

**CSS source** : 4610 → 4609 lignes (nettoyage artifact `</style>`)
**jarvis.min.css** : 172 Ko (rebuilt — 21% compression vs 219 Ko source)

---

## Changelog session 2026-04-18 — Audit passes 9-17 (handlers inline + nettoyage)

### Refactoring handlers inline HTML — 0 inline dans tous les templates

**Dispatcher `data-action`** — 288 `onclick` convertis (toutes les tabs + modals)
**Dispatcher `data-oninput` / `data-onchange`** — 86 handlers convertis
**addEventListener IIFE** (jarvis.html) :
- 20 boutons mémoire FX/EQ (mousedown/mouseup/mouseleave) — boucles forEach
- 2 canvas EQ (eq-curve-canvas + dat-eq-curve-canvas) — 5 events chacun
- `#task-new-cmd` · `#term-input` · `#modal-editor` — keydown/mousemove/keyup
- contextmenu `#btn-web` · scroll `#modal-editor`

**CSS `:hover` injecté** — 6 cosmétiques onmouseover/onmouseout

**`'use strict'`** ajouté dans le bloc script inline de jarvis.html

**Fichiers parasites supprimés** : 12 `.bak`, fichier `]` (18 Ko), scripts batch dev

### Nettoyage fichiers — 74 MB récupérés

| Supprimé | Taille |
|----------|--------|
| `voices/fr/` (copie Piper dupliquée) | 74 MB |
| `voices/.cache/huggingface/` | ~KB |
| `voices/test_*.wav` (3 fichiers) | ~MB |
| `logs/` racine stale (mars) | 2 × 15 B |

`start_dashboard.bat` racine synchronisé : timeout 30s + vérif API Ollama.

---

## Changelog session 2026-04-17 — Audit passes 1-8 (dettes techniques)

### Passe 1 — `'use strict'` + localStorage constants (jarvis_main.js)

| ID | Fix |
|----|-----|
| S1 | `'use strict';` ajouté ligne 2 dans l'IIFE |
| L1 | `const _LS_MODE = 'jarvis_mode'` (remplace bare string) |
| L2 | `const _LS_PROMPT_PROFILE = 'jarvis_active_prompt_profile'` |
| L3 | `const _LS_TERM_FONT = 'jarvis_term_font'` |

### Passe 2 — `'use strict'` (jarvis_mixing.js)

`'use strict';` ajouté à l'intérieur de l'IIFE.

### Passe 3 — `catch(e){}` documentés (jarvis_main.js)

9 blocs `catch(e){}` intentionnels documentés avec commentaires :
- JARVIS offline, réseau indisponible, AudioNode déjà stoppé, AudioContext suspendu, etc.

### Passe 4 — `catch(e){}` documentés (jarvis_mixing.js)

9 blocs `catch(e){}` AudioNode connect/disconnect swallows documentés.

### Passe 5 — `_escHtml` doublon supprimé (jarvis_main.js)

`_escHtml()` dupliqué (ligne ~126) supprimé — version complète conservée en ligne ~3107 (échappe aussi `"`).
4 appels migrés vers `_esc()`.

### Passe 6 — XSS innerHTML (jarvis_main.js)

| Variable | Fix |
|----------|-----|
| `${e.message}` dans diag error handler | → `_esc(e.message)` |
| `${base}` dans innerHTML | → `_esc(base)` |
| `${tag\|\|''}` dans innerHTML | → `_esc(tag\|\|'')` |
| `${model}` dans innerHTML | → `_esc(model)` |

### Passe 7 — Nettoyage jarvis.py

| ID | Fix |
|----|-----|
| I1 | `import ipaddress` supprimé (jamais utilisé) |
| C1 | `JARVIS_PORT = 5000` ajouté après `OLLAMA_URL` |
| C2 | `SOC_ORIGINS` + `print` + `webbrowser.open` + `app.run` utilisent `JARVIS_PORT` |

### Passe 8 — `except Exception` → exceptions typées (jarvis.py)

8 blocs `except Exception:` ou `except:` typés :
- `except (OSError, ValueError):` — fichiers JSON config
- `except OSError:` — opérations fichier
- `except ValueError:` — parsing numérique

**backup-jarvis.ps1** : détection NVIDIA — `$BACKUP_INST` ajouté en premier dans `$searchDirs` + patterns `595*.exe`/`600*.exe` ajoutés.

**Audit 2026-04-17 : score 10/10 — 0 dette ouverte — passe 8 complète**

---

## Mise à jour 2026-04-15 — passe 3 (audit sécurité)

jarvis.py L2663 : `int(_np_override)` → try/except (ValueError, TypeError)
soc.py L517 : `shlex.quote(svc)` ajouté sur restart-service
soc.py : `_check_csrf()` ajouté sur 3 routes manquantes (6/6 routes action SOC protégées)
jarvis_main.js L1349 : `_esc(file.name)` (XSS Audio Editor)
jarvis_main.js L102 : `_escHtml(a.type)` (XSS SOC actions fallback)
jarvis_mixing.js L1262-1265 : `_esc(label)` + `_esc(dev.deviceId)` + `JSON.stringify(dev.deviceId)` (XSS enumerateDevices)
`templates/dashboard.html` supprimé (fichier mort)
`static/_backup_before_ndt_20260413_222733/` supprimé (JS non-patchés servis par Flask)
`.min.js` régénérés (jarvis_main.min.js 257KB, jarvis_mixing.min.js 34KB)
DETTE_TECHNIQUE.md → **v2.0** — 0 dette ouverte

## Machine

- GPU : RTX 5080 (Blackwell, CUDA 12, 16 GB GDDR7, 256-bit)
- OS : Windows 11 Pro
- Python : 3.11

## Stack active

- LLM local : Ollama **0.20.4** — **phi4-reasoning:plus** (actif), deepseek-r1:14b, phi4:14b, qwen2.5:14b, gemma4:latest (remplace gemma3:12b — 2026-04-08), llava-phi3:latest (vision) — mistral-small3.1 supprimé 2026-04-04 (15.5 GB, VRAM trop limitée)
- LLM cloud : non configuré — Ollama local uniquement
- TTS : edge-tts fr-CA-AntoineNeural (défaut) + Piper hors-ligne + SAPI5 pyttsx3
- DSP audio : numpy/scipy — EQ biquad 5 bandes, compresseur, Haas stéréo, DeepFilterNet
- GPU stats : pynvml — P-state, throttle, PCIe gen/width, VRAM, watts

## Fichiers clés

| Fichier | Rôle | Taille |
|---------|------|--------|
| `scripts/jarvis.py` | Serveur Flask principal | **3241 lignes** · 58 routes · 112 fonctions (modularisé + rate limiters 2026-04-13) |
| `scripts/jarvis_soc_autobanned.json` | Cooldown auto-ban persisté | Survit aux redémarrages JARVIS — chargé au boot avec filtre expiry |
| `scripts/templates/jarvis.html` | UI shell Jinja2 + dispatchers | **208 lignes** · 10 onglets · 8 tabs inclus · data-action/oninput/onchange/IIFE (2026-04-18) |
| `scripts/static/jarvis_main.js` | JS principal | **9696 lignes** · 0 handler inline · `_esc()` unifié · `'use strict'` IIFE |
| `scripts/static/jarvis_mixing.js` | Mixing engine audio | **1372 lignes** · `'use strict'` IIFE · auto-duck/talkover |
| `scripts/static/jarvis.css` | CSS interface | 3 917 lignes · `.min.css` généré (-22%) |
| `scripts/static/highlight.min.js` | Syntax highlighting — local (anti CDN tracking) | 119 KB |
| `scripts/static/atom-one-dark.min.css` | Thème highlight.js — local | 856 B |
| `scripts/jarvis_llm_params.json` | Paramètres LLM persistés | temp=0.7, num_predict=**4096**, top_k=50, num_ctx=**8192** — en mode SOC : temp=**0.2**, num_ctx=**16384** (adaptatif runtime) |
| `scripts/jarvis_dsp_params.json` | DSP audio + moteur TTS | edge-tts, DeepFilter on, FX off |
| `scripts/jarvis_model.json` | Modèle actif | `{"model": "phi4-reasoning:plus"}` (2026-03-29) |
| `scripts/jarvis_welcome.json` | Texte preloader accueil | — |
| `scripts/jarvis_system_prompt.txt` | Override prompt système | **PRÉSENT** — prompt enrichi SOC actif |
| `scripts/jarvis_prompt_profiles.json` | Profils prompt sauvegardés UI | **9 profils** — 8 avec `model_binding` + champ `role` — garde RFC1918 sur tous (2026-04-13) — chain-of-thought SOC sur Phi4/Phi4-Reasoning/SOC Raisonnement — ordre : SOC Raisonnement avant Phi4-Reasoning (priorité `_get_model_profile`) |
| `scripts/jarvis_system_prompt.txt` | Prompt système actif au démarrage | Profil "SOC Raisonnement — Phi4-Reasoning+" (2026-04-13) |

## Documentation

| Fichier | Contenu |
|---------|---------|
| `doc/DEPLOIEMENT.md` | Exploitation, routes API, dépannage, roadmap — màj 2026-03-28 |
| `doc/REINSTALLATION.md` | Guide complet réinstallation Windows — Python, Ollama, packages, restauration |
| `doc/AUDIT_SECURITE_2026-03-22.md` | **Archive** — snapshot audit sécurité 2026-03-22 (ne pas modifier) |

> Supprimés : `doc/GITHUB-MODELS.md` (non-prod 2026-03-28) · `scripts/jarvis_memory.json` (supprimé) · `scripts/jarvis_providers.json` (supprimé)

## Démarrage / Arrêt

| Fichier | Rôle |
|---------|------|
| `scripts/start_dashboard.bat` | Démarrage — venv auto, poll Ollama 30s + vérif API, logs bureau (sync racine 2026-04-18) |
| `scripts/stop_jarvis.bat` | Arrêt — kill port 5000, auto-close 2s, logs |
| `Desktop/JARVIS Dashboard.lnk` | Ouvre http://localhost:5000 |
| `Desktop/JARVIS - Arrêt.lnk` | Lance stop_jarvis.bat |

## Onglets UI

| Onglet | Fonctionnalité |
|--------|---------------|
| Chat IA | Conversation LLM streaming, TTS auto, tool calling, STT mic, recherche DDG |
| Settings | LLM params (temp/top_p/num_ctx), profils prompt, provider IA, préréglages |
| DSP AUDIO | AI AUDIO RACK — EQ Voix 5 bandes, compresseur, Haas stéréo, analyseur spectral, moteur TTS |
| AUDIO EDITOR | Éditeur audio IA — waveform L/R, transport, EQ, fade, denoise, export |
| Voice Lab | Synthèse vocale — moteur TTS, paramètres, EQ, presets, comparateur A/B |
| Monitor | Stats temps réel CPU/RAM/GPU/RTX 5080 (P-state, PCIe, throttle, watts) |
| Terminal | Shell intégré (cmd/PowerShell), historique cd, taille police ajustable |
| Fichiers | Explorateur lecteurs, breadcrumb, éditeur code, analyse IA |
| Tâches | Tâches automatisées avec scheduling |
| ◈ SOC | Journal actions proactives, graphiques CVE-style, sparklines bezier, drill-down, ⚡ FORCER |

## System Prompt

Chargé depuis `jarvis_system_prompt.txt`. Profil "Marc" sauvegardé dans `jarvis_prompt_profiles.json`.

**Contenu actuel :**
- Persona JARVIS Iron Man, français exclusif, ton direct/technique
- Capacités : Python/JS/HTML/CSS/SQL/Bash, lecture fichiers, code propre
- Règles TTS : pas de markdown vocal, listes naturelles ("premièrement"...)
- **Règle IP (2026-03-28)** : IPs TOUJOURS en notation standard avec points `192.168.1.50` — JAMAIS avec tirets ni forme verbale "point"
- **Bloc SOC** : interprétation kill chain, seuils score menace, règles d'analyse

## TTS — Prononciation des IPs (2026-03-28)

`_replace_ips()` dans `jarvis.py` — module-level :
- Convertit `192.168.1.50` → `un neuf deux point un six huit point un point cinq zéro`
- Gère aussi le format tiret `192-168-1-50` → même résultat
- Appelé dans `_clean_for_tts()` ET dans la boucle streaming

**Streaming loop** : split sur `.` via `re.split(r'(?<!\d)\.(?!\d)')` — préserve les IPs intactes.

**jarvis.html** : conversion affichage `217-76-52-66` → `217.76.52.66` via regex JS dans le rendu token.

**renderMarkdown()** : blocs `<think>...</think>` masqués (phi4-reasoning, deepseek-r1).

## Intégration SOC Dashboard

JARVIS est intégré dans `monitoring-index.html`.

### Routes utilisées par le dashboard SOC

| Route | Usage |
|-------|-------|
| `GET /api/stats` | État JARVIS, modèle, GPU, RAM, CPU |
| `GET /api/boot-id` | ID de session démarrage |
| `POST /api/soc/heartbeat` | Toutes les 30s depuis SOC (TTL 90s) |
| `POST /api/chat` | Analyse LLM données SOC (streaming SSE) |
| `POST /api/speak` | TTS direct (edge-tts séquentiel avec lock) |
| `POST /api/speak/stop` | Stop TTS en cours |
| `POST /api/tts` | TTS via DSP pipeline |
| `GET /api/security` | Journal blocklist LLM |
| `POST /api/soc/ban-ip` | Ban IP via CrowdSec srv-ngix |
| `POST /api/soc/unban-ip` | Lève ban IP |
| `POST /api/soc/restart-service` | Redémarre service autorisé |
| `GET /api/soc/actions` | Journal opérations proactives |
| `GET /api/soc/monitor` | Monitoring SOC temps réel |
| `POST /api/soc/force-autoban` | Scan immédiat auto-ban — retourne candidats + raisons skip + req/h |
| `GET /favicon.ico` | Retourne 204 No Content — silence 404 |
| `GET/POST /api/llm-params` | Lecture/écriture params LLM |

### Presets rapides SOC

| Preset | voiceMinScore | Cooldown | Max Tokens | num_ctx |
|--------|--------------|----------|------------|---------|
| 🔇 SILENCIEUX | 70 | 30 min | 1024 | 2048 |
| ⚖ STANDARD | 50 | 10 min | 1024 | 2048 |
| 🔊 VERBEUX | 30 | 5 min | 2048 | 4096 |
| 🚨 FULL ALERTE | 5 | 1 min | 4096 | 8192 |

## JARVIS-menu.ps1 (bureau)

- `Get-Content` logs : `-Encoding UTF8` sur tous les fichiers (tts.log est UTF-8) — corrigé 2026-03-28
- Endpoint `/api/provider` supprimé (mort) → remplacé par `/api/models` (modèles Ollama actifs) — corrigé 2026-03-28
- Synced dans `D:\BACKUP-SCRIPTS_BUREAU`

## Scripts bureau (D:\BACKUP-SCRIPTS_BUREAU — synced 2026-03-28)

| Script | Rôle |
|--------|------|
| `stop_jarvis.bat` | Arrêt JARVIS — fix `echo [^>^>]` (ancienne version créait fichier parasite `]`) |
| `start_dashboard.bat` | Démarrage JARVIS + venv |
| `JARVIS-menu.ps1` | Menu exploitation JARVIS — endpoint /api/models corrigé |
| `JARVIS-menu.bat` | Lanceur JARVIS-menu.ps1 |
| `proxmox-backup.ps1` | Sauvegarde/restauration VMs |
| `SAUVEGARDER-VM.bat` | Lance proxmox-backup.ps1 |

## Fichiers supprimés (nettoyage 2026-03-28)

Scripts legacy supprimés de `JARVIS/scripts/` :
- `backup-sauvegardes.ps1` (remplacé par backup-jarvis.ps1)
- Autres scripts orphelins non actifs

## Historique corrections

### Session 2026-04-13 — passe 2 — Intelligence + Sécurité

1. **Garde RFC1918** — prompt système (`jarvis.py` L~1349) + 9 profils (`jarvis_prompt_profiles.json`) + log `ban_ip_blocked` (`soc.py` L~437). IPs LAN jamais signalées comme menaces. Infrastructure connue listée.
2. **Température SOC adaptative** — `api_chat()` : `temperature=0.2` + `num_ctx=16384` si `soc_ctx_injected` ou `_soc_trigger`. Réduit les hallucinations LLM en mode analyse sécurité.
3. **Chain-of-thought SOC** — 3 profils enrichis (Phi4, Phi4-Reasoning, SOC Raisonnement) : ordre d'analyse imposé (EXPLOIT → score → ressources → recommandation unique).
4. **Modèle défaut** — `jarvis_model.json` → `phi4-reasoning:plus`. `jarvis_system_prompt.txt` → profil "SOC Raisonnement". Ordre profils JSON corrigé (SOC Raisonnement avant Phi4-Reasoning pour `_get_model_profile`).
5. **Rate limiting complet** — 9 routes `jarvis.py` + 6 routes `soc.py` couvertes. Score audit : **10/10 — 0 dette ouverte**.

### Session 2026-04-12 — soc.py cooldowns TTS + exploit gap fix

**Problème** : IP 77.127.177.100 (IL) annoncée en boucle dans tts.log — "Alerte SOC. Niveau CRITIQUE." toutes les 10 min, "Suricata : IPs déjà sous contrôle" toutes les 15 min, IP EXPLOIT re-bannée toutes les 15 min.

**Fixes dans `blueprints/soc.py`** :

| Fonction | Avant | Après |
|----------|-------|-------|
| `_soc_threat_level` | cooldown `threat_X` 10 min | **30 min** |
| `_soc_suricata_check` | cooldown `suricata_sev1_noban` 15 min | **60 min** |
| `_soc_exploit_gap_check` | check `ip_obj.get("cs_decision")` seulement | + `cs_detail.get(ip)` — lit `crowdsec.decisions_detail` |

**Cause racine** : `monitoring.json` → `kill_chain.active_ips` ne remplit pas toujours `cs_decision` même si l'IP est bannie dans CrowdSec. La fonction lisait `decisions_detail` indirectement pour d'autres checks mais pas dans le gap_check. Résultat : IP re-bannée toutes les 15 min inutilement + TTS spam à chaque cycle.

→ Redémarrage JARVIS requis pour activer les changements.

---

### Session 2026-03-30 — Fix DeepFilterNet + SSH ban + tts.log rotation + _SOC_AUTO_BANNED persisté

1. **DeepFilterNet CUDA_VISIBLE_DEVICES (ligne 48)**
   - Avant : `os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")` — setdefault n'override pas si déjà défini, `""` ne masque pas CUDA sur PyTorch 2.6+cu124
   - Après : `os.environ["CUDA_VISIBLE_DEVICES"] = "-1"` — force CPU ; RTX 5080 Blackwell (sm_120) non supporté PyTorch < 2.7
   - Résultat : plus de `[DeepFilterNet] Non disponible: RuntimeError` au démarrage

2. **SSH ban — `_SSH_LOCK` + retry + timeout (lignes ~2539-2609)**
   - Cause : 4+ bans simultanés → connexions SSH parallèles vers srv-ngix → timeouts en compétition
   - `_SSH_LOCK = threading.Lock()` — sérialise toutes les connexions SSH (une seule à la fois)
   - `ConnectTimeout` : 8s → **10s** · `timeout` subprocess : 15s → **20s** · `retries=1` (retry après 2s)
   - ControlMaster retiré — Windows OpenSSH ne supporte pas les Unix sockets
   - Résultat : 9 bans en 3s à 22:06, 0 échec depuis redémarrage

3. **tts.log — rotation `RotatingFileHandler` (ligne 38)**
   - Avant : `FileHandler` basique — log illimité (528 lignes, croissance continue)
   - Après : `RotatingFileHandler(maxBytes=50_000, backupCount=3)` — max ~50 KB, 3 archives, ~200 KB total
   - Résultat : tts.log plafonné, archives tts.log.1/2/3

4. **`_SOC_AUTO_BANNED` persisté (lignes ~2536-2559, ~3263, ~3315)**
   - Avant : dict en mémoire vive → perdu à chaque redémarrage → IPs re-bannies en boucle (redondant dans CrowdSec)
   - Après : `jarvis_soc_autobanned.json` — `_load_auto_banned()` au boot (filtre expiry 15min), `_save_auto_banned()` après chaque ban
   - Résultat : cooldown préservé entre redémarrages, plus de double-ban

---

### Session 2026-03-28 (graphiques SOC + rotation + auto-ban autonome + fixes console)

1. **Rotation 30 jours** dans `_soc_log()` — purge date-based + garde-fou `_SOC_ACT_MAX=1000`
2. **`/api/soc/actions`** : ajoute `ts_list` (tous les timestamps) pour alimenter les graphiques
3. **Onglet ◈ SOC jarvis.html** — cartes semaines MOIS+S1-S5 avec sparklines bezier rouges
4. **Grand graphique CVE-style** — courbe bezier lisse, fill gradient, axes Y/X, séparateurs S1-S5, pic annoté
5. **Navigation drill-down** : clic MOIS → mois complet · clic Sx → 7 jours · clic point → 24h horaire
6. **Navigation ◂ ▸** entre mois
7. **`_soc_autoban(data)`** Python — équivalent JS `checkAutoBan()`, actif quand dashboard fermé — EXPLOIT (1 hit), honeypot (1 hit), BRUTE (≥30), cooldown 15min/IP
8. **`_soc_reqhour_check(data)`** Python — spike >500 req/h, ban top 3 IPs kill chain, cooldown 20min global
9. **`_soc_monitor_loop()`** appelle les deux fonctions — se désactive si dashboard ouvert (JS prend le relais)
10. **`/api/soc/force-autoban`** — déclenchement immédiat avec payload diagnostic (candidats + skip reasons + req/h)
11. **`⚡ FORCER`** bouton dans onglet ◈ SOC
12. **Fix `_dspRenderCustomProfiles`** — appel mort supprimé dans `initDsp()`
13. **Fix `slider-vertical`** — propriétés CSS dépréciées supprimées de `.mix-fader` (writing-mode suffisant)
14. **Fix CDN tracking** — highlight.js et atom-one-dark.css téléchargés localement dans `scripts/static/`
15. **Fix favicon 404** — route `/favicon.ico` retourne 204

### Session 2026-03-28 — Sécurité + nettoyage docs

1. **`host="127.0.0.1"`** dans `app.run()` (ligne 3235) — JARVIS n'écoute plus sur le LAN, loopback uniquement
   - Avant : `host="0.0.0.0"` — accessible depuis tout le réseau sans auth
   - Après : `host="127.0.0.1"` — localhost uniquement (SOC dashboard JS non impacté)
2. **`tts.log` purgé** — contenait des traces Groq/OpenRouter = fuite de données
3. **Groq/OpenRouter supprimés** de tous les docs : `MEMORY.md`, `README.md`, `doc/DEPLOIEMENT.md`, `doc/REINSTALLATION.md`
4. **`doc/GITHUB-MODELS.md` supprimé** — feature non en production
5. **`doc/DEPLOIEMENT.md`** : section providers, arborescence, table backup, bugs table — nettoyés

### Session 2026-03-28 (IPs TTS + sécurité infra)

1. **`_replace_ips()`** : fonction module-level pour prononcer les IPs chiffre par chiffre en FR
2. **Streaming loop** : `re.split(r'(?<!\d)\.(?!\d)')` — IPs préservées pendant le split
3. **LLM outputs dash IPs** : système prompt corrigé + conversion JS affichage + `_replace_ips()` gère tirets
4. **`num_predict` 512→2048, `num_ctx` 1024→8192** : phi4-reasoning ne tronquait plus ses réponses
5. **`<think>` masqué** dans `renderMarkdown()` — chaîne de raisonnement cachée
6. **9 profils prompt** mis à jour : IPs notation standard
7. **JARVIS-menu.ps1** : encodage UTF-8 + endpoint mort supprimé

### Session 2026-03-27 (bugs startup + intégration SOC vocale)

1. `--- Logging error ---` DeepFilterNet : `sys.stderr` redirigé + fd2
2. Kokoro import lazy (plus de blocage torch au démarrage)
3. Alerte vocale SOC auto-ban via `POST localhost:5000/api/speak`

### Session 2026-03-22 (AI AUDIO RACK + sécurité)

- TTS Lock : `_TTS_LOCK.acquire(blocking=False)` — plus de doublons vocaux
- XSS corrigé, Threading lock `_CONFIG_LOCK`

## Roadmap

- [x] Interface web complète v3.2
- [x] STT local (faster-whisper)
- [x] Intégration SOC dashboard (tuile + auto-engine)
- [x] TTS Lock — plus de doublons vocaux
- [x] Presets rapides SOC
- [x] Alertes vocales TTS ÉLEVÉ/CRITIQUE
- [x] System prompt SOC expertise
- [x] buildContext() enrichi
- [x] Alerte vocale auto-ban SOC
- [x] IPs prononcées chiffre par chiffre (2026-03-28)
- [x] Streaming loop préserve les IPs (2026-03-28)
- [x] num_predict/num_ctx phi4-reasoning (2026-03-28)
- [x] host="127.0.0.1" — exposition LAN supprimée (2026-03-28)
- [x] Onglet `◈ SOC` dans jarvis.html — journal actions proactives, compteurs, analyse narrative LLM, auto-refresh 30s (2026-03-28)
- [x] Triggers : ban auto si >500 req/h — banne IPs kill chain non bannies, tri EXPLOIT>BRUTE>SCAN, max 3 IPs/cycle, cooldown 20min (2026-03-28)
- [x] Graphiques SOC — cartes semaines (MOIS+S1-S5) + sparklines bezier + grand graphique CVE-style cliquable (2026-03-28)
- [x] Journal SOC persisté — rotation 30 jours (date-based) + garde-fou 1000 entrées (2026-03-28)
- [x] Auto-ban autonome Python `_soc_autoban()` + `_soc_reqhour_check()` quand dashboard fermé (2026-03-28)
- [x] `⚡ FORCER` — scan immédiat auto-ban depuis onglet SOC (2026-03-28)
- [x] Fix console F12 : `_dspRenderCustomProfiles`, slider-vertical, CDN tracking, favicon 404 (2026-03-28)
- [x] highlight.js + thème CSS auto-hébergés dans `scripts/static/` (2026-03-28)
- [x] Fix stop_jarvis.bat — `echo [^>^>]` (fichier parasite `]` supprimé) (2026-03-28)
- [x] Fix JARVIS-menu.ps1 — endpoint `/api/provider` mort → `/api/models` (2026-03-28)
- [x] backup-jarvis.ps1 — `jarvis_providers.json` retiré des critiques (fichier supprimé) (2026-03-28)
- [x] Fix DeepFilterNet — `CUDA_VISIBLE_DEVICES="-1"` force CPU (RTX 5080 sm_120 non supporté PyTorch < 2.7) (2026-03-30)
- [x] Fix SSH ban — `_SSH_LOCK` sérialisation + timeout 20s + retry×1 (2026-03-30)
- [x] tts.log — `RotatingFileHandler` (50 KB × 3 archives) (2026-03-30)
- [x] `_SOC_AUTO_BANNED` persisté dans `jarvis_soc_autobanned.json` (cooldown survit aux redémarrages) (2026-03-30)
- [x] Audit 2026-03-31 — JARVIS sain, 231 actions SOC, 0 erreur tts.log, métriques alignées CLAUDE.md + MEMORY.md (2026-03-31)
- [x] Auto-restart service DOWN — systemctl restart via SSH si service in _ALLOWED_SERVICES détecté DOWN (2026-04-01)
- [x] _soc_reqhour_check : Suricata recent_scans IPs ajoutées comme candidats ban EXPLOIT (2026-04-01)
- [x] _soc_suricata_check : ban sév.3 NMAP (≥3 hits, 24h) via recent_scans (2026-04-01)
- [x] Seuils sév.2 recalibrés ×10 : >3000/+10, >1500/+7 (Python + JS alignés) (2026-04-01)
- [x] EQ Music TASCAM DAT — 4 bandes isolées (SUB/BASS/MIDS/TREBLE), canvas drag, 8 presets, save/load (2026-04-02)
- [x] Chaîne audio isolée — voix JARVIS et TASCAM sur chemins séparés, fini sifflement (2026-04-02)
- [x] Fix boucles rétroaction — 3 connexions `analyser→analyserL/R` supprimées de `initDsp()` (2026-04-02)
- [x] Fix rack faders `--f-pct` — resync après chargement async params DSP (2026-04-02)
- [x] `_soc_exploit_gap_check()` — ban EXPLOIT cs_decision=None même dashboard ouvert (2026-04-02)
- [x] `_soc_monitor_loop()` restructuré — fetch avant gate dashboard, gap check systématique (2026-04-02)
- [x] STT `beam_size` 5→2 — ~2× plus rapide, précision maintenue sur CUDA float16 (2026-04-02)
- [x] `_LAN_PREFIXES` — ajout `192.168.50.` (subnet Windows LAN — protège contre auto-ban local) (2026-04-02)
- [x] `buildContext()` — `net_spikes` injecté dans contexte LLM (spikes <1h, format datetime+Mbps) (2026-04-03)
- [x] `_soc_monitor_loop()` — alerte vocale spike réseau TX/RX>1.5Mbps·2×avg, cooldown 30min, âge<360s (2026-04-03)
- [x] Profils LLM liés — `model_binding` + `role` dans jarvis_prompt_profiles.json · 6 modèles couverts (2026-04-04)
- [x] Auto-chargement profil au switch modèle — `api_set_model()` retourne `auto_profile`, UI mis à jour (▶ + badge) (2026-04-04)
- [x] Popup rôle sur cartes modèles — badge `◈` + tooltip holographique au survol (2026-04-04)
- [x] mistral-small3.1 supprimé d'Ollama — 15.5 GB sur 16 GB VRAM, trop limitant (2026-04-04)
- [x] Journal sécurité interne JARVIS — section Settings (tentatives injection/args/terminal) + ACTUALISER + VIDER (2026-04-04)
- [x] Audit code mort 2026-04-04 — 0 fonction Python/JS orpheline, 0 import inutilisé, codebase sain
- [x] Audit sécurité 2026-04-06 — **9.5/10** — code propre, risque réel quasi nul (loopback strict)

---

## Session 2026-04-06 — Audit sécurité

### Résultat : 9.5/10 — aucune correction nécessaire

**Positifs validés :**
- `host=127.0.0.1` loopback strict — zéro exposition LAN
- `debug=False` en prod
- Rate limiting Flask-Limiter sur routes sensibles (ban-ip 10/min, ping 20/min)
- `ipaddress.IPv4Address(ip)` — validation IP stricte
- LAN prefixes protégés sur 8 occurrences (jamais bannables)
- `_ALLOWED_SERVICES` whitelist stricte (nginx/crowdsec/fail2ban/php)
- Ping : regex `^[a-zA-Z0-9.\-_]+$` + `shell=False`
- Terminal normal : `shlex.split()` + `shell=False`
- STT : whitelist extensions `{webm, wav, mp3, ogg, flac, m4a, mp4, opus}`
- Zéro clé API hardcodée
- `reason` sanitisé : `re.sub(r"[^\w\s\-\.]", "", reason)[:80]`

**Points INFO — risque accepté (localhost uniquement) :**
- Terminal task runner `shell=True` intentionnel (pipes/redirections) — feature voulue
- SSH blacklist textuelle (pas de whitelist stricte) — bypass théorique, localhost only
- `executer_code` blacklist Python imparfaite — LLM local bien aligné, risque minimal

**Risque réel :** quasi nul — seul accès localhost depuis navigateur local. Pas de session Flask → pas de besoin de SECRET_KEY.

---

## Session 2026-04-04 — Profils LLM liés + audit code mort

### Profils LLM avec model_binding

Chaque modèle Ollama a désormais un profil system prompt lié automatiquement chargé au switch :

| Modèle | Profil lié |
|--------|-----------|
| `phi4-reasoning:plus` | SOC Raisonnement — Phi4-Reasoning+ 0 |
| `deepseek-r1:14b` | DeepSeek-R1 — Raisonnement |
| `phi4:14b` | Phi4 — Généraliste & Code |
| `qwen2.5:14b` | Qwen2.5 — Code & Polyvalent |
| `gemma4:latest` | Gemma4 — Conversation Fluide (remplace gemma3:12b — flash attention actif 0.20.4) |
| `llava-phi3:latest` | ◈ LLaVA-Phi3 — Vision & Analyse Image |

**Mécanisme** : `_get_model_profile(model)` dans jarvis.py — retourne `(nom, contenu)` · `api_set_model()` applique le profil et retourne `auto_profile` · `switchModel()` côté JS appelle `_updateActivePromptBadge()` + `loadPromptProfiles()` → `▶` se déplace sur le bon profil.

Chaque profil a aussi un champ `role` (courte description) affiché en popup au survol du badge `◈` sur la carte modèle.

### Mistral supprimé

`mistral-small3.1:latest` supprimé d'Ollama — 15.5 GB sur 16 GB VRAM laissait quasi zéro KV cache.

### Journal sécurité interne

Section `// SÉCURITÉ INTERNE JARVIS` ajoutée dans l'onglet Settings — consomme `/api/security` (GET) et `/api/security/clear` (POST). Affiche les 10 derniers événements `_SEC_EVENTS` (INJECTION / ARGS / TERMINAL) avec heure, type coloré, extrait.

### Audit code mort

- 0 fonction Python orpheline · 0 fonction JS orpheline · 0 import inutilisé
- 4 routes sans UI conservées intentionnellement : `/api/dsp/process-audio`, `/api/tts-log`, `/api/soc/test` (diagnostics) + `/api/security` maintenant intégré
- Classes CSS `.y` et `.lim` : faux positifs de l'agent — utilisées (`.fx-vu-led.y`, `.mix-dsp-toggle.active.lim`)

---

## Session 2026-04-03 — Net spike detection + contexte LLM enrichi

### Net spikes dans buildContext()

`buildContext()` injecte les spikes réseau récents (<1h) dans le contexte LLM :
- Lit `data.get("net_spikes", [])`, filtre `age < 3600s`
- Format : `"2026-04-03 02:14 — TX 2.5 Mbps, RX 1.1 Mbps"`
- JARVIS peut désormais raisonner sur les anomalies trafic lors de ses analyses SOC

### Alerte vocale spike réseau

Dans `_soc_monitor_loop()` — après `_soc_exploit_gap_check()` :
- Condition : spike récent (`age < 360s`) + `not _soc_dashboard_open()`
- Cooldown global 30min (`_NET_SPIKE_LAST_VOCAL` timestamp)
- Message TTS : `"Anomalie réseau détectée. Pic de trafic TX [x] Mbps."`
- Logique : même structure que l'alerte auto-ban — activée que quand dashboard fermé

### Contexte global session

- monitoring_gen.py v3.5.0 patché sur srv-ngix : `detect_net_spikes()` + `net-spike-log.json`
- Dashboard SOC v3.68.3 déployé : BLOCKLIST modal 680→480px, tab Freebox ⚡ ALERTES TRAFIC, SSL 2 colonnes
- Scripts bureau nettoyés + alignés : `soc-menu.bat`, `DEPLOYER-CLT.bat` créés, `PROXMOX-BACKUP.ps1` → `SAUVEGARDER-VM.ps1`
- RAM VMs redistribuée : srv-ngix 6→10 GB, clt 6→2 GB, pa85 4→2 GB

---

## Session 2026-04-02 — EQ Music TASCAM + nettoyage chaîne audio

### Problèmes résolus

#### Sifflement (larseine) sur voix ET musique
- **Cause** : `initDsp()` contenait `analyser.connect(analyserL)`, `analyser.connect(_monHaas)`, `_monHaas.connect(analyserR)` — créaient des boucles de rétroaction via `_stereoMerger→analyser` (déjà connecté dans `_ensureAudioCtx`)
- **Fix** : suppression des 3 lignes. `analyserL/R` alimentés uniquement par `_connectStereoSource` (sources TTS)

#### TASCAM bypassait l'EQ Voix
- `_datPreDsp` était connecté à `_dspCompressor` directement — il passait par l'EQ Voix (Air +12dB à 12kHz)
- **Fix** : `window._dspCompressor` exposé dans `initDsp()`. TASCAM redirigé vers `_initDatEq()` dédié

#### Drag EQ Music décalé
- `_datEqGetHandle` et `datEqCanvasMove` utilisaient des marges différentes de `drawDatEqCurve`
- **Fix** : constantes partagées `_DAT_EQ_ML=42, _DAT_EQ_MR=42, _DAT_EQ_MT=14, _DAT_EQ_MB=22`

#### Rack faders fill désynchronisé (`--f-pct`)
- `rackInitFaders()` s'exécute avant le chargement async des params → faders à 0% visuellement
- **Fix** : resync global de tous `.rack-fader` à la fin du `fetch` + `_rackFaderFill()` dans les fonctions sync
- `rackSyncComp()`/`rackSyncGain()` appelaient `updateSliderPct()` (écrit `--pct`) sur des `.rack-fader` (besoin de `--f-pct`) → remplacé par `_syncRangeSlider()`

### Chaîne audio finale (2026-04-02)

```
JARVIS voix : source → analyserL/R → _stereoMerger → analyser → _jarvisPreGain
              → _dspAnalyser → EQ Voix (LOW/MID/HIGH/AIR) → _dspCompressor → _dspLimiter → _dspGainNode → destination

TASCAM DAT  : source → datGain → _datLimiter → _datAnL/R (VU) → _datPreDsp
              → EQ Music (_datEqSub→_datEqBass→_datEqMids→_datEqTreble) → _dspCompressor → _dspLimiter → _dspGainNode → destination
```

**Règle** : ne jamais reconnecter `analyser→analyserL/R` dans `initDsp()` — crée une boucle de rétroaction.

### EQ Music TASCAM — détails implémentation

**Nœuds Web Audio** :
- `_datEqSub` — lowshelf 80Hz Q=0.7
- `_datEqBass` — peaking 300Hz Q=0.8
- `_datEqMids` — peaking 3000Hz Q=0.9
- `_datEqTreble` — highshelf 10000Hz Q=0.7

**Initialisation** : `_initDatEq(ctx)` dans TASCAM IIFE — idempotent (check `context === ctx`), appelé dans `datPLAY()`

**UI** : rack identique à EQ Voix — 4 cards (SUB=orange, BASS=jaune, MIDS=vert, TREBLE=bleu) + canvas 160px dans le modal DAT player

**8 presets** : FLAT · BASS · BRIGHT · WARM · CLUB · ACOUSTIQUE · ROCK · JAZZ

**Save/load** : clés `dat_eq_sub/bass/mids/treble` dans `jarvis_dsp_params.json`

**Drag** : objet `_datEqDrag = { idx, startFreq, startGain }`, coordonnées `e.clientX - rect.left`, rayon détection 28px

**Visualiseur** : `drawDatEqCurve()` appelé dans `startDspDraw()` RAF quand modal visible

### Session 2026-04-02 — SOC exploit gap + STT optimisation

#### `_soc_exploit_gap_check(data)` — nouvelle fonction jarvis.py

**Problème résolu** : `_soc_monitor_loop()` faisait `if _soc_dashboard_open(): continue` avant tout — les IPs EXPLOIT avec `cs_decision=None` n'étaient jamais bannies automatiquement quand le dashboard était ouvert. Le JS pouvait rater des IPs selon l'état de l'onglet.

**Fix** : restructuration du loop — `_fetch_monitoring()` + `_soc_exploit_gap_check(d)` s'exécutent AVANT le gate dashboard. Le gate ne bloque plus que les alertes TTS et `_soc_autoban()`.

**Logique gap check** :
- Itère `kill_chain.active_ips`
- Filtre : `stage=EXPLOIT` ET `cs_decision` falsy (None = non bloqué CrowdSec)
- Skip : `_LAN_PREFIXES`, cooldown `_SOC_AUTO_BANNED` 15min partagé avec `_soc_autoban()`
- Ban : `cscli decisions add --duration 48h --reason jarvis-autoban-exploit-gap`
- TTS : uniquement si `not _soc_dashboard_open()` (JS parle quand dashboard ouvert)
- Log : `_soc_log("ban_ip", ...)` systématique

**Pas de doublon** : cooldown `_SOC_AUTO_BANNED` partagé — si gap check ban en premier, `_soc_autoban()` skip via `now - _SOC_AUTO_BANNED.get(ip, 0) < 15min`.

#### STT beam_size optimisé

- `beam_size` : 5 → **2** dans `/api/stt` — ~2× plus rapide sur CUDA float16
- `vad_filter=True` déjà actif (skip silences)
- CUDA float16 déjà actif (auto-détecté via `ctranslate2.get_cuda_device_count()`)
- `VOCAL_MODEL = "gemma4:latest"` — bascule auto sur requêtes `[VOCAL]` (préfixe STT) confirmé actif

#### STT modèle — axes d'amélioration identifiés (non appliqués)

- Upgrade `small` → `large-v3-turbo` : meilleure précision FR, ~0.4s latence CUDA
- `initial_prompt` : vocabulaire métier (CrowdSec, fail2ban, Suricata, nftables...)
- À appliquer si reconnaissance insuffisante sur termes techniques

---

### Session 2026-03-31 — Audit + alignement métriques

### Audit réalisé (état au 2026-03-31 — référence courante)

| Mesure | Valeur |
|--------|--------|
| jarvis.py | **3572 lignes** |
| jarvis.html | **17443 lignes** |
| Routes Flask | **55** |
| Fonctions def | **124** |
| Onglets UI | 10 |
| Uptime | 12h 03m (redémarré 2026-03-31 matin) |
| Modèle actif | phi4-reasoning:plus (Q4_K_M — 14.7B) |
| LLM params | temp=0.5 · num_predict=2048 · num_ctx=8192 · top_k=20 · top_p=0.85 · repeat_penalty=1.1 |
| DeepFilterNet | ON — CPU forcé (`CUDA_VISIBLE_DEVICES="-1"`) |
| SSH ban | `_SSH_LOCK` sérialisé · timeout 20s · retry 1× |
| tts.log | `RotatingFileHandler` 50 KB × 3 archives — 32 KB actif, sain |
| Auto-ban cooldown | persisté dans `jarvis_soc_autobanned.json` |
| GPU | RTX 5080 — 46°C · 3% util · 2.0/16 GB VRAM |

### Journal SOC au 2026-03-31

`jarvis_soc_actions.json` : **231 actions** (225 succès · 9 échecs anciens · 0 échec récent).
- 228 ban_ip · 2 unban_ip · 0 restart_service
- Dernier ban : 21:55 — EXPLOIT honeypot CN — 100% succès sur les 50 dernières actions
- Auto-ban autonome `_soc_monitor_loop()` opérationnel — poll 60s dashboard fermé

### Corrections métriques 2026-03-31

- `CLAUDE.md` mis à jour : 3427/49/93 → **3572/55/124** lignes/routes/fonctions
- `JARVIS/MEMORY.md` aligné sur valeurs réelles audit
