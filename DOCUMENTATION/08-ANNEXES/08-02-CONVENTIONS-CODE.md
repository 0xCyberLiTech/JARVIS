---
title: "Conventions de code — Python, JS, commits"
code: "JARVIS-DOC-08-02"
version: "1.0"
date_creation: "2026-05-23"
date_revision: "2026-05-23"
auteur: "Marc Sabater (0xCyberLiTech)"
contributeurs: ["Claude (Anthropic)"]
statut: "Validé"
categorie: "Annexes"
mots_cles: ["conventions", "code-style", "python", "javascript", "commits", "hooks"]
---

# Conventions de code

## Python

### Style général

- **Linter** : ruff (config `ruff.toml`)
- **Version Python** : 3.11 (type hints natifs `str | None`, etc.)
- **Indentation** : 4 espaces (PEP 8)
- **Encoding** : UTF-8 (déclaration shebang inutile)
- **End of line** : LF (pas CRLF même sous Windows)

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

| Élément | Convention | Exemple |
|---|---|---|
| Module | snake_case | `chat_orchestrator.py` |
| Classe | PascalCase | `LlmCtx` |
| Fonction publique | snake_case | `ensure_vram()` |
| Fonction privée | snake_case avec underscore | `_chat_stream_inner()` |
| Constante module | UPPER_SNAKE | `RAG_EMBED_MODEL` |
| Variable module privée | underscore + snake_case | `_jarvis_mode` |
| DI placeholder | underscore | `_log = None` (rempli par init) |

### Docstrings

```python
def ensure_vram(next_model: str) -> None:
    """Décharge le modèle actuellement en VRAM si différent du prochain.

    Évite les collisions VRAM lors du routing automatique inter-modes.

    Protégé par `_vram_lock` : sérialise check + swap + mutation pour éliminer
    la race condition multi-requête."""
```

- Première ligne : résumé concis (impératif)
- Lignes suivantes : détail (séparé par ligne vide si plusieurs paragraphes)
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
    """Injecte les deps consommées par ce module."""
    global _log, _get_model, _set_model
    _log = log
    _get_model = get_model
    _set_model = set_model
```

Pourquoi :
- Pas de variables globales hardcodées
- Testabilité totale (mock chaque dep)
- Découplage entre tuiles

### Commentaires

```python
# Bonne pratique : explique le POURQUOI, pas le QUOI
# ⚠ Protection anti-cascade : voir bug UI reload 2026-05-23
if _threads_started:
    return

# À éviter : commentaires qui répètent le code
x = x + 1  # ❌ on incrémente x
```

## JavaScript

### Style général

- **Linter** : eslint (config `eslint.config.js`)
- **Version** : ES2022 (async/await, optional chaining)
- **Indentation** : 2 espaces
- **Quotes** : simples `'string'` (sauf si la string contient une apostrophe)
- **Semi-colons** : oui systématiquement

### Nommage

| Élément | Convention | Exemple |
|---|---|---|
| Fonction publique | camelCase | `setVoiceMode()` |
| Fonction privée | underscore + camelCase | `_setMode()` |
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
type(scope): description courte (≤ 70 chars)

Description détaillée multi-ligne expliquant le pourquoi du changement,
les alternatives évaluées, l'impact mesuré.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
```

### Types (préfixés)

| Type | Usage |
|---|---|
| `feat` | Nouvelle fonctionnalité |
| `fix` | Correction de bug |
| `refactor` | Réorganisation du code, pas de changement fonctionnel |
| `test` | Ajout ou modification de tests |
| `docs` | Documentation seule |
| `chore` | Maintenance (linter, hooks, build) |
| `perf` | Optimisation performance |
| `style` | Mise en forme code (whitespace, formatting) |

### Scopes typiques

`jarvis` (par défaut, modifications JARVIS), `soc` (blueprints/soc.py),
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
- **NEVER** créer commits vides
- **NEVER** commit fichiers `.env`, `*credentials*`, `*.key`, `soc_config.json`, `jarvis_pve.json`

### Pre-commit hooks (`.pre-commit-config.yaml`)

```
- ruff check (Python)
- eslint (JS)
- (commit échoue si erreur)
```

### Pre-push hook

```
- pytest tests/python/ (1294 tests)
- (push échoue si fail)
```

## Tests

### Structure

```
tests/python/
├── conftest.py                    # Setup : os.environ JARVIS_SKIP_BOOT_THREADS=1 + sys.path
├── test_jarvis_app.py             # Tests app Flask
├── test_jarvis_routes.py          # Tests routes
├── test_jarvis_functions.py       # Tests fonctions pures
├── test_<tuile>_<sous-module>.py  # Tests par tuile
└── ...
```

### Convention nommage tests

```python
def test_<feature>_<scenario>():
    """<phrase explicite décrivant le test>."""
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
statut: "Validé"  # Brouillon | Revue | Validé | Obsolète
categorie: "Présentation"
mots_cles: ["mot1", "mot2", "..."]
---
```

### Conventions Markdown

- **Titre H1** : un seul, en début (après frontmatter)
- **Liens internes** : chemins relatifs (`[doc](../06-BILAN/06-01.md)`)
- **Liens externes** : URL complète (`[Anthropic](https://anthropic.com/)`)
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
