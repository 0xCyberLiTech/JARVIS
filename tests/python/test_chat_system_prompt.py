"""Tests chat_system_prompt — orchestration assemblage system prompt (5 helpers DI)."""
import re

from chat_system_prompt import build


def _make_call(**overrides):
    """Helper avec defaults : tous les fn = identité, soc retourne (system, False)."""
    args = dict(
        last_user="question",
        web_enabled=False,
        soc_ctx_injected=False,
        is_vocal=False,
        system_prompt="SYS_BASE",
        facts_inject_fn=lambda s: s + "+facts",
        rag_relevant_re=re.compile(r"\bRAG_KW\b"),
        rag_inject_fn=lambda s, q: s + "+rag",
        web_search_fn=lambda q: f"WEB[{q}]",
        soc_inject_fn=lambda s, q, vocal, ctx, force: (s + "+soc", False),
        pve_inject_fn=lambda s, q: s + "+pve",
        force_soc=False,
    )
    args.update(overrides)
    return build(
        last_user=args.pop("last_user"),
        web_enabled=args.pop("web_enabled"),
        soc_ctx_injected=args.pop("soc_ctx_injected"),
        is_vocal=args.pop("is_vocal"),
        **args,
    )


# ── Pipeline complet ──────────────────────────────────────────────────────


def test_pipeline_normal_appelle_facts_puis_soc_puis_pve():
    """Pas de RAG (msg court, pas de keyword), pas de web → facts + soc + pve."""
    system, soc_trigger = _make_call(last_user="ok")
    assert system == "SYS_BASE+facts+soc+pve"
    assert soc_trigger is False


def test_pipeline_avec_message_long_60_chars_active_rag():
    long = "a" * 60  # >= 60 chars exactement
    system, _ = _make_call(last_user=long)
    assert "+rag" in system
    assert system == "SYS_BASE+facts+rag+soc+pve"


def test_pipeline_avec_keyword_rag_meme_message_court_active_rag():
    system, _ = _make_call(last_user="RAG_KW")
    assert "+rag" in system


def test_message_juste_en_dessous_60_chars_sans_kw_n_active_pas_rag():
    short = "a" * 59
    system, _ = _make_call(last_user=short)
    assert "+rag" not in system


def test_strip_avant_test_60_chars_pour_le_rag():
    """Padding par espaces n'active pas le RAG (strip avant len)."""
    msg = "  " + "a" * 30 + "  "  # 30 chars utiles + 4 espaces = 34 < 60
    system, _ = _make_call(last_user=msg)
    assert "+rag" not in system


# ── Web search ────────────────────────────────────────────────────────────


def test_web_enabled_avec_question_injecte_resultats_web():
    system, _ = _make_call(web_enabled=True, last_user="cherche X")
    assert "WEB[cherche X]" in system
    assert "Tu as accès à internet" in system


def test_web_enabled_avec_question_vide_n_injecte_pas():
    """`if web_enabled and last_user` : last_user="" est falsy."""
    system, _ = _make_call(web_enabled=True, last_user="")
    assert "WEB[" not in system


def test_web_disabled_n_injecte_jamais_meme_avec_question():
    system, _ = _make_call(web_enabled=False, last_user="cherche X")
    assert "WEB[" not in system


# ── SOC trigger remontée ─────────────────────────────────────────────────


def test_soc_trigger_true_est_remonte_par_la_fonction():
    """Si soc_inject_fn retourne True, build retourne True."""
    system, soc_trigger = _make_call(
        soc_inject_fn=lambda s, q, vocal, ctx, force: (s + "+soc", True),
    )
    assert soc_trigger is True


def test_force_soc_est_passe_a_soc_inject_fn():
    captured = {}

    def soc_fn(s, q, vocal, ctx, force):
        captured["force"] = force
        return s, False

    _make_call(soc_inject_fn=soc_fn, force_soc=True)
    assert captured["force"] is True


def test_is_vocal_et_soc_ctx_injected_passes_a_soc_fn():
    captured = {}

    def soc_fn(s, q, vocal, ctx, force):
        captured.update(vocal=vocal, ctx=ctx)
        return s, False

    _make_call(soc_inject_fn=soc_fn, is_vocal=True, soc_ctx_injected=True)
    assert captured == {"vocal": True, "ctx": True}


# ── Ordre des helpers ────────────────────────────────────────────────────


def test_helpers_appeles_dans_l_ordre_facts_rag_web_soc_pve():
    appels = []

    def facts_fn(s):
        appels.append("facts")
        return s

    def rag_fn(s, q):
        appels.append("rag")
        return s

    def web_fn(q):
        appels.append("web")
        return "WEB"

    def soc_fn(s, q, v, c, f):
        appels.append("soc")
        return s, False

    def pve_fn(s, q):
        appels.append("pve")
        return s

    _make_call(
        last_user="a" * 70,  # active RAG
        web_enabled=True,
        facts_inject_fn=facts_fn,
        rag_inject_fn=rag_fn,
        web_search_fn=web_fn,
        soc_inject_fn=soc_fn,
        pve_inject_fn=pve_fn,
    )
    assert appels == ["facts", "rag", "web", "soc", "pve"]
