"""Tests chat_soc_inject — détection keywords SOC + injection contexte monitoring."""
from chat_soc_inject import SOC_KW, SOC_VOCAL_KW, inject

DEFAULT_RAW = '{"threat_score": 75, "active_attacks": 3}'
DEFAULT_CTX = "Score menace: 75/100. Attaques: 3."


def _fetch_ok(force):
    """Fetch monitoring qui réussit."""
    return True, DEFAULT_RAW


def _fetch_fail(force):
    """Fetch monitoring qui échoue (srv-ngix injoignable)."""
    return False, ""


def _build_ctx(data):
    return DEFAULT_CTX


def _call(**overrides):
    args = dict(
        system="SYS",
        last_user="que se passe-t-il ?",
        is_vocal=False,
        soc_ctx_injected=False,
        force_soc=False,
        fetch_monitoring_fn=_fetch_ok,
        build_monitoring_context_fn=_build_ctx,
    )
    args.update(overrides)
    return inject(**args)


# ── Détection keywords (SOC_KW vs SOC_VOCAL_KW) ──────────────────────────


def test_keyword_soc_simple_declenche_injection():
    system, trigger = _call(last_user="quel est le rapport soc ?")
    assert trigger is True
    assert "Score menace: 75/100" in system


def test_aucun_keyword_n_active_pas_le_trigger():
    system, trigger = _call(last_user="quelle heure est-il ?")
    assert trigger is False
    assert system == "SYS"


def test_keyword_crowdsec_active_le_trigger():
    _, trigger = _call(last_user="combien d'IPs bannies par crowdsec ?")
    assert trigger is True


def test_keyword_kill_chain_active_le_trigger():
    _, trigger = _call(last_user="affiche la kill chain")
    assert trigger is True


def test_detection_case_insensitive():
    """`SOC` en majuscules doit aussi déclencher."""
    _, trigger = _call(last_user="ANALYSE LA SITUATION")
    assert trigger is True


def test_keyword_partiel_dans_phrase_longue_active():
    msg = "salut, j'aimerais voir le rapport SOC stp"
    _, trigger = _call(last_user=msg)
    assert trigger is True


# ── Mode VOCAL (liste resserrée SOC_VOCAL_KW) ────────────────────────────


def test_mode_vocal_utilise_soc_vocal_kw():
    """`monitoring` est dans SOC_KW ET SOC_VOCAL_KW → trigger en vocal."""
    _, trigger = _call(last_user="status monitoring", is_vocal=True)
    assert trigger is True


def test_mode_vocal_n_inclut_pas_certains_keywords_du_mode_texte():
    """`incident` est dans SOC_KW mais PAS dans SOC_VOCAL_KW (faux positifs en conv)."""
    assert "incident" in SOC_KW
    assert "incident" not in SOC_VOCAL_KW
    _, trigger = _call(last_user="raconte-moi un incident", is_vocal=True)
    assert trigger is False


def test_mode_vocal_pareil_keyword_pareil_trigger():
    _, trigger = _call(last_user="kill chain", is_vocal=True)
    assert trigger is True


# ── force_soc : bypass keywords ──────────────────────────────────────────


def test_force_soc_active_meme_sans_keyword():
    """Dashboard SOC chat → force_soc=True, n'importe quelle question."""
    system, trigger = _call(last_user="bonjour", force_soc=True)
    assert trigger is True
    assert "Score menace: 75/100" in system


# ── Marqueur [NO_SOC] : opt-out par profil ───────────────────────────────


def test_marqueur_no_soc_dans_system_desactive_meme_avec_keyword():
    system, trigger = _call(system="SYS [NO_SOC]", last_user="rapport soc")
    assert trigger is False
    # Pas d'injection ajoutée
    assert "Score menace" not in system


def test_marqueur_no_soc_desactive_meme_avec_force_soc():
    """force_soc → trigger=True, puis [NO_SOC] le ramène à False."""
    system, trigger = _call(system="SYS [NO_SOC]", force_soc=True)
    assert trigger is False
    assert "Score menace" not in system


# ── soc_ctx_injected : déjà injecté → pas de double injection ────────────


def test_soc_ctx_deja_injected_n_appelle_pas_fetch_a_nouveau():
    captured = {"called": False}

    def fetch(force):
        captured["called"] = True
        return True, DEFAULT_RAW

    system, trigger = _call(
        last_user="rapport soc", soc_ctx_injected=True, fetch_monitoring_fn=fetch,
    )
    assert trigger is True
    assert captured["called"] is False
    # Pas d'ajout de contexte
    assert system == "SYS"


# ── last_user vide : pas d'injection ─────────────────────────────────────


def test_last_user_vide_n_injecte_rien():
    system, trigger = _call(last_user="", force_soc=True)
    # trigger reste True (force_soc) mais pas d'injection (last_user vide)
    assert trigger is True
    assert system == "SYS"


# ── Fetch échoue : garde-fou anti-hallucination ──────────────────────────


def test_fetch_echoue_injecte_garde_fou_anti_hallucination():
    system, trigger = _call(last_user="rapport soc", fetch_monitoring_fn=_fetch_fail)
    assert trigger is True
    assert "DONNÉES SOC INDISPONIBLES" in system
    assert "INTERDICTION ABSOLUE" in system
    # Doit forcer la réponse standardisée
    assert "Données temps réel SOC non disponibles" in system


def test_fetch_renvoie_raw_vide_traite_comme_echec():
    """ok=True mais raw vide → garde-fou (la condition est `ok and raw`)."""
    system, _ = _call(last_user="rapport soc", fetch_monitoring_fn=lambda force: (True, ""))
    assert "DONNÉES SOC INDISPONIBLES" in system


# ── build_monitoring_context_fn lève une exception ───────────────────────


def test_build_context_exception_fallback_sur_donnees_brutes():
    def build_raises(data):
        raise ValueError("parse fail")

    system, _ = _call(last_user="rapport soc", build_monitoring_context_fn=build_raises)
    assert "Données brutes monitoring.json" in system
    assert "parse partiel: parse fail" in system
    # Tronqué à 2000 chars max — DEFAULT_RAW est court, présent intégralement
    assert DEFAULT_RAW in system


def test_build_context_exception_avec_raw_long_est_tronque_a_2000():
    long_raw = "X" * 5000
    captured = {}

    def fetch(force):
        return True, long_raw

    def build_raises(data):
        raise RuntimeError("err")

    system, _ = _call(
        last_user="rapport soc", fetch_monitoring_fn=fetch,
        build_monitoring_context_fn=build_raises,
    )
    captured["len"] = system.count("X")
    # Doit contenir 2000 X (tronqué), pas 5000
    assert captured["len"] == 2000


def test_fetch_appele_avec_force_true():
    captured = {}

    def fetch(force):
        captured["force"] = force
        return True, DEFAULT_RAW

    _call(last_user="rapport soc", fetch_monitoring_fn=fetch)
    assert captured["force"] is True


# ── Constantes — sanity check ─────────────────────────────────────────────


def test_soc_kw_contient_les_termes_critiques():
    for kw in ["soc", "crowdsec", "kill chain", "menace", "attaque"]:
        assert kw in SOC_KW


def test_soc_vocal_kw_est_un_sous_ensemble_resserre():
    """SOC_VOCAL_KW exclut volontairement certains keywords trop génériques en vocal."""
    # Termes présents dans SOC_KW mais absents de SOC_VOCAL_KW
    exclusions_vocal = {"alerte", "incident"}
    for kw in exclusions_vocal:
        assert kw in SOC_KW, f"{kw} devrait être dans SOC_KW"
        assert kw not in SOC_VOCAL_KW, f"{kw} ne devrait pas être dans SOC_VOCAL_KW"
