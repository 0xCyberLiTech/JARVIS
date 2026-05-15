"""Profiling perf JARVIS — TTS / RAG / Ollama swap / chat latency.

Phase 3 chantier dette technique 2026-05-15.

Mesure sans modifier le code de prod : appels HTTP/API directs avec timestamps
monotonic. Affiche un rapport markdown des bottlenecks.

Usage : python tools/profile_perf.py
Pré-requis : JARVIS lancé sur localhost:5000.
"""
import json
import time
import urllib.request
from urllib.error import URLError

JARVIS = "http://127.0.0.1:5000"  # IPv4 explicite : évite timeout IPv6 ::1 ~2s sur Windows
OLLAMA = "http://127.0.0.1:11434"


def _http_get(url, timeout=30):
    """GET retourne (status, body_bytes, latency_s)."""
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
        return r.status, body, time.monotonic() - t0
    except URLError as e:
        return 0, str(e).encode(), time.monotonic() - t0


def _http_post_json(url, payload, timeout=120):
    """POST JSON retourne (status, body_bytes, latency_s)."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
        return r.status, body, time.monotonic() - t0
    except URLError as e:
        return 0, str(e).encode(), time.monotonic() - t0


def _http_post_first_byte(url, payload, timeout=120):
    """POST JSON retourne le temps jusqu'au PREMIER BYTE (TTFB) + total."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            first_chunk = r.read(1)  # premier byte
            ttfb = time.monotonic() - t0
            rest = r.read()
            total_t = time.monotonic() - t0
            return r.status, len(first_chunk) + len(rest), ttfb, total_t
    except URLError:
        return 0, 0, time.monotonic() - t0, time.monotonic() - t0


def section(title):
    print(f"\n## {title}\n")


def report(label, t_s, extra=""):
    print(f"- **{label}** : {t_s * 1000:.0f} ms{(' · ' + extra) if extra else ''}")


# ── 1. Health + état initial ─────────────────────────────────────────────


section("1. État initial")
status, body, t = _http_get(f"{JARVIS}/api/health")
report("Health JARVIS", t, f"HTTP {status}")
if status != 200:
    print("\n⚠ JARVIS non joignable. Abort.")
    raise SystemExit(1)

status, body, t = _http_get(f"{OLLAMA}/api/ps", timeout=5)
report("Ollama /api/ps (modèles chargés en VRAM)", t, f"HTTP {status}")
try:
    models_loaded = json.loads(body).get("models", [])
    for m in models_loaded:
        print(f"  - {m.get('name')} (size_vram={m.get('size_vram',0)/1e9:.1f} GB)")
except Exception as e:
    print(f"  parse fail: {e}")


# ── 2. Ollama swap times — le plus instructif ────────────────────────────

section("2. Ollama swap times (model load -> first token)")

PROMPT_SHORT = "Bonjour. Réponds en 5 mots."
MODELS = ["phi4:14b", "gemma4:latest", "qwen2.5-coder:14b", "qwen3:8b"]


def _ollama_first_token(model, prompt=PROMPT_SHORT, timeout=120):
    """Mesure : POST /api/chat -> temps du PREMIER TOKEN reçu + total tokens."""
    data = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "options": {"num_predict": 20, "temperature": 0.1},
    }).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=data,
                                 headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    first_t = None
    full = ""
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for line in r:
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    tok = chunk.get("message", {}).get("content", "")
                    if tok and first_t is None:
                        first_t = time.monotonic() - t0
                    full += tok
                    if chunk.get("done"):
                        break
                except Exception:
                    pass
        return first_t, time.monotonic() - t0, full.strip()
    except Exception as e:
        return None, time.monotonic() - t0, f"ERR: {e}"


for model in MODELS:
    print(f"\n### {model}")
    # 1er appel : COLD swap (modèle pas chargé en VRAM)
    first, total, txt = _ollama_first_token(model)
    if first is None:
        print(f"  COLD : ÉCHEC ({total*1000:.0f}ms) — {txt[:80]}")
        continue
    print(f"  COLD : first_token={first * 1000:.0f}ms · total={total * 1000:.0f}ms · réponse: {txt[:60]!r}")

    # 2e appel : WARM (modèle déjà chargé)
    first, total, txt = _ollama_first_token(model)
    if first is not None:
        print(f"  WARM : first_token={first * 1000:.0f}ms · total={total * 1000:.0f}ms")


# ── 3. RAG embedding + recherche ────────────────────────────────────────

section("3. RAG — embedding + recherche")


def _ollama_embed(text):
    """Mesure latence embedding mxbai-embed-large."""
    data = json.dumps({"model": "mxbai-embed-large:latest", "prompt": text}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/embeddings", data=data,
                                 headers={"Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read())
        return time.monotonic() - t0, len(body.get("embedding", []))
    except Exception as e:
        return time.monotonic() - t0, f"ERR: {e}"


queries = [
    ("court", "JARVIS"),
    ("moyen", "Comment JARVIS gère le routing entre modes SOC et CODE ?"),
    ("long", "Explique en détail l'architecture du chantier de dette technique JARVIS, le refactor JS du fichier monolithe jarvis_main.js et comment les modules ont été extraits avec la méthode byte-identique vérifiée par eslint et node check."),
]

for label, q in queries:
    t, dim_or_err = _ollama_embed(q)
    report(f"Embedding {label} ({len(q)} chars)", t, f"dim={dim_or_err}")


# ── 4. TTS edge-tts (mesure TTFB jusqu'au premier byte audio) ──────────

section("4. TTS — premier byte audio (TTFB)")

tts_payload = {
    "text": "Bonjour Marc, JARVIS est en ligne.",
    "voice": "fr-CA-AntoineNeural",
}
status, size, ttfb, total = _http_post_first_byte(f"{JARVIS}/api/tts", tts_payload, timeout=20)
report("TTS edge-tts (TTFB)", ttfb, f"total={total * 1000:.0f}ms · size={size} bytes · HTTP {status}")


# ── 5. /api/stats latence ────────────────────────────────────────────────

section("5. Endpoints UI — polling stats")

for endpoint in ["/api/stats", "/api/sysdiag", "/api/mode", "/api/health"]:
    times = []
    for _ in range(3):
        status, _, t = _http_get(f"{JARVIS}{endpoint}", timeout=10)
        times.append(t)
    avg = sum(times) / len(times)
    mn, mx = min(times), max(times)
    report(endpoint, avg, f"min={mn * 1000:.0f}ms max={mx * 1000:.0f}ms HTTP {status}")


print("\n## Résumé")
print("Voir analyse + recommandations dans le commit suivant.")
