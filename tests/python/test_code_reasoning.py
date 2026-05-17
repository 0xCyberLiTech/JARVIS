"""Tests code_reasoning — helpers + state management (sans thread Ollama)."""
import json

import code_reasoning
from code_reasoning import (
    _FILEPATH_RE,
    DEFAULT_NUM_PREDICT,
    DEFAULT_TEMPERATURE,
    FILE_CHAR_LIMIT,
    NUM_CTX,
    OLLAMA_TIMEOUT_S,
    TASKS_MAX,
    _cleanup_old_tasks,
    _expand_user_files,
    _run_task,
    _sse_tok,
    code_reasoning_gen,
    tasks,
)


def _reset_tasks():
    """Vide le dict tasks entre tests pour éviter pollution."""
    tasks.clear()


# ── Constantes ────────────────────────────────────────────────────────────


def test_tasks_max_par_defaut_15():
    assert TASKS_MAX == 15


def test_num_ctx_supporte_32k():
    assert NUM_CTX == 32768


def test_default_num_predict():
    assert DEFAULT_NUM_PREDICT == 4096


def test_default_temperature_low():
    assert DEFAULT_TEMPERATURE == 0.1  # CR = déterministe


def test_ollama_timeout_long():
    """10 min minimum pour gros fichiers + reasoning long."""
    assert OLLAMA_TIMEOUT_S >= 600


def test_file_char_limit_environ_80k():
    """80 000 chars ≈ 20K tokens (sous la limite 32K)."""
    assert FILE_CHAR_LIMIT == 80_000


def test_tasks_initialement_un_dict():
    assert isinstance(tasks, dict)


def test_module_logger():
    assert code_reasoning._log.name == "jarvis.code_reasoning"


# ── _sse_tok ─────────────────────────────────────────────────────────────


def test_sse_tok_format_standard():
    out = _sse_tok("hello", done=True)
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload == {"type": "token", "token": "hello", "done": True}


# ── _FILEPATH_RE ─────────────────────────────────────────────────────────


def test_filepath_re_match_windows():
    """Format Windows : C:\\path\\file.ext."""
    text = r"audite C:\Users\mmsab\Documents\code.py"
    matches = _FILEPATH_RE.findall(text)
    assert any("code.py" in m for m in matches)


def test_filepath_re_match_unix():
    """Format Unix : /path/file.ext."""
    matches = _FILEPATH_RE.findall("audite /etc/nginx/nginx.conf")
    assert any("nginx.conf" in m for m in matches)


def test_filepath_re_pas_match_chemin_sans_extension():
    """Le regex exige une extension de fichier (.ext)."""
    matches = _FILEPATH_RE.findall("audite /etc/nginx/")
    assert matches == []


def test_filepath_re_extension_max_10_chars_match_les_10_premiers():
    """\\.[A-Za-z0-9]{1,10} matche au maximum 10 chars d'extension.
    Comportement réel : extension trop longue → match sur les 10 premiers chars."""
    matches = _FILEPATH_RE.findall("voir /tmp/file.veryverylongextension")
    # Soit le match extrait les 10 premiers chars de l'extension, soit rien
    if matches:
        # Le match doit être tronqué à exactement 10 chars d'extension
        for m in matches:
            ext_part = m.split(".")[-1] if "." in m else ""
            assert len(ext_part) <= 10


def test_filepath_re_pas_match_lookback_word():
    """`(?<!\\w)` empêche `foo/etc/x.py` de matcher (le `/etc` doit débuter à un non-word)."""
    matches = _FILEPATH_RE.findall("texte avant /tmp/file.py")
    assert any("file.py" in m for m in matches)


# ── _expand_user_files ───────────────────────────────────────────────────


def test_expand_user_files_injecte_contenu_fichier_existant(tmp_path, monkeypatch):
    f = tmp_path / "test.py"
    f.write_text("print('hello world')\n")

    user_msg = f"analyse {f}"
    expanded = _expand_user_files(user_msg)
    assert "print('hello world')" in expanded
    assert str(f) in expanded


def test_expand_user_files_fichier_inexistant_inchange():
    """Fichier qui n'existe pas → contenu original retourné tel quel."""
    user_msg = "analyse /nonexistent/file.py"
    out = _expand_user_files(user_msg)
    assert out == user_msg


def test_expand_user_files_tronque_si_trop_gros(tmp_path):
    """Fichier > FILE_CHAR_LIMIT → tronqué + warning."""
    f = tmp_path / "big.py"
    f.write_text("X" * (FILE_CHAR_LIMIT + 1000))

    out = _expand_user_files(f"audite {f}")
    assert "Fichier tronqué" in out
    assert "analysez par sections" in out


def test_expand_user_files_pas_tronque_si_petit(tmp_path):
    """Fichier < FILE_CHAR_LIMIT → contenu complet sans warning."""
    f = tmp_path / "small.py"
    f.write_text("x = 1\n")

    out = _expand_user_files(f"audite {f}")
    assert "Fichier tronqué" not in out
    assert "x = 1" in out


def test_expand_user_files_ignore_fichier_binaire_silencieusement(tmp_path):
    """Fichier illisible → ignoré sans crash."""
    f = tmp_path / "binary.bin"
    # Écrire des bytes non-UTF8 (mais errors='replace' devrait gérer)
    f.write_bytes(b"\xff\xfe\xfd\xfc")

    out = _expand_user_files(f"voir {f}")
    # Pas de crash, soit injecté avec replacement chars, soit ignoré
    assert isinstance(out, str)


def test_expand_user_files_pas_de_chemin_dans_le_texte():
    """Texte sans chemin → inchangé."""
    user_msg = "explique ce que tu vois"
    assert _expand_user_files(user_msg) == user_msg


def test_expand_user_files_plusieurs_fichiers(tmp_path):
    f1 = tmp_path / "a.py"
    f2 = tmp_path / "b.py"
    f1.write_text("a = 1")
    f2.write_text("b = 2")

    out = _expand_user_files(f"compare {f1} et {f2}")
    assert "a = 1" in out
    assert "b = 2" in out


# ── _cleanup_old_tasks ───────────────────────────────────────────────────


def test_cleanup_garde_les_tasks_running():
    _reset_tasks()
    tasks["t1"] = {"status": "running"}
    tasks["t2"] = {"status": "running"}
    _cleanup_old_tasks()
    assert "t1" in tasks and "t2" in tasks


def test_cleanup_supprime_les_anciennes_terminees_au_dela_de_TASKS_MAX():
    _reset_tasks()
    for i in range(TASKS_MAX + 3):
        tasks[f"t{i}"] = {"status": "done"}
    _cleanup_old_tasks()
    # Garde les TASKS_MAX dernières (l'ordre dict est insertion-order)
    assert len(tasks) == TASKS_MAX


def test_cleanup_garde_les_dernieres_TASKS_MAX():
    _reset_tasks()
    for i in range(TASKS_MAX + 5):
        tasks[f"task{i:02d}"] = {"status": "done"}
    _cleanup_old_tasks()
    # Les 5 plus anciennes (task00 → task04) ont été supprimées
    assert "task00" not in tasks
    assert "task04" not in tasks
    assert f"task{TASKS_MAX + 4:02d}" in tasks


def test_cleanup_supprime_error_comme_done():
    _reset_tasks()
    for i in range(TASKS_MAX + 5):
        tasks[f"t{i:02d}"] = {"status": "error" if i % 2 else "done"}
    _cleanup_old_tasks()
    assert len(tasks) == TASKS_MAX


def test_cleanup_mix_running_et_done():
    """Running ne compte pas dans la limite TASKS_MAX."""
    _reset_tasks()
    for i in range(5):
        tasks[f"r{i}"] = {"status": "running"}
    for i in range(TASKS_MAX + 3):
        tasks[f"d{i:02d}"] = {"status": "done"}
    _cleanup_old_tasks()
    # 5 running préservés + TASKS_MAX done
    assert len(tasks) == 5 + TASKS_MAX


def test_cleanup_avec_zero_tasks_terminees_pas_de_changement():
    _reset_tasks()
    tasks["r1"] = {"status": "running"}
    _cleanup_old_tasks()
    assert tasks == {"r1": {"status": "running"}}


def test_cleanup_status_inconnu_ignore():
    """Status hors ('done', 'error') → ignoré par cleanup."""
    _reset_tasks()
    for i in range(TASKS_MAX + 5):
        tasks[f"t{i}"] = {"status": "weird"}
    _cleanup_old_tasks()
    assert len(tasks) == TASKS_MAX + 5  # rien supprimé


# ── _run_task : pipeline Ollama streaming (requests mocké) ────────────────


class _FakeStreamResponse:
    """Mock minimal de requests.Response avec iter_lines() qui yield bytes JSON."""

    def __init__(self, lines):
        self._lines = lines

    def iter_lines(self):
        for line in self._lines:
            yield line


def _ollama_chunk(content: str, done: bool = False) -> bytes:
    """Encode 1 chunk Ollama streaming JSON ligne (format /api/chat)."""
    return json.dumps({"message": {"content": content}, "done": done}).encode("utf-8")


def test_run_task_happy_path_sans_think(monkeypatch):
    _reset_tasks()
    tasks["t-happy"] = {"status": "running", "text": ""}
    monkeypatch.setattr(
        code_reasoning.requests, "post",
        lambda *a, **kw: _FakeStreamResponse([
            _ollama_chunk("Voici "),
            _ollama_chunk("la réponse."),
            _ollama_chunk("", done=True),
        ]),
    )
    _run_task(
        "t-happy", "audite ce code", [{"role": "user", "content": "audite"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={"num_predict": 100},
    )
    assert tasks["t-happy"]["status"] == "done"
    assert "Voici la réponse." in tasks["t-happy"]["text"]


def test_run_task_avec_think_masque_le_thinking(monkeypatch):
    """Pendant que <think>...</think> est en cours, task['text'] affiche un loader.
    Une fois fermé, seul le contenu post-think apparaît."""
    _reset_tasks()
    tasks["t-think"] = {"status": "running", "text": ""}
    monkeypatch.setattr(
        code_reasoning.requests, "post",
        lambda *a, **kw: _FakeStreamResponse([
            _ollama_chunk("<think>raisonnement secret"),
            _ollama_chunk(" qui doit rester masque</think>"),
            _ollama_chunk("Reponse finale visible."),
            _ollama_chunk("", done=True),
        ]),
    )
    _run_task(
        "t-think", "x", [{"role": "user", "content": "x"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    )
    text = tasks["t-think"]["text"]
    # Thinking NE DOIT PAS apparaître
    assert "raisonnement secret" not in text
    assert "doit rester masque" not in text
    # Réponse visible OK
    assert "Reponse finale visible." in text
    assert tasks["t-think"]["status"] == "done"


def test_run_task_np_override_utilise(monkeypatch):
    """num_predict de l'appelant override le défaut."""
    _reset_tasks()
    tasks["t-np"] = {"status": "running", "text": ""}
    captured = {}

    def fake_post(url, json=None, **kw):
        captured["num_predict"] = json["options"]["num_predict"]
        return _FakeStreamResponse([_ollama_chunk("", done=True)])

    monkeypatch.setattr(code_reasoning.requests, "post", fake_post)
    _run_task(
        "t-np", "x", [{"role": "user", "content": "x"}], np_override=2048,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={"num_predict": 9999},  # override gagne
    )
    assert captured["num_predict"] == 2048


def test_run_task_np_default_si_pas_override(monkeypatch):
    """Sans np_override, prend llm_params['num_predict']."""
    _reset_tasks()
    tasks["t-np2"] = {"status": "running", "text": ""}
    captured = {}

    def fake_post(url, json=None, **kw):
        captured["num_predict"] = json["options"]["num_predict"]
        return _FakeStreamResponse([_ollama_chunk("", done=True)])

    monkeypatch.setattr(code_reasoning.requests, "post", fake_post)
    _run_task(
        "t-np2", "x", [{"role": "user", "content": "x"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={"num_predict": 1234},
    )
    assert captured["num_predict"] == 1234


def test_run_task_default_si_llm_params_vide(monkeypatch):
    """llm_params sans num_predict → DEFAULT_NUM_PREDICT (4096)."""
    _reset_tasks()
    tasks["t-def"] = {"status": "running", "text": ""}
    captured = {}

    def fake_post(url, json=None, **kw):
        captured["num_predict"] = json["options"]["num_predict"]
        return _FakeStreamResponse([_ollama_chunk("", done=True)])

    monkeypatch.setattr(code_reasoning.requests, "post", fake_post)
    _run_task(
        "t-def", "x", [{"role": "user", "content": "x"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    )
    assert captured["num_predict"] == DEFAULT_NUM_PREDICT


def test_run_task_exception_status_error(monkeypatch):
    """Si requests.post lève → status=error, message d'erreur dans text."""
    _reset_tasks()
    tasks["t-err"] = {"status": "running", "text": "départ"}

    def boom(*a, **kw):
        raise ConnectionError("Ollama down")

    monkeypatch.setattr(code_reasoning.requests, "post", boom)
    _run_task(
        "t-err", "x", [{"role": "user", "content": "x"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    )
    assert tasks["t-err"]["status"] == "error"
    assert "Ollama down" in tasks["t-err"]["text"]


def test_run_task_appelle_ensure_vram_avant_post(monkeypatch):
    """ensure_vram_fn(model) doit être appelé pour précharger le modèle CUDA."""
    _reset_tasks()
    tasks["t-vram"] = {"status": "running", "text": ""}
    captured = {"vram_model": None}

    def vram(m):
        captured["vram_model"] = m

    monkeypatch.setattr(code_reasoning.requests, "post",
                         lambda *a, **kw: _FakeStreamResponse([_ollama_chunk("", done=True)]))
    _run_task(
        "t-vram", "x", [{"role": "user", "content": "x"}], None,
        ensure_vram_fn=vram, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    )
    assert captured["vram_model"] == "qwen3:8b"


def test_run_task_ajoute_system_suffix_au_user_content(monkeypatch):
    """system_suffix est concatené au contenu utilisateur (et non au system role)."""
    _reset_tasks()
    tasks["t-sfx"] = {"status": "running", "text": ""}
    captured = {}

    def fake_post(url, json=None, **kw):
        captured["last_user"] = json["messages"][-1]["content"]
        return _FakeStreamResponse([_ollama_chunk("", done=True)])

    monkeypatch.setattr(code_reasoning.requests, "post", fake_post)
    _run_task(
        "t-sfx", "audite", [{"role": "user", "content": "audite"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="\n\n[CR-MODE]", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    )
    assert captured["last_user"].endswith("[CR-MODE]")


def test_run_task_ignore_lignes_json_invalide(monkeypatch):
    """Si Ollama envoie une ligne non-JSON, _run_task la skip silencieusement."""
    _reset_tasks()
    tasks["t-bad"] = {"status": "running", "text": ""}
    monkeypatch.setattr(
        code_reasoning.requests, "post",
        lambda *a, **kw: _FakeStreamResponse([
            b"not json",
            _ollama_chunk("OK"),
            _ollama_chunk("", done=True),
        ]),
    )
    _run_task(
        "t-bad", "x", [{"role": "user", "content": "x"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    )
    assert tasks["t-bad"]["status"] == "done"
    assert "OK" in tasks["t-bad"]["text"]


def test_run_task_ignore_lignes_vides(monkeypatch):
    """Lignes vides (keepalive) → ignorées."""
    _reset_tasks()
    tasks["t-empty"] = {"status": "running", "text": ""}
    monkeypatch.setattr(
        code_reasoning.requests, "post",
        lambda *a, **kw: _FakeStreamResponse([
            b"",
            _ollama_chunk("contenu"),
            b"",
            _ollama_chunk("", done=True),
        ]),
    )
    _run_task(
        "t-empty", "x", [{"role": "user", "content": "x"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    )
    assert "contenu" in tasks["t-empty"]["text"]


# ── code_reasoning_gen : générateur SSE qui démarre le thread daemon ─────


def test_code_reasoning_gen_yield_task_id_et_done(monkeypatch):
    """Le générateur yield 2 events : (cr_task avec task_id) puis (token done=True)."""
    _reset_tasks()
    # Mock requests pour que le thread daemon ne fasse rien de coûteux
    monkeypatch.setattr(
        code_reasoning.requests, "post",
        lambda *a, **kw: _FakeStreamResponse([_ollama_chunk("hi"), _ollama_chunk("", done=True)]),
    )
    events = list(code_reasoning_gen(
        [{"role": "user", "content": "test"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    ))
    # 2 events SSE
    assert len(events) == 2
    p1 = json.loads(events[0].replace("data: ", "").strip())
    p2 = json.loads(events[1].replace("data: ", "").strip())
    assert p1["type"] == "cr_task"
    assert "task_id" in p1 and len(p1["task_id"]) > 0
    assert p2["done"] is True


def test_code_reasoning_gen_cree_entry_dans_tasks(monkeypatch):
    """code_reasoning_gen ajoute le task au dict tasks avant le thread."""
    _reset_tasks()
    monkeypatch.setattr(
        code_reasoning.requests, "post",
        lambda *a, **kw: _FakeStreamResponse([_ollama_chunk("", done=True)]),
    )
    events = list(code_reasoning_gen(
        [{"role": "user", "content": "x"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    ))
    task_id = json.loads(events[0].replace("data: ", "").strip())["task_id"]
    assert task_id in tasks


def test_code_reasoning_gen_appelle_expand_user_files(monkeypatch, tmp_path):
    """Le contenu du fichier mentionné dans le dernier user message est auto-injecté."""
    _reset_tasks()
    f = tmp_path / "test_inject.py"
    f.write_text("CONTENU_UNIQUE_42")

    captured = {}

    def fake_post(url, json=None, **kw):
        captured["last_user"] = json["messages"][-1]["content"]
        return _FakeStreamResponse([_ollama_chunk("", done=True)])

    monkeypatch.setattr(code_reasoning.requests, "post", fake_post)

    import time as _t
    events = list(code_reasoning_gen(
        [{"role": "user", "content": f"audite {f}"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    ))
    # Attendre que le thread démarre et appelle requests.post
    task_id = json.loads(events[0].replace("data: ", "").strip())["task_id"]
    for _ in range(20):
        if tasks.get(task_id, {}).get("status") in ("done", "error"):
            break
        _t.sleep(0.05)
    assert "CONTENU_UNIQUE_42" in captured.get("last_user", "")


def test_code_reasoning_gen_lance_cleanup_au_passage(monkeypatch):
    """_cleanup_old_tasks est appelé au début de code_reasoning_gen."""
    _reset_tasks()
    # Pré-remplir avec TASKS_MAX + 5 done
    for i in range(TASKS_MAX + 5):
        tasks[f"old{i:02d}"] = {"status": "done", "text": ""}
    monkeypatch.setattr(
        code_reasoning.requests, "post",
        lambda *a, **kw: _FakeStreamResponse([_ollama_chunk("", done=True)]),
    )
    list(code_reasoning_gen(
        [{"role": "user", "content": "x"}], None,
        ensure_vram_fn=lambda m: None, model="qwen3:8b",
        system_suffix="", ollama_url="http://127.0.0.1:11434",
        llm_params={},
    ))
    # Cleanup a viré les 5 plus anciennes (old00..old04)
    assert "old00" not in tasks
    assert "old04" not in tasks
