"""Stats GPU/CPU/RAM/réseau/disque — agrégation pour /api/stats et /api/sysdiag.

Extrait de jarvis.py étape 31 (2026-05-23). Trois fonctions :

- `_gpu_cuda_procs(handle)`       : top 3 processus CUDA actifs (PID + nom + MiB)
- `_gpu_extended_stats(handle)`   : 17 métriques NVML étendues (clocks, p-state,
                                    throttle, PCIe, encoder/decoder, CUDA driver…)
- `get_stats()`                    : dict complet pour la tuile WINDOWS du dashboard

État local (mutable, sous lock) :
- `_net_prev`   : compteurs réseau précédents (pour delta Mbps)
- `_disk_prev`  : compteurs disque précédents (pour delta MB/s)
- `_STATS_LOCK` : sérialise la mutation des deux precs

DI via `init(pynvml, nvml_handle, get_model, gpu_temp_warn)` :
- `pynvml`         : module pynvml (déjà importé par jarvis.py)
- `nvml_handle`    : handle GPU obtenu via `nvmlDeviceGetHandleByIndex(0)`
- `get_model`      : callable → str (MODEL jarvis, mutable)
- `gpu_temp_warn`  : seuil °C (constante jarvis.py — partagée tuile system)
"""
import threading
import time

import psutil

# ── DI placeholders ───────────────────────────────────────────────────────────
_pynvml = None
_nvml_handle = None
_get_model = None
_gpu_temp_warn = 82

# ── État local ────────────────────────────────────────────────────────────────
_net_prev = {"t": time.time(), "s": psutil.net_io_counters()}
_disk_prev = {"t": time.time(), "d": psutil.disk_io_counters()}
_STATS_LOCK = threading.Lock()


def init(*, pynvml, nvml_handle, get_model, gpu_temp_warn: int) -> None:
    """Injecte pynvml + handle GPU + getter MODEL + seuil thermique."""
    global _pynvml, _nvml_handle, _get_model, _gpu_temp_warn
    _pynvml = pynvml
    _nvml_handle = nvml_handle
    _get_model = get_model
    _gpu_temp_warn = gpu_temp_warn


def _gpu_cuda_procs(handle):
    """Retourne (count, label) des processus CUDA en cours sur le GPU."""
    try:
        procs = _pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
        _names = []
        for p in procs:
            try:
                _names.append(f"{psutil.Process(p.pid).name()} ({round(p.usedGpuMemory/1024**2)}MB)")
            except Exception:
                _names.append(f"PID {p.pid}")
        return len(procs), " | ".join(_names[:3]) if _names else "—"
    except Exception:
        return 0, "—"


def _gpu_extended_stats(handle):
    try:    fan = _pynvml.nvmlDeviceGetFanSpeed(handle)
    except Exception: fan = None
    try:
        clk_gpu = _pynvml.nvmlDeviceGetClockInfo(handle, _pynvml.NVML_CLOCK_GRAPHICS)
        clk_mem = _pynvml.nvmlDeviceGetClockInfo(handle, _pynvml.NVML_CLOCK_MEM)
    except Exception: clk_gpu = clk_mem = 0
    try:
        enc_util = _pynvml.nvmlDeviceGetEncoderUtilization(handle)[0]
        dec_util = _pynvml.nvmlDeviceGetDecoderUtilization(handle)[0]
    except Exception: enc_util = dec_util = 0
    try:
        p_state = int(_pynvml.nvmlDeviceGetPerformanceState(handle))
    except Exception: p_state = None
    try:
        throttle = _pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(handle)
        throttle_active = bool(throttle & ~0x3)  # masque idle(1)+appclocks(2)
    except Exception: throttle_active = False
    try:
        pcie_gen   = _pynvml.nvmlDeviceGetCurrPcieLinkGeneration(handle)
        pcie_width = _pynvml.nvmlDeviceGetCurrPcieLinkWidth(handle)
    except Exception: pcie_gen = pcie_width = None
    try:
        cv = _pynvml.nvmlSystemGetCudaDriverVersion()
        cuda_ver = f"{cv // 1000}.{(cv % 1000) // 10}"
    except Exception: cuda_ver = "N/A"
    try:
        dv = _pynvml.nvmlSystemGetDriverVersion()
        driver_ver = dv.decode() if isinstance(dv, bytes) else dv
    except Exception: driver_ver = "N/A"
    try:
        max_clk_gpu = _pynvml.nvmlDeviceGetMaxClockInfo(handle, _pynvml.NVML_CLOCK_GRAPHICS)
        max_clk_mem = _pynvml.nvmlDeviceGetMaxClockInfo(handle, _pynvml.NVML_CLOCK_MEM)
    except Exception: max_clk_gpu = max_clk_mem = None
    try:
        temp_slow = _pynvml.nvmlDeviceGetTemperatureThreshold(handle, 1)  # SLOWDOWN
        temp_shut = _pynvml.nvmlDeviceGetTemperatureThreshold(handle, 0)  # SHUTDOWN
    except Exception: temp_slow = temp_shut = None
    try:
        traw = _pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(handle)
        _tr = [(0x1,"IDLE"),(0x2,"APPCLOCKS"),(0x4,"SYNC"),(0x8,"POWER"),
               (0x10,"THERMAL"),(0x20,"RELIABILITY"),(0x40,"HW_LIMIT"),(0x100,"DISPLAY")]
        reasons = [label for mask, label in _tr if traw & mask]
        throttle_reason = ", ".join(reasons) if reasons else "NONE"
    except Exception: throttle_reason = None
    cuda_proc_count, cuda_procs_str = _gpu_cuda_procs(handle)
    return {
        "fan": fan, "clk_gpu": clk_gpu, "clk_mem": clk_mem,
        "enc_util": enc_util, "dec_util": dec_util,
        "p_state": p_state, "throttle": throttle_active,
        "pcie_gen": pcie_gen, "pcie_width": pcie_width,
        "cuda_ver": cuda_ver, "driver_ver": driver_ver,
        "max_clk_gpu": max_clk_gpu, "max_clk_mem": max_clk_mem,
        "temp_slow": temp_slow, "temp_shut": temp_shut,
        "throttle_reason": throttle_reason,
        "cuda_proc_count": cuda_proc_count, "cuda_procs": cuda_procs_str,
    }


def get_stats():
    """Snapshot complet (GPU + CPU + RAM + uptime + net/disk delta + ext NVML)."""
    global _net_prev, _disk_prev
    if _nvml_handle is None:
        raise RuntimeError("NVML non disponible")
    handle = _nvml_handle
    name       = _pynvml.nvmlDeviceGetName(handle)
    temp       = _pynvml.nvmlDeviceGetTemperature(handle, _pynvml.NVML_TEMPERATURE_GPU)
    util       = _pynvml.nvmlDeviceGetUtilizationRates(handle)
    mem        = _pynvml.nvmlDeviceGetMemoryInfo(handle)
    power_draw = _pynvml.nvmlDeviceGetPowerUsage(handle) / 1000
    power_lim  = _pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000
    ext = _gpu_extended_stats(handle)

    ram = psutil.virtual_memory()
    with _STATS_LOCK:
        net_now  = psutil.net_io_counters()
        net_t    = time.time()
        dt       = max(net_t - _net_prev["t"], 0.001)
        net_up   = (net_now.bytes_sent - _net_prev["s"].bytes_sent) / dt / 1024**2
        net_dn   = (net_now.bytes_recv - _net_prev["s"].bytes_recv) / dt / 1024**2
        _net_prev = {"t": net_t, "s": net_now}
        disk_now = psutil.disk_io_counters()
        disk_t   = time.time()
        dt2      = max(disk_t - _disk_prev["t"], 0.001)
        disk_r   = (disk_now.read_bytes  - _disk_prev["d"].read_bytes)  / dt2 / 1024**2
        disk_w   = (disk_now.write_bytes - _disk_prev["d"].write_bytes) / dt2 / 1024**2
        _disk_prev = {"t": disk_t, "d": disk_now}

    uptime_s = int(time.time() - psutil.boot_time())
    h, r = divmod(uptime_s, 3600); m, s = divmod(r, 60)
    cpu_freq = psutil.cpu_freq()

    return {
        "name": name if isinstance(name, str) else name.decode(),
        "temp": temp, "gpu_util": util.gpu, "mem_util": util.memory,
        "mem_used": mem.used/1024**3, "mem_total": mem.total/1024**3, "mem_free": mem.free/1024**3,
        "power_draw": power_draw, "power_limit": power_lim,
        **ext,
        "temp_warn": _gpu_temp_warn,
        "cpu": psutil.cpu_percent(interval=None),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_freq": int(cpu_freq.current) if cpu_freq else 0,
        "ram_used": ram.used/1024**3, "ram_total": ram.total/1024**3,
        "net_up": round(net_up, 2), "net_dn": round(net_dn, 2),
        "disk_r": round(disk_r, 2), "disk_w": round(disk_w, 2),
        "uptime": f"{h}h {m:02d}m {s:02d}s",
        "model": _get_model(),
    }
