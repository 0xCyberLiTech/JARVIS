"""Chat capture — wrapper SSE qui accumule les tokens pour mémoire historique.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 20 (Chat/LLM core).

Wrap un générateur SSE arbitraire (chat_generate, code_reasoning, file_correct, etc.)
pour stocker l'échange complet (user_msg + assistant_response) dans une `deque`
accessible via `/api/history/last` (utilisé par le MCP `jarvis_last_response`).

Dependency injection : la `exchanges_deque` est passée en argument (instance globale
restant dans jarvis.py car partagée par la route /api/history/last).
"""
import json
import time


def capture_gen(gen, user_msg: str, exchanges_deque):
    """Wraps un générateur SSE pour capturer l'échange complet (tokens uniquement).

    `gen` : générateur SSE (chunks au format `data: {json}\\n\\n`)
    `user_msg` : message utilisateur original (tronqué à 500 chars dans la deque)
    `exchanges_deque` : `collections.deque` partagée pour stocker l'historique

    Yields chaque chunk inchangé (passe-plat). Au finally, ajoute l'échange complet.
    """
    tokens = []
    try:
        for chunk in gen:
            yield chunk
            if isinstance(chunk, str) and chunk.startswith("data:"):
                try:
                    ev = json.loads(chunk[5:].strip())
                    if ev.get("type") == "token":
                        tokens.append(ev.get("token", ""))
                except Exception:
                    pass  # chunk SSE non-JSON (commentaire, keep-alive) — ignoré
    finally:
        full = "".join(tokens).strip()
        if full:
            exchanges_deque.append({
                "user": user_msg[:500],
                "assistant": full,
                "ts": time.time(),
            })
