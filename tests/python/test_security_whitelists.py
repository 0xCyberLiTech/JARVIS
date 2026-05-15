"""Tests security_whitelists — validation stricte ops SSH (couche sécurité ultime)."""
from security_whitelists import (
    ALLOWED_APT_PKGS,
    ALLOWED_RESTART_SVCS,
    BLOCKED_SSH_PATTERNS,
    check_write_op,
    parse_upgradable_packages,
)

# ── Constantes — sanity check ─────────────────────────────────────────────


def test_blocked_ssh_patterns_contient_les_pires():
    """Sanity : les patterns destructifs absolus sont présents."""
    for pat in ["rm ", "mkfs", "dd if=", "shutdown", "reboot",
                "qm destroy", "qm migrate", "/etc/passwd", "/etc/shadow"]:
        assert pat in BLOCKED_SSH_PATTERNS, f"manque {pat!r}"


def test_allowed_restart_svcs_contient_le_bouncer_crowdsec():
    assert "crowdsec-firewall-bouncer" in ALLOWED_RESTART_SVCS
    assert "crowdsec" in ALLOWED_RESTART_SVCS
    assert "nginx" in ALLOWED_RESTART_SVCS


def test_allowed_apt_pkgs_contient_les_paquets_securite_courants():
    for p in ["nginx", "fail2ban", "crowdsec", "openssl", "certbot"]:
        assert p in ALLOWED_APT_PKGS


def test_blocked_patterns_compte_au_moins_29():
    """La docstring annonce 29 patterns minimum."""
    assert len(BLOCKED_SSH_PATTERNS) >= 29


# ── check_write_op : systemctl restart ────────────────────────────────────


def test_restart_nginx_est_autorise_renvoie_none():
    assert check_write_op("systemctl restart nginx") is None


def test_restart_crowdsec_est_autorise():
    assert check_write_op("systemctl restart crowdsec") is None


def test_restart_bouncer_est_autorise():
    assert check_write_op("systemctl restart crowdsec-firewall-bouncer") is None


def test_restart_service_inconnu_est_refuse_avec_message():
    msg = check_write_op("systemctl restart docker")
    assert msg is not None
    assert "docker" in msg
    assert "non whitelisté" in msg


def test_restart_case_insensitive_sur_la_commande():
    assert check_write_op("SystemCtl Restart nginx") is None


def test_restart_normalise_le_nom_du_service_en_minuscules():
    """`NGINX` → matché contre 'nginx' dans la whitelist."""
    assert check_write_op("systemctl restart NGINX") is None


def test_restart_avec_espaces_externes_est_strip():
    assert check_write_op("  systemctl restart nginx  ") is None


def test_restart_avec_argument_supplementaire_n_est_pas_match():
    """Pattern strict : seulement `restart <svc>`. Avec arg en plus → pas matché."""
    # Cette commande passera donc le check_write_op (None) mais sera bloquée
    # ailleurs par le pattern blocked "systemctl restart"
    assert check_write_op("systemctl restart nginx --now") is None


# ── check_write_op : apt install/upgrade ─────────────────────────────────


def test_apt_install_nginx_est_autorise():
    assert check_write_op("apt install nginx") is None


def test_apt_get_install_nginx_est_autorise():
    assert check_write_op("apt-get install nginx") is None


def test_apt_install_avec_dash_y_est_autorise():
    assert check_write_op("apt install -y crowdsec") is None


def test_apt_install_avec_debian_frontend_est_autorise():
    assert check_write_op("DEBIAN_FRONTEND=noninteractive apt install -y nginx") is None


def test_apt_upgrade_pkg_autorise():
    assert check_write_op("apt upgrade openssl") is None


def test_apt_install_pkg_inconnu_est_refuse():
    msg = check_write_op("apt install docker.io")
    assert msg is not None
    assert "docker.io" in msg
    assert "non whitelisté" in msg


def test_apt_install_normalise_le_nom_du_paquet_en_minuscules():
    assert check_write_op("apt install NGINX") is None


# ── check_write_op : commandes hors scope ─────────────────────────────────


def test_commande_quelconque_renvoie_none():
    """`check_write_op` ne se prononce pas hors restart/apt → None."""
    assert check_write_op("ls -la") is None
    assert check_write_op("uptime") is None
    assert check_write_op("rm -rf /") is None  # pas son rôle, c'est BLOCKED_SSH_PATTERNS


def test_commande_vide_renvoie_none():
    assert check_write_op("") is None


# ── parse_upgradable_packages ────────────────────────────────────────────


def test_parse_extrait_un_paquet_simple():
    out = parse_upgradable_packages("nginx/jammy 1.24.0 amd64 [upgradable from: 1.18.0]")
    assert out == ["nginx"]


def test_parse_extrait_plusieurs_paquets():
    text = (
        "Listing... Done\n"
        "nginx/jammy 1.24.0 amd64 [upgradable from: 1.18.0]\n"
        "openssl/jammy-security 3.0.10 amd64 [upgradable from: 3.0.2]\n"
        "libssl3/jammy 3.0.10 amd64 [upgradable from: 3.0.2]\n"
    )
    out = parse_upgradable_packages(text)
    assert out == ["nginx", "openssl", "libssl3"]


def test_parse_ignore_les_lignes_sans_slash():
    text = "Listing... Done\nWARNING: pas un paquet\nnginx/jammy 1.0\n"
    assert parse_upgradable_packages(text) == ["nginx"]


def test_parse_input_vide_renvoie_liste_vide():
    assert parse_upgradable_packages("") == []


def test_parse_paquet_avec_chiffres_et_tirets():
    out = parse_upgradable_packages("python3-certbot-nginx/jammy 1.21.0 all\n")
    assert out == ["python3-certbot-nginx"]


def test_parse_paquet_avec_point():
    out = parse_upgradable_packages("php7.4-fpm/jammy 7.4.33 amd64\n")
    assert out == ["php7.4-fpm"]


def test_parse_ignore_paquet_commencant_par_chiffre_ou_majuscule():
    """Pattern exige `[a-z]` au début → 7zip, Nginx ne matchent pas."""
    text = "7zip/jammy 1.0\nNginx/jammy 1.0\nokpkg/jammy 1.0\n"
    assert parse_upgradable_packages(text) == ["okpkg"]
