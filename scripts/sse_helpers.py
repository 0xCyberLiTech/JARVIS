"""SSE Helpers — utilitaires Server-Sent Events partagés.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 14.

Helpers ultra-courts utilisés par tous les bypass generators et routes Flask SSE.
- `SSE_HEADERS` : headers anti-buffering (Nginx X-Accel-Buffering)
- `sse_tok(t, done)` : format event SSE standard pour token streaming
- `sse_response(gen)` : enveloppe Flask Response pour un générateur SSE

Note : plusieurs modules Phase 3 (bypass_simple, bypass_filesystem, bypass_backup,
bypass_code, ssh_terminal) ont leur propre `_sse_tok()` inline pour rester autonomes.
Ce module-ci est utilisé directement par jarvis.py qui a Flask en contexte.
"""
import json

from flask import Response, stream_with_context

# ── Constantes ────────────────────────────────────────────────
SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


# ── Helpers ───────────────────────────────────────────────────

def sse_tok(t: str, done: bool = False) -> str:
    """Helper SSE token commun à tous les bypass generators.

    Format : `data: {"type":"token","token":<t>,"done":<bool>}\\n\\n`
    """
    return f"data: {json.dumps({'type':'token','token':t,'done':done})}\n\n"


def sse_response(gen):
    """Enveloppe un générateur SSE dans une Response Flask standard.

    Applique automatiquement `SSE_HEADERS` (anti-buffering Nginx) et
    `stream_with_context` (préservation contexte Flask dans le générateur).
    """
    return Response(stream_with_context(gen), mimetype="text/event-stream", headers=SSE_HEADERS)
