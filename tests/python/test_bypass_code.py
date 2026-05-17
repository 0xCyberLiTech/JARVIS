"""Tests bypass_code — détection regex + helpers (sans subprocess SCP)."""
import json
import subprocess
from pathlib import Path

import bypass_code
from bypass_code import (
    CODE_DEV_IP,
    CODE_DEV_KEY,
    CODE_DEV_PORT,
    CODE_DEV_VM,
    CODE_EXEC_RE,
    CODE_FILE_RE,
    CODE_REMOTE_DIR,
    CODE_SEND_RE,
    EXEC_TIMEOUT_S,
    LOCAL_SEARCH_DIRS,
    MKDIR_TIMEOUT_S,
    SCP_TIMEOUT_S,
    _sse_tok,
    code_scp_exec_sse,
    detect_code_command,
    find_local_code_file,
)

# ── Constantes ────────────────────────────────────────────────────────────


def test_constantes_dev_pointent_sur_srv_dev_1():
    assert CODE_DEV_VM == "srv-dev-1"
    assert CODE_DEV_IP == "192.168.1.21"
    assert CODE_DEV_PORT == 2272
    assert CODE_REMOTE_DIR == "/tmp/jarvis-code"


def test_code_dev_key_chemin_ssh_id_dev():
    assert CODE_DEV_KEY.endswith("id_dev")
    assert ".ssh" in CODE_DEV_KEY


def test_timeouts_sont_des_int_positifs():
    assert SCP_TIMEOUT_S > 0 and isinstance(SCP_TIMEOUT_S, int)
    assert EXEC_TIMEOUT_S > 0 and isinstance(EXEC_TIMEOUT_S, int)
    assert MKDIR_TIMEOUT_S > 0 and isinstance(MKDIR_TIMEOUT_S, int)


def test_local_search_dirs_inclut_scripts_et_jarvis():
    """Priorité : scripts/ → JARVIS/ → Documents/Downloads/Desktop."""
    paths_str = [str(p) for p in LOCAL_SEARCH_DIRS]
    assert any("scripts" in p for p in paths_str)
    # Le 1er = scripts, le 2e = JARVIS (parent)
    assert LOCAL_SEARCH_DIRS[0].name == "scripts"


# ── Regex CODE_EXEC_RE ───────────────────────────────────────────────────


def test_exec_re_match_execute_sur_dev():
    assert CODE_EXEC_RE.search("execute test.py sur dev")
    assert CODE_EXEC_RE.search("exécute test.py sur srv-dev-1")
    assert CODE_EXEC_RE.search("exécutez script.py sur dev-1")


def test_exec_re_match_lance_run():
    assert CODE_EXEC_RE.search("lance test.py sur dev")
    assert CODE_EXEC_RE.search("run script.py sur dev")
    assert CODE_EXEC_RE.search("teste mon code sur la vm")


def test_exec_re_pas_match_sans_dev():
    """Sans mention de dev → pas match (peut être autre chose)."""
    assert not CODE_EXEC_RE.search("execute test.py")


def test_exec_re_pas_match_sans_verbe_ni_test():
    """Sans verbe ni mot 'test' → pas match."""
    assert not CODE_EXEC_RE.search("script.py sur dev")


# ── Regex CODE_SEND_RE ───────────────────────────────────────────────────


def test_send_re_match_envoie_sur_dev():
    assert CODE_SEND_RE.search("envoie test.py sur dev")
    assert CODE_SEND_RE.search("envoier script.py sur srv-dev-1")


def test_send_re_match_pousse_copie_scp():
    assert CODE_SEND_RE.search("pousse mon code sur dev")
    assert CODE_SEND_RE.search("scp file.py sur dev-1")
    assert CODE_SEND_RE.search("transfère sur la vm dev")


# ── Regex CODE_FILE_RE ───────────────────────────────────────────────────


def test_file_re_match_extensions_classiques():
    for fn in ["test.py", "script.sh", "app.js", "main.go", "code.rs"]:
        m = CODE_FILE_RE.search(f"j'ai {fn} ici")
        assert m is not None, f"manqué : {fn}"
        assert m.group(1) == fn


def test_file_re_match_php_sql_pl_rb_ts():
    for fn in ["page.php", "schema.sql", "script.pl", "app.rb", "main.ts"]:
        assert CODE_FILE_RE.search(fn)


def test_file_re_pas_match_extension_inconnue():
    assert not CODE_FILE_RE.search("doc.pdf")
    assert not CODE_FILE_RE.search("img.png")


def test_file_re_match_avec_tirets_underscore():
    """Filenames avec - et _."""
    assert CODE_FILE_RE.search("mon-script.py")
    assert CODE_FILE_RE.search("test_unitaire.py")


# ── _sse_tok ─────────────────────────────────────────────────────────────


def test_sse_tok_format():
    out = _sse_tok("hello", done=True)
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload == {"type": "token", "token": "hello", "done": True}


def test_sse_tok_done_default_false():
    payload = json.loads(_sse_tok("x").replace("data: ", "").strip())
    assert payload["done"] is False


# ── find_local_code_file ─────────────────────────────────────────────────


def test_find_local_code_file_trouve_fichier_dans_scripts(tmp_path, monkeypatch):
    """Crée un faux fichier dans un dir temp et vérifie find_local_code_file."""
    # On override LOCAL_SEARCH_DIRS pour ne chercher que dans tmp_path
    fake_file = tmp_path / "test_unique.py"
    fake_file.write_text("print('hello')")
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])

    found = find_local_code_file("test_unique.py")
    assert found is not None
    assert found == fake_file


def test_find_local_code_file_retourne_none_si_introuvable(tmp_path, monkeypatch):
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])
    assert find_local_code_file("introuvable_xyz.py") is None


def test_find_local_code_file_priorite_premier_dir(tmp_path, monkeypatch):
    """Le dir en tête de LOCAL_SEARCH_DIRS gagne (priorité scripts/)."""
    dir1 = tmp_path / "first"
    dir2 = tmp_path / "second"
    dir1.mkdir()
    dir2.mkdir()
    (dir1 / "x.py").write_text("# first")
    (dir2 / "x.py").write_text("# second")

    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [dir1, dir2])
    assert find_local_code_file("x.py") == dir1 / "x.py"


def test_find_local_code_file_skip_dir_inexistant(tmp_path, monkeypatch):
    """Un dir inexistant dans LOCAL_SEARCH_DIRS est juste skippé."""
    nonexistent = tmp_path / "doesnotexist"
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    (real_dir / "ok.py").write_text("x")

    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [nonexistent, real_dir])
    assert find_local_code_file("ok.py") == real_dir / "ok.py"


def test_find_local_code_file_skip_si_path_est_un_dir(tmp_path, monkeypatch):
    """Si `filename` correspond à un DIR (pas file), retourne None."""
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])
    (tmp_path / "subdir").mkdir()
    assert find_local_code_file("subdir") is None


# ── detect_code_command ──────────────────────────────────────────────────


def test_detect_code_command_exec():
    result = detect_code_command("exécute test.py sur dev")
    assert result == ("exec", "test.py")


def test_detect_code_command_send():
    result = detect_code_command("envoie script.sh sur dev")
    assert result == ("send", "script.sh")


def test_detect_code_command_aucun_fichier_renvoie_none():
    assert detect_code_command("exécute sur dev") is None


def test_detect_code_command_aucun_verbe_renvoie_none():
    """Note : le mot 'test' EST un verbe valide pour CODE_EXEC_RE (test|tester|testez).
    Donc 'script.py sur dev' (sans verbe) → None."""
    assert detect_code_command("script.py sur dev") is None


def test_detect_code_command_priorite_exec_sur_send():
    """Si les 2 verbes présents, exec gagne (testé en premier dans le code)."""
    result = detect_code_command("exécute et envoie test.py sur dev")
    assert result[0] == "exec"


def test_detect_code_command_extrait_premier_fichier_si_plusieurs():
    """`re.search` → premier match seulement."""
    result = detect_code_command("exécute test.py et helper.sh sur dev")
    assert result == ("exec", "test.py")


# ── Path objects (sanity) ────────────────────────────────────────────────


def test_local_search_dirs_sont_path_objects():
    for d in LOCAL_SEARCH_DIRS:
        assert isinstance(d, Path)


# ── code_scp_exec_sse — SCP + exec sur srv-dev-1 (subprocess mocké) ──────


class _FakeCompletedProcess:
    """Mock minimal de subprocess.CompletedProcess pour subprocess.run()."""

    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _make_ssh_dev1_ok(out: str = "hello world"):
    """Factory : ssh_dev1_fn qui retourne (True, out) à chaque appel."""
    return lambda cmd, timeout=None: (True, out)


def _parse_sse(sse_str: str) -> list:
    """Parse une string SSE en liste de payloads JSON."""
    out = []
    for line in sse_str.split("\n\n"):
        line = line.strip()
        if line.startswith("data: "):
            out.append(json.loads(line[6:]))
    return out


def test_scp_exec_sse_fichier_introuvable(tmp_path, monkeypatch):
    """Fichier inexistant → 1 event SSE done=True avec message d'erreur."""
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])
    events = list(code_scp_exec_sse("inexistant.py", exec_it=True, ssh_dev1_fn=lambda c, timeout=None: (True, "")))
    payloads = [_parse_sse(e)[0] for e in events]
    assert len(payloads) == 1
    assert payloads[0]["done"] is True
    assert "Fichier introuvable" in payloads[0]["token"]
    assert "inexistant.py" in payloads[0]["token"]


def test_scp_exec_sse_scp_succes_et_exec_python(tmp_path, monkeypatch):
    """SCP OK + exec=True sur .py → python3 utilisé pour l'exec."""
    fake_file = tmp_path / "myscript.py"
    fake_file.write_text("print('hi')")
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])
    monkeypatch.setattr(bypass_code.subprocess, "run",
                         lambda *a, **kw: _FakeCompletedProcess(returncode=0, stdout="ok"))

    captured = {"exec_cmd": None}

    def ssh_dev1(cmd, timeout=None):
        # 1er appel = mkdir, 2e appel = python3 exec
        if "python3" in cmd:
            captured["exec_cmd"] = cmd
        return True, "Salut depuis srv-dev-1"

    events = list(code_scp_exec_sse("myscript.py", exec_it=True, ssh_dev1_fn=ssh_dev1))
    text = " ".join(_parse_sse(e)[0]["token"] for e in events)
    assert "myscript.py" in text
    assert "envoyé" in text
    assert "python3" in text
    assert "Salut depuis srv-dev-1" in text
    # Vérifier que la cmd d'exec utilise python3 (pas bash)
    assert "python3" in captured["exec_cmd"]
    assert "myscript.py" in captured["exec_cmd"]


def test_scp_exec_sse_scp_succes_et_exec_bash(tmp_path, monkeypatch):
    """SCP OK + exec=True sur .sh → bash utilisé pour l'exec."""
    fake_file = tmp_path / "deploy.sh"
    fake_file.write_text("echo hi")
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])
    monkeypatch.setattr(bypass_code.subprocess, "run",
                         lambda *a, **kw: _FakeCompletedProcess(returncode=0))

    captured = {"interp": None}

    def ssh_dev1(cmd, timeout=None):
        if cmd.startswith("python3") or cmd.startswith("bash"):
            captured["interp"] = cmd.split()[0]
        return True, "ok"

    list(code_scp_exec_sse("deploy.sh", exec_it=True, ssh_dev1_fn=ssh_dev1))
    assert captured["interp"] == "bash"


def test_scp_exec_sse_send_only_pas_d_exec(tmp_path, monkeypatch):
    """exec_it=False → SCP fait, pas d'exec lancé."""
    fake_file = tmp_path / "x.py"
    fake_file.write_text("x")
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])
    monkeypatch.setattr(bypass_code.subprocess, "run",
                         lambda *a, **kw: _FakeCompletedProcess(returncode=0))

    captured = {"exec_count": 0}

    def ssh_dev1(cmd, timeout=None):
        if "python3" in cmd or cmd.startswith("bash"):
            captured["exec_count"] += 1
        return True, ""

    events = list(code_scp_exec_sse("x.py", exec_it=False, ssh_dev1_fn=ssh_dev1))
    text = " ".join(_parse_sse(e)[0]["token"] for e in events)
    assert captured["exec_count"] == 0   # aucun python3/bash appelé
    assert "Dis `exécute x.py sur dev`" in text
    assert "Fichier disponible" in text


def test_scp_exec_sse_scp_echoue_returncode_non_zero(tmp_path, monkeypatch):
    """subprocess.run renvoie returncode != 0 → message d'erreur SCP, pas d'exec."""
    fake_file = tmp_path / "x.py"
    fake_file.write_text("x")
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])
    monkeypatch.setattr(bypass_code.subprocess, "run",
                         lambda *a, **kw: _FakeCompletedProcess(returncode=1, stderr="permission denied"))

    captured = {"exec_called": False}

    def ssh_dev1(cmd, timeout=None):
        if "python3" in cmd:
            captured["exec_called"] = True
        return True, ""

    events = list(code_scp_exec_sse("x.py", exec_it=True, ssh_dev1_fn=ssh_dev1))
    payloads = [_parse_sse(e)[0] for e in events]
    # Dernier event doit être done=True avec message d'erreur
    assert payloads[-1]["done"] is True
    assert "SCP échoué" in payloads[-1]["token"]
    assert "permission denied" in payloads[-1]["token"]
    assert captured["exec_called"] is False   # pas d'exec si SCP échoue


def test_scp_exec_sse_subprocess_leve_exception(tmp_path, monkeypatch):
    """subprocess.run lève (timeout, OSError…) → message d'erreur clair."""
    fake_file = tmp_path / "x.py"
    fake_file.write_text("x")
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])

    def boom(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="scp", timeout=20)

    monkeypatch.setattr(bypass_code.subprocess, "run", boom)

    events = list(code_scp_exec_sse("x.py", exec_it=True, ssh_dev1_fn=lambda c, timeout=None: (True, "")))
    payloads = [_parse_sse(e)[0] for e in events]
    assert payloads[-1]["done"] is True
    assert "Erreur SCP" in payloads[-1]["token"]


def test_scp_exec_sse_ssh_exec_echoue(tmp_path, monkeypatch):
    """ssh_dev1_fn retourne ok=False pendant exec → message d'erreur SSH."""
    fake_file = tmp_path / "x.py"
    fake_file.write_text("x")
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])
    monkeypatch.setattr(bypass_code.subprocess, "run",
                         lambda *a, **kw: _FakeCompletedProcess(returncode=0))

    # ssh_dev1 : mkdir ok, mais exec fail
    state = {"call": 0}

    def ssh_dev1(cmd, timeout=None):
        state["call"] += 1
        if state["call"] == 1:   # mkdir
            return True, ""
        return False, ""   # exec fail

    events = list(code_scp_exec_sse("x.py", exec_it=True, ssh_dev1_fn=ssh_dev1))
    payloads = [_parse_sse(e)[0] for e in events]
    assert payloads[-1]["done"] is True
    assert "Erreur d'exécution SSH" in payloads[-1]["token"]


def test_scp_exec_sse_exec_sortie_vide(tmp_path, monkeypatch):
    """exec OK mais output vide → '(pas de sortie)'."""
    fake_file = tmp_path / "x.py"
    fake_file.write_text("x")
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])
    monkeypatch.setattr(bypass_code.subprocess, "run",
                         lambda *a, **kw: _FakeCompletedProcess(returncode=0))

    events = list(code_scp_exec_sse("x.py", exec_it=True,
                                     ssh_dev1_fn=lambda c, timeout=None: (True, "")))
    text = " ".join(_parse_sse(e)[0]["token"] for e in events)
    assert "(pas de sortie)" in text


def test_scp_exec_sse_construit_la_bonne_commande_scp(tmp_path, monkeypatch):
    """La commande SCP utilise CODE_DEV_IP, CODE_DEV_PORT, CODE_DEV_KEY, CODE_REMOTE_DIR."""
    fake_file = tmp_path / "test.py"
    fake_file.write_text("x")
    monkeypatch.setattr("bypass_code.LOCAL_SEARCH_DIRS", [tmp_path])

    captured = {"cmd": None}

    def fake_run(cmd, *a, **kw):
        captured["cmd"] = cmd
        return _FakeCompletedProcess(returncode=0)

    monkeypatch.setattr(bypass_code.subprocess, "run", fake_run)

    list(code_scp_exec_sse("test.py", exec_it=False,
                            ssh_dev1_fn=lambda c, timeout=None: (True, "")))
    cmd = captured["cmd"]
    assert cmd[0] == "scp"
    assert CODE_DEV_KEY in cmd
    assert str(CODE_DEV_PORT) in cmd
    assert "StrictHostKeyChecking=no" in cmd
    assert "BatchMode=yes" in cmd
    assert f"root@{CODE_DEV_IP}:{CODE_REMOTE_DIR}/test.py" in cmd
