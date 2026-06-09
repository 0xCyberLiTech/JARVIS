"""Bypass commandes système Hermès — RAG refresh/clear + mémoire clear.

Détecte les phrases de contrôle JARVIS formulées en langage naturel et
exécute l'action directement sans passer par le LLM.

Commandes reconnues :
- rag_refresh : "recharge le RAG", "rafraîchis le RAG", "réindexe le RAG"
- rag_clear   : "vide le RAG", "purge le RAG", "efface le RAG"
- memory_clear: "vide la mémoire", "purge la mémoire", "efface l'historique"

Module pur — zéro import vers jarvis.py.
Les callables d'action sont injectés par bypass/wrappers.py.
"""
import json
import re

# ── Regex de détection ────────────────────────────────────────────────────────

RAG_REFRESH_RE = re.compile(
    r'\b(?:recharge(?:r)?|rafra[iî]chi(?:s|r)?|r[eé]indexe(?:r)?|refresh|reload)'
    r'\s+(?:le\s+|la\s+)?rag\b',
    re.I | re.U,
)

RAG_CLEAR_RE = re.compile(
    r'\b(?:vide(?:r)?|purge(?:r)?|efface(?:r)?|supprime(?:r)?|clear)\s+(?:le\s+)?rag\b',
    re.I | re.U,
)

MEMORY_CLEAR_RE = re.compile(
    r'\b(?:'
    r'(?:vide(?:r)?|purge(?:r)?|efface(?:r)?|supprime(?:r)?|r[eé]initialis[e]?r?)\s+(?:la\s+)?m[eé]moire'
    r'|(?:vide(?:r)?|purge(?:r)?|efface(?:r)?)\s+(?:l[\'e ]?\s*)?historique'
    r')\b',
    re.I | re.U,
)


def detect_system_ctrl_command(msg: str) -> str | None:
    """Retourne la clé de commande si détectée, sinon None."""
    if RAG_REFRESH_RE.search(msg):  return "rag_refresh"
    if MEMORY_CLEAR_RE.search(msg): return "memory_clear"
    if RAG_CLEAR_RE.search(msg):    return "rag_clear"
    return None


# ── Générateurs SSE ───────────────────────────────────────────────────────────

def _sse(text: str):
    yield f"data: {json.dumps({'type':'token','token':text,'done':True})}\n\n"
    yield f"data: {json.dumps({'type':'speak','text':text})}\n\n"


def rag_refresh_sse(refresh_fn):
    """Re-indexe les MEMORY.md via refresh_fn() → {"chunks_added": n, ...}."""
    try:
        result = refresh_fn() or {}
        n = result.get("chunks_added", 0)
        if n > 0:
            rep = f"RAG rechargé. {n} nouveau{'x' if n > 1 else ''} chunk{'s' if n > 1 else ''} indexé{'s' if n > 1 else ''}."
        else:
            rep = "RAG rechargé. Base documentaire déjà à jour."
    except Exception as e:
        rep = f"Erreur rechargement RAG : {e}"
    yield from _sse(rep)


def memory_clear_sse(memory_clear_fn):
    """Efface l'historique de conversation via memory_clear_fn()."""
    try:
        memory_clear_fn()
        rep = "Mémoire effacée. L'historique de conversation a été supprimé."
    except Exception as e:
        rep = f"Erreur purge mémoire : {e}"
    yield from _sse(rep)


def rag_clear_sse(rag_clear_fn):
    """Purge l'index RAG complet via rag_clear_fn()."""
    try:
        rag_clear_fn()
        rep = "Index RAG purgé. La base documentaire est vide."
    except Exception as e:
        rep = f"Erreur purge RAG : {e}"
    yield from _sse(rep)
