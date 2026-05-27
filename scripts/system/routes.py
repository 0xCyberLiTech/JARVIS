"""Routes HTTP de la tuile system."""
import json
import platform
import time

import psutil
from flask import Response

from . import bp, diag

# Accesseurs (lambdas) injectés par __init__.init() — résolus à l'appel
# pour suivre les valeurs réassignées au runtime (MODEL, VOICE) ou les
# états mutables (DSP_PARAMS).
_get_nvml_handle  = None
_get_memory_limit = None
_get_model        = None
_get_voice        = None
_get_dsp_avail    = None
_get_dsp_params   = None
_get_df_status    = None

_GB_BYTES = 1 << 30


def init_routes(*, get_nvml_handle, get_memory_limit, get_model, get_voice,
                get_dsp_avail, get_dsp_params, get_df_status) -> None:
    """Injecte les accesseurs transverses (LLM/voice/DSP) consommés par api_sysdiag."""
    global _get_nvml_handle, _get_memory_limit, _get_model, _get_voice
    global _get_dsp_avail, _get_dsp_params, _get_df_status
    _get_nvml_handle  = get_nvml_handle
    _get_memory_limit = get_memory_limit
    _get_model        = get_model
    _get_voice        = get_voice
    _get_dsp_avail    = get_dsp_avail
    _get_dsp_params   = get_dsp_params
    _get_df_status    = get_df_status


@bp.route("/api/sysdiag")
def api_sysdiag():
    data = diag._diag_cpu_ram_disk()

    # GPU
    data.update(diag._diag_gpu(_get_nvml_handle()))

    # Réseau
    net = psutil.net_io_counters()
    data["net_sent"] = round(net.bytes_sent / 1048576, 1)
    data["net_recv"] = round(net.bytes_recv / 1048576, 1)

    # Système
    uptime_s = int(time.time() - psutil.boot_time())
    h_, r = divmod(uptime_s, 3600); m_, _ = divmod(r, 60)
    data["uptime"]   = f"{h_}h{m_:02d}m"
    data["platform"] = platform.system() + " " + platform.version().split(".")[0]
    data["hostname"] = platform.node()

    # LLM
    data["llm_model"]    = _get_model()
    data["llm_provider"] = "ollama"
    data["llm_voice"]    = _get_voice()

    # Ollama connectivity + latency
    data.update(diag._diag_ollama())

    # DSP + DeepFilterNet
    data["dsp_available"] = _get_dsp_avail()
    dsp_params = _get_dsp_params()
    data["dsp_enabled"]   = dsp_params.get("enabled", False)
    data["dsp_params"]    = dict(dsp_params)
    _df_avail, _df_sample_rate = _get_df_status()
    data["df_available"]  = _df_avail
    data["df_enabled"]    = dsp_params.get("df_enabled", False)
    data["df_sr"]         = _df_sample_rate

    # CPU temperature
    data["cpu_temp"] = diag._diag_cpu_temp()

    # SWAP
    swap = psutil.swap_memory()
    data["swap_total"] = round(swap.total / _GB_BYTES, 1)
    data["swap_used"]  = round(swap.used  / _GB_BYTES, 1)
    data["swap_pct"]   = swap.percent

    # Mémoire conversations
    data["memory_exchanges"] = diag._diag_memory_count()
    data["memory_limit"]     = _get_memory_limit()

    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/json")
