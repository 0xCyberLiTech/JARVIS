"""Tests fonctions pures jarvis.py — helpers RAG, filtre think, chemins, tools.

Campagne couverture (étape 1) — incrément 4, focus `jarvis.py`. Cible les
fonctions pures et semi-pures de l'orchestrateur : découpage RAG, filtre
<think>, validation de chemins d'écriture, timeout SSH adaptatif, tools fichier,
injection de faits. Testables sans réseau ni LLM.
"""
from pathlib import Path

import jarvis as jm

# ── _now_fr ──────────────────────────────────────────────────────────────

def test_now_fr_format():
    out = jm._now_fr()
    assert " — " in out
    assert any(mois in out for mois in jm._MOIS_FR)


def test_now_fr_jour_present():
    out = jm._now_fr()
    assert any(j in out for j in jm._JOURS_FR)


# ── _ssh_timeout — timeout adaptatif ─────────────────────────────────────

def test_ssh_timeout_apt_long():
    assert jm._ssh_timeout("apt-get install nginx") == 180


def test_ssh_timeout_dpkg_long():
    assert jm._ssh_timeout("dpkg --configure -a") == 180


def test_ssh_timeout_commande_normale_defaut():
    assert jm._ssh_timeout("systemctl status nginx") == 15
    assert jm._ssh_timeout("ls -la", default=30) == 30


# ── _think_filter_step — filtre <think>…</think> ─────────────────────────

def test_think_filter_texte_simple_emis():
    chunk, buf, in_think, stop = jm._think_filter_step("bonjour Marc", False)
    assert chunk == "bonjour Marc"
    assert in_think is False


def test_think_filter_ouverture_think():
    chunk, buf, in_think, _stop = jm._think_filter_step("avant<think>après", False)
    assert chunk == "avant"
    assert buf == "après"
    assert in_think is True


def test_think_filter_fermeture_pendant_think():
    chunk, buf, in_think, _stop = jm._think_filter_step("raisonnement</think>réponse", True)
    assert chunk == ""
    assert buf == "réponse"
    assert in_think is False


def test_think_filter_close_orphelin():
    """`</think>` sans `<think>` précédent → texte émis sans le tag."""
    chunk, _buf, _in, _stop = jm._think_filter_step("orphelin</think>suite", False)
    assert chunk == "orphelinsuite"


def test_think_filter_tag_partiel_bufferise():
    """Un `<think>` à cheval (fin de buffer) est conservé pour le token suivant."""
    chunk, buf, _in, _stop = jm._think_filter_step("texte<thi", False)
    assert chunk == "texte"
    assert buf == "<thi"


def test_think_filter_tout_thinking_jete():
    chunk, buf, in_think, _stop = jm._think_filter_step("encore du raisonnement", True)
    assert chunk == ""
    assert in_think is True


# ── _rag_chunk — découpage RAG ───────────────────────────────────────────

def test_rag_chunk_texte_court_ignore():
    """Un fragment < 50 caractères n'est pas indexé."""
    assert jm._rag_chunk("court", "src") == []


def test_rag_chunk_texte_long_decoupe():
    chunks = jm._rag_chunk("ligne de contenu réel. " * 400, "MEMORY.md")
    assert len(chunks) >= 2
    assert all(c["source"] == "MEMORY.md" for c in chunks)
    assert all(len(c["content"]) > 50 for c in chunks)


def test_rag_chunk_texte_vide():
    assert jm._rag_chunk("", "src") == []


# ── _check_local_write_path — garde écriture locale ──────────────────────

def test_check_write_path_systeme_refuse():
    err = jm._check_local_write_path(Path("C:/Windows/system32/evil.txt"))
    assert err is not None and "refusé" in err.lower()


def test_check_write_path_hors_workspace_refuse():
    err = jm._check_local_write_path(Path("C:/un-dossier-au-hasard/x.txt"))
    assert err is not None and "refusé" in err.lower()


def test_check_write_path_dans_workspace_ok():
    assert jm._check_local_write_path(jm._WORKSPACE_ROOT / "scratch_test.tmp") is None


def test_check_write_path_temp_ok(tmp_path):
    """Le dossier Temp est un workspace autorisé (générés / tests)."""
    assert jm._check_local_write_path(tmp_path / "f.txt") is None


# ── _tool_lire_fichier ───────────────────────────────────────────────────

def test_tool_lire_fichier_lit_contenu(tmp_path):
    f = tmp_path / "lu.txt"
    f.write_text("contenu test", encoding="utf-8")
    assert jm._tool_lire_fichier({"chemin": str(f)}) == "contenu test"


def test_tool_lire_fichier_introuvable():
    out = jm._tool_lire_fichier({"chemin": "Z:/nexiste/pas.txt"})
    assert "introuvable" in out.lower()


# ── _tool_ecrire_fichier ─────────────────────────────────────────────────

def test_tool_ecrire_fichier_ecrit_dans_temp(tmp_path):
    f = tmp_path / "ecrit.txt"
    out = jm._tool_ecrire_fichier({"chemin": str(f), "contenu": "données"})
    assert "succès" in out.lower()
    assert f.read_text(encoding="utf-8") == "données"


def test_tool_ecrire_fichier_chemin_systeme_refuse():
    out = jm._tool_ecrire_fichier({"chemin": "C:/Windows/system32/x.txt", "contenu": "x"})
    assert "refusé" in out.lower()


# ── _load_facts / _facts_inject ──────────────────────────────────────────

def test_load_facts_fichier_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(jm, "FACTS_FILE", tmp_path / "absent.json")
    assert jm._load_facts() == []


def test_load_facts_lit_liste(monkeypatch, tmp_path):
    fp = tmp_path / "facts.json"
    fp.write_text('{"facts": ["Marc aime le SOC", "RTX 5080"]}', encoding="utf-8")
    monkeypatch.setattr(jm, "FACTS_FILE", fp)
    assert jm._load_facts() == ["Marc aime le SOC", "RTX 5080"]


def test_facts_inject_ajoute_date(monkeypatch, tmp_path):
    monkeypatch.setattr(jm, "FACTS_FILE", tmp_path / "absent.json")
    out = jm._facts_inject("PROMPT SYSTÈME")
    assert out.startswith("PROMPT SYSTÈME")
    assert "Date et heure" in out


def test_facts_inject_inclut_les_faits(monkeypatch, tmp_path):
    fp = tmp_path / "facts.json"
    fp.write_text('{"facts": ["fait-test-xyz"]}', encoding="utf-8")
    monkeypatch.setattr(jm, "FACTS_FILE", fp)
    out = jm._facts_inject("SYS")
    assert "fait-test-xyz" in out
    assert "MÉMOIRE PERSISTANTE" in out


# ── _sec_log — journal sécurité ──────────────────────────────────────────

def test_sec_log_enregistre_evenement():
    before = len(jm._SEC_EVENTS)
    jm._sec_log("hard", "pattern-test-unique", "snippet")
    assert len(jm._SEC_EVENTS) == before + 1
    assert jm._SEC_EVENTS[-1]["pattern"] == "pattern-test-unique"
    assert jm._SEC_EVENTS[-1]["level"] == "hard"


# ── _cors_origin — politique CORS ────────────────────────────────────────

def test_cors_origin_localhost_autorise():
    assert jm._cors_origin("http://localhost") == "http://localhost"


def test_cors_origin_soc_dashboard_autorise():
    """Une origine du dashboard SOC (192.168.1.50) est renvoyée telle quelle."""
    assert jm._cors_origin("http://192.168.1.50") == "http://192.168.1.50"


def test_cors_origin_inconnue_repli_localhost():
    """Origine hors whitelist → repli sécurisé sur localhost."""
    assert jm._cors_origin("http://evil.example.com") == "http://localhost"


# ── _detect_service_restart — détection restart service ──────────────────

def test_detect_service_restart_nginx():
    host, ssh, svc = jm._detect_service_restart("redémarre nginx maintenant")
    assert (host, svc) == ("srv-ngix", "nginx")
    assert ssh is jm._ssh_ngix


def test_detect_service_restart_crowdsec():
    host, ssh, svc = jm._detect_service_restart("restart crowdsec")
    assert (host, svc) == ("srv-ngix", "crowdsec")


def test_detect_service_restart_fail2ban():
    _host, _ssh, svc = jm._detect_service_restart("relance fail2ban")
    assert svc == "fail2ban"


def test_detect_service_restart_apache_sur_clt():
    host, ssh, svc = jm._detect_service_restart("redémarre apache sur clt")
    assert (host, svc) == ("clt", "apache2")
    assert ssh is jm._ssh_clt


def test_detect_service_restart_apache_sans_hote_ambigu():
    """apache sans hôte explicite → 'ambiguous', pas de fonction SSH."""
    host, ssh, svc = jm._detect_service_restart("redémarre apache")
    assert (host, ssh, svc) == ("ambiguous", None, "apache2")


def test_detect_service_restart_aucun_match():
    assert jm._detect_service_restart("quelle heure est-il ?") is None


# ── _validate_protect_directives — garde directives nginx protégées ──────

def test_validate_protect_directives_restaure_valeur_modifiee():
    """Le LLM a changé une directive protégée → valeur d'origine restaurée."""
    original = "ssl_prefer_server_ciphers off;"
    llm = "ssl_prefer_server_ciphers on;"
    result, changes = jm._validate_protect_directives(original, llm)
    assert "off" in result
    assert len(changes) == 1


def test_validate_protect_directives_aucun_changement():
    """Directive identique → rien à restaurer."""
    content = "ssl_prefer_server_ciphers off;"
    result, changes = jm._validate_protect_directives(content, content)
    assert changes == []
    assert result == content


def test_validate_protect_directives_directive_absente():
    """Directive protégée absente de l'original → aucune restauration."""
    result, changes = jm._validate_protect_directives(
        "server_name example.com;", "server_name autre.com;")
    assert changes == []


# ── _get_model_profile — profil de prompt lié au modèle ──────────────────

def test_get_model_profile_binding_trouve(monkeypatch, tmp_path):
    f = tmp_path / "profiles.json"
    f.write_text('{"soc": {"model_binding": "phi4:14b", "content": "regles SOC"}}',
                 encoding="utf-8")
    monkeypatch.setattr(jm, "PROMPT_PROFILES_FILE", f)
    name, content = jm._get_model_profile("phi4:14b")
    assert (name, content) == ("soc", "regles SOC")


def test_get_model_profile_binding_absent(monkeypatch, tmp_path):
    f = tmp_path / "profiles.json"
    f.write_text('{"soc": {"model_binding": "phi4:14b"}}', encoding="utf-8")
    monkeypatch.setattr(jm, "PROMPT_PROFILES_FILE", f)
    assert jm._get_model_profile("modele-inconnu") == (None, None)


def test_get_model_profile_fichier_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(jm, "PROMPT_PROFILES_FILE", tmp_path / "absent.json")
    assert jm._get_model_profile("phi4:14b") == (None, None)


# ── _load_tasks / _save_tasks — persistance tâches planifiées ────────────

def test_load_tasks_fichier_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(jm, "TASKS_FILE", tmp_path / "absent.json")
    assert jm._load_tasks() == []


def test_save_puis_load_tasks_round_trip(monkeypatch, tmp_path):
    f = tmp_path / "jarvis_tasks.json"
    monkeypatch.setattr(jm, "TASKS_FILE", f)
    tasks = [{"id": "t1", "cmd": "backup"}]
    jm._save_tasks(tasks)
    assert jm._load_tasks() == tasks


def test_load_tasks_json_corrompu_renvoie_liste_vide(monkeypatch, tmp_path):
    f = tmp_path / "jarvis_tasks.json"
    f.write_text("{ pas du json", encoding="utf-8")
    monkeypatch.setattr(jm, "TASKS_FILE", f)
    assert jm._load_tasks() == []


# ── _load_model / _save_model — modèle Ollama persisté ───────────────────

def test_load_model_valeur_connue(monkeypatch, tmp_path):
    f = tmp_path / "model.json"
    f.write_text('{"model": "phi4:14b"}', encoding="utf-8")
    monkeypatch.setattr(jm, "MODEL_FILE", f)
    monkeypatch.setattr(jm, "MODELS", ["phi4:14b", "gemma4:latest"])
    assert jm._load_model() == "phi4:14b"


def test_load_model_valeur_inconnue_repli_premier(monkeypatch, tmp_path):
    """Modèle absent de MODELS → repli sur le premier modèle disponible."""
    f = tmp_path / "model.json"
    f.write_text('{"model": "modele-fantome"}', encoding="utf-8")
    monkeypatch.setattr(jm, "MODEL_FILE", f)
    monkeypatch.setattr(jm, "MODELS", ["phi4:14b", "gemma4:latest"])
    assert jm._load_model() == "phi4:14b"


def test_load_model_fichier_absent_repli(monkeypatch, tmp_path):
    monkeypatch.setattr(jm, "MODEL_FILE", tmp_path / "absent.json")
    monkeypatch.setattr(jm, "MODELS", ["gemma4:latest"])
    assert jm._load_model() == "gemma4:latest"


def test_save_model_ecrit_le_modele_courant(monkeypatch, tmp_path):
    f = tmp_path / "model.json"
    monkeypatch.setattr(jm, "MODEL_FILE", f)
    monkeypatch.setattr(jm, "MODEL", "qwen2.5-coder:14b")
    jm._save_model()
    import json as _j
    assert _j.loads(f.read_text(encoding="utf-8"))["model"] == "qwen2.5-coder:14b"


# ── load_memory / save_memory — historique conversationnel ───────────────

def test_load_memory_fichier_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(jm, "MEMORY_FILE", tmp_path / "absent.json")
    assert jm.load_memory() == []


def test_save_memory_filtre_et_round_trip(monkeypatch, tmp_path):
    """save_memory ne conserve que les messages user/assistant à contenu texte."""
    f = tmp_path / "jarvis_memory.json"
    monkeypatch.setattr(jm, "MEMORY_FILE", f)
    history = [
        {"role": "user", "content": "salut"},
        {"role": "assistant", "content": "bonjour"},
        {"role": "system", "content": "ignoré"},
        {"role": "user", "content": {"non": "texte"}},
    ]
    jm.save_memory(history)
    loaded = jm.load_memory()
    assert loaded == [
        {"role": "user", "content": "salut"},
        {"role": "assistant", "content": "bonjour"},
    ]


# ── _append_memory_summary / _load_memory_summary — résumés de session ───

def test_load_memory_summary_fichier_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(jm, "SUMMARY_FILE", tmp_path / "absent.json")
    assert jm._load_memory_summary() == ""


def test_append_puis_load_memory_summary(monkeypatch, tmp_path):
    f = tmp_path / "jarvis_memory_summary.json"
    monkeypatch.setattr(jm, "SUMMARY_FILE", f)
    jm._append_memory_summary("Marc a travaillé sur le refactor SOC.")
    out = jm._load_memory_summary()
    assert "refactor SOC" in out
