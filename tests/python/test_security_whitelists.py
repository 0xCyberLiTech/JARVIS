"""Tests security_whitelists — validation stricte ops SSH (couche sécurité ultime)."""
import json
import re as _re

from security_whitelists import (
    ALLOWED_APT_PKGS,
    ALLOWED_RESTART_SVCS,
    BLOCKED_SSH_PATTERNS,
    audit_writeop,
    check_write_op,
    is_known_write_op,
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


# ── BLOCKED_SSH_PATTERNS — apt install/upgrade systematiquement filtres ──
# (ajout 2026-05-17 : avant, ces patterns absents permettaient apt install
# <evilpkg> de s'executer sans verification car la boucle d'audit dans
# _tool_commande_ssh_run ne matchait jamais.)


def test_blocked_contient_apt_install_et_upgrade():
    """Les patterns apt install/upgrade DOIVENT etre dans BLOCKED pour
    declencher systematiquement check_write_op."""
    for pat in ["apt install", "apt upgrade", "apt-get install", "apt-get upgrade"]:
        assert pat in BLOCKED_SSH_PATTERNS, f"manque {pat!r}"


# ── is_known_write_op : gardien defense-en-profondeur ────────────────────
# (ajout 2026-05-17 — corrige faille critique : rm/mkfs/dd/shutdown matchaient
# BLOCKED mais s'executaient car check_write_op retournait None hors scope.)


def test_is_known_write_op_systemctl_restart_oui():
    assert is_known_write_op("systemctl restart nginx") is True
    assert is_known_write_op("systemctl restart evilsvc") is True  # forme reconnue
    assert is_known_write_op("SystemCtl Restart nginx") is True  # case insensitive


def test_is_known_write_op_apt_install_oui():
    assert is_known_write_op("apt install nginx") is True
    assert is_known_write_op("apt install evilpkg") is True
    assert is_known_write_op("apt-get install -y crowdsec") is True
    assert is_known_write_op("DEBIAN_FRONTEND=noninteractive apt install -y nginx") is True
    assert is_known_write_op("apt upgrade openssl") is True


def test_is_known_write_op_destructif_non():
    """CRITIQUE : rm/mkfs/dd/shutdown/etc. NE SONT PAS des write ops reconnues."""
    for cmd in [
        "rm -rf /",
        "rm -rf /etc/nginx",
        "mkfs.ext4 /dev/sda",
        "dd if=/dev/zero of=/dev/sda",
        "shutdown now",
        "shutdown -h 0",
        "reboot",
        "qm destroy 100",
        "qm migrate 100 node2",
        "iptables -F",
        "systemctl stop nginx",
        "systemctl disable nginx",
        "chmod 777 /etc/passwd",
        "chown root:root /etc/shadow",
    ]:
        assert is_known_write_op(cmd) is False, f"FAILLE : {cmd!r} accepte comme write op !"


def test_is_known_write_op_commandes_normales_non():
    """Commandes de lecture/diagnostic standard : pas une write op."""
    assert is_known_write_op("ls -la") is False
    assert is_known_write_op("uptime") is False
    assert is_known_write_op("cat /var/log/nginx/access.log") is False
    assert is_known_write_op("") is False


def test_is_known_write_op_pattern_strict_apres_pkg():
    """`systemctl restart nginx --now` n'est PAS forme reconnue (arg supplementaire)
    → is_known_write_op False → refus par defaut (correct)."""
    assert is_known_write_op("systemctl restart nginx --now") is False


# ── check_write_op : commandes hors scope ─────────────────────────────────


def test_commande_quelconque_renvoie_none():
    """`check_write_op` ne se prononce pas hors restart/apt → None.

    ⚠ C'est pourquoi `is_known_write_op` est obligatoire AVANT dans le caller —
    sinon `rm -rf /` matche BLOCKED, check_write_op retourne None, et la
    commande s'execute (faille corrigee 2026-05-17 dans _tool_commande_ssh_run).
    """
    assert check_write_op("ls -la") is None
    assert check_write_op("uptime") is None
    assert check_write_op("rm -rf /") is None  # pas son rôle, c'est is_known_write_op + BLOCKED


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


# ── Audit log write ops SSH (ajout 2026-05-17) ────────────────


def test_audit_writeop_allowed_appends_jsonl(tmp_path):
    """Une write op autorisee est append en JSON ligne."""
    log = tmp_path / "audit.jsonl"
    audit_writeop("nginx", "systemctl restart nginx", allowed=True,
                  output="Job for nginx.service done.", log_path=log,
                  ts="2026-05-17T18:30:00Z")
    lines = log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    rec = json.loads(lines[0])
    assert rec == {
        "ts": "2026-05-17T18:30:00Z",
        "host": "nginx",
        "cmd": "systemctl restart nginx",
        "allowed": True,
        "out_len": 27,
    }


def test_audit_writeop_refused_appends_jsonl(tmp_path):
    """Une write op refusee est aussi tracee (forensic)."""
    log = tmp_path / "audit.jsonl"
    audit_writeop("clt", "systemctl restart evilsvc", allowed=False,
                  output="Refusé : systemctl restart 'evilsvc' non whitelisté",
                  log_path=log, ts="2026-05-17T18:31:00Z")
    rec = json.loads(log.read_text(encoding="utf-8").strip())
    assert rec["allowed"] is False
    assert rec["host"] == "clt"
    assert rec["cmd"] == "systemctl restart evilsvc"
    assert rec["out_len"] > 0


def test_audit_writeop_append_mode_multiple_lignes(tmp_path):
    """Append (pas overwrite) — chaque appel ajoute une ligne."""
    log = tmp_path / "audit.jsonl"
    audit_writeop("nginx", "apt upgrade nginx", allowed=True, log_path=log)
    audit_writeop("clt", "systemctl restart fail2ban", allowed=True, log_path=log)
    audit_writeop("pa85", "rm -rf /", allowed=False, output="Refusé", log_path=log)
    lines = log.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    hosts = [json.loads(line)["host"] for line in lines]
    assert hosts == ["nginx", "clt", "pa85"]


def test_audit_writeop_tronque_cmd_longue(tmp_path):
    """Une commande > 500 chars est tronquee dans le log (limite taille)."""
    log = tmp_path / "audit.jsonl"
    long_cmd = "apt install " + "x" * 600
    audit_writeop("nginx", long_cmd, allowed=False, log_path=log)
    rec = json.loads(log.read_text(encoding="utf-8").strip())
    assert len(rec["cmd"]) == 500


def test_audit_writeop_cree_repertoire_parent(tmp_path):
    """Si logs/ n'existe pas, il est cree automatiquement."""
    log = tmp_path / "subdir" / "nested" / "audit.jsonl"
    audit_writeop("nginx", "systemctl restart nginx", allowed=True, log_path=log)
    assert log.exists()
    assert log.parent.is_dir()


def test_audit_writeop_silently_ignores_io_errors(tmp_path):
    """Si I/O echoue, la fonction ne leve pas — best-effort, ne bloque jamais SSH."""
    # Tente d'ecrire dans un chemin invalide (un fichier au lieu d'un dossier parent)
    blocker = tmp_path / "blocker"
    blocker.write_text("not a dir")
    log = blocker / "audit.jsonl"   # blocker n'est pas un dir → mkdir + open echouent
    # Ne doit pas lever
    audit_writeop("nginx", "systemctl restart nginx", allowed=True, log_path=log)


def test_audit_writeop_default_timestamp_utc_format(tmp_path):
    """Sans ts override, le timestamp est UTC ISO8601 termine par Z."""
    log = tmp_path / "audit.jsonl"
    audit_writeop("nginx", "systemctl restart nginx", allowed=True, log_path=log)
    rec = json.loads(log.read_text(encoding="utf-8").strip())
    # Format attendu : 2026-05-17T18:30:00Z (sans microsecondes, sans +00:00)
    assert _re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", rec["ts"])
