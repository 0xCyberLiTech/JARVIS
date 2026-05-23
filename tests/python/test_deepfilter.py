"""Tests deepfilter — DeepFilterNet wrappers (mock torch + df.enhance)."""
import importlib

import numpy as np
from voice import deepfilter


def _reset_state():
    """Recharge le module pour reset state global entre tests."""
    importlib.reload(deepfilter)


# ── Constantes / state initial ──────────────────────────────────────────


def test_module_logger():
    assert deepfilter._log.name == "jarvis.deepfilter"


def test_df_sr_default_48000():
    """Sample rate par défaut : 48 kHz (standard DeepFilterNet)."""
    _reset_state()
    assert deepfilter._df_sr == 48000


def test_df_available_initial_false():
    """Avant load → not available."""
    _reset_state()
    assert deepfilter._DF_AVAILABLE is False


def test_df_load_done_initial_false():
    _reset_state()
    assert deepfilter._DF_LOAD_DONE is False


def test_df_model_initial_none():
    _reset_state()
    assert deepfilter._df_model is None


# ── get_status (sans force load) ────────────────────────────────────────


def test_get_status_avant_load_renvoie_false_zero():
    """get_status ne force PAS le load → renvoie state actuel."""
    _reset_state()
    available, sr = deepfilter.get_status()
    assert available is False
    assert sr == 0


def test_get_status_apres_charge_succes(monkeypatch):
    """Après chargement réussi → (True, 48000)."""
    _reset_state()
    deepfilter._DF_AVAILABLE = True
    deepfilter._df_sr = 48000
    available, sr = deepfilter.get_status()
    assert available is True
    assert sr == 48000


# ── _load (idempotent) ──────────────────────────────────────────────────


def test_load_marque_load_done_meme_si_echec(monkeypatch):
    """_load doit toujours mettre _DF_LOAD_DONE=True (success ou fail)."""
    _reset_state()
    # Force ImportError sur df.enhance
    import sys
    monkeypatch.setitem(sys.modules, "df.enhance", None)

    deepfilter._load()
    assert deepfilter._DF_LOAD_DONE is True


def test_load_idempotent(monkeypatch):
    """2e appel à _load ne refait pas le travail."""
    _reset_state()
    deepfilter._DF_LOAD_DONE = True
    captured = {"called": False}

    def fake_import(name, *args, **kwargs):
        if name == "df.enhance":
            captured["called"] = True
            raise ImportError()
        return __import__(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    deepfilter._load()
    assert captured["called"] is False


def test_load_succes_mock_complet(monkeypatch):
    """Mock complet df.enhance + torch → _DF_AVAILABLE=True."""
    _reset_state()

    class FakeDfState:
        def sr(self):
            return 48000

    fake_df_state = FakeDfState()
    fake_model = "FAKE_MODEL"
    fake_enhance = lambda m, s, t: t  # noqa: E731

    fake_df_module = type("DF", (), {
        "enhance": fake_enhance,
        "init_df": staticmethod(lambda: (fake_model, fake_df_state, None)),
    })()

    fake_torch = type("T", (), {"from_numpy": staticmethod(lambda x: x)})()

    import sys
    monkeypatch.setitem(sys.modules, "df.enhance", fake_df_module)
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    deepfilter._load()
    assert deepfilter._DF_AVAILABLE is True
    assert deepfilter._df_sr == 48000
    assert deepfilter._df_model is not None


# ── is_available (force load lazy) ──────────────────────────────────────


def test_is_available_force_load(monkeypatch):
    """is_available appelle _load() si pas encore tenté."""
    _reset_state()
    captured = {"called": False}

    def fake_load():
        captured["called"] = True
        deepfilter._DF_LOAD_DONE = True

    monkeypatch.setattr(deepfilter, "_load", fake_load)
    deepfilter.is_available()
    assert captured["called"] is True


def test_is_available_skip_load_si_deja_done(monkeypatch):
    _reset_state()
    deepfilter._DF_LOAD_DONE = True
    deepfilter._DF_AVAILABLE = True
    captured = {"called": False}

    def fake_load():
        captured["called"] = True

    monkeypatch.setattr(deepfilter, "_load", fake_load)
    result = deepfilter.is_available()
    assert captured["called"] is False
    assert result is True


# ── enhance_audio ───────────────────────────────────────────────────────


def test_enhance_audio_indispo_renvoie_signal_original(monkeypatch):
    """Si DeepFilterNet pas dispo → retourne le signal original (no-op safe)."""
    _reset_state()
    deepfilter._DF_LOAD_DONE = True
    deepfilter._DF_AVAILABLE = False
    deepfilter._df_model = None

    audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    out = deepfilter.enhance_audio(audio, sr=44100)
    np.testing.assert_array_equal(out, audio)


def test_enhance_audio_force_load_si_pas_charge(monkeypatch):
    """enhance_audio appelle _load() si pas encore tenté."""
    _reset_state()
    captured = {"called": False}

    def fake_load():
        captured["called"] = True
        deepfilter._DF_LOAD_DONE = True
        deepfilter._DF_AVAILABLE = False

    monkeypatch.setattr(deepfilter, "_load", fake_load)
    deepfilter.enhance_audio(np.array([0.1], dtype=np.float32), sr=48000)
    assert captured["called"] is True


def test_enhance_audio_succes_meme_sample_rate(monkeypatch):
    """Audio à 48 kHz (= _df_sr) → pas de resampling, juste enhance."""
    _reset_state()
    deepfilter._DF_LOAD_DONE = True
    deepfilter._DF_AVAILABLE = True
    deepfilter._df_sr = 48000

    # Mock model + state + enhance
    captured = {"enhance_called": False}

    def fake_enhance(model, state, tensor):
        captured["enhance_called"] = True
        return tensor

    deepfilter._df_model = ("MODEL", "STATE", fake_enhance)

    # Mock torch
    class FakeTensor:
        def __init__(self, arr):
            self.arr = arr

        def unsqueeze(self, dim):
            return self  # ignore

        def squeeze(self, dim):
            return self

        def numpy(self):
            return self.arr

    fake_torch = type("T", (), {"from_numpy": staticmethod(lambda a: FakeTensor(a))})()
    deepfilter._torch = fake_torch

    audio = np.zeros(1000, dtype=np.float32)
    out = deepfilter.enhance_audio(audio, sr=48000)
    assert len(out) == 1000  # même longueur
    assert captured["enhance_called"] is True


def test_enhance_audio_off_by_one_correction_pad(monkeypatch):
    """Si la sortie est plus courte que orig → padding."""
    _reset_state()
    deepfilter._DF_LOAD_DONE = True
    deepfilter._DF_AVAILABLE = True
    deepfilter._df_sr = 48000

    # Le mock enhance retourne un signal raccourci de 1 sample
    class FakeTensor:
        def __init__(self, arr):
            self.arr = arr[:-1] if len(arr) > 1 else arr  # raccourci

        def unsqueeze(self, dim):
            return self

        def squeeze(self, dim):
            return self

        def numpy(self):
            return self.arr

    fake_torch = type("T", (), {"from_numpy": staticmethod(lambda a: FakeTensor(a))})()
    deepfilter._torch = fake_torch
    deepfilter._df_model = ("M", "S", lambda m, s, t: t)

    audio = np.zeros(1000, dtype=np.float32)
    out = deepfilter.enhance_audio(audio, sr=48000)
    # Le padding doit ramener à 1000 samples
    assert len(out) == 1000


def test_enhance_audio_exception_renvoie_original(monkeypatch):
    """Si enhance lève → log + retourne le signal original."""
    _reset_state()
    deepfilter._DF_LOAD_DONE = True
    deepfilter._DF_AVAILABLE = True

    def crash_enhance(*args):
        raise RuntimeError("enhance crashed")

    deepfilter._df_model = ("M", "S", crash_enhance)
    deepfilter._torch = type("T", (), {"from_numpy": staticmethod(lambda a: a)})()

    audio = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    out = deepfilter.enhance_audio(audio, sr=48000)
    np.testing.assert_array_equal(out, audio)


def test_enhance_audio_dtype_float32_preserve(monkeypatch):
    """Le retour doit être float32 (pas float64)."""
    _reset_state()
    deepfilter._DF_LOAD_DONE = True
    deepfilter._DF_AVAILABLE = True
    deepfilter._df_sr = 48000

    class FakeTensor:
        def __init__(self, arr):
            self.arr = arr.astype(np.float64)  # simule float64

        def unsqueeze(self, d):
            return self

        def squeeze(self, d):
            return self

        def numpy(self):
            return self.arr

    deepfilter._torch = type("T", (), {"from_numpy": staticmethod(lambda a: FakeTensor(a))})()
    deepfilter._df_model = ("M", "S", lambda m, s, t: t)

    audio = np.zeros(100, dtype=np.float32)
    out = deepfilter.enhance_audio(audio, sr=48000)
    assert out.dtype == np.float32
