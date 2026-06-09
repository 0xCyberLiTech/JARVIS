"""Bypass apprentissage Hermès — mémorisation explicite de leçons.

Détecte les phrases d'apprentissage et persiste la leçon dans
jarvis_corrections.md, puis l'indexe immédiatement dans le RAG.

Phrases reconnues :
  "souviens-toi que X"  |  "retiens que X"
  "mémorise que X"      |  "apprends que X"
  "note que X"          |  "enregistre que X"

La leçon est indexée dans le RAG à la source "corrections" — elle ressort
automatiquement dans les prochaines réponses si la requête est proche.

Module pur — zéro import vers jarvis.py.
Les callables save_fn / index_fn sont injectés par bypass/wrappers.py.
"""
import json
import re

# ── Regex de détection ────────────────────────────────────────────────────────

LEARN_RE = re.compile(
    r'\b(?:souviens[- ]toi\s+que|retiens\s+que'
    r'|m[eé]morise(?:\s+que)?'
    r'|apprends\s+que|note\s+que|enregistre\s+que)'
    r'\s*:?\s*(.+)',
    re.I | re.U | re.DOTALL,
)


def extract_lesson(msg: str) -> str | None:
    """Extrait le contenu de la leçon depuis le message, ou None si non détecté."""
    m = LEARN_RE.search(msg)
    if not m:
        return None
    lesson = m.group(1).strip().rstrip('.')
    return lesson if lesson else None


# ── Générateur SSE ────────────────────────────────────────────────────────────

def learn_sse(lesson: str, save_fn, index_fn):
    """Persiste la leçon via save_fn(), l'indexe via index_fn(), stream la confirmation."""
    try:
        save_fn(lesson)
        index_fn(lesson)
        rep = f"Mémorisé. J'intègre ça dans ma base : « {lesson[:120]}{'…' if len(lesson) > 120 else ''} »"
    except Exception as e:
        rep = f"Erreur mémorisation : {e}"
    yield f"data: {json.dumps({'type':'token','token':rep,'done':True})}\n\n"
    yield f"data: {json.dumps({'type':'speak','text':rep})}\n\n"
