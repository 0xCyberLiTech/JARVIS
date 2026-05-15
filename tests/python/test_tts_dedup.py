"""Tests tts_dedup — fenêtre 60s anti-doublon TTS cross-source (python-speak ↔ /api/tts)."""
import importlib

import tts_dedup


def _reset_module_state():
    """Réinitialise l'état module-level entre tests."""
    importlib.reload(tts_dedup)


def test_premier_appel_retourne_false_et_enregistre():
    _reset_module_state()
    assert tts_dedup.check_and_register("alerte SOC", now=100.0) is False


def test_meme_texte_dans_la_fenetre_retourne_true():
    _reset_module_state()
    tts_dedup.check_and_register("alerte SOC", now=100.0)
    # 30 secondes plus tard, même texte → duplicat
    assert tts_dedup.check_and_register("alerte SOC", now=130.0) is True


def test_meme_texte_apres_la_fenetre_retourne_false():
    _reset_module_state()
    tts_dedup.check_and_register("alerte SOC", now=100.0)
    # 60.1 secondes plus tard → fenêtre expirée → nouveau
    assert tts_dedup.check_and_register("alerte SOC", now=160.1) is False


def test_texte_different_retourne_false_meme_dans_la_fenetre():
    _reset_module_state()
    tts_dedup.check_and_register("alerte SOC", now=100.0)
    assert tts_dedup.check_and_register("autre texte", now=110.0) is False


def test_nouveau_texte_remplace_l_ancien_dans_le_state():
    _reset_module_state()
    tts_dedup.check_and_register("texte A", now=100.0)
    tts_dedup.check_and_register("texte B", now=110.0)
    # L'ancien texte A n'est plus mémorisé → re-prononçable
    assert tts_dedup.check_and_register("texte A", now=120.0) is False


def test_fenetre_dedup_constante_est_60s():
    assert tts_dedup.DEDUP_WINDOW_S == 60.0


def test_chaine_vide_traitee_comme_n_importe_quelle_chaine():
    _reset_module_state()
    assert tts_dedup.check_and_register("", now=100.0) is False
    assert tts_dedup.check_and_register("", now=110.0) is True


def test_borne_exacte_de_fenetre_est_exclusive():
    """À now=160.0 pile (delta = 60.0), la condition `< 60.0` est False → nouveau."""
    _reset_module_state()
    tts_dedup.check_and_register("borne", now=100.0)
    assert tts_dedup.check_and_register("borne", now=160.0) is False
