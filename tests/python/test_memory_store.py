"""Tests memory/store.py — persistance historique + resumes long terme.

Le module utilise des accesseurs (lambdas) injectes via init() pour resoudre
les chemins/modeles au runtime. Pattern adopte : fixture qui appelle init()
avec tmp_path pour isoler les fichiers + MagicMock pour Ollama.
"""
import json
from unittest.mock import MagicMock

import pytest
from memory import store


@pytest.fixture
def setup_store(tmp_path):
    """Initialise le module store avec fichiers temporaires + circuit mock."""
    mem_file = tmp_path / "memory.json"
    sum_file = tmp_path / "summary.json"
    log = MagicMock()
    circuit = MagicMock()

    store.init(
        get_memory_file=lambda: mem_file,
        get_summary_file=lambda: sum_file,
        get_model=lambda: "phi4:14b",
        get_mode=lambda: "soc",
        memory_limit=5,
        summary_keep=3,
        summary_min_msgs=3,
        general_model="gemma4",
        code_model="qwen2.5-coder",
        ollama_url="http://127.0.0.1:11434",
        ollama_circuit=circuit,
        log=log,
    )
    return {"mem_file": mem_file, "sum_file": sum_file, "log": log, "circuit": circuit}


# Bloc init

def test_init_set_globals_correctement(setup_store):
    """init() doit avoir setté tous les accessors + constantes."""
    assert store._memory_limit == 5
    assert store._summary_keep == 3
    assert store._summary_min_msgs == 3
    assert store._general_model == "gemma4"
    assert store._code_model == "qwen2.5-coder"
    assert store._ollama_url == "http://127.0.0.1:11434"
    assert store._get_model() == "phi4:14b"
    assert store._get_mode() == "soc"


# Bloc load_memory

def test_load_memory_fichier_absent_retourne_liste_vide(setup_store):
    """Fichier inexistant → [] (sans exception)."""
    assert store.load_memory() == []


def test_load_memory_fichier_existe_retourne_contenu(setup_store):
    setup_store["mem_file"].write_text(
        json.dumps([{"role": "user", "content": "hello"}]),
        encoding="utf-8"
    )
    out = store.load_memory()
    assert len(out) == 1
    assert out[0]["content"] == "hello"


def test_load_memory_json_invalide_retourne_liste_vide(setup_store):
    """JSON corrompu → [] + warning loggue."""
    setup_store["mem_file"].write_text("{ not json", encoding="utf-8")
    out = store.load_memory()
    assert out == []
    assert setup_store["log"].warning.called


# Bloc save_memory

def test_save_memory_filtre_roles_invalides(setup_store):
    """Seuls user/assistant avec content str sont gardes."""
    history = [
        {"role": "user", "content": "u1"},
        {"role": "system", "content": "skip"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": 42},  # content non-str → skip
        {"role": "user", "content": "u2"},
    ]
    store.save_memory(history)
    saved = json.loads(setup_store["mem_file"].read_text(encoding="utf-8"))
    assert len(saved) == 3
    assert all(m["content"] in ("u1", "a1", "u2") for m in saved)


def test_save_memory_tronque_a_memory_limit(setup_store):
    """Si > memory_limit, garde les N derniers."""
    history = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
    store.save_memory(history)
    saved = json.loads(setup_store["mem_file"].read_text(encoding="utf-8"))
    assert len(saved) == 5  # memory_limit fixture
    assert saved[-1]["content"] == "msg9"


def test_save_memory_declenche_background_si_excedent_suffisant(setup_store, monkeypatch):
    """Si excedent >= summary_min_msgs (3) → background_summarize lance."""
    called = {"n": 0}

    def fake_thread_start(*a, **k):
        called["n"] += 1

    monkeypatch.setattr(store.threading, "Thread",
                        lambda **k: MagicMock(start=fake_thread_start))
    history = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
    store.save_memory(history)
    assert called["n"] == 1  # 10 msgs - 5 limit = 5 to_summarize >= 3 min


def test_save_memory_pas_de_background_si_excedent_insuffisant(setup_store, monkeypatch):
    """Excedent < summary_min_msgs → pas de thread."""
    called = {"n": 0}
    monkeypatch.setattr(store.threading, "Thread",
                        lambda **k: MagicMock(start=lambda *a, **k: called.__setitem__("n", called["n"] + 1)))
    history = [{"role": "user", "content": f"msg{i}"} for i in range(7)]  # 7-5=2 < 3
    store.save_memory(history)
    assert called["n"] == 0


def test_save_memory_erreur_io_loggue_sans_crasher(setup_store, monkeypatch):
    """Si write_text leve, error logue, pas de raise."""
    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(type(setup_store["mem_file"]), "write_text", boom)
    store.save_memory([{"role": "user", "content": "x"}])
    assert setup_store["log"].error.called


# Bloc _append_memory_summary + _load_memory_summary

def test_append_memory_summary_cree_fichier(setup_store):
    store._append_memory_summary("Resume 1")
    data = json.loads(setup_store["sum_file"].read_text(encoding="utf-8"))
    assert "summaries" in data
    assert len(data["summaries"]) == 1
    assert data["summaries"][0]["content"] == "Resume 1"


def test_append_memory_summary_rotation_summary_keep(setup_store):
    """Si > summary_keep (3), tronque aux 3 derniers."""
    for i in range(5):
        store._append_memory_summary(f"Resume {i}")
    data = json.loads(setup_store["sum_file"].read_text(encoding="utf-8"))
    assert len(data["summaries"]) == 3
    assert data["summaries"][-1]["content"] == "Resume 4"
    assert data["summaries"][0]["content"] == "Resume 2"  # rotation : garde [-3:]


def test_load_memory_summary_fichier_absent_retourne_chaine_vide(setup_store):
    assert store._load_memory_summary() == ""


def test_load_memory_summary_concatene_3_derniers(setup_store):
    for i in range(5):
        store._append_memory_summary(f"Resume {i}")
    out = store._load_memory_summary()
    # rotation a garde Resume2/3/4
    assert "Resume 2" in out
    assert "Resume 3" in out
    assert "Resume 4" in out
    assert "Resume 0" not in out


def test_load_memory_summary_json_invalide_retourne_chaine_vide(setup_store):
    setup_store["sum_file"].write_text("{ broken", encoding="utf-8")
    assert store._load_memory_summary() == ""


# Bloc _summarize_messages (appel Ollama mock)

def test_summarize_messages_succes(setup_store):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"response": "• Point clef 1\n• Point clef 2"}
    setup_store["circuit"].call.return_value = mock_resp

    msgs = [{"role": "user", "content": "marc dit ceci"},
            {"role": "assistant", "content": "jarvis repond cela"}]
    out = store._summarize_messages(msgs)
    assert "Point clef 1" in out
    setup_store["circuit"].call.assert_called_once()


def test_summarize_messages_ollama_ko_retourne_chaine_vide(setup_store):
    mock_resp = MagicMock()
    mock_resp.ok = False
    setup_store["circuit"].call.return_value = mock_resp
    out = store._summarize_messages([{"role": "user", "content": "x"}])
    assert out == ""


def test_summarize_messages_exception_retourne_chaine_vide(setup_store):
    setup_store["circuit"].call.side_effect = RuntimeError("ollama down")
    out = store._summarize_messages([{"role": "user", "content": "x"}])
    assert out == ""
    assert setup_store["log"].warning.called


def test_summarize_messages_choisit_modele_selon_mode_general(setup_store):
    """Mode general → utilise general_model (gemma4)."""
    store._get_mode = lambda: "general"  # override mode
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"response": "ok"}
    setup_store["circuit"].call.return_value = mock_resp

    store._summarize_messages([{"role": "user", "content": "x"}])
    # Verifie que le payload utilisait gemma4
    args, kwargs = setup_store["circuit"].call.call_args
    assert kwargs["json"]["model"] == "gemma4"


# Bloc _background_summarize

def test_background_summarize_appelle_append_si_resume_non_vide(setup_store):
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.json.return_value = {"response": "Resume background"}
    setup_store["circuit"].call.return_value = mock_resp

    store._background_summarize([{"role": "user", "content": "x"}])
    # Le fichier summary doit contenir le resume
    data = json.loads(setup_store["sum_file"].read_text(encoding="utf-8"))
    assert any("Resume background" in s["content"] for s in data["summaries"])


def test_background_summarize_n_append_pas_si_resume_vide(setup_store):
    """Si summarize retourne '', pas d'ecriture du fichier summary."""
    mock_resp = MagicMock()
    mock_resp.ok = False
    setup_store["circuit"].call.return_value = mock_resp

    store._background_summarize([{"role": "user", "content": "x"}])
    assert not setup_store["sum_file"].exists()
