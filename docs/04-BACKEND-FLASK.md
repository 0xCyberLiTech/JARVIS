# Étape 4 — Backend Flask

## Objectif
Le backend Flask est le **serveur central** de JARVIS.  
Il expose les routes HTTP utilisées par l'interface web.

```
Interface web (jarvis.html)
    ↕ HTTP / SSE / WebSocket
Flask (jarvis.py) — 55 routes
    ↕
Ollama LLM | edge-tts | faster-whisper | DeepFilterNet | SSH SOC
```

---

## Étape 4.1 — Structure de l'application Flask

```python
#!/usr/bin/env python3
"""
jarvis.py — Serveur Flask JARVIS
Lancer : python jarvis.py
Accès  : http://localhost:5000
"""

from flask import Flask, render_template, request, Response, jsonify
from flask_cors import CORS
import json, os, threading, logging

app = Flask(__name__)
CORS(app)  # Permet les appels depuis le dashboard SOC

# ── Configuration ─────────────────────────────────────────────
HOST    = "127.0.0.1"   # Loopback uniquement — ne pas exposer sur le réseau
PORT    = 5000
DEBUG   = False

# ── Logging ───────────────────────────────────────────────────
logging.basicConfig(
    filename="logs/jarvis.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# ── Route principale ──────────────────────────────────────────
@app.route("/")
def index():
    return render_template("jarvis.html")


# ── Statut ────────────────────────────────────────────────────
@app.route("/status")
def status():
    """Utilisé par le dashboard SOC pour vérifier que JARVIS est actif."""
    return jsonify({
        "status":  "online",
        "model":   get_active_model(),
        "version": "1.0.0",
    })


if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG, threaded=True)
```

---

## Étape 4.2 — Routes Chat (avec streaming)

```python
@app.route("/chat", methods=["POST"])
def chat():
    """
    Route principale de conversation.
    Supporte le streaming SSE pour afficher les tokens en temps réel.
    """
    data   = request.get_json() or {}
    prompt = data.get("prompt", "").strip()
    model  = data.get("model", get_active_model())

    if not prompt:
        return jsonify({"error": "Prompt vide"}), 400

    def generate():
        try:
            full_response = ""
            for token in chat_with_llm(prompt, model=model, stream=True):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            # Synthèse vocale en arrière-plan
            if data.get("tts", True):
                threading.Thread(
                    target=speak,
                    args=(full_response,),
                    daemon=True
                ).start()

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            logging.error(f"Chat error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@app.route("/quick-prompt", methods=["POST"])
def quick_prompt():
    """
    Prompts rapides prédéfinis — utilisés par les boutons du dashboard SOC.
    Ex: "Analyse les dernières alertes CrowdSec"
    """
    data   = request.get_json() or {}
    prompt = data.get("prompt", "")
    # Ajouter le contexte SOC si disponible
    context = _get_soc_context()
    full_prompt = f"{context}\n\n{prompt}" if context else prompt
    # Déléguer au chat normal
    return chat_with_prompt(full_prompt)
```

---

## Étape 4.3 — Routes TTS

```python
@app.route("/tts", methods=["POST"])
def tts_route():
    """Synthétise un texte en voix."""
    data  = request.get_json() or {}
    text  = data.get("text", "").strip()
    voice = data.get("voice", TTS_VOICE)

    if not text:
        return jsonify({"error": "Texte vide"}), 400

    try:
        speak(text)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/tts/stop", methods=["POST"])
def tts_stop():
    """Interrompt la synthèse vocale en cours."""
    global _tts_queue
    while not _tts_queue.empty():
        try: _tts_queue.get_nowait()
        except: break
    return jsonify({"status": "stopped"})


@app.route("/tts/voices", methods=["GET"])
def tts_voices():
    """Liste les voix disponibles."""
    import asyncio
    voices = asyncio.run(list_french_voices())
    return jsonify(voices)
```

---

## Étape 4.4 — Routes STT

```python
_stt_active = False
_stt_thread = None

@app.route("/stt/start", methods=["POST"])
def stt_start():
    """Démarre l'écoute micro."""
    global _stt_active, _stt_thread
    if _stt_active:
        return jsonify({"status": "already_listening"})

    _stt_active = True
    _stt_thread = threading.Thread(target=_stt_loop, daemon=True)
    _stt_thread.start()
    return jsonify({"status": "listening"})


@app.route("/stt/stop", methods=["POST"])
def stt_stop():
    """Arrête l'écoute micro."""
    global _stt_active
    _stt_active = False
    return jsonify({"status": "stopped"})


def _stt_loop():
    """Boucle d'écoute STT continue."""
    global _stt_active
    while _stt_active:
        try:
            audio = record_until_silence()
            text  = transcribe_audio(audio)
            if text:
                logging.info(f"STT: {text}")
                # Envoyer via SSE aux clients connectés
                _broadcast_event("stt_result", {"text": text})
        except Exception as e:
            logging.error(f"STT error: {e}")
```

---

## Étape 4.5 — Routes modèles

```python
@app.route("/models", methods=["GET"])
def models_list():
    """Liste les modèles Ollama disponibles."""
    import requests as req
    try:
        resp = req.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = resp.json().get("models", [])
        return jsonify({
            "models":  [m["name"] for m in models],
            "active":  get_active_model(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 503


@app.route("/models/select", methods=["POST"])
def model_select():
    """Change le modèle actif."""
    data  = request.get_json() or {}
    model = data.get("model", "")
    try:
        set_active_model(model)
        return jsonify({"status": "ok", "model": model})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
```

---

## Étape 4.6 — Démarrage

```bash
# Démarrer JARVIS
cd scripts
python jarvis.py

# Accès
# http://localhost:5000

# Vérification API
curl http://localhost:5000/status
```

---

**Étape suivante →** [05 — Intégration SOC](./05-INTEGRATION-SOC.md)

---

<div align="center">

<table>
<tr>
<td align="center"><b>🖥️ Infrastructure &amp; Sécurité</b></td>
<td align="center"><b>💻 Développement &amp; Web</b></td>
<td align="center"><b>🤖 Intelligence Artificielle</b></td>
</tr>
<tr>
<td align="center">
  <a href="https://www.kernel.org/"><img src="https://skillicons.dev/icons?i=linux" width="48" title="Linux" /></a>
  <a href="https://www.debian.org"><img src="https://skillicons.dev/icons?i=debian" width="48" title="Debian" /></a>
  <a href="https://www.gnu.org/software/bash/"><img src="https://skillicons.dev/icons?i=bash" width="48" title="Bash" /></a>
  <br/>
  <a href="https://nginx.org"><img src="https://skillicons.dev/icons?i=nginx" width="48" title="Nginx" /></a>
  <a href="https://git-scm.com"><img src="https://skillicons.dev/icons?i=git" width="48" title="Git" /></a>
</td>
<td align="center">
  <a href="https://www.python.org"><img src="https://skillicons.dev/icons?i=python" width="48" title="Python" /></a>
  <a href="https://flask.palletsprojects.com"><img src="https://skillicons.dev/icons?i=flask" width="48" title="Flask" /></a>
  <a href="https://developer.mozilla.org/docs/Web/HTML"><img src="https://skillicons.dev/icons?i=html" width="48" title="HTML5" /></a>
  <br/>
  <a href="https://developer.mozilla.org/docs/Web/CSS"><img src="https://skillicons.dev/icons?i=css" width="48" title="CSS3" /></a>
  <a href="https://developer.mozilla.org/docs/Web/JavaScript"><img src="https://skillicons.dev/icons?i=js" width="48" title="JavaScript" /></a>
  <a href="https://code.visualstudio.com"><img src="https://skillicons.dev/icons?i=vscode" width="48" title="VS Code" /></a>
</td>
<td align="center">
  <a href="https://ollama.com"><img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" /></a>
  <br/><br/>
  <a href="https://anthropic.com"><img src="https://img.shields.io/badge/Anthropic-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic" /></a>
</td>
</tr>
</table>

<br/>

<sub>🔒 Projets proposés par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · Développés en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🔒</sub>

</div>
