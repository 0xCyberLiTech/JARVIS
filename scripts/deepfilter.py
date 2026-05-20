"""DeepFilterNet module — débruitage IA temps réel via CUDA.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 split monolithe (module 4).

Couvre :
- Lazy load DeepFilterNet (torch + df.enhance) — ~500 ms cold start
- Resample auto vers/depuis 48 kHz natif (resample_poly scipy)
- Silence loguru/torchaudio + redirection stderr fd2 (bypass logging Python pour git rev-parse subprocess)
- Off-by-one fix après resample (resample_poly peut produire orig_len ± 1 sample)

Usage : `from deepfilter import enhance_audio; out = enhance_audio(audio_f32, sr=44100)`
Si DeepFilterNet indispo (lib non installée), retourne le signal original sans modification.
"""
import logging
import threading
import time

import numpy as np

_log = logging.getLogger("jarvis.deepfilter")

# ── State ─────────────────────────────────────────────────────
_DF_AVAILABLE = False
_df_model     = None
_df_sr        = 48000
_DF_LOAD_LOCK = threading.Lock()  # évite le double chargement concurrent
_DF_LOAD_DONE = False              # flag : tentative déjà effectuée (succès ou échec)
_torch        = None               # importé lazy à la 1re utilisation


def _load():
    """Charge lazy DeepFilterNet + torch (~500 ms cold start). Idempotent (lock + flag)."""
    global _DF_AVAILABLE, _df_model, _df_sr, _DF_LOAD_DONE, _torch
    with _DF_LOAD_LOCK:
        if _DF_LOAD_DONE:
            return
        _DF_LOAD_DONE = True
        _df_load_t0 = time.monotonic()
        # Silence les loggers verbeux de DeepFilterNet / torchaudio
        for _noisy in ("df", "df.enhance", "df.model", "torchaudio", "torch"):
            logging.getLogger(_noisy).setLevel(logging.ERROR)
        try:
            import os as _os
            import sys as _sys
            # 1. Silence loguru (utilisé par DeepFilterNet — bypass du logging Python standard)
            try:
                from loguru import logger as _loguru_logger
                _loguru_logger.disable("df")
                _loguru_logger.disable("")
            except Exception:
                pass  # loguru optionnel — suppression stderr DeepFilterNet non critique
            # 2. Import torch ici (lazy) — évite 1.5s au démarrage
            try:
                import torch as _torch_mod
                _torch = _torch_mod
            except ImportError:
                _torch = None
            # 3. Redirige sys.stderr Python ET fd2 OS-level vers /dev/null pendant l'import
            #    DeepFilterNet appelle git rev-parse via subprocess → écrit sur fd2, pas sys.stderr
            _saved_py_stderr = _sys.stderr
            _saved_fd2 = None
            try:
                _sys.stderr = open(_os.devnull, "w")
                _fd2_null = _os.open(_os.devnull, _os.O_WRONLY)
                _saved_fd2 = _os.dup(2)
                _os.dup2(_fd2_null, 2)
                _os.close(_fd2_null)
            except Exception:
                _saved_py_stderr = None
            try:
                from df.enhance import enhance, init_df
                model, df_state, _ = init_df()
            finally:
                if _saved_fd2 is not None:
                    try:
                        _os.dup2(_saved_fd2, 2)
                        _os.close(_saved_fd2)
                    except Exception:
                        pass  # restauration fd2 non bloquante
                if _saved_py_stderr is not None:
                    try:
                        _sys.stderr.close()
                    except Exception:
                        pass  # fermeture devnull non bloquante
                    _sys.stderr = _saved_py_stderr  # restaure sys.stderr Python
            _df_model = (model, df_state, enhance)
            _df_sr    = df_state.sr()
            _DF_AVAILABLE = True
            _log.info(f"[TTS-PERF] DeepFilterNet chargé en {time.monotonic() - _df_load_t0:.2f}s — sr={_df_sr}")
        except Exception as e:
            _log.warning(f"[TTS-PERF] DeepFilterNet indisponible après {time.monotonic() - _df_load_t0:.2f}s: {type(e).__name__}")


# ── API publique ──────────────────────────────────────────────

def is_available() -> bool:
    """True si DeepFilterNet est chargé et utilisable. Force le load lazy si pas encore tenté."""
    if not _DF_LOAD_DONE:
        _load()
    return _DF_AVAILABLE


def get_status() -> tuple[bool, int]:
    """Retourne (available, sample_rate) SANS forcer le load (read-only state).
    Utile pour /api/sysdiag où on ne veut pas déclencher 500 ms de chargement."""
    return _DF_AVAILABLE, (_df_sr if _DF_AVAILABLE else 0)


def enhance_audio(audio_f32, sr: int):
    """Débruite un signal float32 mono via DeepFilterNet.
    Rééchantillonne si nécessaire vers 48 kHz et retour.
    Retourne le signal original si DeepFilterNet indispo (no-op safe)."""
    if not _DF_LOAD_DONE:
        _load()
    if not _DF_AVAILABLE or _df_model is None:
        return audio_f32
    model, df_state, enhance = _df_model
    orig_len = len(audio_f32)  # longueur originale — resample_poly peut décaler ±1
    try:
        from math import gcd

        from scipy.signal import resample_poly
        target_sr = _df_sr
        if sr != target_sr:
            g = gcd(target_sr, sr)
            audio_f32 = resample_poly(audio_f32, target_sr // g, sr // g).astype(np.float32)
        # DeepFilterNet attend (1, samples) tensor
        t = _torch.from_numpy(audio_f32).unsqueeze(0)
        enhanced = enhance(model, df_state, t)
        out = enhanced.squeeze(0).numpy()
        if sr != target_sr:
            g = gcd(sr, target_sr)
            out = resample_poly(out, sr // g, target_sr // g).astype(np.float32)
        # Correction off-by-one : resample_poly peut produire orig_len ± 1 sample
        if len(out) > orig_len:
            out = out[:orig_len]
        elif len(out) < orig_len:
            out = np.pad(out, (0, orig_len - len(out)))
        return out.astype(np.float32)
    except Exception as e:
        _log.error(f"[DeepFilterNet] Erreur enhance: {e}")
        return audio_f32
