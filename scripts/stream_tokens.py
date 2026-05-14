"""Stream tokens TTS — wraps un stream LLM en yield tokens + découpage phrases pour TTS.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 24 (Chat/LLM core).

Reçoit un stream Ollama (tokens + done flag) et génère 2 types d'events SSE :
- `{type:'token', token, done}` à chaque token (UI affiche le streaming)
- `{type:'speak', text}` quand une phrase complète est détectée (envoie au TTS)

Découpe sur séparateurs `! ? \\n` immédiatement, et sur `.` SAUF entre chiffres
(préserve IPs `192.168.1.50` et versions `v3.44`).

Dependency injection : `stream_llm_fn` (Ollama streaming) + `clean_text_fn` (TTS cleaner)
+ `phrase_min` (longueur minimum pour envoyer au TTS).
"""
import json
import re

DEFAULT_PHRASE_MIN = 4  # longueur min phrase pour envoi TTS

# Split "." sauf entre chiffres (préserve IPs/versions)
_DOT_SPLIT_RE = re.compile(r'(?<!\d)\.(?!\d)')


def stream_tokens_tts(
    messages: list,
    active_model,
    opts,
    *,
    stream_llm_fn,
    clean_text_fn,
    phrase_min: int = DEFAULT_PHRASE_MIN,
):
    """Stream les tokens LLM et découpe en phrases pour TTS, yield SSE token+speak.

    `stream_llm_fn(messages, model_override, options_override) -> iter[(token, done)]`
    `clean_text_fn(text) -> text` : nettoie markdown avant TTS
    """
    buf = ""
    for token, done in stream_llm_fn(messages, model_override=active_model, options_override=opts):
        buf += token
        yield f"data: {json.dumps({'type': 'token', 'token': token, 'done': done})}\n\n"
        # Split immédiat sur séparateurs forts
        for sep in ("!", "?", "\n"):
            if sep in buf:
                parts = buf.split(sep)
                for phrase in parts[:-1]:
                    phrase = clean_text_fn(phrase.strip())
                    if len(phrase) > phrase_min:
                        yield f"data: {json.dumps({'type': 'speak', 'text': phrase + sep})}\n\n"
                buf = parts[-1]
        # Split "." hors chiffres — préserve IPs (192.168.1.50) et versions (v3.44)
        if '.' in buf:
            parts = _DOT_SPLIT_RE.split(buf)
            for phrase in parts[:-1]:
                phrase = clean_text_fn(phrase.strip())
                if len(phrase) > phrase_min:
                    yield f"data: {json.dumps({'type': 'speak', 'text': phrase + '.'})}\n\n"
            buf = parts[-1]
    # Flush final : reste du buffer si non vide
    buf = clean_text_fn(buf.strip())
    if len(buf) > phrase_min:
        yield f"data: {json.dumps({'type': 'speak', 'text': buf})}\n\n"
