"""Tests chat_routing — sélection modèle Ollama selon mode + flags requête (zéro IO)."""
from chat_routing import resolve_model

GENERAL = "gemma4:latest"
CODE = "qwen2.5-coder:14b"


def _call(**overrides):
    """Helper avec defaults sains."""
    args = dict(
        is_vocal=False,
        no_tools=False,
        model_override=None,
        general_model=GENERAL,
        code_model=CODE,
        current_mode="soc",
    )
    args.update(overrides)
    return resolve_model(**args)


def test_override_soc_renvoie_none_et_label_soc():
    assert _call(model_override="soc") == (None, "SOC")


def test_override_general_renvoie_general_model():
    assert _call(model_override="general") == (GENERAL, "GENERAL")


def test_no_tools_priorite_sur_mode_renvoie_code_term():
    assert _call(no_tools=True, current_mode="soc") == (CODE, "CODE-TERM")


def test_mode_code_renvoie_code_model_label_code():
    assert _call(current_mode="code") == (CODE, "CODE")


def test_is_vocal_en_mode_soc_renvoie_general_model_label_vocal():
    assert _call(is_vocal=True) == (GENERAL, "VOCAL")


def test_mode_general_renvoie_general_model_label_general():
    assert _call(current_mode="general") == (GENERAL, "GENERAL")


def test_mode_soc_par_defaut_renvoie_none_label_soc():
    """Mode SOC sans flags = MODEL par défaut (phi4:14b)."""
    assert _call(current_mode="soc") == (None, "SOC")


def test_mode_code_reasoning_inconnu_tombe_en_soc_par_defaut():
    """current_mode='code_reasoning' n'est pas géré explicitement → SOC default."""
    assert _call(current_mode="code_reasoning") == (None, "SOC")


def test_priorite_override_soc_l_emporte_sur_no_tools():
    """model_override='soc' est testé EN PREMIER → bat no_tools."""
    assert _call(model_override="soc", no_tools=True, current_mode="code") == (None, "SOC")


def test_priorite_override_general_l_emporte_sur_no_tools():
    assert _call(model_override="general", no_tools=True) == (GENERAL, "GENERAL")


def test_priorite_no_tools_l_emporte_sur_current_mode():
    """no_tools est testé avant current_mode='code'."""
    assert _call(no_tools=True, current_mode="code") == (CODE, "CODE-TERM")


def test_is_vocal_combine_avec_mode_general_donne_label_vocal():
    """is_vocal a priorité sur general dans le label."""
    assert _call(is_vocal=True, current_mode="general") == (GENERAL, "VOCAL")
