"""Audio DSP — chaîne de traitement signal vocal (reverb, FX rack, EQ, compresseur).

Extrait de jarvis.py — chantier dette technique 2026-05-14 (Action #4).

Traitement signal PUR : numpy + scipy + miniaudio + DeepFilterNet (module deepfilter).
Aucune dépendance Flask. Seule fonction publique : `apply_dsp_to_mp3(mp3_bytes, params)`
— les params DSP sont injectés en argument (DI) depuis jarvis.py (DSP_PARAMS).

Couvre :
- Reverb à convolution (CUDA torch FFT ou scipy) + IR synthétiques par preset
- FX rack multi-effets : delay, chorus, phaser, flanger, echo, exciter
- Filtres biquad : low/high shelf, peaking, high/low pass (Butterworth)
- Enrichisseur harmonique voix, compresseur dynamique, upmix mono→stéréo Haas
- Pipeline complet : décodage WAV/MP3 → EQ → DeepFilter → enrich → FX → encodage WAV
"""
import io as _io
import logging
import struct as _struct

import numpy as np

from . import deepfilter as _df  # module dédié DeepFilterNet (même tuile voice)

_log = logging.getLogger("jarvis.audio_dsp")

# ── Moteur DSP (scipy + miniaudio) — dégradation gracieuse si absent ──
try:
    import miniaudio as _mini
    from scipy import signal as _sig
    _DSP_AVAILABLE = True
except Exception:
    _DSP_AVAILABLE = False

DSP_AVAILABLE = _DSP_AVAILABLE  # alias public consommé par jarvis.py (/api/sysdiag)

# ── Constantes normalisation int16 ↔ float ──
_INT16_MAX   = 32767     # valeur max entier 16 bits signé (clip audio WAV)
_INT16_MIN   = -32768    # valeur min entier 16 bits signé
_INT16_SCALE = 32768.0   # facteur normalisation int16 ↔ float (2^15)

# ── Cache des réponses impulsionnelles reverb (max 8 entrées, LRU) ──
_FX_IR_CACHE = {}


def _gen_ir(preset: str, sr: int, decay_s: float) -> 'np.ndarray':
    """Génère une réponse impulsionnelle synthétique (reverb) pour le preset."""
    configs = {
        'room':     {'decay': 0.6,  'diffuse': 0.45, 'damping': 0.72, 'predelay': 0.008, 'er_count': 10},
        'studio':   {'decay': 0.9,  'diffuse': 0.50, 'damping': 0.80, 'predelay': 0.010, 'er_count': 12},
        'concert':  {'decay': 2.0,  'diffuse': 0.70, 'damping': 0.50, 'predelay': 0.025, 'er_count': 18},
        'cathedral':{'decay': 4.0,  'diffuse': 0.90, 'damping': 0.28, 'predelay': 0.040, 'er_count': 24},
        'plate':    {'decay': 1.5,  'diffuse': 0.80, 'damping': 0.88, 'predelay': 0.005, 'er_count': 16},
        'cave':     {'decay': 3.0,  'diffuse': 0.65, 'damping': 0.20, 'predelay': 0.060, 'er_count': 14},
        'spring':   {'decay': 0.9,  'diffuse': 0.35, 'damping': 0.60, 'predelay': 0.015, 'er_count':  8},
    }
    cfg = configs.get(preset, configs['room'])
    decay = max(0.1, decay_s)
    n = int(sr * (decay + 0.3))
    t = np.arange(n) / sr
    env = np.exp(-t * (5.5 / decay))
    rng = np.random.default_rng(hash(preset) & 0xFFFF)
    noise = rng.standard_normal(n).astype(np.float32)
    er = np.zeros(n, dtype=np.float32)
    pd = int(cfg['predelay'] * sr)
    for i in range(cfg['er_count']):
        idx = pd + int(sr * 0.003 * i * (1.0 + i * 0.12))
        if idx < n:
            er[idx] += (0.78 ** i)
    try:
        from scipy.signal import butter, sosfilt
        sos = butter(2, cfg['damping'] * 0.88, btype='low', output='sos')
        noise = sosfilt(sos, noise)
    except Exception as e:
        _log.debug(f"[FX] Filtre reverb scipy indisponible, IR non filtré: {e}")
    ir = (er * 0.55 + noise * env.astype(np.float32) * cfg['diffuse'] * 0.45)
    peak = np.max(np.abs(ir))
    if peak > 0:
        ir /= peak
    return ir.astype(np.float32)


def _convolve_reverb(signal: 'np.ndarray', ir: 'np.ndarray', wet: float) -> 'np.ndarray':
    """Convolution reverb — CUDA (torch FFT) si disponible, sinon scipy."""
    try:
        from scipy.signal import fftconvolve
    except ImportError:
        return signal
    try:
        import torch as _torch
    except ImportError:
        _torch = None
    try:
        if _torch is not None and _torch.cuda.is_available():
            n_out = len(signal) + len(ir) - 1
            n_fft = 1 << (n_out - 1).bit_length()
            t_sig = _torch.from_numpy(signal).float().cuda()
            t_ir  = _torch.from_numpy(ir).float().cuda()
            conv  = _torch.fft.irfft(_torch.fft.rfft(t_sig, n=n_fft) *
                                      _torch.fft.rfft(t_ir,  n=n_fft), n=n_fft)
            conv  = conv[:len(signal)].cpu().numpy()
        else:
            conv = fftconvolve(signal, ir)[:len(signal)]
    except Exception:
        try:
            conv = fftconvolve(signal, ir)[:len(signal)]
        except Exception:
            return signal
    peak_c = np.max(np.abs(conv)) + 1e-8
    peak_s = np.max(np.abs(signal)) + 1e-8
    conv = conv / peak_c * peak_s
    return signal * (1.0 - wet) + conv * wet


def _apply_delay(signal: 'np.ndarray', sr: int, delay_ms: float, feedback: float, wet: float) -> 'np.ndarray':
    """Tape echo — délais multiples avec feedback décroissant."""
    delay_n = int(delay_ms / 1000.0 * sr)
    if delay_n <= 0 or delay_n >= len(signal):
        return signal
    fb = min(abs(feedback), 0.90)
    out = signal.copy()
    for k in range(1, 9):
        offset = k * delay_n
        if offset >= len(signal):
            break
        amp = (fb ** k) * wet
        if amp < 1e-6:
            break
        out[offset:] += signal[:len(signal) - offset] * amp
    return np.clip(out, -1.0, 1.0)


def _apply_chorus(signal: 'np.ndarray', sr: int, rate_hz: float, depth_s: float, wet: float) -> 'np.ndarray':
    """Chorus — modulation LFO d'une ligne à délai."""
    n = len(signal)
    lfo = np.sin(2.0 * np.pi * rate_hz * np.arange(n) / sr)
    base_n = int(0.010 * sr)
    depth_n = int(depth_s * sr)
    out = np.empty(n, dtype=np.float32)
    for i in range(n):
        src = i - base_n - int(lfo[i] * depth_n)
        if 0 <= src < n:
            out[i] = signal[i] * (1.0 - wet) + signal[src] * wet
        else:
            out[i] = signal[i]
    return out


def _apply_phaser(signal: 'np.ndarray', sr: int, stages: int, wet: float) -> 'np.ndarray':
    """Phaser — cascade de filtres all-pass avec LFO."""
    try:
        from scipy.signal import lfilter
    except ImportError:
        return signal
    n_s = max(2, min(stages, 12))
    t = np.arange(len(signal)) / sr
    lfo = 0.5 + 0.5 * np.sin(2.0 * np.pi * 0.5 * t)
    out = signal.copy()
    for _ in range(n_s):
        fc = 400.0 + lfo * 800.0
        a0 = (np.tan(np.pi * fc[0] / sr) - 1.0) / (np.tan(np.pi * fc[0] / sr) + 1.0)
        out = lfilter([a0, 1.0], [1.0, a0], out).astype(np.float32)
    return (signal * (1.0 - wet) + out * wet).astype(np.float32)


def _apply_flanger(signal: 'np.ndarray', sr: int, rate_hz: float, depth_s: float, feedback: float, wet: float) -> 'np.ndarray':
    """Flanger — délai court modulé par LFO avec feedback."""
    n = len(signal)
    base_n  = int(0.001 * sr)            # 1ms base fixe
    depth_n = max(1, int(depth_s * sr))  # profondeur modulée
    fb      = float(np.clip(feedback, 0.0, 0.95))
    lfo     = np.sin(2.0 * np.pi * rate_hz * np.arange(n) / sr)
    out     = signal.astype(np.float32).copy()
    fb_val  = np.float32(0.0)
    result  = np.empty(n, dtype=np.float32)
    for i in range(n):
        delay = base_n + int((lfo[i] * 0.5 + 0.5) * depth_n)
        src   = i - delay
        delayed = (out[src] + fb_val * fb) if 0 <= src < n else np.float32(0.0)
        fb_val  = np.float32(np.clip(delayed, -1.0, 1.0))
        result[i] = np.float32(signal[i] * (1.0 - wet) + delayed * wet)
    return np.clip(result, -1.0, 1.0)


def _apply_echo(signal: 'np.ndarray', sr: int, left_ms: float, right_ms: float, feedback: float, wet: float) -> 'np.ndarray':
    """Echo stéréo — deux lignes de délai entrelacées avec feedback."""
    n      = len(signal)
    ln     = max(1, int(left_ms  / 1000.0 * sr))
    rn     = max(1, int(right_ms / 1000.0 * sr))
    fb     = float(np.clip(feedback, 0.0, 0.88))
    out    = signal.astype(np.float32).copy()
    for k in range(1, 10):
        # Gauche
        off_l = k * ln
        if off_l >= n: break
        amp_l = (fb ** k) * wet
        if amp_l < 1e-5: break
        out[off_l:] += (signal[:n - off_l] * amp_l).astype(np.float32)
        # Droite (décalé de rn supplémentaires)
        off_r = off_l + rn
        if off_r >= n: break
        amp_r = amp_l * 0.65
        out[off_r:] += (signal[:n - off_r] * amp_r).astype(np.float32)
    return np.clip(out, -1.0, 1.0)


def _apply_exciter(signal: 'np.ndarray', sr: int, drive_db: float, tone_hz: float, warmth: float, wet: float) -> 'np.ndarray':
    """Exciter harmonique — saturation douce + rehaussement hautes fréquences."""
    gain   = 10 ** (drive_db / 20.0)
    driven = np.tanh(signal * gain) / max(np.tanh(gain), 1e-8)
    try:
        from scipy.signal import butter, sosfilt
        freq_norm = min(float(tone_hz) / (sr / 2.0), 0.98)
        sos_air  = butter(2, freq_norm, btype='high', output='sos')
        air      = sosfilt(sos_air, driven).astype(np.float32)
        freq_w   = min(300.0 / (sr / 2.0), 0.98)
        sos_warm = butter(2, freq_w, btype='low', output='sos')
        warm_sat = np.tanh(sosfilt(sos_warm, signal) * (1.0 + warmth * 2)) * warmth * 0.4
        exciter  = (air * (1.0 - warmth * 0.4) + warm_sat).astype(np.float32)
    except Exception:
        exciter = driven.astype(np.float32)
    return np.clip(signal * (1.0 - wet) + exciter * wet, -1.0, 1.0).astype(np.float32)


def _apply_fx_rack(signal: 'np.ndarray', sr: int, params: dict) -> 'np.ndarray':
    """Applique le FX rack multi-effets sur le signal mono float32."""
    p = params
    if not p.get('fx_enabled', False):
        return signal
    fx_type = p.get('fx_type', 'reverb')
    preset  = p.get('fx_preset', 'room')
    wet     = float(np.clip(p.get('fx_wet', 0.30), 0.0, 1.0))
    try:
        if fx_type == 'reverb' and preset != 'none':
            decay = float(p.get('fx_decay', 1.5))
            cache_key = f"{preset}_{sr}_{decay:.2f}"
            if cache_key not in _FX_IR_CACHE:
                if len(_FX_IR_CACHE) >= 8:
                    del _FX_IR_CACHE[next(iter(_FX_IR_CACHE))]
                _FX_IR_CACHE[cache_key] = _gen_ir(preset, sr, decay)
            return _convolve_reverb(signal, _FX_IR_CACHE[cache_key], wet)
        elif fx_type == 'delay':
            return _apply_delay(signal, sr, float(p.get('fx_delay_ms', 350.0)),
                                float(p.get('fx_delay_feedback', 0.4)), wet)
        elif fx_type == 'chorus':
            return _apply_chorus(signal, sr,
                                 float(p.get('fx_chorus_rate',  0.62)),
                                 float(p.get('fx_chorus_depth', 0.018)),
                                 wet)
        elif fx_type == 'flanger':
            return _apply_flanger(signal, sr,
                                  float(p.get('fx_flanger_rate',     0.30)),
                                  float(p.get('fx_flanger_depth',    0.003)),
                                  float(p.get('fx_flanger_feedback', 0.70)),
                                  wet)
        elif fx_type == 'echo':
            return _apply_echo(signal, sr,
                               float(p.get('fx_echo_left_ms',  375.0)),
                               float(p.get('fx_echo_right_ms', 250.0)),
                               float(p.get('fx_echo_feedback', 0.55)),
                               wet)
        elif fx_type == 'phaser':
            return _apply_phaser(signal, sr, int(p.get('fx_phaser_stages', 6)), wet)
        elif fx_type == 'exciter':
            return _apply_exciter(signal, sr,
                                  float(p.get('fx_exciter_drive',  6.0)),
                                  float(p.get('fx_exciter_tone',   5000.0)),
                                  float(p.get('fx_exciter_warmth', 0.30)),
                                  wet)
    except Exception as e:
        _log.error(f"[FX RACK] Erreur: {e}")
    return signal


def _db2lin(db):
    return 10 ** (db / 20.0)

def _bq_lowshelf(data, sr, freq, gain_db):
    if not _DSP_AVAILABLE or abs(gain_db) < 0.05: return data
    A = _db2lin(gain_db / 2)
    w0 = 2 * np.pi * freq / sr
    cos_w0, sin_w0 = np.cos(w0), np.sin(w0)
    alpha = sin_w0 * np.sqrt(2 * A) / 2  # S=1
    b0 =     A*((A+1) - (A-1)*cos_w0 + 2*np.sqrt(A)*alpha)
    b1 = 2*A*((A-1) - (A+1)*cos_w0)
    b2 =     A*((A+1) - (A-1)*cos_w0 - 2*np.sqrt(A)*alpha)
    a0 =       (A+1) + (A-1)*cos_w0 + 2*np.sqrt(A)*alpha
    a1 =  -2*( (A-1) + (A+1)*cos_w0)
    a2 =       (A+1) + (A-1)*cos_w0 - 2*np.sqrt(A)*alpha
    sos = np.array([[b0/a0, b1/a0, b2/a0, 1.0, a1/a0, a2/a0]])
    return _sig.sosfilt(sos, data)

def _bq_peaking(data, sr, freq, gain_db, Q=0.8):
    if not _DSP_AVAILABLE or abs(gain_db) < 0.05: return data
    A = _db2lin(gain_db / 2)
    w0 = 2 * np.pi * freq / sr
    alpha = np.sin(w0) / (2 * Q)
    cos_w0 = np.cos(w0)
    b0 = 1 + alpha * A;  b1 = -2*cos_w0;  b2 = 1 - alpha * A
    a0 = 1 + alpha / A;  a1 = -2*cos_w0;  a2 = 1 - alpha / A
    sos = np.array([[b0/a0, b1/a0, b2/a0, 1.0, a1/a0, a2/a0]])
    return _sig.sosfilt(sos, data)

def _bq_highshelf(data, sr, freq, gain_db):
    if not _DSP_AVAILABLE or abs(gain_db) < 0.05: return data
    A = _db2lin(gain_db / 2)
    w0 = 2 * np.pi * freq / sr
    cos_w0, sin_w0 = np.cos(w0), np.sin(w0)
    alpha = sin_w0 * np.sqrt(2 * A) / 2
    b0 =      A*((A+1) + (A-1)*cos_w0 + 2*np.sqrt(A)*alpha)
    b1 = -2*A*((A-1) + (A+1)*cos_w0)
    b2 =      A*((A+1) + (A-1)*cos_w0 - 2*np.sqrt(A)*alpha)
    a0 =        (A+1) - (A-1)*cos_w0 + 2*np.sqrt(A)*alpha
    a1 =   2*( (A-1) - (A+1)*cos_w0)
    a2 =        (A+1) - (A-1)*cos_w0 - 2*np.sqrt(A)*alpha
    sos = np.array([[b0/a0, b1/a0, b2/a0, 1.0, a1/a0, a2/a0]])
    return _sig.sosfilt(sos, data)

def _bq_hp(data, sr, freq):
    """Highpass Butterworth 2nd order — coupe les fréquences sous freq Hz."""
    if not _DSP_AVAILABLE: return data
    freq = max(1.0, min(freq, sr // 2 - 50))
    sos = _sig.butter(2, freq / (sr / 2), btype='high', output='sos')
    return _sig.sosfilt(sos, data).astype(np.float32)

def _bq_lp(data, sr, freq):
    """Lowpass Butterworth 2nd order — coupe les fréquences au-dessus de freq Hz."""
    if not _DSP_AVAILABLE: return data
    freq = max(1.0, min(freq, sr // 2 - 50))
    sos = _sig.butter(2, freq / (sr / 2), btype='low', output='sos')
    return _sig.sosfilt(sos, data).astype(np.float32)

def _enrich_voice(signal: 'np.ndarray', sr: int,
                  drive_db: float, tone_hz: float, mix: float, warmth: float) -> 'np.ndarray':
    """Enrichisseur harmonique voix — 3 couches parallèles.

    1. Présence   : peaking +1.5dB @ 2.8kHz Q=1.4 (intelligibilité)
    2. Exciter    : HP tone_hz → tanh saturation → mix parallèle
                    Génère harmoniques 2e/3e sur bande présence+air
    3. Chaleur    : saturation paires douce bande 80-600Hz (tube analog)
    """
    if not _DSP_AVAILABLE or (mix < 0.005 and warmth < 0.005):
        return signal
    out = signal.copy()
    try:
        # ── 1. Présence fixe : +1.5dB @ 2.8kHz —————————————————
        out = _bq_peaking(out, sr, min(2800.0, sr // 2 - 200), 1.5, Q=1.4)

        # ── 2. Exciter harmonique HP→tanh→mix ————————————————————
        if mix > 0.005:
            fn   = min(float(tone_hz) / (sr / 2.0), 0.95)
            sos  = _sig.butter(2, fn, btype='high', output='sos')
            band = _sig.sosfilt(sos, signal).astype(np.float32)   # bande haute du signal original
            g    = _db2lin(drive_db)
            harmonics = np.tanh(band * g) / max(float(np.tanh(g)), 1e-8)
            out  = np.clip(out + harmonics * mix, -1.0, 1.0).astype(np.float32)

        # ── 3. Chaleur tube : saturation paire 80-600Hz ——————————
        if warmth > 0.005:
            f_lo = min(80.0  / (sr / 2.0), 0.95)
            f_hi = min(600.0 / (sr / 2.0), 0.95)
            sos_bp = _sig.butter(2, [f_lo, f_hi], btype='band', output='sos')
            warm   = _sig.sosfilt(sos_bp, signal).astype(np.float32)
            # saturation paire (harmoniques paires = 2e, 4e → chaleur sans stridence)
            warm_sat = warm - (warm ** 3) / 3.0
            out  = np.clip(out + warm_sat * warmth, -1.0, 1.0).astype(np.float32)
    except Exception as e:
        _log.debug(f"[ENRICH] {e}")
    return out


def _compress(data_f32, sr, threshold_db, ratio, attack_s, release_s):
    """Compresseur dynamique — envelope follower one-pole IIR, gain computer feed-forward."""
    if not _DSP_AVAILABLE or ratio < 1.01:
        return data_f32
    thresh = _db2lin(threshold_db)
    att = float(np.exp(-1.0 / max(1, sr * attack_s)))
    rel = float(np.exp(-1.0 / max(1, sr * release_s)))
    level = np.abs(data_f32)
    gr = np.ones(len(data_f32), dtype=np.float32)
    e = 0.0
    for i in range(len(data_f32)):
        lv = float(level[i])
        e = (att * e + (1.0 - att) * lv) if lv > e else (rel * e + (1.0 - rel) * lv)
        if e > thresh > 0.0:
            gr[i] = (thresh + (e - thresh) / ratio) / e
    return data_f32 * gr

def _mono_to_stereo(data_f32, sr, p):
    """Upmix mono → stéréo 2 canaux via effet Haas.
    L = signal direct. R = signal délayé de haas_delay_ms ms.
    stereo_width blende entre mono pur (0.0) et Haas complet (1.0)."""
    width = float(p.get("stereo_width", 0.85))
    delay_ms = float(p.get("haas_delay_ms", 18.0))
    delay_smp = max(0, int(sr * delay_ms / 1000.0))

    L = data_f32.copy()
    R = np.zeros(len(L), dtype=np.float32)
    if delay_smp > 0 and delay_smp < len(L):
        R[delay_smp:] = data_f32[:len(L) - delay_smp]
    else:
        R[:] = data_f32

    # blend: width=0 → R=L (mono), width=1 → R=haas
    R_out = (1.0 - width) * L + width * R
    stereo = np.column_stack([L, R_out])
    return stereo

def _pcm_to_wav(pcm_bytes, sr, ch, bits=16):
    """Encode raw PCM → WAV bytes sans dépendance externe."""
    n_bytes = len(pcm_bytes)
    bps = bits // 8
    buf = _io.BytesIO()
    # RIFF header
    buf.write(b'RIFF')
    buf.write(_struct.pack('<I', 36 + n_bytes))
    buf.write(b'WAVE')
    buf.write(b'fmt ')
    buf.write(_struct.pack('<IHHIIHH', 16, 1, ch, sr, sr * ch * bps, ch * bps, bits))
    buf.write(b'data')
    buf.write(_struct.pack('<I', n_bytes))
    buf.write(pcm_bytes)
    return buf.getvalue()

def _dsp_enrich(d, sr, p):
    return _enrich_voice(d, sr,
                         float(p.get("enrich_drive",   2.5)),
                         float(p.get("enrich_tone",  2800.0)),
                         float(p.get("enrich_mix",    0.15)),
                         float(p.get("enrich_warmth", 0.06)))

def _dsp_eq_gain(d, sr, p, nyq, eq_flat):
    d = _bq_hp(d, sr, 20)
    d = _bq_lp(d, sr, min(16000, nyq))
    if not eq_flat:
        d = _bq_lowshelf(d,  sr, 250,   p["eq_low"])
        d = _bq_peaking( d,  sr, 1000,  p["eq_mid"],  Q=0.8)
        d = _bq_peaking( d,  sr, 4000,  p["eq_high"], Q=0.9)
        d = _bq_highshelf(d, sr, min(14000, nyq), p["eq_air"])
    d = _compress(d, sr, p["comp_threshold"], p["comp_ratio"], p["comp_attack"], p["comp_release"])
    return d * _db2lin(p["gain"])

def _dsp_decode_audio(mp3_bytes: bytes, is_wav: bool):
    """Décode WAV ou MP3 → (raw float32 1D, sample_rate, channels)."""
    if is_wav:
        import io as _io_wav
        import wave as _wave
        with _wave.open(_io_wav.BytesIO(mp3_bytes)) as wf:
            sr  = wf.getframerate()
            ch  = wf.getnchannels()
            raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / _INT16_SCALE
    else:
        decoded = _mini.decode(mp3_bytes, output_format=_mini.SampleFormat.SIGNED16)
        sr  = decoded.sample_rate
        ch  = decoded.nchannels
        raw = np.frombuffer(decoded.samples, dtype=np.int16).astype(np.float32) / _INT16_SCALE
    return raw, sr, ch

def _dsp_apply_chain(samples: "np.ndarray", sr: int, p: dict, df_on: bool, eq_flat: bool) -> "np.ndarray":
    """Applique EQ → DeepFilter → enrich → FX sur un canal mono (float32)."""
    nyq = sr // 2 - 200  # clamp Nyquist — évite instabilité filtre (ex: Piper 22050Hz)
    out = _dsp_eq_gain(samples, sr, p, nyq, eq_flat)
    if df_on:
        out = _df.enhance_audio(out, sr)
    if p.get("enrich_enabled", True):
        out = _dsp_enrich(out, sr, p)
    if p.get("fx_enabled"):
        out = _apply_fx_rack(out, sr, p)
    return out

def apply_dsp_to_mp3(mp3_bytes, params, df_override=None):
    """Applique la chaîne DSP (EQ + gain + stéréo Haas) au MP3 ou WAV.
    `params` : dict DSP_PARAMS injecté depuis jarvis.py (DI).
    df_override=False : bypass DeepFilterNet (ex: source 24kHz → évite artefacts resampling).
    Retourne toujours un WAV stéréo si stereo_enabled, sinon WAV mono.
    Fallback sur audio original en cas d'erreur."""
    p = params
    is_wav    = mp3_bytes[:4] == b'RIFF'
    orig_mime = "audio/wav" if is_wav else "audio/mpeg"
    if not _DSP_AVAILABLE or not p.get("enabled", True):
        return mp3_bytes, orig_mime
    stereo_wanted = p.get("stereo_enabled", True)
    eq_flat = all(abs(p.get(k, 0)) < 0.05 for k in ["eq_low","eq_mid","eq_high","eq_air","gain"])
    df_on   = p.get("df_enabled", False) if df_override is None else bool(df_override)
    if eq_flat and not stereo_wanted and not df_on and not p.get("fx_enabled", False):
        return mp3_bytes, orig_mime
    try:
        raw, sr, ch = _dsp_decode_audio(mp3_bytes, is_wav)
        if ch == 2:
            # Signal déjà stéréo — chaîne DSP canal par canal
            raw2 = raw.reshape(-1, 2)
            out  = np.zeros_like(raw2)
            for c in range(2):
                out[:, c] = _dsp_apply_chain(raw2[:, c], sr, p, df_on, eq_flat)
            raw_out = np.clip(out.flatten() * _INT16_SCALE, _INT16_MIN, _INT16_MAX).astype(np.int16)
            out_ch  = 2
        else:
            # Signal mono — chaîne DSP puis upmix stéréo Haas si demandé
            d = _dsp_apply_chain(raw, sr, p, df_on, eq_flat)
            if stereo_wanted:
                stereo  = _mono_to_stereo(d, sr, p)
                raw_out = np.clip(stereo.flatten() * _INT16_SCALE, _INT16_MIN, _INT16_MAX).astype(np.int16)
                out_ch  = 2
            else:
                raw_out = np.clip(d * _INT16_SCALE, _INT16_MIN, _INT16_MAX).astype(np.int16)
                out_ch  = 1
        return _pcm_to_wav(raw_out.tobytes(), sr, out_ch), "audio/wav"
    except Exception as e:
        _log.error(f"[DSP] Erreur: {e}")
        return mp3_bytes, orig_mime
