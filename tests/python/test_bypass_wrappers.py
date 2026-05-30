"""Tests bypass/wrappers — 11 wrappers DI couplés jarvis (étape 27).

Couvre : 4 détecteurs Proxmox (service/vm/reboot/update) + 2 wrappers code +
4 wrappers backup + apt_upgrade_bypass_sse (logique réelle).
"""
import json
from unittest.mock import MagicMock

import pytest
from bypass import proxmox as bypass_pve
from bypass import wrappers as bp_wrap


@pytest.fixture(autouse=True)
def _reinit_wrappers():
    """DI propre avant chaque test + restauration de l'état initial après yield.

    Sans cette restauration, les tests bypass_wrappers contaminent les tests
    suivants (test_jarvis_functions::test_detect_service_restart_*) qui lisent
    `jm._detect_service_restart` (= alias vers `bp_wrap.detect_service_restart`)
    et s'attendent à la VRAIE fonction _ssh_nginx injectée au boot de jarvis."""
    # Snapshot état actuel pour restauration en teardown
    saved = {k: getattr(bp_wrap, k) for k in (
        "_ssh_nginx", "_ssh_proxmox", "_ssh_clt", "_ssh_pa85", "_ssh_dev1",
        "_bypass_pve", "_bypass_code", "_bypass_bk",
        "_pve_fetch_state", "_sse_tok", "_log",
        "_pending_infra_cmd", "_allowed_scripts",
        "_ssh_apt_timeout_s", "_svc_bouncer",
        "VM_START_SSH_MAP", "UPDATE_REBOOT_HOSTS", "SVC_RESTART_RE",
    )}

    ssh_nginx    = MagicMock(name="ssh_nginx",    return_value=(True, ""))
    ssh_proxmox = MagicMock(name="ssh_proxmox", return_value=(True, ""))
    ssh_clt     = MagicMock(name="ssh_clt",     return_value=(True, ""))
    ssh_pa85    = MagicMock(name="ssh_pa85",    return_value=(True, ""))
    ssh_dev1    = MagicMock(name="ssh_dev1",    return_value=(True, ""))

    bypass_code_mod = MagicMock()
    bypass_code_mod.detect_code_command = MagicMock(return_value=None)
    bypass_code_mod.code_scp_exec_sse = MagicMock(return_value=iter([]))

    bypass_bk_mod = MagicMock()
    bypass_bk_mod.detect_backup_command = MagicMock(return_value=None)
    bypass_bk_mod.backup_sse = MagicMock(return_value=iter([]))
    bypass_bk_mod.jarvis_backup_log_sse = MagicMock(return_value=iter([]))
    bypass_bk_mod.jarvis_backup_sse = MagicMock(return_value=iter([]))

    pve_fetch_state = MagicMock(return_value={"vms": [{"vmid": 108, "name": "srv-nginx", "status": "running"}]})

    def sse_tok(txt, done=False):
        return f"data: {json.dumps({'type':'token','token':txt,'done':done})}\n\n"

    bp_wrap.init(
        ssh_nginx=ssh_nginx,
        ssh_proxmox=ssh_proxmox,
        ssh_clt=ssh_clt,
        ssh_pa85=ssh_pa85,
        ssh_dev1=ssh_dev1,
        bypass_pve=bypass_pve,            # vrai module pour SVC_RESTART_RE
        bypass_code=bypass_code_mod,
        bypass_bk=bypass_bk_mod,
        pve_fetch_state=pve_fetch_state,
        sse_tok=sse_tok,
        log=MagicMock(),
        pending_infra_cmd={},
        allowed_scripts={"backup-jarvis": "C:/fake/jarvis.ps1", "disk-report": "C:/disk.ps1"},
        ssh_apt_timeout_s=180,
        svc_bouncer="crowdsec-firewall-bouncer",
    )
    try:
        yield
    finally:
        # Restaure l'état initial pour ne pas contaminer les tests suivants
        for k, v in saved.items():
            setattr(bp_wrap, k, v)


# ── init() — tables/regex calculées ────────────────────────────────────────


def test_init_calcule_tables_couplees_ssh():
    """init() rempli VM_START_SSH_MAP + UPDATE_REBOOT_HOSTS + SVC_RESTART_RE."""
    assert 108 in bp_wrap.VM_START_SSH_MAP
    assert bp_wrap.VM_START_SSH_MAP[108][0] == "srv-nginx"
    assert len(bp_wrap.UPDATE_REBOOT_HOSTS) == 5  # nginx, clt, pa85, dev-1, proxmox
    assert bp_wrap.SVC_RESTART_RE is not None


# ── detect_service_restart ─────────────────────────────────────────────────


def test_detect_service_restart_nginx_route_vers_nginx():
    """'redémarre nginx' → (srv-nginx, ssh_nginx, nginx)."""
    result = bp_wrap.detect_service_restart("redémarre nginx maintenant")
    assert result is not None
    host, ssh_fn, svc = result
    assert host == "srv-nginx"
    assert ssh_fn is bp_wrap._ssh_nginx
    assert svc == "nginx"


def test_detect_service_restart_crowdsec_route_vers_nginx():
    """'restart crowdsec' → srv-nginx."""
    host, _ssh, svc = bp_wrap.detect_service_restart("restart crowdsec")
    assert host == "srv-nginx"
    assert svc == "crowdsec"


def test_detect_service_restart_apache_sur_clt_route():
    """'redémarre apache sur clt' → (clt, ssh_clt, apache2)."""
    host, ssh_fn, svc = bp_wrap.detect_service_restart("redémarre apache sur clt")
    assert host == "clt"
    assert ssh_fn is bp_wrap._ssh_clt
    assert svc == "apache2"


def test_detect_service_restart_apache_sans_hote_ambigu():
    """'redémarre apache' sans préciser clt/pa85 → host='ambiguous'."""
    host, ssh_fn, svc = bp_wrap.detect_service_restart("redémarre apache")
    assert host == "ambiguous"
    assert ssh_fn is None


def test_detect_service_restart_aucun_match_renvoie_none():
    """Texte sans verbe de restart → None."""
    assert bp_wrap.detect_service_restart("quelle heure est-il ?") is None


# ── detect_vm_command (avec injection vms_api via pve_fetch_state) ─────────


def test_detect_vm_command_appelle_pve_fetch_state():
    """detect_vm_command() appelle pve_fetch_state() pour récupérer vms_api."""
    bp_wrap.detect_vm_command("démarre srv-nginx")
    bp_wrap._pve_fetch_state.assert_called_once()


def test_detect_vm_command_propage_vms_api_vide_si_state_none():
    """Si pve_fetch_state() retourne None → vms_api = [] (pas KeyError)."""
    bp_wrap._pve_fetch_state = MagicMock(return_value=None)
    result = bp_wrap.detect_vm_command("démarre une vm")
    # Pas de crash, retourne None ou structure attendue par bypass_pve.detect_vm_command([])
    assert result is None or isinstance(result, tuple)


# ── detect_reboot_command + detect_update_command (injection hosts) ────────


def test_detect_reboot_command_passe_update_reboot_hosts():
    """detect_reboot_command délègue avec UPDATE_REBOOT_HOSTS."""
    result = bp_wrap.detect_reboot_command("reboot srv-nginx")
    assert result is not None
    host, _ssh, _is_pve = result
    assert host == "srv-nginx"


def test_detect_update_command_passe_update_reboot_hosts():
    """detect_update_command détègue avec UPDATE_REBOOT_HOSTS."""
    result = bp_wrap.detect_update_command("mise à jour proxmox")
    assert result is not None
    host, _ssh, is_pve = result
    assert host == "proxmox"
    assert is_pve is True


# ── Wrappers code (délégation pure vers bypass_code) ──────────────────────


def test_detect_code_command_delegue_a_bypass_code():
    """detect_code_command() appelle bypass_code.detect_code_command(text)."""
    bp_wrap.detect_code_command("envoie le code script.py")
    bp_wrap._bypass_code.detect_code_command.assert_called_once_with("envoie le code script.py")


def test_code_scp_exec_sse_injecte_ssh_dev1():
    """code_scp_exec_sse() délègue + injecte _ssh_dev1 en 3ème argument."""
    list(bp_wrap.code_scp_exec_sse("script.py", True))  # consume generator
    bp_wrap._bypass_code.code_scp_exec_sse.assert_called_once_with("script.py", True, bp_wrap._ssh_dev1)


# ── Wrappers backup (délégation + résolution chemin script) ────────────────


def test_detect_backup_command_delegue_a_bypass_bk():
    """detect_backup_command() délègue à bypass_bk."""
    bp_wrap.detect_backup_command("lance la sauvegarde VM")
    bp_wrap._bypass_bk.detect_backup_command.assert_called_once_with("lance la sauvegarde VM")


def test_backup_sse_resout_script_path_depuis_allowed_scripts():
    """backup_sse(key) résout via allowed_scripts puis délègue."""
    list(bp_wrap.backup_sse("disk-report"))
    bp_wrap._bypass_bk.backup_sse.assert_called_once_with("C:/disk.ps1", "disk-report")


def test_backup_sse_cle_inconnue_resout_chemin_vide():
    """Clé hors whitelist → script_path = '' (bypass_bk.backup_sse gère l'erreur)."""
    list(bp_wrap.backup_sse("inconnu"))
    bp_wrap._bypass_bk.backup_sse.assert_called_once_with("", "inconnu")


def test_jarvis_backup_log_sse_delegue_sans_arg():
    """jarvis_backup_log_sse() délègue sans paramètre."""
    list(bp_wrap.jarvis_backup_log_sse())
    bp_wrap._bypass_bk.jarvis_backup_log_sse.assert_called_once_with()


def test_jarvis_backup_sse_resout_clé_backup_jarvis():
    """jarvis_backup_sse() résout toujours la clé 'backup-jarvis'."""
    list(bp_wrap.jarvis_backup_sse())
    bp_wrap._bypass_bk.jarvis_backup_sse.assert_called_once_with("C:/fake/jarvis.ps1")


# ── apt_upgrade_bypass_sse (logique réelle, pas wrapper) ───────────────────


def _parse_speak_event(event: str) -> dict:
    """Parse 'data: {json}\\n\\n' et retourne le dict avec accent décodés."""
    payload = event.replace("data: ", "").strip()
    return json.loads(payload)


def test_apt_upgrade_bypass_sse_succes_yield_paquets():
    """ssh_fn retourne ok=True → message succès + nb paquets installés."""
    pending = {
        "host":     "clt",
        "ssh_fn":   MagicMock(return_value=(True, "Setting up pkg1\nSetting up pkg2")),
        "packages": ["pkg1", "pkg2"],
    }
    events = list(bp_wrap.apt_upgrade_bypass_sse(pending))
    # Au moins : header + chaque paquet + ligne vide + message succès + token done + speak
    assert len(events) >= 5
    # Le ssh_fn a été appelé avec apt-get upgrade
    cmd = pending["ssh_fn"].call_args[0][0]
    assert "apt-get upgrade" in cmd
    assert "pkg1 pkg2" in cmd
    # Le dernier event est un payload speak JSON (ensure_ascii=True → accents en \u00xx)
    speak = _parse_speak_event(events[-1])
    assert speak["type"] == "speak"
    assert "Mise à jour Apache réussie sur clt" in speak["text"]


def test_apt_upgrade_bypass_sse_echec_yield_erreur():
    """ssh_fn retourne ok=False → message erreur tronqué + speak erreur."""
    pending = {
        "host":     "pa85",
        "ssh_fn":   MagicMock(return_value=(False, "Some long error output " * 50)),
        "packages": ["apache2"],
    }
    events = list(bp_wrap.apt_upgrade_bypass_sse(pending))
    # Le speak event final (JSON décodé) mentionne erreur
    speak = _parse_speak_event(events[-1])
    assert "Erreur lors de la mise à jour sur pa85" in speak["text"]


def test_apt_upgrade_bypass_sse_clear_pending_infra_cmd():
    """Au démarrage de la fonction, _pending_infra_cmd est vidé."""
    bp_wrap._pending_infra_cmd["zombie"] = "data"
    pending = {
        "host":     "clt",
        "ssh_fn":   MagicMock(return_value=(True, "")),
        "packages": ["pkg"],
    }
    list(bp_wrap.apt_upgrade_bypass_sse(pending))
    assert "zombie" not in bp_wrap._pending_infra_cmd


def test_apt_upgrade_bypass_sse_trace_audit_writeop(monkeypatch):
    """La MAJ bypass réelle trace la write-op SSH dans audit_writeops.jsonl (gap fix 2026-05-30)."""
    spy = MagicMock()
    monkeypatch.setattr(bp_wrap._sec, "audit_writeop", spy)
    pending = {
        "host":     "proxmox",
        "ssh_fn":   MagicMock(return_value=(True, "Setting up a...\nSetting up b...\n")),
        "packages": ["pkg-a", "pkg-b"],
    }
    list(bp_wrap.apt_upgrade_bypass_sse(pending))
    spy.assert_called_once()
    args, kwargs = spy.call_args
    assert args[0] == "proxmox"
    assert "apt-get upgrade" in args[1]
    assert kwargs["allowed"] is True
