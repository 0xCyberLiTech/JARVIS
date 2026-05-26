"""Tests bypass_filesystem — détection regex + SSE génération (DI ssh_fn mockable)."""
import json

from bypass.filesystem import (
    FADD_RE,
    FCORR_RE,
    FEDIT_RE,
    FNAME_RE,
    FPATH_RE,
    FREAD_RE,
    SUR_VM_RE,
    _resolve_path,
    _resolve_vm,
    _sse_tok,
    detect_file_command,
    detect_multi_file_command,
    file_command_sse,
)


def _vm_map():
    """Map de test : alias → (vm_name, ssh_fn_dummy)."""
    ssh_nginx = lambda cmd: (True, f"OK: {cmd}")  # noqa: E731
    ssh_clt = lambda cmd: (True, f"CLT: {cmd}")  # noqa: E731
    return {
        "nginx": ("srv-nginx", ssh_nginx),
        "srv-nginx": ("srv-nginx", ssh_nginx),
        "clt": ("srv-clt", ssh_clt),
        "srv-clt": ("srv-clt", ssh_clt),
    }


# ── Regex de détection ────────────────────────────────────────────────────


def test_fread_re_match_lis():
    assert FREAD_RE.search("lis le fichier")


def test_fread_re_match_cat():
    assert FREAD_RE.search("cat /etc/hosts")


def test_fread_re_match_affiche():
    assert FREAD_RE.search("affiche le contenu")


def test_fedit_re_match_modifie():
    assert FEDIT_RE.search("modifie cette ligne")


def test_fedit_re_match_edite():
    assert FEDIT_RE.search("édite le fichier")


def test_fadd_re_match_ajoute():
    assert FADD_RE.search("ajoute une entrée")


def test_fadd_re_match_insere():
    assert FADD_RE.search("insère cette ligne")


def test_fcorr_re_match_corrige():
    assert FCORR_RE.search("corrige le fichier")


def test_fcorr_re_match_propose():
    assert FCORR_RE.search("propose une version corrigée")


def test_sur_vm_re_match_explicite():
    m = SUR_VM_RE.search("sur srv-nginx maintenant")
    assert m is not None
    assert m.group(1).lower() == "srv-nginx"


def test_sur_vm_re_match_alias_court():
    m = SUR_VM_RE.search("sur nginx")
    assert m.group(1).lower() == "nginx"


def test_fpath_re_match_chemin_absolu():
    matches = FPATH_RE.findall("voir /etc/nginx/nginx.conf")
    assert any("/etc/nginx/nginx.conf" in g for pair in matches for g in pair)


def test_fname_re_match_nginx_conf():
    assert FNAME_RE.search("nginx.conf")


# ── _resolve_path ────────────────────────────────────────────────────────


def test_resolve_path_chemin_absolu():
    assert _resolve_path("voir /etc/nginx/nginx.conf") == "/etc/nginx/nginx.conf"


def test_resolve_path_nom_fichier_resolu_vers_etc():
    """Nom de fichier connu sans chemin → préfixe /etc/."""
    assert _resolve_path("voir nginx.conf") == "/etc/nginx.conf"


def test_resolve_path_hosts_resolu_vers_etc_hosts():
    """Cas spécial 'hosts' → /etc/hosts (pas /etc/host)."""
    assert _resolve_path("affiche hosts") == "/etc/hosts"


def test_resolve_path_aucun_match_renvoie_none():
    assert _resolve_path("bonjour Marc") is None


def test_resolve_path_chemin_relatif_etc_prefixe_par_slash():
    """Pattern 'etc/foo' → /etc/foo (préfixe /)."""
    assert _resolve_path("ouvre etc/passwd") == "/etc/passwd"


# ── _resolve_vm ──────────────────────────────────────────────────────────


def test_resolve_vm_explicite_sur_nginx():
    vm_name, _ = _resolve_vm("lis nginx.conf sur srv-nginx", _vm_map())
    assert vm_name == "srv-nginx"


def test_resolve_vm_par_nom_dans_le_texte():
    """Pas de 'sur', mais le nom apparaît → match secondaire."""
    vm_name, _ = _resolve_vm("affiche srv-clt /etc/hosts", _vm_map())
    assert vm_name == "srv-clt"


def test_resolve_vm_aucune_match_renvoie_none():
    assert _resolve_vm("aucune VM ici", _vm_map()) is None


def test_resolve_vm_priorite_sur_l_explicite():
    """Si 'sur srv-nginx' présent, gagne même si srv-clt aussi mentionné ailleurs."""
    vm_name, _ = _resolve_vm("lis sur srv-nginx le fichier de srv-clt", _vm_map())
    assert vm_name == "srv-nginx"


# ── detect_file_command ──────────────────────────────────────────────────


def test_detect_file_command_lecture_complete():
    result = detect_file_command("lis nginx.conf sur srv-nginx", _vm_map())
    assert result is not None
    action, vm, ssh, path = result
    assert action == "read"
    assert vm == "srv-nginx"
    assert path == "/etc/nginx.conf"


def test_detect_file_command_edition():
    result = detect_file_command("modifie nginx.conf sur srv-nginx", _vm_map())
    assert result[0] == "edit"


def test_detect_file_command_ajout():
    result = detect_file_command("ajoute une entrée dans hosts sur srv-nginx", _vm_map())
    assert result[0] == "add"


def test_detect_file_command_priorite_add_sur_edit_sur_read():
    """Le code teste add > edit > read."""
    result = detect_file_command("modifie et ajoute hosts sur srv-nginx", _vm_map())
    assert result[0] == "add"  # ajoute gagne


def test_detect_file_command_aucun_verbe_renvoie_none():
    assert detect_file_command("bonjour, nginx.conf sur srv-nginx", _vm_map()) is None


def test_detect_file_command_aucun_path_renvoie_none():
    assert detect_file_command("lis sur srv-nginx", _vm_map()) is None


def test_detect_file_command_aucune_vm_renvoie_none():
    # Note 2026-05-26 : 'nginx.conf' matche desormais l'alias 'nginx' (nouveau hostname).
    # On utilise 'myfile.conf' pour valider l'absence de VM mentionnee.
    assert detect_file_command("lis myfile.conf", _vm_map()) is None


# ── detect_multi_file_command ────────────────────────────────────────────


def test_detect_multi_file_au_moins_2_chemins():
    result = detect_multi_file_command(
        "corrige /etc/nginx/nginx.conf et /var/log/syslog sur srv-nginx",
        _vm_map(),
    )
    assert result is not None
    action, vm, _, paths = result
    assert action == "read"  # multi = forcé read
    assert vm == "srv-nginx"
    assert len(paths) == 2


def test_detect_multi_file_un_seul_chemin_renvoie_none():
    """1 seul fichier → pas multi."""
    result = detect_multi_file_command("corrige /etc/nginx/nginx.conf sur srv-nginx", _vm_map())
    assert result is None


def test_detect_multi_file_action_edit_devient_read():
    """Multi-fichiers = read seul (jamais edit/add)."""
    result = detect_multi_file_command(
        "modifie /etc/hosts et /etc/passwd sur srv-nginx",
        _vm_map(),
    )
    assert result[0] == "read"


def test_detect_multi_file_aucun_verbe_renvoie_none():
    result = detect_multi_file_command(
        "/etc/hosts et /etc/passwd sur srv-nginx",  # pas de verbe
        _vm_map(),
    )
    assert result is None


# ── _sse_tok ─────────────────────────────────────────────────────────────


def test_sse_tok_format_standard():
    out = _sse_tok("hello", done=True)
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload == {"type": "token", "token": "hello", "done": True}


def test_sse_tok_done_default_false():
    out = _sse_tok("x")
    payload = json.loads(out.replace("data: ", "").strip())
    assert payload["done"] is False


# ── file_command_sse ─────────────────────────────────────────────────────


def test_file_command_sse_lecture_fichier_succes():
    def ssh_ok(cmd):
        return True, "contenu fichier"

    events = list(file_command_sse("read", "srv-nginx", ssh_ok, "/etc/nginx.conf"))
    # 1) ssh_file event, 2) token done, 3) speak
    assert len(events) == 3
    p1 = json.loads(events[0].replace("data: ", "").strip())
    assert p1["type"] == "ssh_file"
    assert p1["vm"] == "srv-nginx"
    assert p1["path"] == "/etc/nginx.conf"
    assert p1["content"] == "contenu fichier"


def test_file_command_sse_ssh_echec_yield_message_erreur():
    def ssh_fail(cmd):
        return False, ""

    events = list(file_command_sse("read", "srv-nginx", ssh_fail, "/etc/nginx.conf"))
    # Un seul event : token erreur
    assert len(events) == 1
    p = json.loads(events[0].replace("data: ", "").strip())
    assert p["type"] == "token"
    assert p["done"] is True
    assert "Erreur" in p["token"]


def test_file_command_sse_repertoire_utilise_ls_la():
    """Path se terminant par / → ls -la, pas cat."""
    captured = {}

    def ssh_capture(cmd):
        captured["cmd"] = cmd
        return True, "drwxr-xr-x ..."

    list(file_command_sse("read", "srv-nginx", ssh_capture, "/etc/"))
    assert captured["cmd"] == "ls -la /etc/"


def test_file_command_sse_basename_sans_extension_traite_comme_repertoire():
    """`/etc` (sans extension) → ls -la."""
    captured = {}

    def ssh_capture(cmd):
        captured["cmd"] = cmd
        return True, "drwxr-xr-x ..."

    list(file_command_sse("read", "srv-nginx", ssh_capture, "/etc"))
    assert captured["cmd"] == "ls -la /etc"


def test_file_command_sse_fichier_avec_extension_utilise_cat():
    """`/etc/nginx.conf` (extension) → cat."""
    captured = {}

    def ssh_capture(cmd):
        captured["cmd"] = cmd
        return True, "server { ... }"

    list(file_command_sse("read", "srv-nginx", ssh_capture, "/etc/nginx.conf"))
    assert captured["cmd"] == "cat /etc/nginx.conf"


def test_file_command_sse_speak_mentionne_le_path():
    def ssh_ok(cmd):
        return True, "x"

    events = list(file_command_sse("read", "srv-nginx", ssh_ok, "/etc/hosts"))
    speak = json.loads(events[2].replace("data: ", "").strip())
    assert speak["type"] == "speak"
    assert "/etc/hosts" in speak["text"]
