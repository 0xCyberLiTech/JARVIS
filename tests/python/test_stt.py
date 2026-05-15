"""Tests stt — wrappers Whisper (faster-whisper) avec mock complet."""
import importlib

import stt


def _reset_state():
    """Reset state module-level entre tests pour le lazy loading."""
    importlib.reload(stt)


# ── Constantes ────────────────────────────────────────────────────────────


def test_whisper_model_size_large_v3_turbo():
    assert stt._WHISPER_MODEL_SIZE == "large-v3-turbo"


def test_stt_initial_prompt_contient_vocabulaire_soc():
    """Le initial_prompt doit injecter le vocabulaire SOC pour améliorer la reconnaissance."""
    for term in ["CrowdSec", "fail2ban", "Suricata", "Proxmox", "JARVIS", "Ollama"]:
        assert term in stt._STT_INITIAL_PROMPT


def test_stt_max_bytes_25mb():
    assert stt._STT_MAX_BYTES == 25_000_000


def test_stt_allowed_ext_couvre_formats_courants():
    """Sanity : les formats audio courants sont autorisés."""
    for ext in ["wav", "mp3", "ogg", "flac", "webm", "m4a", "opus"]:
        assert ext in stt._STT_ALLOWED_EXT


def test_module_logger():
    assert stt._log.name == "jarvis.stt"


# ── API publique : getters ──────────────────────────────────────────────


def test_get_model_size():
    assert stt.get_model_size() == "large-v3-turbo"


def test_get_max_bytes():
    assert stt.get_max_bytes() == 25_000_000


def test_get_allowed_ext_renvoie_set():
    assert isinstance(stt.get_allowed_ext(), set)
    assert "wav" in stt.get_allowed_ext()


# ── is_loaded / is_available avant chargement ──────────────────────────


def test_is_loaded_false_au_demarrage():
    """Avant tout chargement → False."""
    _reset_state()
    assert stt.is_loaded() is False


def test_is_available_none_au_demarrage():
    """Avant tout test, _WHISPER_AVAILABLE = None (pas testé)."""
    _reset_state()
    assert stt.is_available() is None


# ── _get_whisper avec mock faster_whisper ──────────────────────────────


def test_get_whisper_succes_avec_mock(monkeypatch):
    """Mock faster_whisper.WhisperModel → _get_whisper renvoie l'instance mockée."""
    _reset_state()

    class FakeWhisperModel:
        def __init__(self, model_size, device, compute_type):
            self.model_size = model_size
            self.device = device
            self.compute_type = compute_type

    fake_module = type("FW", (), {"WhisperModel": FakeWhisperModel})()
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", fake_module)

    # Mock ctranslate2 pour forcer device=cpu (sans CUDA)
    fake_ct2 = type("CT", (), {"get_cuda_device_count": staticmethod(lambda: 0)})()
    monkeypatch.setitem(__import__("sys").modules, "ctranslate2", fake_ct2)

    model = stt._get_whisper()
    assert model is not None
    assert model.model_size == "large-v3-turbo"
    assert model.device == "cpu"
    assert model.compute_type == "int8"
    assert stt.is_loaded() is True
    assert stt.is_available() is True


def test_get_whisper_import_error_renvoie_none(monkeypatch):
    """Si faster_whisper non installé → _get_whisper renvoie None + _WHISPER_AVAILABLE=False."""
    _reset_state()
    # Forcer ImportError sur faster_whisper
    import sys
    monkeypatch.delitem(sys.modules, "faster_whisper", raising=False)
    original_import = __builtins__["__import__"] if isinstance(__builtins__, dict) else __builtins__.__import__

    def fake_import(name, *args, **kwargs):
        if name == "faster_whisper":
            raise ImportError("not installed")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    model = stt._get_whisper()
    assert model is None
    assert stt.is_available() is False


def test_get_whisper_idempotent_si_deja_charge(monkeypatch):
    """2e appel à _get_whisper → renvoie la même instance (lazy + cache)."""
    _reset_state()

    instances = []

    class FakeWhisperModel:
        def __init__(self, *args, **kwargs):
            instances.append(self)

    fake_module = type("FW", (), {"WhisperModel": FakeWhisperModel})()
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", fake_module)
    fake_ct2 = type("CT", (), {"get_cuda_device_count": staticmethod(lambda: 0)})()
    monkeypatch.setitem(__import__("sys").modules, "ctranslate2", fake_ct2)

    m1 = stt._get_whisper()
    m2 = stt._get_whisper()
    assert m1 is m2
    assert len(instances) == 1  # WhisperModel construit UNE seule fois


def test_get_whisper_device_cuda_si_dispo(monkeypatch):
    """Si CUDA dispo (device count > 0) → device='cuda'."""
    _reset_state()

    class FakeWhisperModel:
        def __init__(self, model_size, device, compute_type):
            self.device = device

    fake_module = type("FW", (), {"WhisperModel": FakeWhisperModel})()
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", fake_module)
    fake_ct2 = type("CT", (), {"get_cuda_device_count": staticmethod(lambda: 1)})()
    monkeypatch.setitem(__import__("sys").modules, "ctranslate2", fake_ct2)

    model = stt._get_whisper()
    assert model.device == "cuda"


def test_get_whisper_ctranslate2_exception_fallback_cpu(monkeypatch):
    """Si ctranslate2 lève → fallback device='cpu'."""
    _reset_state()

    class FakeWhisperModel:
        def __init__(self, model_size, device, compute_type):
            self.device = device

    fake_module = type("FW", (), {"WhisperModel": FakeWhisperModel})()
    monkeypatch.setitem(__import__("sys").modules, "faster_whisper", fake_module)

    class CrashCt2:
        @staticmethod
        def get_cuda_device_count():
            raise RuntimeError("ctranslate2 broken")

    monkeypatch.setitem(__import__("sys").modules, "ctranslate2", CrashCt2())
    model = stt._get_whisper()
    assert model.device == "cpu"


# ── transcribe ──────────────────────────────────────────────────────────


def test_transcribe_whisper_indispo_leve_runtime_error(monkeypatch):
    """Si _get_whisper retourne None → RuntimeError (faster-whisper non installé)."""
    _reset_state()
    monkeypatch.setattr(stt, "_get_whisper", lambda: None)

    import pytest
    with pytest.raises(RuntimeError) as exc_info:
        stt.transcribe("/tmp/test.wav")
    assert "faster-whisper non installé" in str(exc_info.value)


def test_transcribe_appelle_modele_avec_initial_prompt(monkeypatch):
    """transcribe doit passer initial_prompt + lang + beam_size + vad_filter au modèle."""
    _reset_state()
    captured = {}

    class FakeSegment:
        def __init__(self, text):
            self.text = text

    class FakeInfo:
        language = "fr"

    def fake_transcribe(path, language=None, beam_size=None, vad_filter=None, initial_prompt=None):
        captured["path"] = path
        captured["language"] = language
        captured["beam_size"] = beam_size
        captured["vad_filter"] = vad_filter
        captured["initial_prompt"] = initial_prompt
        return ([FakeSegment("Bonjour"), FakeSegment("Marc")], FakeInfo())

    fake_model = type("FM", (), {"transcribe": staticmethod(fake_transcribe)})()
    monkeypatch.setattr(stt, "_get_whisper", lambda: fake_model)

    text, lang = stt.transcribe("/audio/test.wav", lang="fr")
    assert text == "Bonjour Marc"
    assert lang == "fr"
    assert captured["beam_size"] == 2
    assert captured["vad_filter"] is True
    assert captured["initial_prompt"] == stt._STT_INITIAL_PROMPT


def test_transcribe_concatene_segments_avec_strip():
    """transcribe doit strip et concaténer les segments avec un espace."""
    _reset_state()

    class FakeSegment:
        def __init__(self, text):
            self.text = text

    class FakeInfo:
        language = "en"

    def fake_transcribe(path, **kwargs):
        return (
            [FakeSegment("  hello   "), FakeSegment("world  ")],
            FakeInfo(),
        )

    import pytest
    monkeypatch_attr = pytest.MonkeyPatch()
    fake_model = type("FM", (), {"transcribe": staticmethod(fake_transcribe)})()
    monkeypatch_attr.setattr(stt, "_get_whisper", lambda: fake_model)

    try:
        text, lang = stt.transcribe("/audio/test.wav", lang="en")
        assert text == "hello world"
        assert lang == "en"
    finally:
        monkeypatch_attr.undo()
