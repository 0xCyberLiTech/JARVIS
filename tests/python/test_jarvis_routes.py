"""Tests routes Flask jarvis.py — couverture des endpoints GET « lecture ».

Cible l'audit dette : critère Tests — `jarvis.py` orchestrateur Flask sous-couvert
au niveau unitaire. Chaque test exerce un handler de route via test_client (pas de
serveur démarré, pas de side-effect lourd) → coverage réelle des routes lecture.

Stratégie : routes GET qui renvoient du JSON sans muter d'état. Assertions
robustes (forme du payload), pas de sur-spécification.
"""
import json

import jarvis as jm
import pytest


@pytest.fixture(scope="module")
def client():
    jm.app.testing = True
    return jm.app.test_client()


def _json(r):
    """Parse le corps JSON d'une réponse, échoue proprement sinon."""
    return json.loads(r.data)


# ── Santé / état système ────────────────────────────────────────────────

def test_api_stats_renvoie_dict(client):
    r = client.get("/api/stats")
    assert r.status_code == 200
    assert isinstance(_json(r), dict)


def test_api_ollama_status_renvoie_dict(client):
    r = client.get("/api/ollama-status")
    assert r.status_code == 200
    assert isinstance(_json(r), dict)


def test_api_vram_renvoie_dict(client):
    r = client.get("/api/vram")
    assert r.status_code == 200
    assert isinstance(_json(r), dict)


def test_api_sysdiag_renvoie_dict(client):
    r = client.get("/api/sysdiag")
    assert r.status_code == 200
    assert isinstance(_json(r), dict)


# ── STT / TTS / voix ────────────────────────────────────────────────────

def test_api_stt_status_renvoie_dict(client):
    r = client.get("/api/stt/status")
    assert r.status_code == 200
    assert isinstance(_json(r), dict)


def test_api_tts_status_renvoie_dict(client):
    r = client.get("/api/tts/status")
    assert r.status_code == 200
    assert isinstance(_json(r), dict)


def test_api_tts_log_renvoie_200(client):
    r = client.get("/api/tts-log")
    assert r.status_code == 200


def test_api_tts_local_voices_renvoie_200(client):
    r = client.get("/api/tts/local/voices")
    assert r.status_code == 200


def test_api_speak_status_renvoie_dict(client):
    r = client.get("/api/speak/status")
    assert r.status_code == 200
    assert isinstance(_json(r), dict)


def test_api_speak_queue_renvoie_200(client):
    r = client.get("/api/speak/queue")
    assert r.status_code == 200


def test_api_voices_get_renvoie_200(client):
    r = client.get("/api/voices")
    assert r.status_code == 200


def test_api_voice_prints_get_renvoie_200(client):
    r = client.get("/api/voice/prints")
    assert r.status_code == 200


def test_api_voice_samples_get_renvoie_200(client):
    r = client.get("/api/voice/samples")
    assert r.status_code == 200


# ── Config / état applicatif ────────────────────────────────────────────

def test_api_dsp_params_get_renvoie_dict(client):
    r = client.get("/api/dsp-params")
    assert r.status_code == 200
    assert isinstance(_json(r), dict)


def test_api_models_get_renvoie_200(client):
    r = client.get("/api/models")
    assert r.status_code == 200


def test_api_tasks_get_renvoie_200(client):
    r = client.get("/api/tasks")
    assert r.status_code == 200


def test_api_history_last_renvoie_200(client):
    r = client.get("/api/history/last")
    assert r.status_code == 200


def test_api_security_get_renvoie_200(client):
    r = client.get("/api/security")
    assert r.status_code == 200


# ── Routes POST — validation d'entrée (chemin de refus) ─────────────────

def test_api_prompt_profiles_delete_inexistant_idempotent(client):
    """DELETE d'un profil de prompt inexistant → géré (idempotent, pas de 500)."""
    r = client.delete("/api/prompt-profiles/profil-qui-n-existe-pas-xyz")
    assert r.status_code in (200, 404)


def test_api_facts_post_facts_non_liste_refuse(client):
    """POST /api/facts avec `facts` qui n'est pas une liste → 400 (branche validation)."""
    r = client.post("/api/facts", json={"facts": "pas-une-liste"})
    assert r.status_code == 400


def test_api_facts_post_corps_non_dict_ne_crashe_pas(client, monkeypatch, tmp_path):
    """POST /api/facts avec un corps JSON non-objet → géré sans 500 (garde isinstance)."""
    monkeypatch.setattr(jm, "FACTS_FILE", tmp_path / "facts.json")
    r = client.post("/api/facts", json="pas-un-dict")
    assert r.status_code == 200


def test_api_models_post_sans_modele_refuse(client):
    """POST changement de modèle sans nom → 4xx."""
    r = client.post("/api/models", json={})
    assert r.status_code in (400, 422)


def test_api_speak_post_sans_texte_geree(client):
    """POST /api/speak sans texte → géré sans 500."""
    r = client.post("/api/speak", json={})
    assert r.status_code in (200, 400, 422)


def test_api_cr_poll_id_inconnu_geree(client):
    """Poll d'un task_id Code-Reasoning inconnu → réponse gérée, pas de 500."""
    r = client.get("/api/cr-poll/task-inexistant-xyz")
    assert r.status_code in (200, 404)
