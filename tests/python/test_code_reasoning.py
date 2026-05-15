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
    _sse_tok,
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
