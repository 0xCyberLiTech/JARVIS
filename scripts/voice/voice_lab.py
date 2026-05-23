"""Voice Lab module — analyse acoustique + voice prints + samples.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 split monolithe (module 2).
Couvre :
- Analyse librosa : pitch (yin), centroid, rolloff, flatness, MFCC, RMS, mel-spec
- Classification voix (SOPRANO / TÉNOR / BASSE / ...) + brightness/breathiness/voicing
- EQ preset auto basé sur features
- Voice prints CRUD (lister / serve / delete) — voice_prints/
- Voice samples — static/voice_samples/<lang>/
"""
import logging
import re
import wave
from pathlib import Path

_log = logging.getLogger("jarvis.voice_lab")

# ── Paths ─────────────────────────────────────────────────────
_VP_DIR      = Path(__file__).parent.parent / "voice_prints"
_SAMPLES_DIR = Path(__file__).parent.parent / "static" / "voice_samples"

# ── Helpers privés ────────────────────────────────────────────

def _safe_print_name(name: str) -> str:
    """Sanitize un nom de voice print : alphanum + tiret/underscore, max 64 chars."""
    return re.sub(r"[^\w\-]", "_", name.replace(".wav", ""))[:64]


def _eq_preset(pitch_median, centroid_mean, rolloff_mean):
    cn = max(0.0, min(1.0, (centroid_mean - 500) / 5000.0))
    rn = max(0.0, min(1.0, rolloff_mean / 8000.0))
    return {
        "low":   round(-2.0 * (1.0 - min(pitch_median / 150.0, 1.0)), 1),
        "lomid": round(2.0 - 4.0 * cn, 1),
        "mid":   round(max(-3.0, min(3.0, 3.0 - 5.0 * cn)), 1),
        "himid": round(max(-3.0, min(3.0, 2.5 - 5.0 * rn)), 1),
        "air":   round(3.5 - 2.5 * cn, 1),
    }


def _classify_type(pitch_median):
    if pitch_median > 250:  return "SOPRANO"
    if pitch_median > 200:  return "MEZZO / ALTO"
    if pitch_median > 160:  return "TÉNOR"
    if pitch_median > 120:  return "BARYTON"
    if pitch_median > 80:   return "BASSE"
    if pitch_median > 50:   return "BASSE PROFONDE"
    if pitch_median > 0:    return "SUB-BASS / INST."
    return "NON DÉTECTÉ"


# ── API publique : analyse ────────────────────────────────────

def is_librosa_available() -> bool:
    """Test si librosa est installé."""
    try:
        import librosa  # noqa: F401
        return True
    except ImportError:
        return False


def analyse_features(y, sr, fmin: float, fmax: float, n_mels: int) -> dict:
    """Calcule toutes les features acoustiques d'un signal audio mono float32.

    Retourne un dict avec : dur, sr, waveform (200 pts), pitch_curve (200 pts),
    spectrum (mel-spec), pitch metrics, centroid/rolloff/flatness/zcr,
    dynamic_range_db, mfcc_means, voice_type, brightness, breathiness, voicing,
    eq_preset.
    """
    import librosa
    import librosa.feature
    import numpy as np

    step_wf = max(1, len(y) // 200)
    waveform = [round(float(v), 4) for v in y[::step_wf][:200]]

    f0 = librosa.yin(y, fmin=fmin, fmax=fmax, sr=sr)
    f0_valid = f0[(f0 > fmin) & (f0 < fmax)]
    pitch_median = float(np.median(f0_valid)) if len(f0_valid) > 0 else 0.0
    pitch_min = float(np.percentile(f0_valid, 10)) if len(f0_valid) > 0 else 0.0
    pitch_max = float(np.percentile(f0_valid, 90)) if len(f0_valid) > 0 else 0.0
    pitch_curve = [round(min(float(v), fmax), 1) for v in f0[::max(1, len(f0) // 200)][:200]]

    sc = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    centroid_mean = float(np.mean(sc))
    rolloff_mean = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]))
    flatness_mean = float(np.mean(librosa.feature.spectral_flatness(y=y)[0]))
    mfcc_means = [round(float(v), 2) for v in np.mean(librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13), axis=1)]
    zcr_mean = float(np.mean(librosa.feature.zero_crossing_rate(y)[0]))

    rms = librosa.feature.rms(y=y)[0]
    rms_max = float(np.percentile(rms, 95))
    rms_floor = float(np.percentile(rms[rms > 1e-6], 5)) if np.any(rms > 1e-6) else 1e-6
    dynamic_range_db = round(20 * np.log10(rms_max / max(rms_floor, 1e-6)), 1) if rms_max > 0 else 0.0

    mel_db = librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=sr, n_mels=n_mels), ref=np.max)
    spectrum = [round(float(v), 1) for v in np.mean(mel_db, axis=1)]

    return {
        "dur": len(y) / sr, "sr": int(sr),
        "waveform": waveform, "pitch_curve": pitch_curve, "spectrum": spectrum,
        "pitch_median": pitch_median, "pitch_min": pitch_min, "pitch_max": pitch_max,
        "centroid_mean": centroid_mean, "rolloff_mean": rolloff_mean,
        "flatness_mean": flatness_mean, "zcr_mean": zcr_mean,
        "dynamic_range_db": dynamic_range_db, "mfcc_means": mfcc_means,
        "voice_type": _classify_type(pitch_median),
        "brightness":  "SOMBRE"  if centroid_mean < 1500 else "NEUTRE" if centroid_mean < 3000 else "BRILLANT",
        "breathiness": "SOUFFLÉ" if flatness_mean > 0.05 else "MIXTE"  if flatness_mean > 0.01 else "NET",
        "voicing":     "VOISÉE"  if zcr_mean < 0.1       else "MIXTE"  if zcr_mean < 0.2       else "BRUIT",
        "eq_preset": _eq_preset(pitch_median, centroid_mean, rolloff_mean),
    }


def load_audio(audio_path: str, duration: float = 60.0):
    """Wrapper librosa.load — retourne (y, sr) mono float32, max <duration> secondes."""
    import librosa
    return librosa.load(audio_path, sr=None, mono=True, duration=duration)


# ── API publique : voice prints ───────────────────────────────

def list_prints() -> list[dict]:
    """Liste les WAV dans voice_prints/ avec name/size_kb/duration."""
    result = []
    if not _VP_DIR.exists():
        return result
    for wav in sorted(_VP_DIR.glob("*.wav")):
        dur = 0.0
        try:
            with wave.open(str(wav), "rb") as wf:
                dur = round(wf.getnframes() / wf.getframerate(), 2)
        except Exception:
            pass  # durée non critique si fichier WAV malformé
        result.append({
            "name": wav.stem,
            "size_kb": round(wav.stat().st_size / 1024),
            "duration": dur,
        })
    return result


def get_print_path(name: str) -> Path | None:
    """Retourne le Path d'un voice print sanitisé, None si introuvable."""
    safe = _safe_print_name(name)
    wav_path = _VP_DIR / f"{safe}.wav"
    return wav_path if wav_path.exists() else None


def delete_print(name: str) -> tuple[bool, str]:
    """Supprime un voice print. Retourne (ok, sanitized_name_or_error)."""
    safe = _safe_print_name(name)
    wav_path = _VP_DIR / f"{safe}.wav"
    if not wav_path.exists():
        return False, "Fichier introuvable"
    wav_path.unlink()
    _log.info(f"[VOICE-PRINT] Supprimé : {wav_path.name}")
    return True, safe


# ── API publique : voice samples ──────────────────────────────

def list_samples() -> list[dict]:
    """Liste les WAV dans static/voice_samples/<lang>/."""
    result = []
    if not _SAMPLES_DIR.exists():
        return result
    for lang_dir in sorted(_SAMPLES_DIR.iterdir()):
        if not lang_dir.is_dir() or lang_dir.name.startswith("."):
            continue
        for wav in sorted(lang_dir.glob("*.wav")):
            result.append({
                "lang": lang_dir.name.upper(),
                "name": wav.stem.replace("_", " "),
                "file": wav.name,
                "url": f"/static/voice_samples/{lang_dir.name}/{wav.name}",
                "size_kb": round(wav.stat().st_size / 1024),
            })
    return result
