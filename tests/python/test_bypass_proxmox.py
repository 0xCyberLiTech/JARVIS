"""Tests bypass_proxmox — détection commandes VM/reboot/update (DI complet, 0 I/O)."""
import re

from bypass.proxmox import (
    PVE_STOP_BLACKLIST,
    REBOOT_DEFER_RE,
    REBOOT_MACHINE_RE,
    REBOOT_NOW_RE,
    REBOOT_SVC_CHECKS,
    UPDATE_ACTION_RE,
    VM_ALIASES,
    VM_ALL_START_RE,
    VM_ALL_STOP_RE,
    VM_EXCLUDE_RE,
    VM_START_ACTION_RE,
    VM_STOP_ACTION_RE,
    detect_reboot_command,
    detect_update_command,
    detect_vm_command,
    make_svc_restart_re,
)

# ── Constantes ────────────────────────────────────────────────────────────


def test_pve_stop_blacklist_inclut_opnsense():
    """opnsense (VM 100) ne doit jamais être auto-arrêté (firewall réseau)."""
    assert 100 in PVE_STOP_BLACKLIST


def test_vm_aliases_srv_ngix_resolu_vers_srv_nginx():
    """Rétrocompat 2026-05-26 : ancien nom 'srv-ngix' → nouveau 'srv-nginx'."""
    assert VM_ALIASES["srv-ngix"] == "srv-nginx"


def test_reboot_svc_checks_couvre_les_hotes_principaux():
    for host in ["srv-nginx", "srv-clt", "srv-pa85", "proxmox", "srv-dev-1"]:
        assert host in REBOOT_SVC_CHECKS
    assert "nginx" in REBOOT_SVC_CHECKS["srv-nginx"]
    assert "apache2" in REBOOT_SVC_CHECKS["srv-clt"]


# ── Regex actions ────────────────────────────────────────────────────────


def test_update_action_re_match_mise_a_jour():
    assert UPDATE_ACTION_RE.search("mise à jour de srv-nginx")
    assert UPDATE_ACTION_RE.search("met à jour")
    assert UPDATE_ACTION_RE.search("update svr")
    assert UPDATE_ACTION_RE.search("upgrade nginx")
    assert UPDATE_ACTION_RE.search("MAJ machine")


def test_reboot_now_re_match_reboot_redemarre():
    assert REBOOT_NOW_RE.search("reboot maintenant")
    assert REBOOT_NOW_RE.search("redémarre")
    assert REBOOT_NOW_RE.search("redemarre maintenant")


def test_reboot_defer_re_match_plus_tard():
    assert REBOOT_DEFER_RE.search("plus tard")
    assert REBOOT_DEFER_RE.search("reporte")
    assert REBOOT_DEFER_RE.search("pas maintenant")


def test_vm_stop_re_match_arrete_stop():
    assert VM_STOP_ACTION_RE.search("arrête srv-nginx")
    assert VM_STOP_ACTION_RE.search("stop la VM")
    assert VM_STOP_ACTION_RE.search("éteins clt")
    assert VM_STOP_ACTION_RE.search("shutdown")


def test_vm_start_re_match_demarre_start():
    assert VM_START_ACTION_RE.search("démarre srv-nginx")
    assert VM_START_ACTION_RE.search("start the vm")
    assert VM_START_ACTION_RE.search("allume clt")


def test_vm_exclude_re_match_sauvegarde():
    """Sauvegarde, restart, etc. invalident la détection VM."""
    assert VM_EXCLUDE_RE.search("sauvegarde srv-nginx")
    assert VM_EXCLUDE_RE.search("backup la vm")
    assert VM_EXCLUDE_RE.search("redémarre apache2")


def test_vm_all_stop_re_match_toutes_les_vms():
    assert VM_ALL_STOP_RE.search("arrête toutes les vms")
    assert VM_ALL_STOP_RE.search("stop machines virtuelles")


def test_vm_all_start_re_match_toutes_les_vms():
    assert VM_ALL_START_RE.search("démarre toutes les vms")
    assert VM_ALL_START_RE.search("redémarre les serveurs")


def test_reboot_machine_re_match_simple():
    assert REBOOT_MACHINE_RE.search("reboot ngix")


# ── make_svc_restart_re ──────────────────────────────────────────────────


def test_make_svc_restart_re_compile_avec_bouncer_personnalise():
    rx = make_svc_restart_re("crowdsec-firewall-bouncer")
    assert rx.search("redémarre nginx")
    assert rx.search("restart crowdsec-firewall-bouncer")
    assert rx.search("restart suricata")


def test_make_svc_restart_re_match_relance():
    rx = make_svc_restart_re("bouncer")
    assert rx.search("relance fail2ban")


def test_make_svc_restart_re_pas_match_service_inconnu():
    rx = make_svc_restart_re("bouncer")
    assert not rx.search("redémarre docker")


# ── detect_vm_command ────────────────────────────────────────────────────


def _vms_api():
    """vms_api stub : 4 VMs typiques."""
    return [
        {"vmid": 100, "name": "opnsense"},   # blacklisté
        {"vmid": 106, "name": "srv-clt"},
        {"vmid": 107, "name": "srv-pa85"},
        {"vmid": 108, "name": "srv-nginx"},
    ]


def test_detect_vm_stop_simple_par_nom():
    result = detect_vm_command("arrête srv-nginx", _vms_api())
    assert result == ("stop", [(108, "srv-nginx")])


def test_detect_vm_start_simple_par_nom():
    result = detect_vm_command("démarre srv-clt", _vms_api())
    assert result == ("start", [(106, "srv-clt")])


def test_detect_vm_par_vmid():
    result = detect_vm_command("stop 108", _vms_api())
    assert result == ("stop", [(108, "srv-nginx")])


def test_detect_vm_alias_srv_nginx_resolu_en_srv_ngix():
    """L'alias 'srv-nginx' (sans le typo) doit être résolu vers srv-nginx."""
    result = detect_vm_command("arrête srv-nginx", _vms_api())
    assert result == ("stop", [(108, "srv-nginx")])


def test_detect_vm_blacklist_opnsense_pas_match_meme_si_demande():
    """opnsense (vmid=100) ne doit JAMAIS être proposé pour stop."""
    result = detect_vm_command("arrête opnsense", _vms_api())
    assert result is None


def test_detect_vm_exclude_re_invalide_si_sauvegarde():
    """`sauvegarde srv-nginx` → bloqué par VM_EXCLUDE_RE."""
    assert detect_vm_command("sauvegarde srv-nginx", _vms_api()) is None


def test_detect_vm_aucun_verbe_renvoie_none():
    assert detect_vm_command("info srv-nginx", _vms_api()) is None


def test_detect_vm_verbe_mais_aucune_vm_renvoie_none():
    assert detect_vm_command("démarre", _vms_api()) is None


def test_detect_vm_dynamic_avec_toutes_les_vms():
    """`arrête toutes les vms` (sans nom précis) → 'dynamic'."""
    result = detect_vm_command("arrête toutes les vms", _vms_api())
    assert result == ("stop", "dynamic")


def test_detect_vm_plusieurs_vms_dans_le_texte():
    result = detect_vm_command("arrête srv-clt et srv-pa85", _vms_api())
    assert result[0] == "stop"
    vmids = [v[0] for v in result[1]]
    assert 106 in vmids and 107 in vmids


def test_detect_vm_blacklist_personnalisee():
    result = detect_vm_command("arrête srv-nginx", _vms_api(), blacklist={108})
    assert result is None


def test_detect_vm_alias_map_personnalise():
    custom = {"web": "srv-nginx"}
    result = detect_vm_command("arrête web", _vms_api(), alias_map=custom)
    assert result == ("stop", [(108, "srv-nginx")])


def test_detect_vm_pas_de_doublons_dans_resultat():
    """Si même VM mentionnée deux fois (par nom + vmid) → un seul tuple."""
    result = detect_vm_command("stop srv-nginx la 108", _vms_api())
    assert len(result[1]) == 1


# ── detect_reboot_command ────────────────────────────────────────────────


def _host_map():
    """host_map stub : 3 hôtes typiques."""
    return [
        (["ngix", "srv-nginx"], "srv-nginx", lambda c: (True, ""), False),
        (["clt", "srv-clt"], "srv-clt", lambda c: (True, ""), False),
        (["proxmox"], "proxmox", lambda c: (True, ""), True),
    ]


def test_detect_reboot_simple():
    result = detect_reboot_command("reboot srv-nginx", _host_map())
    assert result is not None
    label, _, is_pve = result
    assert label == "srv-nginx"
    assert is_pve is False


def test_detect_reboot_alias_court():
    result = detect_reboot_command("redémarre ngix", _host_map())
    assert result[0] == "srv-nginx"


def test_detect_reboot_proxmox_is_pve_true():
    result = detect_reboot_command("reboot proxmox", _host_map())
    assert result[2] is True


def test_detect_reboot_aucun_match_renvoie_none():
    assert detect_reboot_command("info ngix", _host_map()) is None


def test_detect_reboot_verbe_mais_hote_inconnu():
    assert detect_reboot_command("reboot serveur-x", _host_map()) is None


# ── detect_update_command ────────────────────────────────────────────────


def test_detect_update_simple():
    result = detect_update_command("mise à jour srv-clt", _host_map())
    assert result[0] == "srv-clt"


def test_detect_update_match_upgrade():
    result = detect_update_command("upgrade ngix", _host_map())
    assert result[0] == "srv-nginx"


def test_detect_update_match_maj():
    result = detect_update_command("maj ngix", _host_map())
    assert result[0] == "srv-nginx"


def test_detect_update_aucun_verbe_renvoie_none():
    assert detect_update_command("info srv-nginx", _host_map()) is None


def test_detect_update_verbe_mais_hote_inconnu():
    assert detect_update_command("update inconnu", _host_map()) is None


# ── Vérification cohérence regex (escape + \b) ───────────────────────────


def test_make_svc_restart_re_escape_bouncer_avec_caracteres_speciaux():
    """Le bouncer contient '-' qui doit être escapé proprement."""
    rx = make_svc_restart_re("my.weird-bouncer.svc")
    assert isinstance(rx, re.Pattern)
    assert rx.search("restart my.weird-bouncer.svc")
