"""Threads de démarrage JARVIS — préchauffage, surveillance, sync.

Extrait de jarvis.py étape 29 (2026-05-23). Regroupe les 9 threads daemon
lancés au boot du serveur Flask :

1. `kokoro_preload`        : précharge Kokoro ff_siwis + DSP (inconditionnel)
2. `tts_connectivity_loop` : surveille Internet (10 s) → switch edge/kokoro/piper/sapi
3. `gpu_temp_monitor_loop` : surveille température GPU (30 s) → alerte vocale ≥82 °C
4. `rag_embed_prewarm`     : précharge mxbai-embed-large en VRAM (T+5 s)
5. `boot_vram_cleanup`     : décharge modèles résiduels Ollama (T+25 s)
6. `soc_model_prewarm`     : précharge phi4:14b SOC (T+30 s, ctx=8192)
7. `kokoro_prewarm`        : précharge Kokoro CUDA (T+60 s, évite cold start 42 s)
8. `rag_live_prewarm_start`: thread pour le pré-chauffage du cache logs SOC
9. `rag_auto_refresh_loop` : ré-indexe MEMORY.md (4 fichiers) toutes les 6 h
10. `vram_sync_loop`       : sync `_vram_model` avec /api/ps Ollama (60 s)

Dépendances injectées via `init(...)` (DI massive — ~20 deps couvrant tous les
threads en une seule passe). `start_all()` démarre les 10 threads en daemon.

`_vram_model` côté jarvis.py est muté via les callables `get_vram_model` /
`set_vram_model` (sous protection `_VRAM_LOCK`), pour éviter le couplage par
global mutable.

Garde-fou : variable d'env `JARVIS_SKIP_BOOT_THREADS=1` → `start_all()`
retourne immédiatement sans rien lancer. Utile pour les smoke tests
(`python -c "import jarvis"`) qui ne doivent ni synthétiser, ni toucher la
VRAM, ni interférer avec une instance JARVIS en service sur la même machine.
"""
import json
import os
import socket
import threading
import time
import urllib.request as _ur
from pathlib import Path

# ── DI placeholders ───────────────────────────────────────────────────────────
_log = None
_dsp_params: dict = {}
_tts_eng = None
_apply_dsp_to_mp3 = None
_pynvml = None
_nvml_handle = None
_speak = None
_ollama_circuit = None
_req = None
_ollama_url = ""
_rag_embed_model = ""
_soc_num_ctx = 8192
_workspace_root: Path | None = None
_rag_index_text = None
_rag_live_prewarm = None
_vram_lock = None
_get_model = None       # callable → str (MODEL jarvis, mutable)
_get_vram_model = None  # callable → str | None
_set_vram_model = None  # callable(str | None)
_soc_cooldown_ok = None

# Constantes (overridables via init)
_OLLAMA_DIAG_TIMEOUT_S = 3
_GPU_TEMP_WARN = 82
_GPU_MON_START_S = 20
_GPU_MON_POLL_S = 30
_RAG_REFRESH_H = 6

# ── Stop events (utilisés par les loops infinis) ──────────────────────────────
_tts_stop_evt = threading.Event()
_gpu_stop_evt = threading.Event()
_rag_refresh_stop_evt = threading.Event()

# État externalisé du switch TTS auto (None = inconnu → premier cycle force le switch)
_tts_internet_was_up: bool | None = None

# Garde anti-double-démarrage : blueprints/soc.py contient `from jarvis import X`
# dans des fonctions thread qui ré-importent jarvis.py comme module (Python ne le
# voit pas dans sys.modules car il tourne en __main__) et ré-exécutent tout le
# top-level → start_all() rappelé → 10 threads boot relancés une 2ème fois →
# kokoro_preload synthétise à nouveau "JARVIS opérationnel.", boot_vram_cleanup
# décharge des modèles, prewarm phi4 force la VRAM → interférence avec la session
# utilisateur (bug reproduit par Marc 2026-05-23 14:30 lecture audio + slider EQ).
_threads_started = False


def init(
    *,
    log,
    dsp_params: dict,
    tts_eng,
    apply_dsp_to_mp3,
    pynvml,
    nvml_handle,
    speak,
    ollama_circuit,
    req,
    ollama_url: str,
    rag_embed_model: str,
    soc_num_ctx: int,
    workspace_root: Path,
    rag_index_text,
    rag_live_prewarm,
    vram_lock,
    get_model,
    get_vram_model,
    set_vram_model,
    soc_cooldown_ok,
    ollama_diag_timeout_s: int = 3,
    gpu_temp_warn: int = 82,
    gpu_mon_start_s: int = 20,
    gpu_mon_poll_s: int = 30,
    rag_refresh_h: int = 6,
) -> None:
    """Injecte les ~20 deps consommées par les threads boot."""
    global _log, _dsp_params, _tts_eng, _apply_dsp_to_mp3
    global _pynvml, _nvml_handle, _speak
    global _ollama_circuit, _req, _ollama_url, _rag_embed_model, _soc_num_ctx
    global _workspace_root, _rag_index_text, _rag_live_prewarm
    global _vram_lock, _get_model, _get_vram_model, _set_vram_model
    global _soc_cooldown_ok
    global _OLLAMA_DIAG_TIMEOUT_S, _GPU_TEMP_WARN, _GPU_MON_START_S, _GPU_MON_POLL_S, _RAG_REFRESH_H

    _log = log
    _dsp_params = dsp_params
    _tts_eng = tts_eng
    _apply_dsp_to_mp3 = apply_dsp_to_mp3
    _pynvml = pynvml
    _nvml_handle = nvml_handle
    _speak = speak
    _ollama_circuit = ollama_circuit
    _req = req
    _ollama_url = ollama_url
    _rag_embed_model = rag_embed_model
    _soc_num_ctx = soc_num_ctx
    _workspace_root = workspace_root
    _rag_index_text = rag_index_text
    _rag_live_prewarm = rag_live_prewarm
    _vram_lock = vram_lock
    _get_model = get_model
    _get_vram_model = get_vram_model
    _set_vram_model = set_vram_model
    _soc_cooldown_ok = soc_cooldown_ok
    _OLLAMA_DIAG_TIMEOUT_S = ollama_diag_timeout_s
    _GPU_TEMP_WARN = gpu_temp_warn
    _GPU_MON_START_S = gpu_mon_start_s
    _GPU_MON_POLL_S = gpu_mon_poll_s
    _RAG_REFRESH_H = rag_refresh_h


# ── Threads ───────────────────────────────────────────────────────────────────

def kokoro_preload() -> None:
    if _dsp_params.get("tts_engine") != "kokoro":
        return
    try:
        _warm_wav = _tts_eng.kokoro_synth("JARVIS opérationnel.", "ff_siwis")
        _apply_dsp_to_mp3(_warm_wav)
        _log.info("[TTS-Kokoro] Préchargement ff_siwis + DSP terminé.")
    except Exception as _e:
        _log.warning(f"[TTS-Kokoro] Préchargement échoué: {_e}")


def tts_connectivity_loop() -> None:
    """Vérifie toutes les 10 s si speech.platform.bing.com est joignable.
    Internet OK → edge-tts Antoine (si tts_default_engine == 'edge')
    Internet KO → Kokoro → Piper → SAPI5 (premier moteur local disponible)
    Premier cycle forcé au démarrage (_tts_internet_was_up = None).
    Arrêt propre : _tts_stop_evt.set()."""
    global _tts_internet_was_up
    while not _tts_stop_evt.is_set():
        try:
            s = socket.create_connection(("speech.platform.bing.com", 443), timeout=_OLLAMA_DIAG_TIMEOUT_S)
            s.close()
            up = True
        except OSError:
            up = False

        if up != _tts_internet_was_up:
            default_eng = _dsp_params.get("tts_default_engine", "edge")
            cur_eng = _dsp_params.get("tts_engine", "edge")
            if up:
                if default_eng == "edge" and cur_eng != "edge":
                    _dsp_params["tts_engine"] = "edge"
                    _log.info("[TTS-AUTO] Internet OK → edge-tts Antoine (défaut EDGE)")
                else:
                    _log.info(f"[TTS-AUTO] Internet OK — défaut={default_eng}, engine={cur_eng}, pas de switch")
            else:
                if _tts_eng.is_kokoro_available() is not False:
                    _dsp_params["tts_engine"] = "kokoro"
                    _log.info("[TTS-AUTO] Internet KO → Kokoro (fallback local)")
                elif _tts_eng.is_piper_available():
                    _dsp_params["tts_engine"] = "piper"
                    _log.info("[TTS-AUTO] Internet KO → Piper local")
                elif _tts_eng.is_sapi_available():
                    _dsp_params["tts_engine"] = "sapi"
                    _log.info("[TTS-AUTO] Internet KO → SAPI5")
                else:
                    _log.info("[TTS-AUTO] Internet KO → aucun moteur local disponible")
            _tts_internet_was_up = up

        _tts_stop_evt.wait(10)


def gpu_temp_monitor_loop() -> None:
    """Surveille la température GPU (30 s). Alerte vocale si temp ≥ seuil, cooldown 15 min."""
    time.sleep(_GPU_MON_START_S)
    while not _gpu_stop_evt.wait(_GPU_MON_POLL_S):
        try:
            if _nvml_handle is None:
                continue
            temp = _pynvml.nvmlDeviceGetTemperature(_nvml_handle, _pynvml.NVML_TEMPERATURE_GPU)
            if temp >= _GPU_TEMP_WARN and _soc_cooldown_ok("gpu_temp_warn", minutes=15):
                _speak(f"Alerte thermique. Température GPU à {temp} degrés. Seuil d'alerte à {_GPU_TEMP_WARN} degrés. Vérifier la ventilation.")
        except Exception as _ge:
            _log.error(f"[GPU-TEMP-MON] {_ge}")


def rag_embed_prewarm() -> None:
    """Précharge mxbai-embed-large en VRAM. T+5 s — avant le LLM."""
    time.sleep(5)
    try:
        _ollama_circuit.call(
            _req.post,
            f"{_ollama_url}/api/embeddings",
            json={"model": _rag_embed_model, "prompt": "warm", "keep_alive": "10m"},
            timeout=30,
        )
        _log.info(f"[RAG] {_rag_embed_model} préchauffé (keep_alive=10m — dé-épinglé 2026-05-20, anti-éviction VRAM)")
    except Exception as e:
        _log.warning(f"[RAG] Préchargement embed échoué : {e}")


def boot_vram_cleanup() -> None:
    """Décharge les modèles Ollama résiduels du mode précédent (T+25 s)."""
    time.sleep(25)
    try:
        r = _req.get(f"{_ollama_url}/api/ps", timeout=8)
        if not r.ok:
            return
        loaded = [m.get("name", "") for m in (r.json().get("models") or [])]
        embed_base = _rag_embed_model.split(":")[0]
        model_now = _get_model()
        for m in loaded:
            if m == model_now or m.split(":")[0] == embed_base:
                continue
            payload = json.dumps({"model": m, "prompt": "", "stream": False, "keep_alive": 0}).encode()
            _r = _ur.Request(f"{_ollama_url}/api/generate", data=payload, method="POST")
            _r.add_header("Content-Type", "application/json")
            with _ur.urlopen(_r, timeout=10):
                pass
            _log.info(f"[BOOT-VRAM] {m} déchargé (résidu mode précédent)")
    except Exception as e:
        _log.warning(f"[BOOT-VRAM] cleanup: {e}")


def soc_model_prewarm() -> None:
    """Précharge le modèle SOC (phi4:14b) en VRAM (T+30 s, ctx=_soc_num_ctx)."""
    time.sleep(30)
    _t0 = time.monotonic()
    try:
        _ollama_circuit.call(
            _req.post,
            f"{_ollama_url}/api/generate",
            json={"model": _get_model(), "prompt": "", "stream": False, "keep_alive": "30m",
                  "options": {"num_ctx": _soc_num_ctx}},
            timeout=180,
        )
        _log.info(f"[TTS-PERF] [BOOT-VRAM] {_get_model()} préchargé (SOC default, ctx={_soc_num_ctx}) en {time.monotonic() - _t0:.2f}s")
    except Exception as e:
        _log.warning(f"[BOOT-VRAM] preload SOC: {e}")


def kokoro_prewarm() -> None:
    """Précharge Kokoro CUDA en VRAM (T+60 s, cold start 42 s évité)."""
    time.sleep(60)
    _t0 = time.monotonic()
    try:
        _tts_eng._get_kokoro("f")
        if _tts_eng.is_kokoro_available():
            _log.info(f"[TTS-PERF] [BOOT-TTS] Kokoro préchargé en VRAM en {time.monotonic() - _t0:.2f}s (cold start évité)")
        else:
            _log.info("[TTS-PERF] [BOOT-TTS] Kokoro indisponible — pas de préchauffage")
    except Exception as e:
        _log.warning(f"[BOOT-TTS] Kokoro prewarm échoué : {e}")


def rag_auto_refresh_loop() -> None:
    """Ré-indexe les 4 MEMORY.md (JARVIS/SOC/PROXMOX/NGINX) toutes les `_RAG_REFRESH_H` heures."""
    _paths = [
        str(_workspace_root / "JARVIS"  / "MEMORY.md"),
        str(_workspace_root / "SOC"     / "MEMORY.md"),
        str(_workspace_root / "PROXMOX" / "MEMORY.md"),
        str(_workspace_root / "NGINX"   / "MEMORY.md"),
    ]
    while not _rag_refresh_stop_evt.wait(_RAG_REFRESH_H * 3600):
        for path_str in _paths:
            p = Path(path_str)
            if p.exists():
                try:
                    _rag_index_text(p.read_text(encoding="utf-8", errors="ignore"), p.name)
                except Exception as e:
                    _log.warning(f"[RAG] Auto-refresh {p.name}: {e}")
        _log.info("[RAG] Auto-refresh 6h terminé.")


def vram_sync_loop() -> None:
    """Sync `_vram_model` avec /api/ps Ollama (60 s)."""
    while True:
        time.sleep(60)
        try:
            r = _req.get(f"{_ollama_url}/api/ps", timeout=5)
            if not r.ok:
                continue
            loaded = [m.get("name", "") for m in (r.json().get("models") or [])]
            embed_base = _rag_embed_model.split(":")[0]
            chat_loaded = [m for m in loaded if m.split(":")[0] != embed_base]
            with _vram_lock:
                cur = _get_vram_model()
                if not chat_loaded:
                    if cur is not None:
                        _log.info(f"[VRAM-SYNC] Ollama a déchargé {cur} (TTL/mémoire) — _vram_model reset")
                        _set_vram_model(None)
                elif cur not in chat_loaded:
                    actual = chat_loaded[0]
                    _log.info(f"[VRAM-SYNC] désynchro : interne={cur} → réel={actual}")
                    _set_vram_model(actual)
        except Exception as e:
            _log.debug(f"[VRAM-SYNC] {e}")


def start_all() -> None:
    """Démarre les 10 threads daemon dans l'ordre attendu par le boot.

    Garde-fous (2 niveaux) :
    1. `JARVIS_SKIP_BOOT_THREADS` env flag : aucun thread démarré (smoke imports).
    2. `_threads_started` idempotence : si start_all() est rappelé (cas
       blueprints/soc.py `from jarvis import X` dans une fonction thread qui
       ré-exécute le top-level de jarvis.py), on ne relance PAS les threads.
       Sans ça, kokoro_preload synthétise à nouveau, boot_vram_cleanup décharge
       des modèles Ollama actifs, prewarm phi4 force la VRAM → interférence avec
       la session utilisateur (bug Marc 2026-05-23 14:30)."""
    global _threads_started
    if os.environ.get("JARVIS_SKIP_BOOT_THREADS"):
        _log.info("[BOOTSTRAP] JARVIS_SKIP_BOOT_THREADS défini — threads boot SHUNTÉS (smoke import)")
        return
    if _threads_started:
        _log.info("[BOOTSTRAP] start_all() déjà appelé — threads boot SHUNTÉS (anti-double-import)")
        return
    _threads_started = True
    threading.Thread(target=kokoro_preload,        daemon=True, name="kokoro-preload").start()
    threading.Thread(target=tts_connectivity_loop, daemon=True).start()
    threading.Thread(target=gpu_temp_monitor_loop, daemon=True).start()
    threading.Thread(target=_rag_live_prewarm,     daemon=True, name="rag-live-prewarm").start()
    threading.Thread(target=rag_embed_prewarm,     daemon=True, name="rag-embed-prewarm").start()
    threading.Thread(target=boot_vram_cleanup,     daemon=True, name="boot-vram-cleanup").start()
    threading.Thread(target=soc_model_prewarm,     daemon=True, name="soc-model-prewarm").start()
    threading.Thread(target=kokoro_prewarm,        daemon=True, name="kokoro-prewarm").start()
    threading.Thread(target=rag_auto_refresh_loop, daemon=True, name="rag-auto-refresh").start()
    threading.Thread(target=vram_sync_loop,        daemon=True, name="vram-sync").start()
