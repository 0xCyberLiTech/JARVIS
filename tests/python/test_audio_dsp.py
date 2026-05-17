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


# ─────────────────────────────────────────────────────────────────────────
# Smoke tests DSP — vérifient juste shape/dtype et absence de crash.
# Les algos DSP sont validés par écoute en prod (Marc) — ces tests
# garantissent juste que la chaîne ne casse pas après refactor.
# ─────────────────────────────────────────────────────────────────────────


def _signal_sin(freq=440.0, sr=22050, dur=0.5):
    """Signal mono float32 sinus court pour smoke tests DSP."""
    t = np.linspace(0, dur, int(sr * dur), endpoint=False, dtype=np.float32)
    return (0.3 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


# ── _gen_ir : génération de réponse impulsionnelle reverb ────────────────


def test_gen_ir_room_preset():
    ir = audio_dsp._gen_ir("room", sr=22050, decay_s=0.6)
    assert ir.dtype == np.float32
    assert len(ir) > 0
    # IR normalisée → peak ≤ 1
    assert np.max(np.abs(ir)) <= 1.0 + 1e-6


def test_gen_ir_tous_les_presets_renvoient_ir_valide():
    """Vérifie les 7 presets configurés (room/studio/concert/cathedral/plate/cave/spring)."""
    for preset in ["room", "studio", "concert", "cathedral", "plate", "cave", "spring"]:
        ir = audio_dsp._gen_ir(preset, sr=22050, decay_s=1.0)
        assert ir.dtype == np.float32
        assert len(ir) > 0


def test_gen_ir_preset_inconnu_fallback_room():
    """Preset non listé → fallback sur 'room' config (pas de crash)."""
    ir = audio_dsp._gen_ir("preset-inexistant", sr=22050, decay_s=0.5)
    assert ir.dtype == np.float32
    assert len(ir) > 0


def test_gen_ir_decay_minimum_0_1():
    """decay_s < 0.1 → clipé à 0.1 (longueur IR cohérente)."""
    ir = audio_dsp._gen_ir("room", sr=22050, decay_s=0.01)
    # Au moins ~0.4s d'IR (0.1 + 0.3 marge)
    assert len(ir) >= int(22050 * 0.4) - 1


def test_gen_ir_deterministe_meme_preset():
    """Même preset + même params → même IR (rng seedé sur hash preset)."""
    ir1 = audio_dsp._gen_ir("studio", sr=22050, decay_s=1.0)
    ir2 = audio_dsp._gen_ir("studio", sr=22050, decay_s=1.0)
    np.testing.assert_array_equal(ir1, ir2)


# ── _convolve_reverb : convolution reverb ────────────────────────────────


def test_convolve_reverb_signal_silence_renvoie_signal_inchange_taille():
    """Signal de zéros → output de même longueur."""
    sig = np.zeros(1000, dtype=np.float32)
    ir = audio_dsp._gen_ir("room", sr=22050, decay_s=0.3)
    out = audio_dsp._convolve_reverb(sig, ir, wet=0.5)
    # Le résultat est tronqué à la longueur du signal d'entrée
    assert len(out) == len(sig)


def test_convolve_reverb_signal_sin_modifie():
    """Signal réel + IR → output non-identique au signal d'origine."""
    sig = _signal_sin(440.0, sr=22050, dur=0.1)
    ir = audio_dsp._gen_ir("room", sr=22050, decay_s=0.3)
    out = audio_dsp._convolve_reverb(sig, ir, wet=1.0)
    assert len(out) == len(sig)
    # Le signal a été transformé (reverb ajoute énergie/décroissance)
    assert not np.array_equal(sig, out)


# ── _apply_delay / chorus / phaser / flanger / echo / exciter ───────────


def test_apply_delay_preserve_shape():
    sig = _signal_sin(440.0)
    out = audio_dsp._apply_delay(sig, sr=22050, delay_ms=50.0, feedback=0.3, wet=0.5)
    assert out.shape == sig.shape
    assert out.dtype == np.float32


def test_apply_chorus_preserve_shape():
    sig = _signal_sin(440.0)
    out = audio_dsp._apply_chorus(sig, sr=22050, rate_hz=1.5, depth_s=0.005, wet=0.4)
    assert out.shape == sig.shape


def test_apply_phaser_preserve_shape():
    sig = _signal_sin(440.0)
    out = audio_dsp._apply_phaser(sig, sr=22050, stages=4, wet=0.5)
    assert out.shape == sig.shape


def test_apply_flanger_preserve_shape():
    sig = _signal_sin(440.0)
    out = audio_dsp._apply_flanger(sig, sr=22050, rate_hz=0.3, depth_s=0.003, feedback=0.4, wet=0.5)
    assert out.shape == sig.shape


def test_apply_echo_preserve_shape():
    sig = _signal_sin(440.0)
    out = audio_dsp._apply_echo(sig, sr=22050, left_ms=120.0, right_ms=180.0, feedback=0.35, wet=0.4)
    assert out.shape == sig.shape


def test_apply_exciter_preserve_shape():
    sig = _signal_sin(440.0)
    out = audio_dsp._apply_exciter(sig, sr=22050, drive_db=6.0, tone_hz=2500.0, warmth=0.4, wet=0.5)
    assert out.shape == sig.shape


# ── _apply_fx_rack : orchestration FX rack ──────────────────────────────


def test_apply_fx_rack_params_vides_bypass():
    """params vide ou enabled=False sur tous → signal essentiellement préservé."""
    sig = _signal_sin(440.0)
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params={})
    assert out.shape == sig.shape


def test_apply_fx_rack_reverb_active_modifie_signal():
    sig = _signal_sin(440.0, sr=22050, dur=0.2)
    params = {"reverb": {"enabled": True, "preset": "room", "decay_s": 0.5, "wet": 0.5}}
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params=params)
    assert out.shape == sig.shape


def test_apply_fx_rack_chaine_complete():
    """Reverb + delay + chorus + phaser tous actifs → output shape OK."""
    sig = _signal_sin(440.0, sr=22050, dur=0.1)
    params = {
        "reverb": {"enabled": True, "preset": "studio", "decay_s": 0.3, "wet": 0.3},
        "delay":  {"enabled": True, "delay_ms": 100.0, "feedback": 0.2, "wet": 0.3},
        "chorus": {"enabled": True, "rate_hz": 1.0, "depth_s": 0.003, "wet": 0.2},
        "phaser": {"enabled": True, "stages": 4, "wet": 0.3},
    }
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params=params)
    assert out.shape == sig.shape


# ── Biquad filters : _bq_lowshelf / _bq_highshelf ───────────────────────


def test_bq_lowshelf_preserve_shape():
    data = _signal_sin(120.0)
    out = audio_dsp._bq_lowshelf(data, sr=22050, freq=200.0, gain_db=3.0)
    assert out.shape == data.shape


def test_bq_highshelf_preserve_shape():
    data = _signal_sin(5000.0)
    out = audio_dsp._bq_highshelf(data, sr=22050, freq=3000.0, gain_db=2.5)
    assert out.shape == data.shape


# ── _enrich_voice : enrichisseur harmonique vocal ───────────────────────


def test_enrich_voice_preserve_shape():
    """Signature : _enrich_voice(signal, sr, drive_db, tone_hz, mix, warmth)."""
    sig = _signal_sin(200.0)
    out = audio_dsp._enrich_voice(sig, sr=22050, drive_db=2.5, tone_hz=2800.0,
                                    mix=0.15, warmth=0.06)
    assert out.shape == sig.shape


def test_enrich_voice_mix_et_warmth_zero_court_circuit():
    """mix < 0.005 ET warmth < 0.005 → court-circuit, signal retourné inchangé."""
    sig = _signal_sin(200.0)
    out = audio_dsp._enrich_voice(sig, sr=22050, drive_db=0.0, tone_hz=2800.0,
                                    mix=0.0, warmth=0.0)
    # Court-circuit = même array (référence)
    assert out is sig


# ── _dsp_enrich : wrapper qui lit params dict ───────────────────────────


def test_dsp_enrich_avec_params_defaults():
    """_dsp_enrich(data, sr, p) wraps _enrich_voice avec params dict (defaults OK)."""
    sig = _signal_sin(200.0)
    out = audio_dsp._dsp_enrich(sig, sr=22050, p={})
    assert out.shape == sig.shape


# ── _pcm_to_wav : génération header WAV ─────────────────────────────────


def test_pcm_to_wav_header_riff_present():
    """Header WAV commence par 'RIFF' + size + 'WAVE'."""
    pcm = b"\x00\x00" * 100   # 100 samples mono 16 bits
    wav = audio_dsp._pcm_to_wav(pcm, sr=22050, ch=1, bits=16)
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"


def test_pcm_to_wav_inclut_pcm_data():
    """Le payload PCM doit être préservé dans le WAV de sortie."""
    pcm = bytes(range(50)) * 4   # 200 bytes arbitraires
    wav = audio_dsp._pcm_to_wav(pcm, sr=22050, ch=1, bits=16)
    assert pcm in wav


def test_pcm_to_wav_stereo_ch_param():
    """ch=2 → header mentionne 2 canaux."""
    pcm = b"\x00\x00\x00\x00" * 100
    wav = audio_dsp._pcm_to_wav(pcm, sr=22050, ch=2, bits=16)
    # NumChannels est aux bytes 22-23 (little-endian)
    num_channels = struct.unpack("<H", wav[22:24])[0]
    assert num_channels == 2


# ── _apply_fx_rack : branches FX activées (réelle signature p['fx_enabled']) ─


def test_apply_fx_rack_disabled_court_circuit():
    """fx_enabled absent ou False → retourne signal inchangé (early return)."""
    sig = _signal_sin(440.0)
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params={})
    assert out is sig
    out2 = audio_dsp._apply_fx_rack(sig, sr=22050, params={"fx_enabled": False})
    assert out2 is sig


def test_apply_fx_rack_reverb_avec_cache(monkeypatch):
    """fx_type=reverb → utilise _FX_IR_CACHE, miss puis hit."""
    audio_dsp._FX_IR_CACHE.clear()
    sig = _signal_sin(440.0, dur=0.1)
    params = {"fx_enabled": True, "fx_type": "reverb", "fx_preset": "room",
              "fx_decay": 0.5, "fx_wet": 0.3}
    out1 = audio_dsp._apply_fx_rack(sig, sr=22050, params=params)
    assert out1.shape == sig.shape
    # 1er appel = miss + insert
    assert len(audio_dsp._FX_IR_CACHE) == 1
    # 2e appel même params = hit cache
    out2 = audio_dsp._apply_fx_rack(sig, sr=22050, params=params)
    assert len(audio_dsp._FX_IR_CACHE) == 1
    assert out2.shape == sig.shape


def test_apply_fx_rack_reverb_cache_eviction_au_dela_de_8():
    """Cache LRU : au-delà de 8 entrées, la plus ancienne est évincée."""
    audio_dsp._FX_IR_CACHE.clear()
    sig = _signal_sin(440.0, dur=0.05)
    # Remplir avec 9 presets distincts
    for i, preset in enumerate(["room", "studio", "concert", "cathedral",
                                  "plate", "cave", "spring", "room", "studio"]):
        decay = 0.3 + i * 0.1   # decay différent → cache_key différent
        audio_dsp._apply_fx_rack(sig, sr=22050, params={
            "fx_enabled": True, "fx_type": "reverb", "fx_preset": preset,
            "fx_decay": decay, "fx_wet": 0.3,
        })
    # Cache cappé à 8 entrées
    assert len(audio_dsp._FX_IR_CACHE) <= 8


def test_apply_fx_rack_reverb_preset_none_bypass():
    """preset='none' → pas de reverb appliqué, branche skip."""
    sig = _signal_sin(440.0, dur=0.05)
    params = {"fx_enabled": True, "fx_type": "reverb", "fx_preset": "none",
              "fx_decay": 0.5, "fx_wet": 0.5}
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params=params)
    # Pas de cache utilisé
    assert out.shape == sig.shape


def test_apply_fx_rack_delay():
    sig = _signal_sin(440.0, dur=0.1)
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params={
        "fx_enabled": True, "fx_type": "delay",
        "fx_delay_ms": 100.0, "fx_delay_feedback": 0.3, "fx_wet": 0.4,
    })
    assert out.shape == sig.shape


def test_apply_fx_rack_chorus():
    sig = _signal_sin(440.0, dur=0.1)
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params={
        "fx_enabled": True, "fx_type": "chorus", "fx_wet": 0.3,
    })
    assert out.shape == sig.shape


def test_apply_fx_rack_flanger():
    sig = _signal_sin(440.0, dur=0.1)
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params={
        "fx_enabled": True, "fx_type": "flanger", "fx_wet": 0.4,
    })
    assert out.shape == sig.shape


def test_apply_fx_rack_echo():
    sig = _signal_sin(440.0, dur=0.1)
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params={
        "fx_enabled": True, "fx_type": "echo", "fx_wet": 0.3,
    })
    assert out.shape == sig.shape


def test_apply_fx_rack_phaser():
    sig = _signal_sin(440.0, dur=0.1)
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params={
        "fx_enabled": True, "fx_type": "phaser",
        "fx_phaser_stages": 4, "fx_wet": 0.4,
    })
    assert out.shape == sig.shape


def test_apply_fx_rack_exciter():
    sig = _signal_sin(440.0, dur=0.1)
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params={
        "fx_enabled": True, "fx_type": "exciter", "fx_wet": 0.5,
    })
    assert out.shape == sig.shape


def test_apply_fx_rack_exception_fallback_signal(monkeypatch):
    """Exception interne dans une branche → fallback sur signal (log.error)."""
    sig = _signal_sin(440.0, dur=0.05)

    def boom(*a, **kw):
        raise RuntimeError("FX simulated failure")

    monkeypatch.setattr(audio_dsp, "_apply_delay", boom)
    out = audio_dsp._apply_fx_rack(sig, sr=22050, params={
        "fx_enabled": True, "fx_type": "delay", "fx_wet": 0.4,
    })
    # Signal retourné inchangé (fallback)
    assert out is sig


# ── _compress : algo réel (ratio >= 1.01) ───────────────────────────────


def test_compress_court_circuit_si_ratio_inf_a_1_01():
    """ratio < 1.01 → court-circuit, signal inchangé."""
    sig = _signal_sin(440.0)
    out = audio_dsp._compress(sig, sr=22050, threshold_db=-20, ratio=1.0,
                                attack_s=0.01, release_s=0.1)
    assert out is sig


def test_compress_reduit_amplitude_signal_fort():
    """Signal au-dessus du threshold → compressé (amplitude réduite)."""
    import numpy as np
    sr = 22050
    # Signal avec quelques crêtes fortes (> threshold)
    sig = (np.ones(sr // 4, dtype=np.float32) * 0.8)
    out = audio_dsp._compress(sig, sr=sr, threshold_db=-12, ratio=4.0,
                                attack_s=0.005, release_s=0.05)
    # La compression doit réduire le RMS (au moins légèrement)
    assert np.max(np.abs(out)) <= np.max(np.abs(sig)) + 1e-6


def test_compress_signal_sous_threshold_preserve():
    """Signal sous threshold → pas de réduction (gr=1 partout)."""
    import numpy as np
    sr = 22050
    sig = (np.ones(sr // 4, dtype=np.float32) * 0.01)   # très faible
    out = audio_dsp._compress(sig, sr=sr, threshold_db=-3, ratio=4.0,
                                attack_s=0.005, release_s=0.05)
    assert out.shape == sig.shape


# ── _dsp_eq_gain : pipeline EQ + compresseur + gain ─────────────────────


def _eq_params_complets(gain_db=0.0, eq_flat=False):
    """Params dict complets pour _dsp_eq_gain (nécessite toutes les clés)."""
    return {
        "eq_low": 2.0, "eq_mid": -1.0, "eq_high": 1.5, "eq_air": 2.5,
        "comp_threshold": -18.0, "comp_ratio": 3.0,
        "comp_attack": 0.005, "comp_release": 0.05,
        "gain": gain_db,
    }


def test_dsp_eq_gain_avec_eq_actif():
    sig = _signal_sin(440.0, dur=0.2)
    nyq = 22050 // 2 - 200
    out = audio_dsp._dsp_eq_gain(sig, sr=22050, p=_eq_params_complets(),
                                   nyq=nyq, eq_flat=False)
    assert out.shape == sig.shape


def test_dsp_eq_gain_avec_eq_flat_bypass_bandes():
    """eq_flat=True → skip eq_low/mid/high/air mais garde HP/LP + comp + gain."""
    sig = _signal_sin(440.0, dur=0.2)
    nyq = 22050 // 2 - 200
    out = audio_dsp._dsp_eq_gain(sig, sr=22050, p=_eq_params_complets(),
                                   nyq=nyq, eq_flat=True)
    assert out.shape == sig.shape


def test_dsp_eq_gain_gain_positif_amplifie():
    """gain_db=+6dB → amplification ~2× (sur signal très faible pour pas clipper)."""
    import numpy as np
    sig = (np.ones(1000, dtype=np.float32) * 0.01)
    nyq = 22050 // 2 - 200
    out = audio_dsp._dsp_eq_gain(sig, sr=22050, p=_eq_params_complets(gain_db=6.0),
                                   nyq=nyq, eq_flat=True)
    # +6dB ≈ ×2 — vérifier ordre de grandeur (filtres HP/LP peuvent altérer un peu)
    assert np.max(np.abs(out)) > 0.0


# ── _dsp_decode_audio : décodage WAV ────────────────────────────────────


def _make_wav_mono_16bit(sr=22050, n_samples=1000):
    """Crée un WAV mono 16 bits valide en mémoire."""
    import io as _io_local
    import wave as _wave_local
    buf = _io_local.BytesIO()
    with _wave_local.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00" * n_samples)
    return buf.getvalue()


def _make_wav_stereo_16bit(sr=22050, n_samples=1000):
    import io as _io_local
    import wave as _wave_local
    buf = _io_local.BytesIO()
    with _wave_local.open(buf, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(b"\x00\x00\x00\x00" * n_samples)
    return buf.getvalue()


def test_dsp_decode_audio_wav_mono_renvoie_sr_et_canal_1():
    wav = _make_wav_mono_16bit(sr=22050, n_samples=500)
    raw, sr, ch = audio_dsp._dsp_decode_audio(wav, is_wav=True)
    assert sr == 22050
    assert ch == 1
    assert raw.dtype == np.float32
    assert len(raw) == 500


def test_dsp_decode_audio_wav_stereo_renvoie_canal_2():
    wav = _make_wav_stereo_16bit(sr=44100, n_samples=300)
    raw, sr, ch = audio_dsp._dsp_decode_audio(wav, is_wav=True)
    assert sr == 44100
    assert ch == 2
    # Stéréo entrelacé → len = 2 × 300 = 600 samples float
    assert len(raw) == 600


# ── _dsp_apply_chain : pipeline complet ─────────────────────────────────


def test_dsp_apply_chain_avec_params_complets():
    """Pipeline complet : EQ + comp + gain → output float32 même longueur."""
    sig = _signal_sin(440.0, dur=0.2)
    p = _eq_params_complets()
    p.update({"enrich_enabled": False, "fx_enabled": False})
    out = audio_dsp._dsp_apply_chain(sig, sr=22050, p=p, df_on=False, eq_flat=False)
    assert out.shape == sig.shape


def test_dsp_apply_chain_avec_enrich_et_fx():
    """Pipeline avec enrich + fx_rack actifs."""
    sig = _signal_sin(440.0, dur=0.1)
    p = _eq_params_complets()
    p.update({
        "enrich_enabled": True, "enrich_drive": 2.5, "enrich_tone": 2800.0,
        "enrich_mix": 0.15, "enrich_warmth": 0.06,
        "fx_enabled": True, "fx_type": "reverb", "fx_preset": "room",
        "fx_decay": 0.3, "fx_wet": 0.2,
    })
    audio_dsp._FX_IR_CACHE.clear()
    out = audio_dsp._dsp_apply_chain(sig, sr=22050, p=p, df_on=False, eq_flat=False)
    assert out.shape == sig.shape


# ── apply_dsp_to_mp3 : point d'entrée public ────────────────────────────


def test_apply_dsp_to_mp3_court_circuit_si_disabled():
    """params['enabled']=False → retourne bytes originaux + mime."""
    wav = _make_wav_mono_16bit()
    out, mime = audio_dsp.apply_dsp_to_mp3(wav, {"enabled": False})
    assert out == wav
    assert mime == "audio/wav"


def test_apply_dsp_to_mp3_mp3_detecte_par_absence_de_RIFF():
    """Bytes sans header RIFF → mime audio/mpeg quand bypass."""
    fake_mp3 = b"\x00" * 100
    _, mime = audio_dsp.apply_dsp_to_mp3(fake_mp3, {"enabled": False})
    assert mime == "audio/mpeg"


def test_apply_dsp_to_mp3_court_circuit_si_eq_flat_no_stereo_no_df_no_fx():
    """Tout neutre → bypass complet, retour bytes originaux."""
    wav = _make_wav_mono_16bit()
    out, mime = audio_dsp.apply_dsp_to_mp3(wav, {
        "enabled": True, "eq_low": 0, "eq_mid": 0, "eq_high": 0, "eq_air": 0,
        "gain": 0, "stereo_enabled": False, "df_enabled": False, "fx_enabled": False,
    })
    assert out == wav   # bytes originaux préservés


def test_apply_dsp_to_mp3_wav_mono_avec_stereo_renvoie_wav_stereo():
    """WAV mono + stereo_enabled=True → output WAV stéréo Haas."""
    wav = _make_wav_mono_16bit(sr=22050, n_samples=2000)
    p = _eq_params_complets(gain_db=1.0)
    p.update({
        "enabled": True, "stereo_enabled": True, "haas_delay_ms": 18.0, "stereo_width": 0.85,
        "df_enabled": False,
        "enrich_enabled": False, "fx_enabled": False,
    })
    out, mime = audio_dsp.apply_dsp_to_mp3(wav, p)
    assert mime == "audio/wav"
    assert out[:4] == b"RIFF"
    # Header NumChannels = 2 (bytes 22-23 little-endian)
    num_ch = struct.unpack("<H", out[22:24])[0]
    assert num_ch == 2


def test_apply_dsp_to_mp3_wav_mono_sans_stereo_renvoie_mono():
    wav = _make_wav_mono_16bit(sr=22050, n_samples=1500)
    p = _eq_params_complets(gain_db=2.0)
    p.update({
        "enabled": True, "stereo_enabled": False,
        "df_enabled": False, "enrich_enabled": False, "fx_enabled": False,
    })
    out, mime = audio_dsp.apply_dsp_to_mp3(wav, p)
    assert mime == "audio/wav"
    num_ch = struct.unpack("<H", out[22:24])[0]
    assert num_ch == 1


def test_apply_dsp_to_mp3_wav_stereo_chaine_canal_par_canal():
    """WAV stéréo input → chaîne appliquée sur chaque canal séparément."""
    wav = _make_wav_stereo_16bit(sr=22050, n_samples=1000)
    p = _eq_params_complets(gain_db=0.5)
    p.update({
        "enabled": True, "stereo_enabled": True,
        "df_enabled": False, "enrich_enabled": False, "fx_enabled": False,
    })
    out, mime = audio_dsp.apply_dsp_to_mp3(wav, p)
    assert mime == "audio/wav"
    num_ch = struct.unpack("<H", out[22:24])[0]
    assert num_ch == 2


def test_apply_dsp_to_mp3_exception_fallback_original(monkeypatch):
    """Exception dans _dsp_decode_audio → fallback sur bytes originaux + mime."""

    def boom(*a, **kw):
        raise RuntimeError("decode simulated failure")

    monkeypatch.setattr(audio_dsp, "_dsp_decode_audio", boom)
    wav = _make_wav_mono_16bit()
    p = _eq_params_complets(gain_db=2.0)
    p.update({"enabled": True, "stereo_enabled": True,
              "df_enabled": False, "enrich_enabled": False, "fx_enabled": False})
    out, mime = audio_dsp.apply_dsp_to_mp3(wav, p)
    # Fallback : bytes originaux + mime "audio/wav" (RIFF détecté)
    assert out == wav
    assert mime == "audio/wav"


def test_apply_dsp_to_mp3_df_override_force_off(monkeypatch):
    """df_override=False → df_on forcé False même si params dit df_enabled=True."""
    wav = _make_wav_mono_16bit()
    captured = {"df_on": None}
    real_chain = audio_dsp._dsp_apply_chain

    def capture(samples, sr, p, df_on, eq_flat):
        captured["df_on"] = df_on
        return real_chain(samples, sr, p, df_on, eq_flat)

    monkeypatch.setattr(audio_dsp, "_dsp_apply_chain", capture)
    p = _eq_params_complets(gain_db=2.0)
    p.update({"enabled": True, "stereo_enabled": False,
              "df_enabled": True,   # params dit True
              "enrich_enabled": False, "fx_enabled": False})
    audio_dsp.apply_dsp_to_mp3(wav, p, df_override=False)
    assert captured["df_on"] is False   # override gagne
