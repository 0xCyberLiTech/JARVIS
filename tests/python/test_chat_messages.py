"""Tests chat_messages — assemblage history → liste messages Ollama (zéro IO)."""
from chat_messages import _VOCAL_OVERRIDE, build_messages


def test_mode_normal_renvoie_system_puis_history():
    history = [
        {"role": "user", "content": "salut"},
        {"role": "assistant", "content": "bonjour Marc"},
    ]
    out = build_messages("tu es JARVIS", history, is_vocal=False)
    assert out == [{"role": "system", "content": "tu es JARVIS"}, *history]


def test_mode_normal_history_vide():
    out = build_messages("tu es JARVIS", [], is_vocal=False)
    assert out == [{"role": "system", "content": "tu es JARVIS"}]


def test_mode_vocal_avec_history_injecte_override_avant_dernier_msg():
    history = [
        {"role": "user", "content": "premier"},
        {"role": "assistant", "content": "réponse"},
        {"role": "user", "content": "dernier message"},
    ]
    out = build_messages("system base", history, is_vocal=True)
    assert out == [
        {"role": "system", "content": "system base"},
        {"role": "user", "content": "premier"},
        {"role": "assistant", "content": "réponse"},
        {"role": "system", "content": _VOCAL_OVERRIDE},
        {"role": "user", "content": "dernier message"},
    ]


def test_mode_vocal_sans_history_concatene_override_au_system():
    out = build_messages("system base", [], is_vocal=True)
    assert out == [{"role": "system", "content": "system base\n\n" + _VOCAL_OVERRIDE}]


def test_mode_vocal_avec_un_seul_msg_history_injecte_override_avant():
    history = [{"role": "user", "content": "salut"}]
    out = build_messages("sys", history, is_vocal=True)
    assert out == [
        {"role": "system", "content": "sys"},
        {"role": "system", "content": _VOCAL_OVERRIDE},
        {"role": "user", "content": "salut"},
    ]


def test_vocal_override_contient_consignes_clefs():
    """Sanity check : l'override vocal mentionne bien les règles attendues."""
    assert "MODE VOCAL JARVIS" in _VOCAL_OVERRIDE
    assert "1 à 3 phrases" in _VOCAL_OVERRIDE
    assert "JAMAIS de markdown" in _VOCAL_OVERRIDE
    assert "CRITIQUE" in _VOCAL_OVERRIDE


def test_history_n_est_pas_mute_par_la_fonction():
    history = [{"role": "user", "content": "x"}]
    history_avant = list(history)
    build_messages("sys", history, is_vocal=True)
    assert history == history_avant
