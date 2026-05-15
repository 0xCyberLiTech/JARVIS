"""Tests tts_cleaner — markdown → texte parlable + IP chiffre par chiffre."""
from tts_cleaner import _DIGITS_FR, _ip_octet, clean_for_tts, replace_ips

# ── Helper _ip_octet ──────────────────────────────────────────────────────


def test_ip_octet_192_devient_un_neuf_deux():
    assert _ip_octet("192") == "un neuf deux"


def test_ip_octet_zero_seul():
    assert _ip_octet("0") == "zéro"


def test_ip_octet_un_chiffre():
    assert _ip_octet("5") == "cinq"


def test_ip_octet_trois_chiffres_meme_digit():
    assert _ip_octet("111") == "un un un"


def test_digits_fr_couvre_0_a_9():
    assert set(_DIGITS_FR.keys()) == {str(i) for i in range(10)}


# ── replace_ips ───────────────────────────────────────────────────────────


def test_replace_ips_format_point():
    assert replace_ips("ban 192.168.1.50") == "ban un neuf deux point un six huit point un point cinq zéro"


def test_replace_ips_format_tiret():
    """Format avec tirets utilisé par certains profils LLM."""
    out = replace_ips("ban 10-0-0-1")
    assert out == "ban un zéro point zéro point zéro point un"


def test_replace_ips_plusieurs_ips_dans_le_texte():
    out = replace_ips("source 1.2.3.4 vers 5.6.7.8")
    assert "un point deux point trois point quatre" in out
    assert "cinq point six point sept point huit" in out


def test_replace_ips_pas_d_ip_pas_de_changement():
    assert replace_ips("juste du texte sans IP") == "juste du texte sans IP"


def test_replace_ips_n_attaque_pas_les_pseudo_ips():
    """`1234.5678` n'est pas une IP (groupes > 3 chiffres) → inchangé."""
    assert replace_ips("ref 1234.5678.91011.1213") == "ref 1234.5678.91011.1213"


# ── clean_for_tts (cœur du module) ────────────────────────────────────────


def test_clean_supprime_balises_think_deepseek():
    assert clean_for_tts("<think>raisonnement interne</think>réponse") == "réponse"


def test_clean_supprime_blocs_de_code_triple_backtick():
    text = "voici du code:\n```python\nx = 1\n```\nfin"
    assert "x = 1" not in clean_for_tts(text)
    assert "voici du code" in clean_for_tts(text)


def test_clean_garde_contenu_du_code_inline():
    """Le code inline `foo` doit garder le contenu."""
    assert clean_for_tts("la commande `ls -la` liste") == "la commande ls -la liste"


def test_clean_supprime_les_etoiles_du_gras():
    assert clean_for_tts("**important** alerte") == "important alerte"


def test_clean_supprime_les_underscores_double_du_gras():
    assert clean_for_tts("__gras__ texte") == "gras texte"


def test_clean_supprime_les_etoiles_simples_de_l_italique():
    assert clean_for_tts("*emphase* ici") == "emphase ici"


def test_clean_supprime_les_tildes_du_barre():
    assert clean_for_tts("~~rayé~~ et le reste") == "rayé et le reste"


def test_clean_supprime_les_diese_des_titres():
    assert clean_for_tts("# Titre principal\nsuite") == "Titre principal\nsuite"
    assert clean_for_tts("### Sous-titre") == "Sous-titre"


def test_clean_supprime_les_numeros_de_liste_numerotee():
    out = clean_for_tts("1. premier\n2. deuxième")
    assert out == "premier\ndeuxième"


def test_clean_supprime_les_puces_de_liste():
    out = clean_for_tts("- item un\n* item deux\n+ item trois")
    assert out == "item un\nitem deux\nitem trois"


def test_clean_garde_le_texte_des_liens_markdown():
    assert clean_for_tts("voir [doc](http://example.com) pour info") == "voir doc pour info"


def test_clean_supprime_les_images_markdown():
    """L'espace double laissé par la suppression est normalisé à 1 par la regex finale."""
    assert clean_for_tts("texte ![alt](img.png) suite") == "texte suite"


def test_clean_remplace_les_pipes_de_tableau_par_espace():
    out = clean_for_tts("| col1 | col2 |")
    assert "|" not in out


def test_clean_supprime_les_lignes_de_separation():
    out = clean_for_tts("avant\n---\naprès")
    assert "---" not in out


def test_clean_supprime_les_chevrons_de_citation():
    assert clean_for_tts("> citation\nsuite") == "citation\nsuite"


def test_clean_normalise_les_lignes_vides_a_2_max():
    out = clean_for_tts("a\n\n\n\n\nb")
    assert out == "a\n\nb"


def test_clean_normalise_les_espaces_multiples_a_1():
    out = clean_for_tts("a    b")
    assert out == "a b"


def test_clean_strip_le_resultat():
    assert clean_for_tts("   texte   ") == "texte"


def test_clean_convertit_les_ips_en_dernier():
    """L'IP doit être lue chiffre par chiffre dans le résultat final."""
    assert "un neuf deux" in clean_for_tts("**alerte** sur 192.168.1.50")


def test_clean_pipeline_complet_realiste():
    """Cas complet : titre + gras + code + IP."""
    md = "## Alerte SOC\n\n**192.168.1.50** est sur la liste `ban`.\n\n- niveau: critique"
    out = clean_for_tts(md)
    assert "##" not in out
    assert "**" not in out
    assert "`" not in out
    assert "un neuf deux point un six huit point un point cinq zéro" in out
    assert "niveau: critique" in out
