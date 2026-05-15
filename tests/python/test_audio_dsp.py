"""Tests audio_dsp — DSP pur (numpy + scipy + miniaudio + DeepFilterNet).

Couvre les parties pures sans dépendance audio réel : _db2lin, _pcm_to_wav,
_mono_to_stereo, court-circuits (gain<0.05, ratio<1.01), apply_dsp_to_mp3
en bypass, et constantes.
"""
import struct

import audio_dsp
import numpy as np
import pytest
from audio_dsp import (
    _FX_IR_CACHE,
    _INT16_MAX,
    _INT16_MIN,
    _INT16_SCALE,
    DSP_AVAILABLE,
    _bq_hp,
    _bq_lp,
    _bq_peaking,
    _compress,
    _db2lin,
    _mono_to_stereo,
    _pcm_to_wav,
    apply_dsp_to_mp3,
)

# ── Constantes int16 ─────────────────────────────────────────────────────


def test_int16_max_min_scale_sont_les_valeurs_standard():
    assert _INT16_MAX == 32767
    assert _INT16_MIN == -32768
    assert _INT16_SCALE == 32768.0


def test_dsp_available_est_un_bool():
    assert isinstance(DSP_AVAILABLE, bool)


def test_fx_ir_cache_initialement_vide_ou_dict():
    assert isinstance(_FX_IR_CACHE, dict)


# ── _db2lin (conversion dB → linéaire) ───────────────────────────────────


def test_db2lin_zero_db_donne_unite():
    assert _db2lin(0) == pytest.approx(1.0)


def test_db2lin_20_db_donne_environ_10():
    assert _db2lin(20) == pytest.approx(10.0)


def test_db2lin_minus_20_db_donne_environ_0_1():
    assert _db2lin(-20) == pytest.approx(0.1)


def test_db2lin_6_db_donne_environ_2():
    """+6 dB ≈ doublement de l'amplitude."""
    assert _db2lin(6) == pytest.approx(2.0, abs=0.01)


def test_db2lin_minus_6_db_donne_environ_0_5():
    """-6 dB ≈ moitié de l'amplitude."""
    assert _db2lin(-6) == pytest.approx(0.5, abs=0.01)


def test_db2lin_40_db_donne_100():
    assert _db2lin(40) == pytest.approx(100.0)


# ── _pcm_to_wav (encodage WAV header) ────────────────────────────────────


def test_pcm_to_wav_header_riff_correct():
    pcm = b"\x00\x01" * 100  # 200 bytes PCM
    wav = _pcm_to_wav(pcm, sr=48000, ch=1, bits=16)
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert wav[12:16] == b"fmt "


def test_pcm_to_wav_taille_riff_correcte():
    pcm = b"\x00" * 100
    wav = _pcm_to_wav(pcm, sr=48000, ch=1)
    riff_size = struct.unpack("<I", wav[4:8])[0]
    assert riff_size == 36 + 100  # 36 bytes header + data


def test_pcm_to_wav_data_chunk_correct():
    pcm = b"\xab\xcd" * 50  # 100 bytes
    wav = _pcm_to_wav(pcm, sr=44100, ch=2)
    # 'data' marker à offset 36
    assert wav[36:40] == b"data"
    data_size = struct.unpack("<I", wav[40:44])[0]
    assert data_size == 100
    # PCM data après
    assert wav[44:144] == pcm


def test_pcm_to_wav_sample_rate_encode():
    wav = _pcm_to_wav(b"\x00" * 4, sr=22050, ch=1)
    # sample rate à offset 24-28 (RIFF[0-12]+fmt[12-20]+chunk_size+pcm_format+ch+SR)
    sr_encoded = struct.unpack("<I", wav[24:28])[0]
    assert sr_encoded == 22050


def test_pcm_to_wav_channels_encode():
    # mono
    wav = _pcm_to_wav(b"\x00" * 4, sr=48000, ch=1)
    assert struct.unpack("<H", wav[22:24])[0] == 1
    # stéréo
    wav = _pcm_to_wav(b"\x00" * 4, sr=48000, ch=2)
    assert struct.unpack("<H", wav[22:24])[0] == 2


def test_pcm_to_wav_pcm_vide_genere_header_seul():
    wav = _pcm_to_wav(b"", sr=48000, ch=1)
    assert len(wav) == 44  # header WAV standard
    assert wav[:4] == b"RIFF"


# ── _mono_to_stereo (upmix Haas) ─────────────────────────────────────────


def test_mono_to_stereo_renvoie_array_2D_2_canaux():
    mono = np.ones(1000, dtype=np.float32)
    stereo = _mono_to_stereo(mono, sr=48000, p={})
    assert stereo.shape == (1000, 2)


def test_mono_to_stereo_canal_gauche_est_signal_direct():
    """L = signal direct, doit être identique au mono."""
    mono = np.linspace(-1, 1, 500, dtype=np.float32)
    stereo = _mono_to_stereo(mono, sr=48000, p={})
    np.testing.assert_array_equal(stereo[:, 0], mono)


def test_mono_to_stereo_width_zero_donne_R_egal_L():
    """width=0 → mono pur (R = L)."""
    mono = np.linspace(-1, 1, 500, dtype=np.float32)
    stereo = _mono_to_stereo(mono, sr=48000, p={"stereo_width": 0.0, "haas_delay_ms": 18.0})
    np.testing.assert_array_almost_equal(stereo[:, 0], stereo[:, 1])


def test_mono_to_stereo_haas_delay_decale_le_canal_droit():
    """width=1 + delay > 0 : R = L décalé de delay_smp samples."""
    mono = np.zeros(1000, dtype=np.float32)
    mono[0] = 1.0  # impulsion
    delay_ms = 18.0
    sr = 48000
    delay_smp = int(sr * delay_ms / 1000.0)
    stereo = _mono_to_stereo(mono, sr=sr, p={"stereo_width": 1.0, "haas_delay_ms": delay_ms})
    # L : impulsion à index 0
    assert stereo[0, 0] == 1.0
    # R : impulsion à index delay_smp (avec width=1, R = R_haas pur)
    assert stereo[delay_smp, 1] == pytest.approx(1.0)


def test_mono_to_stereo_dtype_float32():
    mono = np.ones(100, dtype=np.float32)
    stereo = _mono_to_stereo(mono, sr=48000, p={})
    assert stereo.dtype == np.float32


# ── Filtres biquad — court-circuit gain trop petit ───────────────────────


def test_bq_peaking_gain_quasi_nul_renvoie_data_inchangee():
    """gain_db < 0.05 → bypass."""
    data = np.linspace(-1, 1, 100, dtype=np.float32)
    out = _bq_peaking(data, sr=48000, freq=1000, gain_db=0.0)
    np.testing.assert_array_equal(out, data)


def test_bq_peaking_gain_juste_sous_seuil_005_renvoie_inchange():
    data = np.ones(50, dtype=np.float32)
    out = _bq_peaking(data, sr=48000, freq=1000, gain_db=0.04)
    np.testing.assert_array_equal(out, data)


# ── _compress — court-circuit ratio trop petit ───────────────────────────


def test_compress_ratio_quasi_1_renvoie_inchange():
    """ratio < 1.01 → bypass (rien à compresser)."""
    data = np.linspace(-0.5, 0.5, 100, dtype=np.float32)
    out = _compress(data, sr=48000, threshold_db=-20.0, ratio=1.0,
                    attack_s=0.005, release_s=0.05)
    np.testing.assert_array_equal(out, data)


# ── _bq_hp / _bq_lp — clamp Nyquist ──────────────────────────────────────


@pytest.mark.skipif(not DSP_AVAILABLE, reason="scipy/miniaudio absent")
def test_bq_hp_freq_au_dela_de_nyquist_clamp_proprement():
    """Une freq > Nyquist - 50 doit être clampée — ne doit PAS crasher."""
    data = np.random.randn(1000).astype(np.float32)
    out = _bq_hp(data, sr=48000, freq=30000)  # Nyquist = 24000
    assert len(out) == 1000


@pytest.mark.skipif(not DSP_AVAILABLE, reason="scipy/miniaudio absent")
def test_bq_lp_freq_negative_clamp_a_1():
    """freq <= 0 doit être clampé à 1.0 — ne doit PAS crasher."""
    data = np.random.randn(500).astype(np.float32)
    out = _bq_lp(data, sr=48000, freq=-100)
    assert len(out) == 500


# ── apply_dsp_to_mp3 — bypass cases ──────────────────────────────────────


def test_apply_dsp_disabled_renvoie_audio_inchange_et_mime_d_origine():
    """params['enabled']=False → bytes inchangés + MIME source."""
    fake_wav = b"RIFF\x00\x00\x00\x00WAVE..."
    out, mime = apply_dsp_to_mp3(fake_wav, {"enabled": False})
    assert out == fake_wav
    assert mime == "audio/wav"


def test_apply_dsp_mp3_disabled_renvoie_mime_mpeg():
    """Source non-WAV (MP3) avec enabled=False → MIME audio/mpeg."""
    fake_mp3 = b"ID3\x00...mp3 data..."
    out, mime = apply_dsp_to_mp3(fake_mp3, {"enabled": False})
    assert out == fake_mp3
    assert mime == "audio/mpeg"


def test_apply_dsp_eq_flat_sans_stereo_sans_df_sans_fx_renvoie_inchange():
    """Tous les modules off → bypass complet (pas de décodage)."""
    fake_wav = b"RIFF\x00\x00\x00\x00WAVE..."
    p = {
        "enabled": True,
        "stereo_enabled": False,
        "df_enabled": False,
        "fx_enabled": False,
        "eq_low": 0.0, "eq_mid": 0.0, "eq_high": 0.0, "eq_air": 0.0, "gain": 0.0,
    }
    out, mime = apply_dsp_to_mp3(fake_wav, p)
    assert out == fake_wav
    assert mime == "audio/wav"


def test_apply_dsp_donnees_corrompues_fallback_sur_original():
    """Décodage qui crash → exception → fallback sur audio original."""
    bad_wav = b"RIFF\x04\x00\x00\x00WAVEjunk"  # WAV invalide
    p = {
        "enabled": True,
        "stereo_enabled": True,  # force le décodage
        "df_enabled": False,
        "fx_enabled": False,
        "eq_low": 0.0, "eq_mid": 0.0, "eq_high": 0.0, "eq_air": 0.0, "gain": 0.0,
        "stereo_width": 0.85, "haas_delay_ms": 18.0,
        "comp_threshold": -20, "comp_ratio": 4, "comp_attack": 0.005, "comp_release": 0.05,
    }
    if not DSP_AVAILABLE:
        pytest.skip("DSP non disponible — bypass complet, pas de fallback à tester")
    out, mime = apply_dsp_to_mp3(bad_wav, p)
    # Fallback : retourne original + son MIME
    assert out == bad_wav
    assert mime == "audio/wav"


def test_apply_dsp_signature_signature_explicite():
    """Smoke test : la fonction accepte 2 ou 3 args (df_override optionnel)."""
    fake = b"RIFF" + b"\x00" * 100
    out, mime = apply_dsp_to_mp3(fake, {"enabled": False})  # 2 args
    assert isinstance(out, bytes)
    out2, mime2 = apply_dsp_to_mp3(fake, {"enabled": False}, df_override=False)  # 3 args
    assert isinstance(out2, bytes)


# ── Module logger ─────────────────────────────────────────────────────────


def test_module_logger_jarvis_audio_dsp():
    """Sanity : le logger porte le bon nom."""
    assert audio_dsp._log.name == "jarvis.audio_dsp"
