"""Outils fichier exposés au LLM via tool-calling — lecture/écriture/listage.

Tuile `files` — pas de routes HTTP. Les fonctions sont consommées par le
dispatcher `execute_tool()` de l'ossature quand le LLM appelle un outil.

Garde-fou écriture : `_check_local_write_path` refuse les chemins système
(Windows/System32, ProgramData, etc.) et les chemins hors workspace.

Dépendances injectées par `init()` : `workspace_roots` (liste des racines où
l'écriture locale est autorisée).
"""
from pathlib import Path

# Dépendances injectées par init() — depuis l'ossature.
_workspace_roots: list = []

_BLOCKED_LOCAL_WRITE = [
    "windows", "system32", "syswow64", "program files",
    "drivers\\etc", "drivers/etc",
    "\\appdata\\roaming\\microsoft", "/appdata/roaming/microsoft",
    "\\programdata\\", "/programdata/",
]

_RGLOB_EXCLUDED = {".git", ".ssh", "node_modules", "__pycache__",
                   ".venv", "venv", ".env", "dist", "build"}
_RGLOB_MAX_DEPTH = 5


def init(*, workspace_roots: list) -> None:
    """Injecte la liste des racines workspace où l'écriture locale est OK."""
    global _workspace_roots
    _workspace_roots = workspace_roots


def _tool_lire_fichier(args):
    path = Path(args["chemin"])
    if not path.exists():
        return f"Erreur : fichier introuvable → {path}"
    return path.read_text(encoding="utf-8", errors="replace")[:8000]


def _check_local_write_path(path: Path) -> str | None:
    resolved = str(path.resolve()).lower().replace("\\", "/")
    for blocked in _BLOCKED_LOCAL_WRITE:
        if blocked.lower() in resolved:
            return f"[JARVIS] Accès refusé : chemin système protégé → {path}"
    try:
        r = path.resolve()
        if not any(r == root.resolve() or r.is_relative_to(root.resolve()) for root in _workspace_roots):
            return f"[JARVIS] Accès refusé : chemin hors workspace → {path}"
    except Exception:
        return f"[JARVIS] Accès refusé : chemin invalide → {path}"
    return None


def _tool_ecrire_fichier(args):
    path = Path(args["chemin"])
    err = _check_local_write_path(path)
    if err:
        return err
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["contenu"], encoding="utf-8")
    return f"Fichier écrit avec succès : {path}"


def _tool_modifier_fichier(args):
    path = Path(args["chemin"])
    err = _check_local_write_path(path)
    if err:
        return err
    if not path.exists():
        return f"Erreur : fichier introuvable → {path}"
    content = path.read_text(encoding="utf-8", errors="replace")
    if args["ancien"] not in content:
        return "Erreur : texte introuvable dans le fichier."
    path.write_text(content.replace(args["ancien"], args["nouveau"], 1), encoding="utf-8")
    return f"Fichier modifié avec succès : {path}"


def _tool_lister_dossier(args):
    path = Path(args["chemin"])
    if not path.exists():
        return f"Erreur : dossier introuvable → {path}"
    items = [("📁" if p.is_dir() else "📄") + " " + p.name for p in sorted(path.iterdir())]
    return "\n".join(items) if items else "(dossier vide)"


def _tool_arborescence_projet(args):
    root = Path(args["chemin"])
    depth = min(int(args.get("profondeur", 2)), 3)
    if not root.exists():
        return f"Erreur : dossier introuvable → {root}"
    lines = [f"📁 {root.name}/"]
    def _walk(p, lvl):
        if lvl > depth:
            return
        indent = "  " * lvl
        for item in sorted(p.iterdir()):
            if item.name.startswith('.') or item.name == '__pycache__':
                continue
            if item.is_dir():
                lines.append(f"{indent}📁 {item.name}/")
                _walk(item, lvl + 1)
            else:
                lines.append(f"{indent}📄 {item.name}")
    _walk(root, 1)
    return "\n".join(lines)


def _tool_lire_plusieurs_fichiers(args):
    chemins = args.get("chemins", [])[:5]
    parts = []
    for c in chemins:
        p = Path(c)
        if p.exists():
            content = p.read_text(encoding="utf-8", errors="replace")[:4000]
            parts.append(f"=== {p.name} ({p}) ===\n{content}")
        else:
            parts.append(f"=== {p.name} === [INTROUVABLE : {p}]")
    return "\n\n".join(parts) if parts else "Aucun fichier spécifié."


def _tool_rechercher_dans_fichiers(args):
    dossier = Path(args["dossier"])
    pattern = args["pattern"]
    ext     = args.get("extension", "")
    if not dossier.exists():
        return f"Erreur : dossier introuvable → {dossier}"
    results = []
    glob_pat = f"*{ext}" if ext else "*"
    for f in dossier.rglob(glob_pat):
        # Exclure dossiers sensibles et limiter la profondeur
        try:
            rel = f.relative_to(dossier)
        except ValueError:
            continue
        parts = rel.parts
        if any(p in _RGLOB_EXCLUDED for p in parts) or len(parts) > _RGLOB_MAX_DEPTH:
            continue
        if not f.is_file(): continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.lower() in line.lower():
                    results.append(f"{f}:{i}: {line.strip()}")
                    if len(results) >= 30: break
        except OSError:
            continue
        if len(results) >= 30: break
    return "\n".join(results) if results else "Aucun résultat trouvé."
