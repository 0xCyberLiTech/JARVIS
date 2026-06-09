"""Tests llm_opts — construction options Ollama selon contexte SOC, modèle, longueur."""
from llm_opts import (
    DEFAULT_NUM_CTX_SHORT,
    DEFAULT_REASONING_NP_MIN,
    DEFAULT_SOC_NUM_CTX,
    DEFAULT_SOC_TEMPERATURE,
    REASONING_RE,
    build_llm_opts,
)

DEFAULT_MODEL = "phi4:14b"
LLM_PARAMS = {"num_ctx": 8192, "temperature": 0.7}


def _call(**overrides):
    args = dict(
        np_override=None,
        soc_ctx_injected=False,
        soc_trigger=False,
        active_model=None,
        msg_len=0,
        default_model=DEFAULT_MODEL,
        llm_params=LLM_PARAMS,
    )
    args.update(overrides)
    return build_llm_opts(**args)


# ── Defaults / cas de base ────────────────────────────────────────────────


def test_aucun_flag_aucune_longueur_renvoie_none():
    """Pas d'override np, pas de SOC, msg_len=0 → None (= defaults Ollama)."""
    assert _call() is None


def test_constantes_sont_les_valeurs_attendues():
    assert DEFAULT_SOC_TEMPERATURE == 0.2
    assert DEFAULT_SOC_NUM_CTX == 8192
    assert DEFAULT_NUM_CTX_SHORT == 4096
    assert DEFAULT_REASONING_NP_MIN == 768


# ── num_predict (np_override) ─────────────────────────────────────────────


def test_np_override_int_est_propage():
    out = _call(np_override=512)
    assert out == {"num_predict": 512}


def test_np_override_string_numerique_est_converti():
    out = _call(np_override="256")
    assert out == {"num_predict": 256}


def test_np_override_invalide_est_ignore():
    """Une valeur non-numérique → np devient None → pas dans opts."""
    assert _call(np_override="abc") is None


def test_np_override_none_explicite_est_ignore():
    assert _call(np_override=None) is None


# ── Mode SOC (ctx injecté ou trigger) ─────────────────────────────────────


def test_soc_ctx_injected_force_temperature_02_et_num_ctx_8192():
    out = _call(soc_ctx_injected=True)
    assert out["temperature"] == 0.2
    assert out["num_ctx"] == 8192


def test_soc_trigger_seul_force_aussi_temperature_et_num_ctx():
    out = _call(soc_trigger=True)
    assert out["temperature"] == 0.2
    assert out["num_ctx"] == 8192


def test_soc_combine_avec_np_override_garde_les_deux():
    out = _call(np_override=400, soc_ctx_injected=True)
    assert out == {"num_predict": 400, "temperature": 0.2, "num_ctx": 8192}


# ── Plancher reasoning en SOC ─────────────────────────────────────────────


def test_modele_qwen3_reasoning_en_soc_force_plancher_768():
    """qwen3:8b matché par REASONING_RE → plancher 768 si np en dessous."""
    out = _call(np_override=300, soc_ctx_injected=True, active_model="qwen3:8b")
    assert out["num_predict"] == 768


def test_modele_phi4_reasoning_en_soc_force_plancher_768():
    """phi4-reasoning matche REASONING_RE → np doit être >= 768."""
    out = _call(np_override=200, soc_ctx_injected=True, active_model="phi4-reasoning:14b")
    assert out["num_predict"] == 768


def test_modele_deepseek_r1_en_soc_force_plancher_768():
    out = _call(np_override=500, soc_ctx_injected=True, active_model="deepseek-r1:7b")
    assert out["num_predict"] == 768


def test_modele_reasoning_avec_np_deja_au_dessus_garde_la_valeur():
    """np=1500 > 768 → garde 1500."""
    out = _call(np_override=1500, soc_ctx_injected=True, active_model="phi4-reasoning")
    assert out["num_predict"] == 1500


def test_plancher_reasoning_ne_s_applique_pas_hors_soc():
    """phi4-reasoning hors SOC → np garde sa valeur."""
    out = _call(np_override=200, soc_ctx_injected=False, active_model="phi4-reasoning:14b")
    assert out["num_predict"] == 200


def test_modele_reasoning_default_si_active_model_none():
    """active_model=None → fallback sur default_model pour le test reasoning."""
    out = _call(np_override=200, soc_ctx_injected=True, active_model=None,
                default_model="phi4-reasoning:14b")
    assert out["num_predict"] == 768


# ── Requête courte (msg_len < 200) ───────────────────────────────────────


def test_requete_courte_hors_soc_active_num_ctx_short():
    out = _call(msg_len=50)
    assert out == {"num_ctx": 4096}


def test_requete_courte_borne_199_active_num_ctx_short():
    out = _call(msg_len=199)
    assert out == {"num_ctx": 4096}


def test_requete_courte_borne_200_n_active_pas_num_ctx_short():
    """msg_len=200 → condition < 200 False → pas d'override."""
    assert _call(msg_len=200) is None


def test_requete_courte_msg_len_zero_n_active_pas_num_ctx_short():
    """msg_len=0 → condition msg_len > 0 False → pas d'override."""
    assert _call(msg_len=0) is None


def test_num_ctx_short_respecte_le_minimum_avec_llm_params():
    """min(num_ctx_short=4096, llm_params['num_ctx']=2048) = 2048."""
    out = _call(msg_len=50, llm_params={"num_ctx": 2048})
    assert out == {"num_ctx": 2048}


def test_requete_courte_en_soc_le_soc_l_emporte():
    """SOC actif → num_ctx 8192 (pas 4096), même si msg court."""
    out = _call(msg_len=50, soc_ctx_injected=True)
    assert out["num_ctx"] == 8192


# ── Pattern reasoning ────────────────────────────────────────────────────


def test_pattern_reasoning_match_phi4_reasoning():
    assert REASONING_RE.search("phi4-reasoning:14b") is not None


def test_pattern_reasoning_match_deepseek_r1():
    assert REASONING_RE.search("deepseek-r1:7b") is not None


def test_pattern_reasoning_ne_match_pas_phi4():
    assert REASONING_RE.search("phi4:14b") is None


def test_pattern_reasoning_match_qwen3():
    """qwen3 est un modèle reasoning (think natif) — doit matcher REASONING_RE."""
    assert REASONING_RE.search("qwen3:8b") is not None
    assert REASONING_RE.search("qwen3:14b") is not None


def test_pattern_reasoning_case_insensitive():
    assert REASONING_RE.search("DEEPSEEK-R1") is not None
