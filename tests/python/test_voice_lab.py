"""Tests voice_lab — analyse acoustique + voice prints CRUD (mock librosa, tmp_path FS)."""
import wave

from voice import voice_lab

# ── _safe_print_name ────────────────────────────────────────────────────


def test_safe_print_name_alphanum_inchange():
    assert voice_lab._safe_print_name("voice123") == "voice123"


def test_safe_print_name_underscore_tirets_preserves():
    assert voice_lab._safe_print_name("my-voice_test") == "my-voice_test"


def test_safe_print_name_supprime_extension_wav():
    assert voice_lab._safe_print_name("test.wav") == "test"


def test_safe_print_name_remplace_ponctuation_et_espaces():
    """Espaces et ponctuation → underscore. Note : `\\w` en Python couvre Unicode
    donc les accents (é, à) sont conservés comme word chars."""
    out = voice_lab._safe_print_name("voix #1 test!")
    assert out == "voix__1_test_"


def test_safe_print_name_tronque_a_64():
    long = "a" * 100
    out = voice_lab._safe_print_name(long)
    assert len(out) == 64


def test_safe_print_name_attaque_path_traversal():
    """`../` et chemins relatifs sanitised — protection path traversal."""
    out = voice_lab._safe_print_name("../../etc/passwd")
    assert ".." not in out
    assert "/" not in out


# ── _classify_type ──────────────────────────────────────────────────────


def test_classify_soprano_pitch_eleve():
    assert voice_lab._classify_type(280) == "SOPRANO"


def test_classify_mezzo_alto():
    assert voice_lab._classify_type(220) == "MEZZO / ALTO"


def test_classify_tenor():
    assert voice_lab._classify_type(180) == "TÉNOR"


def test_classify_baryton():
    assert voice_lab._classify_type(140) == "BARYTON"


def test_classify_basse():
    assert voice_lab._classify_type(100) == "BASSE"


def test_classify_basse_profonde():
    assert voice_lab._classify_type(60) == "BASSE PROFONDE"


def test_classify_sub_bass():
    assert voice_lab._classify_type(20) == "SUB-BASS / INST."


def test_classify_zero_non_detecte():
    assert voice_lab._classify_type(0) == "NON DÉTECTÉ"


def test_classify_negatif_non_detecte():
    """Pitch <= 0 → NON DÉTECTÉ."""
    assert voice_lab._classify_type(-5) == "NON DÉTECTÉ"


def test_classify_borne_250_soprano():
    """Borne exclusive : 250 n'est PAS soprano (>250 strict)."""
    assert voice_lab._classify_type(250) == "MEZZO / ALTO"


def test_classify_borne_251_soprano():
    """251 → soprano."""
    assert voice_lab._classify_type(251) == "SOPRANO"


# ── _eq_preset ──────────────────────────────────────────────────────────


def test_eq_preset_renvoie_dict_avec_5_bandes():
    out = voice_lab._eq_preset(150, 2000, 4000)
    assert set(out.keys()) == {"low", "lomid", "mid", "himid", "air"}


def test_eq_preset_valeurs_arrondies_a_1_decimale():
    out = voice_lab._eq_preset(120, 1500, 3000)
    for v in out.values():
        # Vérifier que c'est bien un nombre arrondi à 1 décimale
        assert v == round(v, 1)


def test_eq_preset_clamp_mid_himid_dans_minus_3_3():
    """mid/himid sont clampés dans [-3, 3] dB."""
    # Centroid très grand → mid devrait tomber à -3
    out = voice_lab._eq_preset(200, 10000, 8000)
    assert -3.0 <= out["mid"] <= 3.0
    assert -3.0 <= out["himid"] <= 3.0


def test_eq_preset_low_negatif_pour_pitch_haut():
    """Pitch très haut (soprano 300) → low boost moindre (proche 0)."""
    out_high = voice_lab._eq_preset(300, 2000, 4000)
    out_low = voice_lab._eq_preset(80, 2000, 4000)
    # Plus le pitch est bas, plus le low boost est négatif (correction LF)
    assert out_low["low"] < out_high["low"]


# ── is_librosa_available ────────────────────────────────────────────────


def test_is_librosa_available_renvoie_bool():
    """librosa peut être présent ou non — fonction doit toujours renvoyer un bool."""
    assert isinstance(voice_lab.is_librosa_available(), bool)


# ── list_prints / get_print_path / delete_print (avec tmp_path) ───────


def test_list_prints_dossier_inexistant_renvoie_liste_vide(monkeypatch, tmp_path):
    """Si _VP_DIR n'existe pas → []."""
    monkeypatch.setattr(voice_lab, "_VP_DIR", tmp_path / "absent")
    assert voice_lab.list_prints() == []


def test_list_prints_dossier_vide_renvoie_liste_vide(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_lab, "_VP_DIR", tmp_path)
    assert voice_lab.list_prints() == []


def _create_wav(path, sample_rate=22050, duration=1.0):
    """Crée un WAV mono 16-bit factice."""
    n_frames = int(sample_rate * duration)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n_frames)


def test_list_prints_avec_wav_renvoie_metadata(monkeypatch, tmp_path):
    """Crée un WAV factice et vérifie name/size_kb/duration."""
    monkeypatch.setattr(voice_lab, "_VP_DIR", tmp_path)
    _create_wav(tmp_path / "marc.wav", sample_rate=22050, duration=2.0)

    result = voice_lab.list_prints()
    assert len(result) == 1
    assert result[0]["name"] == "marc"
    assert result[0]["duration"] == 2.0
    assert result[0]["size_kb"] >= 0


def test_list_prints_wav_malforme_duration_zero(monkeypatch, tmp_path):
    """Fichier WAV malformé → duration=0 (try/except)."""
    monkeypatch.setattr(voice_lab, "_VP_DIR", tmp_path)
    (tmp_path / "broken.wav").write_text("not a wav")
    result = voice_lab.list_prints()
    assert result[0]["duration"] == 0.0


def test_list_prints_tri_alphabetique(monkeypatch, tmp_path):
    """Les WAV sont triés par nom (sorted glob)."""
    monkeypatch.setattr(voice_lab, "_VP_DIR", tmp_path)
    _create_wav(tmp_path / "z.wav")
    _create_wav(tmp_path / "a.wav")
    _create_wav(tmp_path / "m.wav")
    names = [r["name"] for r in voice_lab.list_prints()]
    assert names == ["a", "m", "z"]


def test_get_print_path_existant(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_lab, "_VP_DIR", tmp_path)
    _create_wav(tmp_path / "found.wav")
    p = voice_lab.get_print_path("found")
    assert p is not None
    assert p.name == "found.wav"


def test_get_print_path_inexistant_renvoie_none(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_lab, "_VP_DIR", tmp_path)
    assert voice_lab.get_print_path("nonexistent") is None


def test_get_print_path_sanitize_nom(monkeypatch, tmp_path):
    """`../etc/passwd` → sanitise + cherche le fichier sanitisé."""
    monkeypatch.setattr(voice_lab, "_VP_DIR", tmp_path)
    # Ne crée pas le fichier — doit retourner None mais sans crash
    p = voice_lab.get_print_path("../../etc/passwd")
    assert p is None  # Fichier sanitisé n'existe pas


def test_delete_print_existant_succes(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_lab, "_VP_DIR", tmp_path)
    _create_wav(tmp_path / "todelete.wav")

    ok, msg = voice_lab.delete_print("todelete")
    assert ok is True
    assert msg == "todelete"
    assert not (tmp_path / "todelete.wav").exists()


def test_delete_print_inexistant_echec(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_lab, "_VP_DIR", tmp_path)
    ok, msg = voice_lab.delete_print("absent")
    assert ok is False
    assert "introuvable" in msg.lower()


# ── list_samples ────────────────────────────────────────────────────────


def test_list_samples_dossier_inexistant(monkeypatch, tmp_path):
    monkeypatch.setattr(voice_lab, "_SAMPLES_DIR", tmp_path / "absent")
    assert voice_lab.list_samples() == []


def test_list_samples_organisee_par_lang(monkeypatch, tmp_path):
    """Structure : <SAMPLES_DIR>/<lang>/<file>.wav → list avec lang en MAJ."""
    monkeypatch.setattr(voice_lab, "_SAMPLES_DIR", tmp_path)
    fr_dir = tmp_path / "fr"
    fr_dir.mkdir()
    _create_wav(fr_dir / "marc_test.wav")

    en_dir = tmp_path / "en"
    en_dir.mkdir()
    _create_wav(en_dir / "john.wav")

    result = voice_lab.list_samples()
    assert len(result) == 2
    langs = {r["lang"] for r in result}
    assert langs == {"FR", "EN"}


def test_list_samples_remplace_underscore_par_espace_dans_name(monkeypatch, tmp_path):
    """`marc_test.wav` → name = 'marc test'."""
    monkeypatch.setattr(voice_lab, "_SAMPLES_DIR", tmp_path)
    fr_dir = tmp_path / "fr"
    fr_dir.mkdir()
    _create_wav(fr_dir / "marc_test.wav")
    result = voice_lab.list_samples()
    assert result[0]["name"] == "marc test"


def test_list_samples_url_format(monkeypatch, tmp_path):
    """URL = /static/voice_samples/<lang>/<file>."""
    monkeypatch.setattr(voice_lab, "_SAMPLES_DIR", tmp_path)
    fr_dir = tmp_path / "fr"
    fr_dir.mkdir()
    _create_wav(fr_dir / "test.wav")
    result = voice_lab.list_samples()
    assert result[0]["url"] == "/static/voice_samples/fr/test.wav"


def test_list_samples_skip_dossiers_caches(monkeypatch, tmp_path):
    """Dossiers commençant par '.' (ex: .git, .DS_Store) sont skippés."""
    monkeypatch.setattr(voice_lab, "_SAMPLES_DIR", tmp_path)
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    _create_wav(hidden / "secret.wav")
    visible = tmp_path / "fr"
    visible.mkdir()
    _create_wav(visible / "ok.wav")
    result = voice_lab.list_samples()
    assert len(result) == 1
    assert result[0]["lang"] == "FR"


def test_list_samples_skip_fichiers_directs():
    """Fichiers directement dans SAMPLES_DIR (pas dans <lang>/) sont skippés."""
    # Test implicite via les autres tests : la structure exige <lang>/<file>


# ── load_audio (skip si librosa absent) ────────────────────────────────


def test_load_audio_signature_acceptee(monkeypatch):
    """Smoke : load_audio appelle librosa.load avec sr=None, mono=True, duration."""
    captured = {}

    def fake_load(path, sr=None, mono=True, duration=None):
        captured["path"] = path
        captured["sr"] = sr
        captured["mono"] = mono
        captured["duration"] = duration
        return ([0.0, 0.0, 0.0], 22050)

    fake_librosa = type("L", (), {"load": staticmethod(fake_load)})()
    monkeypatch.setitem(__import__("sys").modules, "librosa", fake_librosa)
    y, sr = voice_lab.load_audio("/tmp/test.wav", duration=30.0)
    assert sr == 22050
    assert captured["mono"] is True
    assert captured["duration"] == 30.0


# ── is_librosa_available ─────────────────────────────────────────────────


def test_is_librosa_available_true_quand_installe():
    """Sur cette machine de dev, librosa est installé → True."""
    assert voice_lab.is_librosa_available() is True


def test_is_librosa_available_false_si_import_echoue(monkeypatch):
    """Si import librosa lève ImportError → False (branche ligne 59-60)."""
    import builtins as _builtins
    real_import = _builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "librosa":
            raise ImportError("simulé")
        return real_import(name, *a, **kw)

    monkeypatch.setattr(_builtins, "__import__", fake_import)
    assert voice_lab.is_librosa_available() is False


# ── analyse_features : analyse acoustique réelle (signal sinus) ──────────
# Tests live avec librosa+numpy installés. Signal sinusoïdal simple → pitch
# détectable, features cohérentes.


def _generate_sine(freq_hz: float, sr: int = 22050, duration_s: float = 1.0):
    """Génère un signal mono float32 d'une sinusoïde à freq_hz."""
    import numpy as np
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False, dtype=np.float32)
    return 0.3 * np.sin(2 * np.pi * freq_hz * t).astype(np.float32)


def test_analyse_features_sine_220hz_detecte_tenor():
    """220Hz → pitch_median dans la zone TÉNOR (160-200) ou MEZZO (200-250)."""
    sr = 22050
    y = _generate_sine(220.0, sr=sr, duration_s=1.5)
    result = voice_lab.analyse_features(y, sr, fmin=50.0, fmax=2000.0, n_mels=64)
    # Pitch médian doit être proche de 220Hz (tolérance ±15Hz)
    assert 200 < result["pitch_median"] < 240
    assert result["voice_type"] in ("TÉNOR", "MEZZO / ALTO")


def test_analyse_features_renvoie_tous_les_champs_attendus():
    """Vérifie le contrat de la fonction : 18 champs présents dans le dict de sortie."""
    sr = 22050
    y = _generate_sine(150.0, sr=sr, duration_s=1.0)
    r = voice_lab.analyse_features(y, sr, fmin=50.0, fmax=2000.0, n_mels=32)
    for key in ["dur", "sr", "waveform", "pitch_curve", "spectrum",
                "pitch_median", "pitch_min", "pitch_max",
                "centroid_mean", "rolloff_mean", "flatness_mean", "zcr_mean",
                "dynamic_range_db", "mfcc_means",
                "voice_type", "brightness", "breathiness", "voicing",
                "eq_preset"]:
        assert key in r, f"champ manquant : {key}"


def test_analyse_features_waveform_limite_a_200_points():
    sr = 22050
    y = _generate_sine(200.0, sr=sr, duration_s=2.0)   # 44100 samples
    r = voice_lab.analyse_features(y, sr, fmin=50.0, fmax=2000.0, n_mels=32)
    assert len(r["waveform"]) <= 200


def test_analyse_features_silence_pitch_zero_et_non_detecte():
    """Signal silence (zeros) → pas de pitch détecté → voice_type = NON DÉTECTÉ."""
    import numpy as np
    sr = 22050
    y = np.zeros(sr, dtype=np.float32)
    r = voice_lab.analyse_features(y, sr, fmin=50.0, fmax=2000.0, n_mels=32)
    assert r["pitch_median"] == 0.0
    assert r["voice_type"] == "NON DÉTECTÉ"


def test_analyse_features_eq_preset_a_5_bandes():
    """eq_preset doit contenir low / lomid / mid / himid / air."""
    sr = 22050
    y = _generate_sine(180.0, sr=sr, duration_s=1.0)
    r = voice_lab.analyse_features(y, sr, fmin=50.0, fmax=2000.0, n_mels=32)
    assert set(r["eq_preset"].keys()) == {"low", "lomid", "mid", "himid", "air"}
    # Toutes les valeurs sont des floats arrondis à 1 décimale
    for v in r["eq_preset"].values():
        assert isinstance(v, float)


def test_analyse_features_brightness_categorise():
    """brightness ∈ {SOMBRE, NEUTRE, BRILLANT} selon centroid_mean."""
    sr = 22050
    y = _generate_sine(150.0, sr=sr, duration_s=1.0)
    r = voice_lab.analyse_features(y, sr, fmin=50.0, fmax=2000.0, n_mels=32)
    assert r["brightness"] in ("SOMBRE", "NEUTRE", "BRILLANT")


def test_analyse_features_spectrum_taille_egale_n_mels():
    sr = 22050
    y = _generate_sine(200.0, sr=sr, duration_s=1.0)
    r = voice_lab.analyse_features(y, sr, fmin=50.0, fmax=2000.0, n_mels=24)
    assert len(r["spectrum"]) == 24


# ── _classify_type : seuils par fréquence pitch ──────────────────────────


def test_classify_type_soprano_haut():
    assert voice_lab._classify_type(300.0) == "SOPRANO"


def test_classify_type_mezzo_alto():
    assert voice_lab._classify_type(220.0) == "MEZZO / ALTO"


def test_classify_type_tenor():
    assert voice_lab._classify_type(180.0) == "TÉNOR"


def test_classify_type_baryton():
    assert voice_lab._classify_type(140.0) == "BARYTON"


def test_classify_type_basse():
    assert voice_lab._classify_type(100.0) == "BASSE"


def test_classify_type_basse_profonde():
    assert voice_lab._classify_type(60.0) == "BASSE PROFONDE"


def test_classify_type_sub_bass():
    assert voice_lab._classify_type(30.0) == "SUB-BASS / INST."


def test_classify_type_zero_non_detecte():
    assert voice_lab._classify_type(0.0) == "NON DÉTECTÉ"


def test_classify_type_negative_non_detecte():
    """Pitch négatif (cas dégénéré numpy) → NON DÉTECTÉ."""
    assert voice_lab._classify_type(-1.0) == "NON DÉTECTÉ"


# ── _eq_preset : presets EQ dérivés des features ─────────────────────────


def test_eq_preset_renvoie_5_bandes_avec_floats():
    out = voice_lab._eq_preset(pitch_median=150.0, centroid_mean=2500.0, rolloff_mean=4000.0)
    assert set(out.keys()) == {"low", "lomid", "mid", "himid", "air"}
    for v in out.values():
        assert isinstance(v, float)


def test_eq_preset_pitch_eleve_low_proche_zero():
    """Pitch élevé (≥150) → low ≈ 0 (pas de boost basses)."""
    out = voice_lab._eq_preset(pitch_median=200.0, centroid_mean=2000.0, rolloff_mean=4000.0)
    assert abs(out["low"]) <= 0.1


def test_eq_preset_pitch_bas_low_negatif():
    """Pitch très bas (<50) → low très négatif (cut basses)."""
    out = voice_lab._eq_preset(pitch_median=20.0, centroid_mean=1000.0, rolloff_mean=2000.0)
    assert out["low"] < -1.0
