"""Routes HTTP de la tuile **vision** — /api/vision multimodal."""
import json

from flask import Response, request

from . import bp, llava

_ollama_url       = ""
_vision_timeout_s = 60
_sse_headers      = None
_rag_inject_fn    = None


def init_routes(*, ollama_url, vision_timeout_s, sse_headers, rag_inject_fn) -> None:
    global _ollama_url, _vision_timeout_s, _sse_headers, _rag_inject_fn
    _ollama_url       = ollama_url
    _vision_timeout_s = vision_timeout_s
    _sse_headers      = sse_headers
    _rag_inject_fn    = rag_inject_fn


@bp.route("/api/vision", methods=["POST"])
def api_vision():
    """Pipeline vision gemma4 multimodal — analyse image en un seul passage.
    Body: {image_b64, prompt, pipeline=true}.
    pipeline=false : mode direct (prompt simple)."""
    data      = request.json or {}
    image_b64 = data.get("image_b64", "")
    prompt    = data.get("prompt", "").strip()
    pipeline  = data.get("pipeline", True)
    if not image_b64:
        return Response(json.dumps({"error": "image_b64 manquante"}), status=400, mimetype="application/json")
    if "," in image_b64:
        header, image_b64 = image_b64.split(",", 1)
        allowed_mime = ("image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp")
        if not any(m in header for m in allowed_mime):
            return Response(json.dumps({"error": "Format image non supporté (jpeg/png/gif/webp/bmp)"}), status=400, mimetype="application/json")
    if pipeline:
        user_q = prompt or "Analyse cette image et donne tes observations détaillées."
        system = _rag_inject_fn(llava.DEFAULT_PIPELINE_SYSTEM, user_q)
        gen = llava.stream_pipeline(_ollama_url, image_b64, system, user_q, _vision_timeout_s)
    else:
        gen = llava.stream_direct(_ollama_url, image_b64, prompt, _vision_timeout_s)
    return Response(gen, mimetype="text/event-stream", headers=_sse_headers)
