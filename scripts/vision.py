"""Vision module — analyse image multimodale via gemma4.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 split monolithe (module 5).

gemma4 fait le pipeline complet en 1 seul appel Ollama (texte + image). Pas de
modèle dédié vision séparé. Streaming SSE pour UX temps réel.

2 modes :
- `stream_direct()` : prompt simple, pas de system prompt, pas de RAG
- `stream_pipeline()` : system prompt enrichi (passé en param par l'appelant qui injecte le RAG)
"""
import json
import logging

import requests

_log = logging.getLogger("jarvis.vision")

# ── Constantes ────────────────────────────────────────────────
MODEL = "gemma4:latest"
DEFAULT_TEMPERATURE = 0.3


def stream_direct(ollama_url: str, image_b64: str, prompt: str, timeout: int):
    """Génère SSE pour analyse image en mode direct (sans system prompt).

    Yields : SSE events JSON dict {type:'token'|'speak', token/text:..., done:bool}.
    """
    pl = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": prompt or "Décris cette image en détail en français.",
            "images": [image_b64],
        }],
        "stream": True,
        "options": {"temperature": DEFAULT_TEMPERATURE},
    }
    full_text = ""
    try:
        with requests.post(f"{ollama_url}/api/chat", json=pl, stream=True, timeout=timeout) as r:
            try:
                for line in r.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    done = chunk.get("done", False)
                    if token:
                        full_text += token
                        yield f"data: {json.dumps({'type':'token','token':token,'done':done})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type':'token','token':f'Erreur gemma4 vision: {e}','done':True})}\n\n"
                return
        if full_text.strip():
            yield f"data: {json.dumps({'type':'speak','text':full_text[:500]})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type':'token','token':f'Erreur connexion Ollama (vision): {e}','done':True})}\n\n"


def stream_pipeline(ollama_url: str, image_b64: str, system: str, user_query: str, timeout: int):
    """Génère SSE pour analyse image en mode pipeline (system prompt + user prompt).

    L'appelant (route Flask) est responsable d'injecter le RAG dans `system` avant l'appel.

    Yields : SSE events JSON dict.
    """
    pl = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_query, "images": [image_b64]},
        ],
        "stream": True,
        "options": {"temperature": DEFAULT_TEMPERATURE},
    }
    full_text = ""
    try:
        with requests.post(f"{ollama_url}/api/chat", json=pl, stream=True, timeout=timeout) as r:
            try:
                for line in r.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    done = chunk.get("done", False)
                    if token:
                        full_text += token
                        yield f"data: {json.dumps({'type':'token','token':token,'done':done})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type':'token','token':f'Erreur gemma4 vision pipeline: {e}','done':True})}\n\n"
                return
        if full_text.strip():
            yield f"data: {json.dumps({'type':'speak','text':full_text[:600]})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type':'token','token':f'Erreur pipeline vision: {e}','done':True})}\n\n"


DEFAULT_PIPELINE_SYSTEM = (
    "Tu es JARVIS, assistant IA expert en analyse visuelle. "
    "Décris précisément le contenu de l'image (textes, chiffres, graphiques, éléments visuels), "
    "puis réponds à la question de l'utilisateur."
)
