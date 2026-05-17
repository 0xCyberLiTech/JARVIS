"""Tests chat_soc_inject — détection keywords SOC + injection contexte monitoring."""
import json as _json

from chat_soc_inject import (
    SOC_KW,
    SOC_VOCAL_KW,
    _format_defense_block,
    _kpi_with_delta,
    inject,
)

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


# ── _kpi_with_delta : formatage val + delta vs hier ───────────────────────


def test_kpi_with_delta_sans_delta_renvoie_juste_la_val():
    assert _kpi_with_delta({"bans_24h": 42}, {}, "bans_24h") == "42"


def test_kpi_with_delta_avec_pct_positif_prefixe_plus():
    out = _kpi_with_delta({"bans_24h": 42}, {"bans_24h": {"pct": 15}}, "bans_24h")
    assert out == "42 (+15%)"


def test_kpi_with_delta_avec_pct_negatif_garde_signe():
    out = _kpi_with_delta({"bans_24h": 30}, {"bans_24h": {"pct": -25}}, "bans_24h")
    assert out == "30 (-25%)"


def test_kpi_with_delta_pct_zero_prefixe_plus():
    """0% est traité comme positif (>= 0 → '+')."""
    out = _kpi_with_delta({"bans_24h": 10}, {"bans_24h": {"pct": 0}}, "bans_24h")
    assert out == "10 (+0%)"


def test_kpi_with_delta_kpi_absent_retourne_zero():
    """Clé absente du kpi → val=0."""
    assert _kpi_with_delta({}, {}, "bans_24h") == "0"


def test_kpi_with_delta_deltas_none_pas_de_crash():
    """deltas=None → comportement = pas de delta connu."""
    assert _kpi_with_delta({"bans_24h": 5}, None, "bans_24h") == "5"


def test_kpi_with_delta_pct_none_pas_de_suffixe():
    """delta présent mais pct=None → pas de suffixe."""
    out = _kpi_with_delta({"bans_24h": 5}, {"bans_24h": {"pct": None}}, "bans_24h")
    assert out == "5"


# ── _format_defense_block : sérialisation compact ~500 chars ───────────────


def _defense_full():
    """defense_24h.json typique v1.2 — heatmap 96 buckets 15min."""
    return {
        "generated_at": "2026-05-17T10:00:00Z",
        "kpi": {"total_actions": 1000, "bans_24h": 50, "waf_clt_24h": 100,
                "waf_pa85_24h": 75, "ids_sev1": 5, "ids_sev2": 20,
                "geo_24h": 200, "fail2ban_active": 12, "ufw_24h": 300},
        "kpi_delta": {"bans_24h": {"pct": 10}, "waf_clt_24h": {"pct": -5}},
        "heatmap_24h": [0] * 95 + [310],   # pic sur la tranche courante (dernier bucket)
        "heatmap_bucket_min": 15,
        "top_country": [{"value": "CN", "count": 120}, {"value": "RU", "count": 80}],
        "top_as": [{"value": "AS4134", "count": 60}],
        "top_scenario": [{"value": "http-probing", "count": 40}],
    }


def test_format_defense_block_contient_kpi_principaux():
    out = _format_defense_block(_defense_full())
    assert "Actions totales: 1000" in out
    assert "Bans CrowdSec: 50 (+10%)" in out
    assert "WAF CLT: 100 (-5%)" in out
    assert "Suricata: 5 sev1/20 sev2" in out
    assert "GeoBlock: 200" in out


def test_format_defense_block_peak_sur_tranche_courante():
    """Le dernier bucket de heatmap a la valeur max → label 'tranche courante'."""
    out = _format_defense_block(_defense_full())
    assert "tranche courante" in out
    assert "310 actions sur la tranche" in out


def test_format_defense_block_peak_minutes_ago_sous_60():
    """Pic à 2 buckets de la fin (15min × 2 = 30min)."""
    d = _defense_full()
    d["heatmap_24h"] = [0] * 93 + [300, 0, 0]   # peak à index 93 → (96-1-93)=2 buckets ago
    out = _format_defense_block(d)
    assert "il y a 30min" in out


def test_format_defense_block_peak_h_pile_sans_minutes():
    """Pic à 4 buckets (15min × 4 = 60min = 1h pile)."""
    d = _defense_full()
    d["heatmap_24h"] = [0] * 91 + [300] + [0] * 4   # index 91 → (95-91)=4 → 60min → h-1
    out = _format_defense_block(d)
    assert "h-1" in out
    assert "h-1 0min" not in out   # pas d'ajout " 0min" si pile


def test_format_defense_block_peak_h_avec_minutes_restantes():
    """Pic à 5 buckets (15min × 5 = 75min = h-1 15min)."""
    d = _defense_full()
    d["heatmap_24h"] = [0] * 90 + [300] + [0] * 5   # index 90 → (95-90)=5 → 75min → h-1 15min
    out = _format_defense_block(d)
    assert "h-1 15min" in out


def test_format_defense_block_heatmap_vide_renvoie_na():
    d = _defense_full()
    d["heatmap_24h"] = []
    out = _format_defense_block(d)
    assert "n/a" in out


def test_format_defense_block_bucket_min_fallback_60_si_24_buckets():
    """Si heatmap_bucket_min absent ET len(heat) <= 24 → fallback 60min/bucket."""
    d = _defense_full()
    d["heatmap_24h"] = [0] * 23 + [100]   # 24 buckets
    d.pop("heatmap_bucket_min")
    out = _format_defense_block(d)
    # Pic sur tranche courante (dernier) → "tranche courante"
    assert "tranche courante" in out
    # Granularité = 60min mentionnée dans le label "Pic 60min:"
    assert "Pic 60min:" in out


def test_format_defense_block_bucket_min_fallback_15_si_plus_de_24_buckets():
    """Si heatmap_bucket_min absent ET len(heat) > 24 → fallback 15min/bucket."""
    d = _defense_full()
    d.pop("heatmap_bucket_min")
    out = _format_defense_block(d)
    assert "Pic 15min:" in out


def test_format_defense_block_top_value_tronque_a_14_chars():
    """Une value trop longue est tronquée à 14 chars."""
    d = _defense_full()
    d["top_country"] = [{"value": "ABCDEFGHIJKLMNOPQ", "count": 99}]  # 17 chars
    out = _format_defense_block(d)
    assert "ABCDEFGHIJKLMN(99)" in out  # 14 chars + (99)


def test_format_defense_block_top_value_absent_devient_question_mark():
    d = _defense_full()
    d["top_as"] = [{"count": 50}]   # pas de "value"
    out = _format_defense_block(d)
    assert "?(50)" in out


def test_format_defense_block_generated_at_inclus_dans_header():
    out = _format_defense_block(_defense_full())
    assert "[DÉFENSE 24H AGRÉGÉE — 2026-05-17T10:00:00Z]" in out


def test_format_defense_block_generated_at_absent_devient_question_mark():
    d = _defense_full()
    d.pop("generated_at")
    out = _format_defense_block(d)
    assert "[DÉFENSE 24H AGRÉGÉE — ?]" in out


def test_format_defense_block_top_listes_vides():
    d = _defense_full()
    d["top_country"] = []
    d["top_as"] = None   # accepte None aussi (`x or []`)
    out = _format_defense_block(d)
    assert "Top pays: \n" in out
    assert "Top AS: \n" in out


# ── inject() avec fetch_defense_fn (branch ligne 184-189) ─────────────────


def test_inject_avec_fetch_defense_ajoute_bloc_compact():
    """fetch_defense_fn fourni + SOC déclenché → bloc DÉFENSE 24H injecté."""
    defense_raw = _json.dumps(_defense_full())
    system, trigger = _call(
        last_user="rapport soc",
        fetch_defense_fn=lambda force: (True, defense_raw),
    )
    assert trigger is True
    assert "DÉFENSE 24H AGRÉGÉE" in system
    assert "Actions totales: 1000" in system


def test_inject_fetch_defense_echoue_ne_bloque_pas():
    """fetch_defense renvoie (False, '') → pas de bloc ajouté mais inject continue."""
    system, _ = _call(
        last_user="rapport soc",
        fetch_defense_fn=lambda force: (False, ""),
    )
    # Le système contient toujours l'injection monitoring de base
    assert "Score menace: 75/100" in system
    # Pas de bloc défense
    assert "DÉFENSE 24H AGRÉGÉE" not in system


def test_inject_fetch_defense_json_invalide_silencieux():
    """JSON invalide → ne lève pas, pas de bloc ajouté (bloc défense optionnel)."""
    system, _ = _call(
        last_user="rapport soc",
        fetch_defense_fn=lambda force: (True, "{not json"),
    )
    # Pas de crash, injection monitoring de base présente
    assert "Score menace: 75/100" in system
    assert "DÉFENSE 24H AGRÉGÉE" not in system


def test_inject_sans_fetch_defense_pas_de_bloc():
    """fetch_defense_fn=None (défaut) → pas de bloc défense ajouté."""
    system, _ = _call(last_user="rapport soc")
    assert "DÉFENSE 24H AGRÉGÉE" not in system


def test_inject_fetch_defense_appele_avec_force_false():
    """fetch_defense est appelé avec force=False (cache OK pour défense, frais pour monitoring)."""
    captured = {}

    def fetch_def(force):
        captured["force"] = force
        return True, _json.dumps(_defense_full())

    _call(last_user="rapport soc", fetch_defense_fn=fetch_def)
    assert captured["force"] is False
