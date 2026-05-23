"""Tuile **files** — outils fichier exposés au LLM via tool-calling.

Architecture par tuiles (refactor jarvis.py étape 6, 2026-05-23) — 4ème tuile
après `system/`, `memory/`, `rag/`. Autoportante : zéro import vers
`jarvis.py`. **Pas de routes HTTP** — les fonctions sont consommées par le
dispatcher `execute_tool()` de l'ossature quand le LLM appelle un outil.

Public surface :
- `init()` : injection unique de `workspace_roots`.
- Fonctions exportées (alias depuis `tools`) : `_tool_lire_fichier`,
  `_tool_ecrire_fichier`, `_tool_modifier_fichier`, `_tool_lister_dossier`,
  `_tool_arborescence_projet`, `_tool_lire_plusieurs_fichiers`,
  `_tool_rechercher_dans_fichiers`, `_check_local_write_path`.
"""
from . import tools

# Ré-export pour usage `import files as f; f._tool_lire_fichier(...)`
init                          = tools.init
_check_local_write_path       = tools._check_local_write_path
_tool_lire_fichier            = tools._tool_lire_fichier
_tool_ecrire_fichier          = tools._tool_ecrire_fichier
_tool_modifier_fichier        = tools._tool_modifier_fichier
_tool_lister_dossier          = tools._tool_lister_dossier
_tool_arborescence_projet     = tools._tool_arborescence_projet
_tool_lire_plusieurs_fichiers = tools._tool_lire_plusieurs_fichiers
_tool_rechercher_dans_fichiers = tools._tool_rechercher_dans_fichiers
