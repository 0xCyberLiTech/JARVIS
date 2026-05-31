"""Tests commands/sse — 6 SSE generators VM/reboot/update/service.

Couvre : vm_execute_one, vm_command_sse (avec/sans dynamic, blacklist
opnsense), post_start_verify_sse, update_machine_sse (reboot needed
ou pas), pve_stop_vms_before_reboot, reboot_machine_sse, service_restart_sse.

Tous les subprocess + SSH + Proxmox API sont mockés.
"""
import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest
from commands import sse

# ── Fixture autouse : DI propre avant chaque test ──────────────────────────


@pytest.fixture(autouse=True)
def _reinit_commands_sse():
    """Inject les dépendances minimales pour les tests, avec restauration
    de l'état initial en teardown (anti-pollution)."""
    saved = {k: getattr(sse, k) for k in (
        "_ssh_proxmox", "_pve_fetch_state", "_bypass_pve", "_vm_start_ssh_map",
        "_pending_reboot", "_sse_tok", "_log",
    )}

    # Mock du module bypass_pve (juste les 2 attributs utilisés)
    bp = MagicMock()
    bp.PVE_STOP_BLACKLIST = {100}              # opnsense protégé
    bp.REBOOT_SVC_CHECKS  = {"srv-nginx": ["nginx", "crowdsec"]}

    def sse_tok(text, done=False):
        return "data: " + json.dumps({"type": "token", "token": text, "done": done}) + "\n\n"

    sse.init(
        ssh_proxmox=["ssh", "-i", "/k", "root@px"],
        ssh_proxmox_cmd_timeout_s=15,
        ssh_proxmox_state_timeout_s=8,
        ssh_apt_timeout_s=180,
        systemctl_restart_timeout_s=15,
        systemctl_status_timeout_s=8,
        pve_fetch_state=MagicMock(return_value={"vms": []}),
        bypass_pve=bp,
        vm_start_ssh_map={108: ("srv-nginx", MagicMock(return_value=(True, "OK")))},
        pending_reboot={},
        sse_tok=sse_tok,
        log=MagicMock(),
    )
    try:
        yield
    finally:
        for k, v in saved.items():
            setattr(sse, k, v)


def _parse_events(events):
    """Parse une liste d'events SSE → liste de dicts JSON."""
    out = []
    for e in events:
        payload = e.replace("data: ", "").strip()
        if payload:
            try:
                out.append(json.loads(payload))
            except json.JSONDecodeError:
                out.append({"raw": payload})
    return out


# ── vm_execute_one ─────────────────────────────────────────────────────────


def test_vm_execute_one_succes_renvoie_4tuple():
    """subprocess.run OK + qm status renvoie 'status: running' → (True, msg, verbe, état)."""
    proc_action = MagicMock(returncode=0, stdout="", stderr="")
    proc_status = MagicMock(returncode=0, stdout="status: running")
    with patch.object(sse.subprocess, "run", side_effect=[proc_action, proc_status]):
        ok, msg, verb, state = sse.vm_execute_one("start", 108, "srv-nginx")
    assert ok is True
    assert "srv-nginx" in msg and "108" in msg and "running" in msg
    assert verb == "démarrée"
    assert state == "running"


def test_vm_execute_one_action_stop_verbe_arretee():
    """action='stop' → verbe = 'arrêtée'."""
    proc_action = MagicMock(returncode=0, stdout="", stderr="")
    proc_status = MagicMock(returncode=0, stdout="status: stopped")
    with patch.object(sse.subprocess, "run", side_effect=[proc_action, proc_status]):
        _ok, _msg, verb, state = sse.vm_execute_one("stop", 108, "srv-nginx")
    assert verb == "arrêtée"
    assert state == "stopped"


def test_vm_execute_one_echec_returncode_non_zero():
    """returncode != 0 → (False, msg erreur, '', '')."""
    proc_action = MagicMock(returncode=1, stdout="", stderr="VM 999 not found")
    with patch.object(sse.subprocess, "run", side_effect=[proc_action, MagicMock(stdout="")]):
        ok, msg, verb, state = sse.vm_execute_one("start", 999, "absente")
    assert ok is False
    assert "Erreur SSH" in msg
    assert "absente" in msg
    assert verb == "" and state == ""


def test_vm_execute_one_timeout_renvoie_false():
    """subprocess.TimeoutExpired propagé en (False, str(exc))."""
    with patch.object(sse.subprocess, "run", side_effect=subprocess.TimeoutExpired("qm", 15)):
        ok, msg, verb, state = sse.vm_execute_one("start", 108, "srv-nginx")
    assert ok is False
    assert "Erreur SSH srv-nginx" in msg


# ── vm_command_sse ─────────────────────────────────────────────────────────


def test_vm_command_sse_liste_explicite_yield_token_par_vm():
    """Liste explicite de VMs → 1 intro + 1 résultat par VM + done + speak."""
    with patch.object(sse, "vm_execute_one", return_value=(True, "VM ok\n", "démarrée", "running")):
        events = _parse_events(list(sse.vm_command_sse("start", [(108, "srv-nginx"), (107, "srv-pa85")])))
    tokens = [e for e in events if e.get("type") == "token"]
    speaks = [e for e in events if e.get("type") == "speak"]
    assert len(speaks) == 1
    assert "srv-nginx" in speaks[0]["text"] and "srv-pa85" in speaks[0]["text"]
    # Au moins 4 tokens (2 intro + 2 result)
    assert sum(1 for t in tokens if "Exécution" in t.get("token", "")) == 2


def test_vm_command_sse_dynamic_stop_filtre_running_et_blacklist():
    """action=stop + dynamic → filtre les VMs status=running ET hors PVE_STOP_BLACKLIST."""
    sse._pve_fetch_state = MagicMock(return_value={"vms": [
        {"vmid": 100, "status": "running", "name": "opnsense"},  # blacklist
        {"vmid": 108, "status": "running", "name": "srv-nginx"},
        {"vmid": 999, "status": "stopped", "name": "off"},        # déjà stopped
    ]})
    with patch.object(sse, "vm_execute_one", return_value=(True, "ok\n", "arrêtée", "stopped")):
        events = _parse_events(list(sse.vm_command_sse("stop", "dynamic")))
    speaks = [e for e in events if e.get("type") == "speak"]
    assert len(speaks) == 1
    assert "srv-nginx" in speaks[0]["text"]
    assert "opnsense" not in speaks[0]["text"]


def test_vm_command_sse_dynamic_api_inaccessible_renvoie_erreur():
    """Si pve_fetch_state retourne None → message erreur + done True."""
    sse._pve_fetch_state = MagicMock(return_value=None)
    events = _parse_events(list(sse.vm_command_sse("start", "dynamic")))
    assert len(events) == 1
    assert "API Proxmox inaccessible" in events[0]["token"]
    assert events[0]["done"] is True


def test_vm_command_sse_dynamic_aucune_vm_a_action_message_clair():
    """Filtre dynamique vide → message 'Aucune VM ...' + done True."""
    sse._pve_fetch_state = MagicMock(return_value={"vms": [
        {"vmid": 999, "status": "stopped", "name": "off"},
    ]})
    events = _parse_events(list(sse.vm_command_sse("stop", "dynamic")))
    assert len(events) == 1
    assert "Aucune VM en cours" in events[0]["token"]
    assert events[0]["done"] is True


# ── post_start_verify_sse ──────────────────────────────────────────────────


def test_post_start_verify_sse_ssh_ko_apres_polling_renvoie_inaccessible():
    """ssh_fn renvoie toujours (False, _) → après 12 retries, message inaccessible."""
    ssh = MagicMock(return_value=(False, "no route"))
    with patch.object(sse.time, "sleep"):  # accélère le test
        events = _parse_events(list(sse.post_start_verify_sse("srv-test", ssh)))
    assert any("inaccessible" in e.get("token", "") for e in events)


def test_post_start_verify_sse_ssh_ok_check_services_actifs():
    """ssh_fn OK + services tous 'active' → tokens 'Tous les services sont actifs'."""
    ssh = MagicMock(side_effect=[
        (True, "OK"),                                              # echo OK ping
        (True, "up 3 days"),                                       # uptime
        (True, "active"),                                          # systemctl is-active nginx
        (True, "active"),                                          # systemctl is-active crowdsec
    ])
    with patch.object(sse.time, "sleep"):
        events = _parse_events(list(sse.post_start_verify_sse("srv-nginx", ssh)))
    full = "".join(e.get("token", "") for e in events)
    assert "accessible" in full
    assert "Tous les services sont actifs" in full
    assert "nginx" in full and "crowdsec" in full


def test_post_start_verify_sse_service_inactif_message_echec():
    """Si un service est inactif → message 'Certains services sont en échec'."""
    ssh = MagicMock(side_effect=[
        (True, "OK"),
        (True, "up 3 days"),
        (True, "inactive"),  # nginx KO
        (True, "active"),    # crowdsec OK
    ])
    with patch.object(sse.time, "sleep"):
        events = _parse_events(list(sse.post_start_verify_sse("srv-nginx", ssh)))
    full = "".join(e.get("token", "") for e in events)
    assert "en échec" in full


# ── update_machine_sse ─────────────────────────────────────────────────────


def test_update_machine_sse_apt_update_echec_arret_immediat():
    """ssh_fn apt-get update KO → token erreur + done True + return."""
    ssh = MagicMock(return_value=(False, "Could not resolve"))
    events = _parse_events(list(sse.update_machine_sse("srv-test", ssh)))
    full = "".join(e.get("token", "") for e in events)
    assert "Erreur apt-get update" in full


def test_update_machine_sse_succes_sans_reboot():
    """apt-get update OK + upgrade OK + pas de reboot-required → message 'à jour' + speak."""
    ssh = MagicMock(side_effect=[
        (True, "Reading package lists..."),                           # apt-get update
        (True, "Setting up pkg1\nSetting up pkg2\nSetting up pkg3"),  # apt-get upgrade
        (True, "NO_REBOOT"),                                          # test reboot-required
    ])
    events = _parse_events(list(sse.update_machine_sse("srv-clt", ssh)))
    full = "".join(e.get("token", "") for e in events)
    assert "3 paquet" in full and "mis à jour" in full
    speaks = [e for e in events if e.get("type") == "speak"]
    assert any("3 paquets installés" in s["text"] for s in speaks)


def test_update_machine_sse_reboot_needed_set_pending():
    """Si /var/run/reboot-required existe → _pending_reboot set + message 'Redémarrage requis'."""
    ssh = MagicMock(side_effect=[
        (True, "Reading package lists..."),
        (True, "Setting up pkg1"),
        (True, "REBOOT_NEEDED"),
    ])
    events = _parse_events(list(sse.update_machine_sse("srv-clt", ssh)))
    full = "".join(e.get("token", "") for e in events)
    assert "Redémarrage requis" in full
    assert sse._pending_reboot.get("host") == "srv-clt"
    speaks = [e for e in events if e.get("type") == "speak"]
    assert any("Reboot maintenant ou reporter" in s["text"] for s in speaks)


def test_update_machine_sse_is_proxmox_avertissement_vms():
    """is_proxmox=True → avertissement 'VMs actives non affectées' en tête."""
    ssh = MagicMock(side_effect=[(True, ""), (True, ""), (True, "NO_REBOOT")])
    events = _parse_events(list(sse.update_machine_sse("proxmox", ssh, is_proxmox=True)))
    full = "".join(e.get("token", "") for e in events)
    assert "hyperviseur" in full and "VMs actives non affectées" in full


# ── pve_stop_vms_before_reboot ─────────────────────────────────────────────


def test_pve_stop_vms_before_reboot_polling_confirme_stopped():
    """qm stop OK + qm status 'stopped' au 1er polling → ✓ confirmation."""
    proc_stop   = MagicMock(returncode=0)
    proc_status = MagicMock(stdout="status: stopped")
    with patch.object(sse.subprocess, "run", side_effect=[proc_stop, proc_status]), \
         patch.object(sse.time, "sleep"):
        events = _parse_events(list(sse.pve_stop_vms_before_reboot([(108, "srv-nginx")])))
    full = "".join(e.get("token", "") for e in events)
    assert "srv-nginx" in full
    assert "arrêtée" in full


def test_pve_stop_vms_before_reboot_erreur_qm_stop_skip_polling():
    """qm stop returncode != 0 → ✗ message erreur, pas de polling status."""
    proc_stop = MagicMock(returncode=1, stdout="", stderr="VM is locked")
    with patch.object(sse.subprocess, "run", return_value=proc_stop), \
         patch.object(sse.time, "sleep"):
        events = _parse_events(list(sse.pve_stop_vms_before_reboot([(108, "srv-nginx")])))
    full = "".join(e.get("token", "") for e in events)
    assert "✗" in full and "srv-nginx" in full


# ── reboot_machine_sse ─────────────────────────────────────────────────────


def test_reboot_machine_sse_non_proxmox_redemarrage_direct():
    """is_proxmox=False → reboot direct + ssh fn 'reboot' + post_start_verify."""
    ssh = MagicMock(return_value=(True, "OK"))
    pending = {"host": "srv-clt", "ssh_fn": ssh, "is_proxmox": False}
    with patch.object(sse, "post_start_verify_sse", return_value=iter([])):
        events = _parse_events(list(sse.reboot_machine_sse(pending)))
    full = "".join(e.get("token", "") for e in events)
    assert "Redémarrage de" in full and "srv-clt" in full
    # ssh_fn appelé avec 'reboot' au moins une fois
    cmds = [c.args[0] for c in ssh.call_args_list]
    assert "reboot" in cmds


def test_reboot_machine_sse_proxmox_arrete_vms_avant():
    """is_proxmox=True + VMs running → pve_stop_vms_before_reboot puis reboot."""
    ssh = MagicMock(return_value=(True, "OK"))
    pending = {"host": "proxmox", "ssh_fn": ssh, "is_proxmox": True}
    sse._pve_fetch_state = MagicMock(return_value={"vms": [
        {"vmid": 108, "status": "running", "name": "srv-nginx"},
        {"vmid": 100, "status": "running", "name": "opnsense"},   # blacklist
    ]})
    with patch.object(sse, "pve_stop_vms_before_reboot", return_value=iter([
        "data: " + json.dumps({"type": "token", "token": "stop", "done": False}) + "\n\n"
    ])), patch.object(sse, "post_start_verify_sse", return_value=iter([])):
        events = _parse_events(list(sse.reboot_machine_sse(pending)))
    full = "".join(e.get("token", "") for e in events)
    speaks = [e for e in events if e.get("type") == "speak"]
    assert any("Redémarrage Proxmox terminé" in s["text"] for s in speaks)
    assert "redémarre manuellement" in full.lower()


def test_reboot_machine_sse_proxmox_aucune_vm_running_direct():
    """is_proxmox=True mais 0 VM running → message 'Aucune VM ... redémarrage direct'."""
    ssh = MagicMock(return_value=(True, "OK"))
    pending = {"host": "proxmox", "ssh_fn": ssh, "is_proxmox": True}
    sse._pve_fetch_state = MagicMock(return_value={"vms": []})
    with patch.object(sse, "post_start_verify_sse", return_value=iter([])):
        events = _parse_events(list(sse.reboot_machine_sse(pending)))
    full = "".join(e.get("token", "") for e in events)
    assert "Aucune VM" in full and "redémarrage direct" in full


# ── reboot_machine_request_sse (1er tour : NE reboot PAS) ───────────────────


def test_reboot_machine_request_sse_pve_refuse_et_renvoie_au_menu():
    """is_proxmox=True → REFUS : aucun reboot, aucun pending, redirige vers le menu."""
    ssh = MagicMock(return_value=(True, "OK"))
    pending = {"host": "proxmox", "ssh_fn": ssh, "is_proxmox": True}
    events = _parse_events(list(sse.reboot_machine_request_sse(pending)))
    full = "".join(e.get("token", "") for e in events)
    speaks = [e for e in events if e.get("type") == "speak"]
    # Aucune commande SSH reboot, aucun pending posé
    assert ssh.call_count == 0
    assert sse._pending_reboot == {}
    assert "menu" in full.lower() and "voix" in full.lower()
    assert any("menu" in s["text"].lower() for s in speaks)


def test_reboot_machine_request_sse_vm_met_en_attente_sans_rebooter():
    """is_proxmox=False → pose _pending_reboot + demande confirmation, NE reboot PAS."""
    ssh = MagicMock(return_value=(True, "OK"))
    pending = {"host": "srv-clt", "ssh_fn": ssh, "is_proxmox": False}
    events = _parse_events(list(sse.reboot_machine_request_sse(pending)))
    full = "".join(e.get("token", "") for e in events)
    # Pas de reboot dans ce tour
    assert ssh.call_count == 0
    # Pending posé pour le 2e tour
    assert sse._pending_reboot.get("host") == "srv-clt"
    assert sse._pending_reboot.get("ssh_fn") is ssh
    assert "Confirme le redémarrage" in full and "srv-clt" in full


# ── service_restart_sse ────────────────────────────────────────────────────


def test_service_restart_sse_succes_actif():
    """systemctl restart OK + is-active 'active' → message 'actif' + speak 'redémarré avec succès'."""
    ssh = MagicMock(side_effect=[
        (True, ""),       # systemctl restart
        (True, "active"), # systemctl is-active
    ])
    events = _parse_events(list(sse.service_restart_sse("srv-nginx", ssh, "nginx")))
    full = "".join(e.get("token", "") for e in events)
    speaks = [e for e in events if e.get("type") == "speak"]
    assert "nginx actif" in full
    assert any("redémarré avec succès" in s["text"] for s in speaks)


def test_service_restart_sse_echec_restart_renvoie_etat_inactif():
    """restart KO + is-active 'inactive' → message échec + speak 'Service inactif'."""
    ssh = MagicMock(side_effect=[
        (False, "Job failed"),
        (True, "inactive"),
    ])
    events = _parse_events(list(sse.service_restart_sse("srv-nginx", ssh, "nginx")))
    full = "".join(e.get("token", "") for e in events)
    speaks = [e for e in events if e.get("type") == "speak"]
    assert "Échec redémarrage" in full
    assert any("Échec du redémarrage" in s["text"] for s in speaks)


def test_service_restart_sse_exception_ssh_renvoie_erreur():
    """ssh_func lance Exception sur restart → token erreur + speak 'Erreur SSH'."""
    ssh = MagicMock(side_effect=Exception("connection refused"))
    events = _parse_events(list(sse.service_restart_sse("srv-nginx", ssh, "nginx")))
    full = "".join(e.get("token", "") for e in events)
    speaks = [e for e in events if e.get("type") == "speak"]
    assert "Erreur SSH" in full
    assert any("Erreur SSH lors du redémarrage" in s["text"] for s in speaks)


# ── update_machine_sse : traçage forensique write-op (gap fix 2026-05-30) ──


def test_update_machine_sse_trace_audit_writeop(monkeypatch):
    """Chaque dist-upgrade réel via bypass UI trace la write-op dans audit_writeops.jsonl."""
    spy = MagicMock()
    monkeypatch.setattr(sse._sec, "audit_writeop", spy)
    ssh = MagicMock(side_effect=[
        (True, ""),                                     # apt-get update
        (True, "Setting up a...\nSetting up b...\n"),   # dist-upgrade (2 paquets)
        (True, "NO_REBOOT"),                            # reboot-required check
    ])
    list(sse.update_machine_sse("proxmox", ssh, is_proxmox=True))
    spy.assert_called_once()
    args, kwargs = spy.call_args
    assert args[0] == "proxmox"
    assert "dist-upgrade" in args[1]
    assert kwargs["allowed"] is True
