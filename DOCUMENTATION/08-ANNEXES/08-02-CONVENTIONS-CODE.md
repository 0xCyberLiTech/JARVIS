---
title: "Conventions de code â€” Python, JS, commits"
code: "JARVIS-DOC-08-02"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-06-09"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "ValidÃ©"
categorie: "Annexes"
mots_cles: ["conventions", "code-style", "python", "javascript", "commits", "hooks"]
---

# Conventions de code

## Python

### Style gÃ©nÃ©ral

- **Linter** : ruff (config `ruff.toml`)
- **Version Python** : 3.11 (type hints natifs `str | None`, etc.)
- **Indentation** : 4 espaces (PEP 8)
- **Encoding** : UTF-8 (dÃ©claration shebang inutile)
- **End of line** : LF (pas CRLF mÃªme sous Windows)

### Imports

```python
# 1. Standard library
import json
import os
from pathlib import Path

# 2. Third-party
from flask import Blueprint, Response

# 3. Local (projet)
from chat import orchestrator
from . import bp
```

### Nommage

| Ã‰lÃ©ment | Convention | Exemple |
|---|---|---|
| Module | snake_case | `chat_orchestrator.py` |
| Classe | PascalCase | `LlmCtx` |
| Fonction publique | snake_case | `ensure_vram()` |
| Fonction privÃ©e | snake_case avec underscore | `_chat_stream_inner()` |
| Constante module | UPPER_SNAKE | `RAG_EMBED_MODEL` |
| Variable module privÃ©e | underscore + snake_case | `_jarvis_mode` |
| DI placeholder | underscore | `_log = None` (rempli par init) |

### Docstrings

```python
def ensure_vram(next_model: str) -> None:
    """DÃ©charge le modÃ¨le actuellement en VRAM si diffÃ©rent du prochain.

    Ã‰vite les collisions VRAM lors du routing automatique inter-modes.

    ProtÃ©gÃ© par `_vram_lock` : sÃ©rialise check + swap + mutation pour Ã©liminer
    la race condition multi-requÃªte."""
```

- PremiÃ¨re ligne : rÃ©sumÃ© concis (impÃ©ratif)
- Lignes suivantes : dÃ©tail (sÃ©parÃ© par ligne vide si plusieurs paragraphes)
- Mention des invariants ou contraintes (lock, race, etc.)

### Type hints

- **Obligatoire** sur les signatures de fonctions publiques
- **Optionnel** sur les variables locales
- Style Python 3.11 : `str | None` au lieu de `Optional[str]`

### Pattern DI (Dependency Injection)

```python
# Module-level placeholders
_log = None
_get_model = None
_set_model = None


def init(*, log, get_model, set_model) -> None:
    """Injecte les deps consommÃ©es par ce module."""
    global _log, _get_model, _set_model
    _log = log
    _get_model = get_model
    _set_model = set_model
```

Pourquoi :
- Pas de variables globales hardcodÃ©es
- TestabilitÃ© totale (mock chaque dep)
- DÃ©couplage entre tuiles

### Commentaires

```python
# Bonne pratique : explique le POURQUOI, pas le QUOI
# âš  Protection anti-cascade : voir bug UI reload 2026-05-23
if _threads_started:
    return

# Ã€ Ã©viter : commentaires qui rÃ©pÃ¨tent le code
x = x + 1  # âŒ on incrÃ©mente x
```

## JavaScript

### Style gÃ©nÃ©ral

- **Linter** : eslint (config `eslint.config.js`)
- **Version** : ES2022 (async/await, optional chaining)
- **Indentation** : 2 espaces
- **Quotes** : simples `'string'` (sauf si la string contient une apostrophe)
- **Semi-colons** : oui systÃ©matiquement

### Nommage

| Ã‰lÃ©ment | Convention | Exemple |
|---|---|---|
| Fonction publique | camelCase | `setVoiceMode()` |
| Fonction privÃ©e | underscore + camelCase | `_setMode()` |
| Variable | camelCase | `let activeMode = 'soc';` |
| Constante module | UPPER_SNAKE | `const _MODE_TARGET_MODEL = {...};` |
| Variable globale | underscore + camelCase | `var _jarvisMode = 'soc';` |
| Event handler | onAction | `onclick = () => setModeCode();` |

### Pattern fetch SSE (Server-Sent Events)

```javascript
async function streamFromChat(payload) {
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const reader = resp.body.getReader();
  // ...
}
```

### Pattern send-and-forget (instrumentation)

```javascript
// JS-DIAG : envoi de log au serveur sans bloquer
navigator.sendBeacon('/api/_diag/jslog', JSON.stringify(data));
// Fallback : fetch keepalive
fetch('/api/_diag/jslog', {
  method: 'POST',
  body: JSON.stringify(data),
  keepalive: true,
}).catch(() => {});
```

## Commits Git

### Format

```
type(scope): description courte (â‰¤ 70 chars)

Description dÃ©taillÃ©e multi-ligne expliquant le pourquoi du changement,
les alternatives Ã©valuÃ©es, l'impact mesurÃ©.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

### Types (prÃ©fixÃ©s)

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalitÃ© |
| `fix` | Correction de bug |
| `refactor` | RÃ©organisation du code, pas de changement fonctionnel |
| `test` | Ajout ou modification de tests |
| `docs` | Documentation seule |
| `chore` | Maintenance (linter, hooks, build) |
| `perf` | Optimisation performance |
| `style` | Mise en forme code (whitespace, formatting) |

### Scopes typiques

`jarvis` (par dÃ©faut, modifications JARVIS), `soc` (blueprints/soc.py),
`tests`, `docs`, `ci`, `infra`.

### Exemples

```
refactor(jarvis): llm/vram + llm/stream - VRAM swap + stream Ollama (etape 35)

23eme tuile : llm/ regroupe le coeur runtime LLM extrait de jarvis.py.

llm/vram.py (98L) :
- ensure_vram(next_model) : decharge modele courant si different
- ollama_swap(unload, load) : unload SYNCHRONE + preload BACKGROUND
- DI : log, get_model, get_vram_model, set_vram_model, vram_lock, ollama_url

ruff: All checks passed.
pytest: 1214 passed (zero regression).
```

```
fix(jarvis): idempotence _log.addHandler + start_all() (bug doublons / interference VRAM)

[diagnostic detaille]

A faire chez Marc : redemarrer JARVIS pour activer le fix.
```

### Garde-fous Git

- **NEVER** commit `--no-verify` ou `--no-gpg-sign` (sauf demande explicite)
- **NEVER** force push sur main/master (sauf demande explicite)
- **NEVER** modifier la config git (`git config user.X`)
- **NEVER** crÃ©er commits vides
- **NEVER** commit fichiers `.env`, `*credentials*`, `*.key`, `soc_config.json`, `jarvis_pve.json`

### Pre-commit hooks (`.pre-commit-config.yaml`)

```
- ruff check (Python)
- eslint (JS)
- (commit Ã©choue si erreur)
```

### Pre-push hook

```
- pytest tests/python/ (1294 tests)
- (push Ã©choue si fail)
```

## Tests

### Structure

```
tests/python/
â”œâ”€â”€ conftest.py                    # Setup : os.environ JARVIS_SKIP_BOOT_THREADS=1 + sys.path
â”œâ”€â”€ test_jarvis_app.py             # Tests app Flask
â”œâ”€â”€ test_jarvis_routes.py          # Tests routes
â”œâ”€â”€ test_jarvis_functions.py       # Tests fonctions pures
â”œâ”€â”€ test_<tuile>_<sous-module>.py  # Tests par tuile
â””â”€â”€ ...
```

### Convention nommage tests

```python
def test_<feature>_<scenario>():
    """<phrase explicite dÃ©crivant le test>."""
    # Given (setup)
    # When (action)
    # Then (assertion)
```

### Mock patterns

```python
# Patch d'attribut module
with patch.object(module, "function", return_value=42):
    result = module.consumer()

# Fixture autouse pour DI propre
@pytest.fixture(autouse=True)
def _reinit_module():
    saved = {k: getattr(module, k) for k in (...)}
    module.init(...)
    yield
    for k, v in saved.items():
        setattr(module, k, v)
```

## Documentation

### Frontmatter YAML obligatoire

```yaml
---
title: "Titre humain"
code: "JARVIS-DOC-NN-MM"
version: "1.0"
date_creation: "YYYY-MM-DD"
date_revision: "YYYY-MM-DD"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "ValidÃ©"  # Brouillon | Revue | ValidÃ© | ObsolÃ¨te
categorie: "PrÃ©sentation"
mots_cles: ["mot1", "mot2", "..."]
---
```

### Conventions Markdown

- **Titre H1** : un seul, en dÃ©but (aprÃ¨s frontmatter)
- **Liens internes** : chemins relatifs (`[doc](../06-BILAN/06-01.md)`)
- **Liens externes** : URL complÃ¨te (`[Anthropic](https://anthropic.com/)`)
- **Code inline** : backticks simples `var_name`
- **Bloc code** : triple backticks avec langage (` ```python `)
- **Tableaux** : alignement `|---|---|` simple

## Fichiers gitignored (sensibles)

```gitignore
*.log
*.log.*
scripts/jarvis_secret.key
scripts/jarvis_pve.json
scripts/soc_config.json
scripts/jarvis_dsp_params.json
scripts/jarvis_llm_params.json
scripts/jarvis_system_prompt.txt
scripts/jarvis_rag/
*.bak.*
```

**Ne JAMAIS** committer ces fichiers, ni les indexer dans le RAG.

