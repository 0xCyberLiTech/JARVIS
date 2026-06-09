"""Gestion VRAM Ollama — swap synchrone modèle avec preload background.

Extrait de jarvis.py étape 35 (2026-05-23). Deux fonctions consommées par
`api_mode` (changement de mode utilisateur) et par `chat/orchestrator`
(routing automatique inter-modes pendant un chat) :

- `ensure_vram(next_model)` : décharge le modèle courant si différent du
  prochain. Sérialisé par `_VRAM_LOCK` pour éliminer la race condition
  multi-requête (ex: /api/chat user A + /api/sysdiag _diag_ollama en
  parallèle).
- `ollama_swap(unload, load)` : unload SYNCHRONE (keep_alive=0, attente
  confirmation) puis preload BACKGROUND (keep_alive=30m, thread daemon).
  Synchrone pour garantir VRAM libre avant le chargement du modèle
  suivant — évite le split VRAM/RAM.

DI via `init(log, get_model, get_vram_model, set_vram_model, vram_lock,
ollama_url)` — les deps mutables (`_vram_model` global) passent par
getter/setter callables pour ne pas dupliquer l'état.
"""
import json
import threading
import urllib.request

from .config import OLLAMA_URL as _OLLAMA_URL_DEFAULT

# ── DI placeholders ───────────────────────────────────────────────────────────
_log = None
_get_model = None
_get_vram_model = None
_set_vram_model = None
_vram_lock = None
_ollama_url = _OLLAMA_URL_DEFAULT  # placeholder DI — remplacé par init()


def init(*, log, get_model, get_vram_model, set_vram_model, vram_lock, ollama_url) -> None:
    """Injecte logger + getters/setter _vram_model + _VRAM_LOCK + URL Ollama."""
    global _log, _get_model, _get_vram_model, _set_vram_model, _vram_lock, _ollama_url
    _log = log
    _get_model = get_model
    _get_vram_model = get_vram_model
    _set_vram_model = set_vram_model
    _vram_lock = vram_lock
    _ollama_url = ollama_url


def ensure_vram(next_model: str) -> None:
    """Décharge le modèle actuellement en VRAM si différent du prochain.
    Évite les collisions VRAM lors du routing automatique inter-modes.

    Protégé par `_vram_lock` : sérialise check + swap + mutation pour éliminer
    la race condition multi-requête."""
    effective = next_model or _get_model()
    with _vram_lock:
        cur = _get_vram_model()
        if cur and cur != effective:
            _log.info(f"[VRAM] Routing switch : {cur} → {effective} — unload forcé")
            ollama_swap(cur, effective)
        _set_vram_model(effective)


def ollama_swap(unload_model: str, load_model: str) -> None:
    """Décharge `unload_model` (keep_alive=0) SYNCHRONE, puis preload `load_model` en background.

    Synchrone pour garantir VRAM libre avant le chargement du modèle suivant
    (évite le split VRAM/RAM). Le preload tourne dans un thread daemon —
    300 ms à 3 min selon la taille du modèle, on n'attend pas."""
    # 1. Unload synchrone — on attend la confirmation avant de continuer
    try:
        payload = json.dumps({
            "model": unload_model, "prompt": "", "stream": False, "keep_alive": 0
        }).encode()
        req_u = urllib.request.Request(
            f"{_ollama_url}/api/generate",
            data=payload, method="POST"
        )
        req_u.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req_u, timeout=8):
            pass
        _log.info(f"[VRAM] {unload_model} déchargé (sync)")
    except Exception as e:
        _log.warning(f"[VRAM] unload {unload_model}: {e}")

    # 2. Preload du nouveau modèle en background — VRAM est maintenant libre
    def _preload():
        try:
            payload = json.dumps({
                "model": load_model, "prompt": "", "stream": False, "keep_alive": "30m"
            }).encode()
            req_p = urllib.request.Request(
                f"{_ollama_url}/api/generate",
                data=payload, method="POST"
            )
            req_p.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req_p, timeout=180):
                pass
            _log.info(f"[VRAM] {load_model} préchargé (plein VRAM)")
        except Exception as e:
            _log.warning(f"[VRAM] preload {load_model}: {e}")

    threading.Thread(target=_preload, daemon=True).start()
