"""Tests tts_engines — 4 engines TTS (edge-tts/Kokoro/Piper/SAPI5) mockés."""
import importlib
from collections import OrderedDict
from unittest.mock import MagicMock

from voice import tts_engines


def _reset_state():
    importlib.reload(tts_engines)


# ── Constantes ──────────────────────────────────────────────────────────


def test_module_logger():
    assert tts_engines._log.name == "jarvis.tts_engines"


def test_edge_default_voice_fr_ca():
    assert tts_engines.EDGE_DEFAULT_VOICE == "fr-CA-AntoineNeural"


def test_kokoro_default_voice_ff_siwis():
    assert tts_engines._KOKORO_DEFAULT_VOICE == "ff_siwis"


def test_piper_max_models_3():
    assert tts_engines._PIPER_MAX_MODELS == 3


def test_kokoro_valid_prefixes():
    assert tts_engines._KOKORO_VALID_PREFIXES == ("ff_", "fm_", "af_", "am_", "bf_", "bm_")


def test_voices_dir_existe():
    assert tts_engines.VOICES_DIR.exists()


# ── _normalize_kokoro_voice ─────────────────────────────────────────────


def test_normalize_kokoro_voice_valide_passe():
    assert tts_engines._normalize_kokoro_voice("ff_siwis") == "ff_siwis"
    assert tts_engines._normalize_kokoro_voice("am_alex") == "am_alex"
    assert tts_engines._normalize_kokoro_voice("bf_emma") == "bf_emma"


def test_normalize_kokoro_voice_invalide_fallback():
    assert tts_engines._normalize_kokoro_voice("xx_unknown") == "ff_siwis"
    assert tts_engines._normalize_kokoro_voice("") == "ff_siwis"
    assert tts_engines._normalize_kokoro_voice("ab") == "ff_siwis"


def test_normalize_kokoro_voice_none():
    assert tts_engines._normalize_kokoro_voice(None) == "ff_siwis"


# ── is_*_available ──────────────────────────────────────────────────────


def test_is_kokoro_available_initial_none():
    _reset_state()
    assert tts_engines.is_kokoro_available() is None


def test_is_kokoro_available_apres_set_true():
    _reset_state()
    tts_engines._KOKORO_AVAILABLE = True
    assert tts_engines.is_kokoro_available() is True


def test_is_piper_available_renvoie_bool():
    assert isinstance(tts_engines.is_piper_available(), bool)


def test_is_sapi_available_renvoie_bool():
    assert isinstance(tts_engines.is_sapi_available(), bool)


# ── list_piper_models ───────────────────────────────────────────────────


def test_list_piper_models_renvoie_liste(tmp_path, monkeypatch):
    """Crée 2 .onnx valides + 1 sans .onnx.json (ignoré)."""
    monkeypatch.setattr(tts_engines, "VOICES_DIR", tmp_path)
    (tmp_path / "voice_a.onnx").write_bytes(b"x")
    (tmp_path / "voice_a.onnx.json").write_text("{}")
    (tmp_path / "voice_b.onnx").write_bytes(b"x")
    (tmp_path / "voice_b.onnx.json").write_text("{}")
    (tmp_path / "voice_c.onnx").write_bytes(b"x")  # pas de .onnx.json
    models = tts_engines.list_piper_models()
    assert "voice_a" in models
    assert "voice_b" in models
    assert "voice_c" not in models


def test_list_piper_models_dossier_vide(tmp_path, monkeypatch):
    monkeypatch.setattr(tts_engines, "VOICES_DIR", tmp_path)
    assert tts_engines.list_piper_models() == []


# ── list_sapi_voices ────────────────────────────────────────────────────


def test_list_sapi_voices_indispo_retourne_liste_vide(monkeypatch):
    monkeypatch.setattr(tts_engines, "_PYTTSX3_AVAILABLE", False)
    assert tts_engines.list_sapi_voices() == []


def test_list_sapi_voices_dispo_retourne_voix(monkeypatch):
    monkeypatch.setattr(tts_engines, "_PYTTSX3_AVAILABLE", True)
    fake_voice = MagicMock()
    fake_voice.id = "fr_id"
    fake_voice.name = "Hortense"
    fake_engine = MagicMock()
    fake_engine.getProperty.return_value = [fake_voice]
    fake_pyttsx3 = MagicMock()
    fake_pyttsx3.init.return_value = fake_engine
    monkeypatch.setattr(tts_engines, "_pyttsx3", fake_pyttsx3)
    voices = tts_engines.list_sapi_voices()
    assert voices == [{"id": "fr_id", "name": "Hortense"}]


def test_list_sapi_voices_exception_retourne_vide(monkeypatch):
    monkeypatch.setattr(tts_engines, "_PYTTSX3_AVAILABLE", True)
    fake_pyttsx3 = MagicMock()
    fake_pyttsx3.init.side_effect = Exception("init failed")
    monkeypatch.setattr(tts_engines, "_pyttsx3", fake_pyttsx3)
    assert tts_engines.list_sapi_voices() == []


# ── _get_piper_model ────────────────────────────────────────────────────


def test_get_piper_model_introuvable_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(tts_engines, "VOICES_DIR", tmp_path)
    monkeypatch.setattr(tts_engines, "_piper_models", OrderedDict())
    try:
        tts_engines._get_piper_model("inconnu")
    except FileNotFoundError as e:
        assert "introuvable" in str(e)


def test_get_piper_model_charge_et_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(tts_engines, "VOICES_DIR", tmp_path)
    onnx = tmp_path / "v1.onnx"
    onnx.write_bytes(b"x")
    cache = OrderedDict()
    monkeypatch.setattr(tts_engines, "_piper_models", cache)
    fake_voice_obj = MagicMock(name="PiperVoiceLoaded")
    fake_piper = MagicMock()
    fake_piper.load.return_value = fake_voice_obj
    monkeypatch.setattr(tts_engines, "_PiperVoice", fake_piper)
    result = tts_engines._get_piper_model("v1")
    assert result is fake_voice_obj
    assert "v1" in tts_engines._piper_models


def test_get_piper_model_cache_hit_pas_de_reload(tmp_path, monkeypatch):
    """2e appel : pas de chargement, juste move_to_end."""
    monkeypatch.setattr(tts_engines, "VOICES_DIR", tmp_path)
    cache = OrderedDict()
    sentinel = MagicMock(name="cached_voice")
    cache["already"] = sentinel
    monkeypatch.setattr(tts_engines, "_piper_models", cache)
    fake_piper = MagicMock()
    monkeypatch.setattr(tts_engines, "_PiperVoice", fake_piper)
    result = tts_engines._get_piper_model("already")
    assert result is sentinel
    fake_piper.load.assert_not_called()


def test_get_piper_model_lru_eviction(tmp_path, monkeypatch):
    """Quand cache > _PIPER_MAX_MODELS → eviction du plus ancien."""
    monkeypatch.setattr(tts_engines, "VOICES_DIR", tmp_path)
    monkeypatch.setattr(tts_engines, "_PIPER_MAX_MODELS", 2)
    cache = OrderedDict()
    cache["old1"] = MagicMock()
    cache["old2"] = MagicMock()
    monkeypatch.setattr(tts_engines, "_piper_models", cache)
    (tmp_path / "new.onnx").write_bytes(b"x")
    fake_piper = MagicMock()
    fake_piper.load.return_value = MagicMock()
    monkeypatch.setattr(tts_engines, "_PiperVoice", fake_piper)
    tts_engines._get_piper_model("new")
    assert "old1" not in tts_engines._piper_models
    assert "old2" in tts_engines._piper_models
    assert "new" in tts_engines._piper_models


# ── _get_kokoro ─────────────────────────────────────────────────────────


def test_get_kokoro_import_failure_set_unavailable(monkeypatch):
    """Si import KPipeline échoue → _KOKORO_AVAILABLE=False, retourne None."""
    _reset_state()
    import sys
    monkeypatch.setitem(sys.modules, "kokoro", None)
    result = tts_engines._get_kokoro("f")
    assert result is None
    assert tts_engines._KOKORO_AVAILABLE is False


def test_get_kokoro_deja_unavailable(monkeypatch):
    """Si _KOKORO_AVAILABLE=False → retourne None directement."""
    _reset_state()
    tts_engines._KOKORO_AVAILABLE = False
    assert tts_engines._get_kokoro("f") is None


def test_get_kokoro_pipeline_existant(monkeypatch):
    """Si _kokoro_pipeline déjà chargé → retourne sans recharger."""
    _reset_state()
    sentinel = MagicMock(name="pipeline")
    tts_engines._KOKORO_AVAILABLE = True
    tts_engines._kokoro_pipeline = sentinel
    assert tts_engines._get_kokoro("f") is sentinel


# ── kokoro_synth ────────────────────────────────────────────────────────


def test_kokoro_synth_indisponible_raise(monkeypatch):
    """Si Kokoro pipeline est None → RuntimeError."""
    _reset_state()
    monkeypatch.setattr(tts_engines, "_get_kokoro", lambda lang="f": None)
    try:
        tts_engines.kokoro_synth("hello")
        raise AssertionError("attendu RuntimeError")
    except RuntimeError as e:
        assert "non disponible" in str(e)


def test_kokoro_synth_aucun_audio_raise(monkeypatch):
    """Si pipeline ne produit aucun chunk → RuntimeError."""
    _reset_state()
    fake_pipe = MagicMock(return_value=iter([]))
    monkeypatch.setattr(tts_engines, "_get_kokoro", lambda lang="f": fake_pipe)
    try:
        tts_engines.kokoro_synth("hello")
        raise AssertionError("attendu RuntimeError")
    except RuntimeError as e:
        assert "aucun audio" in str(e)


def test_kokoro_synth_pipeline_exception_reset(monkeypatch):
    """Pipeline qui raise → reset du _kokoro_pipeline + propagation."""
    _reset_state()
    fake_pipe = MagicMock(side_effect=ValueError("boom"))
    tts_engines._kokoro_pipeline = MagicMock()
    monkeypatch.setattr(tts_engines, "_get_kokoro", lambda lang="f": fake_pipe)
    try:
        tts_engines.kokoro_synth("hello")
        raise AssertionError("attendu ValueError")
    except ValueError:
        pass
    assert tts_engines._kokoro_pipeline is None


def test_kokoro_synth_succes(monkeypatch):
    """Pipeline qui produit audio → bytes WAV non vide."""
    _reset_state()
    import numpy as _np
    fake_audio = _np.zeros(1000, dtype=_np.float32)
    fake_pipe = MagicMock(return_value=iter([(None, None, fake_audio)]))
    monkeypatch.setattr(tts_engines, "_get_kokoro", lambda lang="f": fake_pipe)
    monkeypatch.setattr(tts_engines, "_np_kokoro", _np)
    fake_sf = MagicMock()
    def _write(buf, data, sr, format=None, subtype=None):
        buf.write(b"RIFF" + b"\x00" * 100)
    fake_sf.write.side_effect = _write
    monkeypatch.setattr(tts_engines, "_sf", fake_sf)
    result = tts_engines.kokoro_synth("hello", voice="ff_siwis", speed=1.0)
    assert isinstance(result, bytes)
    assert result.startswith(b"RIFF")


def test_kokoro_synth_speed_clamped(monkeypatch):
    """speed > 2.0 doit être clampé à 2.0."""
    _reset_state()
    captured = {}
    def _fake_pipe(text, voice=None, speed=None):
        captured["speed"] = speed
        return iter([])
    monkeypatch.setattr(tts_engines, "_get_kokoro", lambda lang="f": _fake_pipe)
    try:
        tts_engines.kokoro_synth("x", speed=5.0)
    except RuntimeError:
        pass  # on ignore l'erreur "aucun audio", on veut juste vérifier le clamp
    assert captured["speed"] == 2.0


def test_kokoro_synth_speed_min_clamped(monkeypatch):
    """speed < 0.5 doit être clampé à 0.5."""
    _reset_state()
    captured = {}
    def _fake_pipe(text, voice=None, speed=None):
        captured["speed"] = speed
        return iter([])
    monkeypatch.setattr(tts_engines, "_get_kokoro", lambda lang="f": _fake_pipe)
    try:
        tts_engines.kokoro_synth("x", speed=0.1)
    except RuntimeError:
        pass
    assert captured["speed"] == 0.5


# ── piper_synth ─────────────────────────────────────────────────────────


def test_piper_synth_aucun_modele_raise(monkeypatch):
    monkeypatch.setattr(tts_engines, "list_piper_models", lambda: [])
    try:
        tts_engines.piper_synth("hello")
        raise AssertionError("attendu RuntimeError")
    except RuntimeError as e:
        assert "Aucun modèle" in str(e)


def test_piper_synth_succes(tmp_path, monkeypatch):
    """Avec modèle valide → bytes WAV produit."""
    monkeypatch.setattr(tts_engines, "VOICES_DIR", tmp_path)
    (tmp_path / "v1.onnx").write_bytes(b"x")
    monkeypatch.setattr(tts_engines, "list_piper_models", lambda: ["v1"])
    fake_chunk = MagicMock()
    fake_chunk.sample_channels = 1
    fake_chunk.sample_width = 2
    fake_chunk.sample_rate = 22050
    fake_chunk.audio_int16_bytes = b"\x00\x00" * 100
    fake_voice_obj = MagicMock()
    fake_voice_obj.synthesize.return_value = iter([fake_chunk])
    monkeypatch.setattr(tts_engines, "_get_piper_model", lambda name: fake_voice_obj)
    result = tts_engines.piper_synth("hello", model_name="v1")
    assert isinstance(result, bytes)
    assert result.startswith(b"RIFF")


def test_piper_synth_modele_inexistant_fallback_premier(tmp_path, monkeypatch):
    """Si model_name fourni mais introuvable → fallback premier dispo."""
    monkeypatch.setattr(tts_engines, "VOICES_DIR", tmp_path)
    (tmp_path / "v1.onnx").write_bytes(b"x")
    monkeypatch.setattr(tts_engines, "list_piper_models", lambda: ["v1"])
    captured = {}
    def _get(name):
        captured["name"] = name
        m = MagicMock()
        ch = MagicMock()
        ch.sample_channels = 1
        ch.sample_width = 2
        ch.sample_rate = 22050
        ch.audio_int16_bytes = b"\x00\x00"
        m.synthesize.return_value = iter([ch])
        return m
    monkeypatch.setattr(tts_engines, "_get_piper_model", _get)
    tts_engines.piper_synth("hi", model_name="inexistant")
    assert captured["name"] == "v1"


def test_piper_synth_aucun_chunk_raise(tmp_path, monkeypatch):
    monkeypatch.setattr(tts_engines, "VOICES_DIR", tmp_path)
    (tmp_path / "v1.onnx").write_bytes(b"x")
    monkeypatch.setattr(tts_engines, "list_piper_models", lambda: ["v1"])
    fake_voice_obj = MagicMock()
    fake_voice_obj.synthesize.return_value = iter([])
    monkeypatch.setattr(tts_engines, "_get_piper_model", lambda name: fake_voice_obj)
    try:
        tts_engines.piper_synth("hi")
        raise AssertionError("attendu RuntimeError")
    except RuntimeError as e:
        assert "aucun audio" in str(e)


# ── sapi5_synth ─────────────────────────────────────────────────────────


def test_sapi5_synth_succes(monkeypatch, tmp_path):
    monkeypatch.setattr(tts_engines, "_PYTTSX3_AVAILABLE", False)
    fake_wav = tmp_path / "out.wav"
    fake_wav.write_bytes(b"RIFF" + b"\x00" * 200)
    monkeypatch.setattr(tts_engines.tempfile, "mkstemp",
                        lambda suffix=None: (0, str(fake_wav)))
    monkeypatch.setattr(tts_engines.os, "close", lambda fd: None)
    fake_run = MagicMock()
    fake_run.returncode = 0
    fake_run.stderr = ""
    monkeypatch.setattr(tts_engines.subprocess, "run", lambda *a, **kw: fake_run)
    result = tts_engines.sapi5_synth("hello")
    assert isinstance(result, bytes)
    assert result.startswith(b"RIFF")


def test_sapi5_synth_powershell_fail_raise(monkeypatch, tmp_path):
    monkeypatch.setattr(tts_engines, "_PYTTSX3_AVAILABLE", False)
    fake_wav = tmp_path / "out.wav"
    fake_wav.write_bytes(b"")  # < 100 bytes
    monkeypatch.setattr(tts_engines.tempfile, "mkstemp",
                        lambda suffix=None: (0, str(fake_wav)))
    monkeypatch.setattr(tts_engines.os, "close", lambda fd: None)
    fake_run = MagicMock()
    fake_run.returncode = 1
    fake_run.stderr = "ps error"
    monkeypatch.setattr(tts_engines.subprocess, "run", lambda *a, **kw: fake_run)
    try:
        tts_engines.sapi5_synth("hi")
        raise AssertionError("attendu RuntimeError")
    except RuntimeError as e:
        assert "PS SAPI" in str(e)


def test_sapi5_synth_voice_id_resolu(monkeypatch, tmp_path):
    """Avec voice_id fourni + pyttsx3 dispo → SelectVoice par nom."""
    monkeypatch.setattr(tts_engines, "_PYTTSX3_AVAILABLE", True)
    fake_voice = MagicMock()
    fake_voice.id = "TARGET_ID"
    fake_voice.name = "Hortense"
    fake_engine = MagicMock()
    fake_engine.getProperty.return_value = [fake_voice]
    fake_pyttsx3 = MagicMock()
    fake_pyttsx3.init.return_value = fake_engine
    monkeypatch.setattr(tts_engines, "_pyttsx3", fake_pyttsx3)
    fake_wav = tmp_path / "out.wav"
    fake_wav.write_bytes(b"RIFF" + b"\x00" * 200)
    monkeypatch.setattr(tts_engines.tempfile, "mkstemp",
                        lambda suffix=None: (0, str(fake_wav)))
    monkeypatch.setattr(tts_engines.os, "close", lambda fd: None)
    captured = {}
    def _run(args, **kw):
        captured["cmd"] = args
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        return m
    monkeypatch.setattr(tts_engines.subprocess, "run", _run)
    tts_engines.sapi5_synth("hi", voice_id="TARGET_ID")
    cmd_str = " ".join(captured["cmd"])
    assert "Hortense" in cmd_str


# ── edge_generate_mp3 ───────────────────────────────────────────────────


def test_edge_generate_mp3_succes_premier_essai(monkeypatch, tmp_path):
    """Si _edge_tts_async réussit du 1er coup → retourne le path."""
    expected_path = str(tmp_path / "out.mp3")
    async def _fake_async(text, voice=None):
        return expected_path
    monkeypatch.setattr(tts_engines, "_edge_tts_async", _fake_async)
    result = tts_engines.edge_generate_mp3("hello")
    assert result == expected_path


def test_edge_generate_mp3_retry_apres_echec(monkeypatch, tmp_path):
    """1er essai échoue, 2e réussit → retry fonctionne."""
    expected_path = str(tmp_path / "out2.mp3")
    counter = {"n": 0}
    async def _fake_async(text, voice=None):
        counter["n"] += 1
        if counter["n"] == 1:
            raise RuntimeError("transient")
        return expected_path
    monkeypatch.setattr(tts_engines, "_edge_tts_async", _fake_async)
    monkeypatch.setattr(tts_engines.time, "sleep", lambda s: None)
    result = tts_engines.edge_generate_mp3("hello")
    assert result == expected_path
    assert counter["n"] == 2


def test_edge_generate_mp3_3_echecs_raise(monkeypatch):
    """3 échecs consécutifs → raise la dernière exception."""
    counter = {"n": 0}
    async def _fake_async(text, voice=None):
        counter["n"] += 1
        raise RuntimeError(f"err {counter['n']}")
    monkeypatch.setattr(tts_engines, "_edge_tts_async", _fake_async)
    monkeypatch.setattr(tts_engines.time, "sleep", lambda s: None)
    try:
        tts_engines.edge_generate_mp3("x")
        raise AssertionError("attendu RuntimeError")
    except RuntimeError as e:
        assert "err 3" in str(e)
    assert counter["n"] == 3


def test_edge_generate_mp3_dns_delay_specifique(monkeypatch):
    """Erreur 'getaddrinfo' → délai _EDGE_DNS_RETRY_S (1.0s)."""
    sleeps = []
    monkeypatch.setattr(tts_engines.time, "sleep", lambda s: sleeps.append(s))
    counter = {"n": 0}
    async def _fake_async(text, voice=None):
        counter["n"] += 1
        if counter["n"] < 3:
            raise OSError("getaddrinfo failed")
        return "/tmp/x"
    monkeypatch.setattr(tts_engines, "_edge_tts_async", _fake_async)
    tts_engines.edge_generate_mp3("x")
    assert tts_engines._EDGE_DNS_RETRY_S in sleeps
