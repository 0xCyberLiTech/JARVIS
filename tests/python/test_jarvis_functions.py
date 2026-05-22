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
