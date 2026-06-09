"""Tests routes HTTP voice — cas non couverts par test_jarvis_routes.py.

Cible voice/routes.py (36% → cible ≥50%).
Utilise jm.app.test_client() (application complète, JARVIS_SKIP_BOOT_THREADS=1)
avec monkeypatch ciblé sur les fonctions qui causent des effets de bord réels.
"""
import json
import queue
from unittest.mock import MagicMock, patch

import jarvis as jm
import pytest
import voice.routes as vr


@pytest.fixture(scope="module")
def client():
    jm.app.testing = True
    return jm.app.test_client()


# ── POST /api/speak — avec texte (lignes 151-155) ────────────────────────

def test_api_speak_avec_texte_appelle_speak_fn(client, monkeypatch):
    """api_speak avec texte → speak_fn appelée, log TTS, réponse 200."""
    called = {"n": 0}
    monkeypatch.setattr(vr, "_speak_fn", lambda txt, blocking=False: called.__setitem__("n", called["n"] + 1))
    logger_mock = MagicMock()
    monkeypatch.setattr(vr, "_tts_logger", logger_mock)
    rv = client.post("/api/speak", json={"text": "bonjour JARVIS"})
    assert rv.status_code == 200
    assert called["n"] == 1
    logger_mock.info.assert_called_once()


def test_api_speak_sans_texte_ne_pas_appeler_speak_fn(client, monkeypatch):
    """api_speak sans texte → speak_fn NON appelée."""
    called = {"n": 0}
    monkeypatch.setattr(vr, "_speak_fn", lambda txt, blocking=False: called.__setitem__("n", 1))
    rv = client.post("/api/speak", json={})
    assert rv.status_code == 200
    assert called["n"] == 0


# ── POST /api/speak/stop — drainages queues (lignes 162-177) ─────────────

def test_api_speak_stop_draine_queues(client, monkeypatch):
    """api_speak_stop draine les 2 queues + appelle WinMM."""
    q1 = queue.Queue()
    q2 = queue.Queue()
    q1.put("item1")
    q1.put("item2")
    q2.put("item3")
    monkeypatch.setattr(vr, "_speak_queue",    q1)
    monkeypatch.setattr(vr, "_speak_deferred", q2)
    rv = client.post("/api/speak/stop")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True
    assert data["drained"] == 3
    assert q1.empty()
    assert q2.empty()


def test_api_speak_stop_queues_vides_ok(client, monkeypatch):
    monkeypatch.setattr(vr, "_speak_queue",    queue.Queue())
    monkeypatch.setattr(vr, "_speak_deferred", queue.Queue())
    rv = client.post("/api/speak/stop")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["drained"] == 0


# ── GET /api/tts-log — exception handlers (lignes 211-212, 218-219) ──────

def test_api_tts_log_n_invalide_valeur_defaut(client):
    """n=abc → ValueError capturé → n=50 (défaut)."""
    rv = client.get("/api/tts-log?n=abc")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert "lines" in data


def test_api_tts_log_fichier_existant_ok(client, tmp_path, monkeypatch):
    """Log path existant → lignes retournées."""
    log_f = tmp_path / "tts.log"
    log_f.write_text("ligne1\nligne2\nligne3\n")
    monkeypatch.setattr(vr, "_tts_log_path", log_f)
    rv = client.get("/api/tts-log?n=2")
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert len(data["lines"]) == 2


# ── POST /api/voices — api_set_voice (lignes 402-405) ────────────────────

def test_api_set_voice_succes(client, monkeypatch):
    """set_voice(id) renvoie True → ok:True + voix active."""
    monkeypatch.setattr(vr, "_set_voice",  lambda v: True)
    monkeypatch.setattr(vr, "_get_voice",  lambda: "fr-CA-AntoineNeural")
    rv = client.post("/api/voices", json={"voice": "fr-CA-AntoineNeural"})
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True
    assert "voice" in data


def test_api_set_voice_echec_400(client, monkeypatch):
    """set_voice(id) renvoie False → ok:False + 400."""
    monkeypatch.setattr(vr, "_set_voice", lambda v: False)
    rv = client.post("/api/voices", json={"voice": "voix-inconnue"})
    assert rv.status_code == 400
    assert json.loads(rv.data)["ok"] is False


# ── POST /api/voice/analyse — helper _voice_analyse_err (ligne 411-413) ──

def test_api_voice_analyse_librosa_absent(client, monkeypatch):
    """librosa non disponible → 500 avec message d'erreur."""
    with patch("voice.routes.voice_lab.is_librosa_available", return_value=False):
        rv = client.post("/api/voice/analyse")
    assert rv.status_code == 500
    data = json.loads(rv.data)
    assert data["ok"] is False
    assert "librosa" in data["error"]


def test_api_voice_analyse_aucun_fichier(client, monkeypatch):
    """librosa ok mais pas de fichier audio → 400."""
    with patch("voice.routes.voice_lab.is_librosa_available", return_value=True):
        rv = client.post("/api/voice/analyse")
    assert rv.status_code == 400
    data = json.loads(rv.data)
    assert data["ok"] is False
    assert "fichier" in data["error"].lower() or "audio" in data["error"].lower()


# ── POST /api/voice/print/delete — lignes 492-501 ───────────────────────

def test_api_voice_print_delete_nom_manquant_400(client):
    """Suppression sans nom → 400."""
    rv = client.post("/api/voice/print/delete", json={})
    assert rv.status_code == 400
    data = json.loads(rv.data)
    assert data["ok"] is False


def test_api_voice_print_delete_nom_inexistant_404(client):
    """Suppression d'un print inexistant → 404."""
    with patch("voice.routes.voice_lab.delete_print", return_value=(False, "Introuvable")):
        rv = client.post("/api/voice/print/delete", json={"name": "ghost"})
    assert rv.status_code == 404
    data = json.loads(rv.data)
    assert data["ok"] is False


def test_api_voice_print_delete_succes(client):
    """Suppression OK → 200 ok:True."""
    with patch("voice.routes.voice_lab.delete_print", return_value=(True, "ghost")):
        rv = client.post("/api/voice/print/delete", json={"name": "ghost"})
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data["ok"] is True


# ── GET /api/voice/print/audio/<name> — lignes 484-487 ───────────────────

def test_api_voice_print_audio_inexistant_404(client):
    """get_print_path → None → 404."""
    with patch("voice.routes.voice_lab.get_print_path", return_value=None):
        rv = client.get("/api/voice/print/audio/ghost.wav")
    assert rv.status_code == 404


def test_api_voice_print_audio_existant_ok(client, tmp_path):
    """get_print_path → chemin réel → send_file 200."""
    wav_f = tmp_path / "test.wav"
    # WAV minimal valide (44 bytes = header RIFF)
    wav_f.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
                      b"\x22\x56\x00\x00\x44\xac\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    with patch("voice.routes.voice_lab.get_print_path", return_value=wav_f):
        rv = client.get("/api/voice/print/audio/test.wav")
    assert rv.status_code == 200


# ── POST /api/speak/stop — exception ctypes (lignes 167-168) ─────────────

def test_api_speak_stop_winmm_echec_log_et_ok(client, monkeypatch):
    """Si WinDLL lève, exception attrapée → ok:True quand même."""
    monkeypatch.setattr(vr, "_speak_queue",    queue.Queue())
    monkeypatch.setattr(vr, "_speak_deferred", queue.Queue())
    log_mock = MagicMock()
    monkeypatch.setattr(vr, "_log", log_mock)
    with patch("ctypes.WinDLL", side_effect=OSError("WinMM non disponible")):
        rv = client.post("/api/speak/stop")
    assert rv.status_code == 200
    log_mock.info.assert_called()


# ── _apply_dsp — ligne 90 ────────────────────────────────────────────────

def test_apply_dsp_delegue_a_audio_dsp(monkeypatch):
    """_apply_dsp appelle audio_dsp.apply_dsp_to_mp3 avec les bons args."""
    monkeypatch.setattr(vr, "_get_dsp_params", lambda: {"bass": 0.5})
    with patch("voice.routes.audio_dsp.apply_dsp_to_mp3", return_value=(b"wav", "audio/wav")) as m:
        result = vr._apply_dsp(b"mp3data")
    m.assert_called_once_with(b"mp3data", {"bass": 0.5}, None)
    assert result == (b"wav", "audio/wav")
