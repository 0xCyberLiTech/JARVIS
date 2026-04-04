# Étape 2 — LLM local avec Ollama

## Objectif
Connecter JARVIS à Ollama pour que les réponses de l'assistant  
soient générées par un LLM tournant entièrement en local.

```
Utilisateur → JARVIS (Flask) → Ollama API (localhost:11434) → LLM → réponse
```

---

## Étape 2.1 — Démarrer Ollama

```bash
# Démarrer le serveur Ollama
ollama serve

# Ollama écoute sur http://localhost:11434
# Vérifier
curl http://localhost:11434/api/tags
```

> Sur Windows, Ollama démarre automatiquement au démarrage une fois installé.

---

## Étape 2.2 — Interroger un modèle via l'API

```python
import requests, json

OLLAMA_URL = "http://localhost:11434"

def chat_with_llm(prompt, model="phi4", system_prompt=None, stream=True):
    """
    Envoie un prompt à Ollama et retourne la réponse.
    stream=True : retourne les tokens au fur et à mesure (pour SSE).
    stream=False : attend la réponse complète.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model":   model,
        "messages": messages,
        "stream":  stream,
        "options": {
            "temperature":  0.7,
            "num_ctx":      4096,
            "num_predict":  512,
        }
    }

    resp = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        stream=stream,
        timeout=60
    )
    resp.raise_for_status()

    if not stream:
        return resp.json()["message"]["content"]

    # Streaming : yield chaque token
    full_response = ""
    for line in resp.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        token = chunk.get("message", {}).get("content", "")
        full_response += token
        yield token
        if chunk.get("done"):
            break

    return full_response
```

---

## Étape 2.3 — Système de prompts

```python
# System prompt SOC — adapté à votre infrastructure
SYSTEM_PROMPT_SOC = """Tu es JARVIS, assistant IA spécialisé en cybersécurité.
Tu surveilles un serveur Linux Debian avec nginx, CrowdSec, Suricata IDS et fail2ban.

Tes capacités :
- Analyser les alertes de sécurité en temps réel
- Suggérer des actions défensives (ban IP, restart service)
- Expliquer les attaques détectées (MITRE ATT&CK)
- Répondre en français, de façon concise et technique

Tes règles :
- Ne jamais révéler de données sensibles (tokens, mots de passe)
- Toujours expliquer le raisonnement avant une action
- Prioriser la sécurité sur la disponibilité
"""

# Exemple d'utilisation
for token in chat_with_llm(
    prompt="Analyse cette alerte CrowdSec : 150 bans en 1 heure depuis des IPs chinoises",
    model="phi4",
    system_prompt=SYSTEM_PROMPT_SOC,
    stream=True
):
    print(token, end="", flush=True)
```

---

## Étape 2.4 — Route Flask avec streaming SSE

```python
from flask import Flask, Response, request, stream_with_context
import json

app = Flask(__name__)

@app.route("/chat", methods=["POST"])
def chat():
    """Route Flask — streaming Server-Sent Events."""
    data    = request.get_json()
    prompt  = data.get("prompt", "")
    model   = data.get("model", "phi4")

    def generate():
        try:
            for token in chat_with_llm(prompt, model=model, stream=True):
                # Format SSE
                yield f"data: {json.dumps({'token': token})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
```

---

## Étape 2.5 — Gestion du modèle actif

```python
import json, os

MODEL_FILE = os.path.join(os.path.dirname(__file__), "jarvis_model.json")

def get_active_model():
    """Retourne le modèle Ollama actuellement actif."""
    try:
        with open(MODEL_FILE) as f:
            return json.load(f).get("model", "phi4")
    except Exception:
        return "phi4"

def set_active_model(model_name):
    """Change le modèle actif (sans redémarrage)."""
    # Vérifier que le modèle est disponible dans Ollama
    resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    available = [m["name"] for m in resp.json().get("models", [])]
    if model_name not in available:
        raise ValueError(f"Modèle '{model_name}' non disponible dans Ollama")
    with open(MODEL_FILE, "w") as f:
        json.dump({"model": model_name}, f)
    return True
```

---

## Paramètres LLM recommandés

```json
// jarvis_llm_params.json
{
    "temperature":  0.7,
    "num_ctx":      4096,
    "num_predict":  512,
    "top_k":        40,
    "top_p":        0.9,
    "repeat_penalty": 1.1
}
```

| Paramètre | Rôle | Valeur conseillée |
|-----------|------|------------------|
| `temperature` | Créativité (0=déterministe, 1=créatif) | 0.6–0.8 |
| `num_ctx` | Taille du contexte (tokens) | 4096–8192 |
| `num_predict` | Longueur max de la réponse | 256–1024 |
| `repeat_penalty` | Évite les répétitions | 1.1 |

---

**Étape suivante →** [03 — Pipeline audio TTS/STT](./03-PIPELINE-AUDIO.md)
