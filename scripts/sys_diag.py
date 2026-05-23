"""Diagnostics système — GPU/CPU/RAM/disque/Ollama + compteur mémoire.

Extrait de jarvis.py le 2026-05-23 (refactor incrémental jarvis.py étape 1).
Cluster consommé uniquement par la route `/api/sysdiag` (et le polling de
santé). Side-effect free, sauf `_diag_ollama` qui peut déclencher une alerte
vocale via `_speak` injecté quand Ollama passe d'OK à DOWN.

Dépendances injectées par `init()` : speak, ollama_url, memory_file.
État interne `_ollama_prev_ok` : anti-spam de l'alerte vocale (un seul TTS
sur la transition OK→DOWN, pas à chaque sondage).
"""
import json
import time

import psutil
import pynvml
import requests as req

_GB_BYTES = 1 << 30
_OLLAMA_DIAG_TIMEOUT_S = 3

# Dépendances injectées par init() — depuis jarvis.py
_speak       = None
_ollama_url  = None
_memory_file = None

# État interne — anti-spam de l'alerte vocale "Ollama hors ligne"
_ollama_prev_ok: bool | None = None


def init(speak, ollama_url, memory_file) -> None:
    """Injecte les dépendances (TTS speak + URL Ollama + chemin mémoire)."""
    global _speak, _ollama_url, _memory_file
    _speak       = speak
    _ollama_url  = ollama_url
    _memory_file = memory_file


def _diag_gpu(h):
    try:
        if h is None:
            raise RuntimeError("NVML non disponible")
        name_raw = pynvml.nvmlDeviceGetName(h)
        mem = pynvml.nvmlDeviceGetMemoryInfo(h)
        try:   gpu_temp  = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
        except Exception: gpu_temp = None
        try:   gpu_power = round(pynvml.nvmlDeviceGetPowerUsage(h) / 1000, 1)
        except Exception: gpu_power = None
        try:   gpu_clock = pynvml.nvmlDeviceGetClockInfo(h, pynvml.NVML_CLOCK_GRAPHICS)
        except Exception: gpu_clock = None
        return {
            "gpu_name":   name_raw.decode() if isinstance(name_raw, bytes) else name_raw,
            "gpu_pct":    pynvml.nvmlDeviceGetUtilizationRates(h).gpu,
            "vram_used":  round(mem.used  / _GB_BYTES, 1),
            "vram_total": round(mem.total / _GB_BYTES, 1),
            "gpu_temp": gpu_temp, "gpu_power": gpu_power, "gpu_clock": gpu_clock,
        }
    except Exception:
        return {"gpu_name": "N/A", "gpu_pct": 0, "vram_used": 0, "vram_total": 0,
                "gpu_temp": None, "gpu_power": None, "gpu_clock": None}


def _diag_ollama():
    global _ollama_prev_ok
    try:
        t0 = time.time()
        r_ol = req.get(f"{_ollama_url}/api/tags", timeout=_OLLAMA_DIAG_TIMEOUT_S)
        ok      = r_ol.status_code == 200
        latency = round((time.time() - t0) * 1000)
        models  = [m["name"] for m in r_ol.json().get("models", [])]
    except Exception:
        ok = False; latency = -1; models = []
    if _ollama_prev_ok is not False and ok is False:
        _speak("Attention, Ollama est hors ligne. Le moteur LLM est indisponible.")
    _ollama_prev_ok = ok
    return {"ollama_ok": ok, "ollama_latency": latency, "ollama_models": models}


def _diag_cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            return round(next(iter(temps.values()))[0].current, 1)
    except Exception:
        pass  # capteurs non disponibles sur ce système
    return None


def _diag_memory_count():
    try:
        hist = json.loads(_memory_file.read_text(encoding="utf-8")) if _memory_file.exists() else []
        return len(hist)
    except (OSError, ValueError):
        return 0


def _diag_cpu_ram_disk() -> dict:
    data = {}
    data["cpu_pct"]     = psutil.cpu_percent(interval=0.5)
    freq                = psutil.cpu_freq()
    data["cpu_freq"]    = round(freq.current / 1000, 2) if freq else 0
    data["cpu_cores"]   = psutil.cpu_count(logical=False)
    data["cpu_threads"] = psutil.cpu_count(logical=True)
    ram = psutil.virtual_memory()
    data["ram_total"] = round(ram.total / _GB_BYTES, 1)
    data["ram_used"]  = round(ram.used  / _GB_BYTES, 1)
    data["ram_pct"]   = ram.percent
    try:
        disk = psutil.disk_usage("C:\\")
        data["disk_total"] = round(disk.total / _GB_BYTES, 0)
        data["disk_used"]  = round(disk.used  / _GB_BYTES, 0)
        data["disk_pct"]   = disk.percent
    except Exception:
        data["disk_total"] = data["disk_used"] = data["disk_pct"] = 0
    return data
