"""Générateurs SSE — commandes VM Proxmox / reboot / update apt / restart service.

Tuile `commands` — pas de routes HTTP, juste 7 générateurs SSE consommés
par le routing bypass (`_chat_try_bypass`) quand un message utilisateur
correspond à une commande infra (start/stop VM, reboot, update, restart service).

Dépendances injectées par `init()` :
- _ssh_proxmox          : tableau de commande SSH Proxmox (ssh -i ... root@...)
- _pve_fetch_state      : callable → état Proxmox (cache 30s)
- _bypass_pve           : module (PVE_STOP_BLACKLIST, REBOOT_SVC_CHECKS)
- _vm_start_ssh_map     : dict VMID → (host_label, ssh_fn) pour vérification post-start
- _pending_reboot       : dict mutable partagé (état reboot différé)
- _sse_tok              : helper SSE
- 5 timeouts + log
"""
import json
import subprocess
import time

import security_whitelists as _sec

_ssh_proxmox = None
_ssh_proxmox_cmd_timeout_s = 15
_ssh_proxmox_state_timeout_s = 8
_ssh_apt_timeout_s = 180
_systemctl_restart_timeout_s = 15
_systemctl_status_timeout_s = 8
_pve_fetch_state = None
_bypass_pve = None
_vm_start_ssh_map = None
_pending_reboot = None
_sse_tok = None
_log = None


def init(*, ssh_proxmox, ssh_proxmox_cmd_timeout_s, ssh_proxmox_state_timeout_s,
         ssh_apt_timeout_s, systemctl_restart_timeout_s, systemctl_status_timeout_s,
         pve_fetch_state, bypass_pve, vm_start_ssh_map, pending_reboot,
         sse_tok, log) -> None:
    globals().update({
        "_ssh_proxmox": ssh_proxmox,
        "_ssh_proxmox_cmd_timeout_s": ssh_proxmox_cmd_timeout_s,
        "_ssh_proxmox_state_timeout_s": ssh_proxmox_state_timeout_s,
        "_ssh_apt_timeout_s": ssh_apt_timeout_s,
        "_systemctl_restart_timeout_s": systemctl_restart_timeout_s,
        "_systemctl_status_timeout_s": systemctl_status_timeout_s,
        "_pve_fetch_state": pve_fetch_state,
        "_bypass_pve": bypass_pve,
        "_vm_start_ssh_map": vm_start_ssh_map,
        "_pending_reboot": pending_reboot,
        "_sse_tok": sse_tok,
        "_log": log,
    })


def vm_execute_one(action, vmid, vmname):
    """Exécute qm action sur une VM et vérifie l'état post-commande."""
    try:
        r  = subprocess.run(_ssh_proxmox + [f"qm {action} {vmid}"],
                            capture_output=True, text=True, timeout=_ssh_proxmox_cmd_timeout_s)
        ok = r.returncode == 0
        output = r.stdout.strip() or r.stderr.strip() or ""
    except Exception as e:
        ok, output = False, str(e)
    real_state = ""
    try:
        rs = subprocess.run(_ssh_proxmox + [f"qm status {vmid}"],
                            capture_output=True, text=True, timeout=_ssh_proxmox_state_timeout_s)
        real_state = rs.stdout.strip().lower()
    except Exception:
        pass
    if ok:
        verb  = "arrêtée" if action == "stop" else "démarrée"
        state = real_state.replace("status:", "").strip() if real_state else ("stopped" if action == "stop" else "running")
        return ok, f"VM {vmname} ({vmid}) {verb}. État : {state}\n", verb, state
    return False, f"Erreur SSH {vmname} : {output[:200]}\n", "", ""


def vm_command_sse(action, vm_list):
    """Exécute qm stop/start sur Proxmox pour une ou plusieurs VMs — bypass LLM."""
    if vm_list == "dynamic":
        state = _pve_fetch_state()
        if not state:
            _err = json.dumps({"type": "token", "token": "Erreur : API Proxmox inaccessible — commande annulée.\n", "done": True})
            yield "data: " + _err + "\n\n"
            return
        target_status = "running" if action == "stop" else "stopped"
        vm_list = [
            (v["vmid"], v.get("name", f"vm{v['vmid']}"))
            for v in state.get("vms", [])
            if v.get("status") == target_status and v.get("vmid") not in _bypass_pve.PVE_STOP_BLACKLIST
        ]
        if not vm_list:
            _txt = "Aucune VM en cours d'exécution à arrêter.\n" if action == "stop" else "Aucune VM arrêtée à démarrer.\n"
            yield "data: " + json.dumps({"type": "token", "token": _txt, "done": True}) + "\n\n"
            return
    results = []
    for vmid, vmname in vm_list:
        intro = f"Exécution : qm {action} {vmid} ({vmname})...\n"
        yield f"data: {json.dumps({'type': 'token', 'token': intro, 'done': False})}\n\n"
        ok, result, verb, state = vm_execute_one(action, vmid, vmname)
        results.append((vmname, ok, verb, state))
        yield f"data: {json.dumps({'type': 'token', 'token': result, 'done': False})}\n\n"
        if action == "start" and ok:
            check = _vm_start_ssh_map.get(vmid)
            if check:
                host_lbl, ssh_fn_vm = check
                yield from post_start_verify_sse(host_lbl, ssh_fn_vm)
    ok_parts   = [f"VM {n} {v}, état {s}" for n, ok, v, s in results if ok]
    fail_parts = [f"VM {n} en erreur"     for n, ok, v, s in results if not ok]
    summary    = ". ".join(ok_parts + fail_parts) + "." if (ok_parts or fail_parts) else "Opération terminée."
    yield f"data: {json.dumps({'type': 'token', 'token': '', 'done': True})}\n\n"
    yield f"data: {json.dumps({'type': 'speak', 'text': summary})}\n\n"


def post_start_verify_sse(host_label, ssh_fn):
    """Polling SSH + vérification services après start ou reboot — fonction commune."""
    time.sleep(20)
    ssh_ok = False
    for _ in range(12):
        try:
            ok_ping, _ = ssh_fn("echo OK", timeout=6)
            if ok_ping:
                ssh_ok = True
                break
        except Exception:
            pass
        time.sleep(8)
    if not ssh_ok:
        yield _sse_tok(f"✗ **{host_label}** inaccessible après 2 minutes — vérification manuelle requise.\n", done=True)
        return
    _, uptime_out = ssh_fn("uptime -p 2>/dev/null || uptime", timeout=8)
    svcs = _bypass_pve.REBOOT_SVC_CHECKS.get(host_label, [])
    yield _sse_tok(f"**{host_label}** accessible — {(uptime_out or '').strip()}\n")
    if svcs:
        yield _sse_tok("Vérification des services :\n\n")
    all_ok = True
    for svc in svcs:
        _, svc_out = ssh_fn(f"systemctl is-active {svc}", timeout=10)
        status = (svc_out or "").strip().lower()
        if status == "active":
            icon = "✓"
        elif status == "activating":
            icon = "⟳"
        else:
            icon = "✗"
            all_ok = False
        yield _sse_tok(f"  {icon} **{svc}** : {status}\n")
    if all_ok and svcs:
        yield _sse_tok("\nTous les services sont actifs.\n")
    elif svcs:
        yield _sse_tok("\nCertains services sont en échec — vérification requise.\n")


def update_machine_sse(host_label, ssh_fn, is_proxmox=False):
    """apt-get update + upgrade -y sur un hôte SSH — bypass LLM. Détecte reboot requis."""
    if is_proxmox:
        yield _sse_tok("Mise à jour de l'hyperviseur **Proxmox** — VMs actives non affectées.\n\n")
    yield _sse_tok(f"apt-get update sur **{host_label}**...\n")
    ok_upd, out_upd = ssh_fn("apt-get update 2>&1 | tail -3", timeout=60)
    if not ok_upd:
        yield _sse_tok(f"Erreur apt-get update :\n{(out_upd or '')[:300]}\n", done=True)
        return
    yield _sse_tok("Index mis à jour.\n\napt-get dist-upgrade -y...\n")
    ok_upg, out_upg = ssh_fn(
        "DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -y 2>&1", timeout=_ssh_apt_timeout_s)
    # Traçage forensique : write-op SSH réelle via bypass UI (zéro LLM) — comble le
    # trou d'audit (le bypass ne passait pas par ssh/tools.py → audit_writeops.jsonl).
    _sec.audit_writeop(host_label, "apt-get dist-upgrade -y", allowed=ok_upg, output=out_upg or "")
    if not ok_upg:
        yield _sse_tok(f"Erreur apt-get upgrade :\n{(out_upg or '')[:400]}\n", done=True)
        return
    updated = sum(1 for ln in (out_upg or "").splitlines()
                  if "Paramétrage de" in ln or "Setting up" in ln)
    yield _sse_tok(f"**{updated} paquet(s) mis à jour** sur **{host_label}**.\n\n")
    _, rb_out = ssh_fn(
        "test -f /var/run/reboot-required && echo REBOOT_NEEDED || echo NO_REBOOT", timeout=10)
    needs_reboot = "REBOOT_NEEDED" in (rb_out or "")
    if needs_reboot:
        _pending_reboot.clear()
        _pending_reboot.update({"host": host_label, "ssh_fn": ssh_fn, "is_proxmox": is_proxmox, "ts": time.time()})
        warn = "Proxmox — toutes les VMs s'arrêteront au reboot.\n" if is_proxmox else ""
        yield _sse_tok(
            f"**Redémarrage requis** sur **{host_label}**.\n{warn}"
            f"Réponds **`reboot maintenant`** ou **`reporter`**.\n", done=True)
        tts = f"Mise à jour de {host_label} terminée. Redémarrage requis. Reboot maintenant ou reporter ?"
    else:
        yield _sse_tok(f"Pas de redémarrage nécessaire. **{host_label}** est à jour.\n", done=True)
        tts = f"Mise à jour de {host_label} terminée, {updated} paquets installés."
    yield "data: " + json.dumps({"type": "speak", "text": tts}) + "\n\n"


def pve_stop_vms_before_reboot(running):
    """Arrêt propre des VMs Proxmox avec polling confirmation — avant reboot hyperviseur."""
    yield _sse_tok(f"Arrêt propre de **{len(running)} VM(s)** avant redémarrage Proxmox...\n\n")
    for vmid, vmname in running:
        yield _sse_tok(f"  qm stop {vmid} ({vmname})...\n")
        try:
            r = subprocess.run(
                _ssh_proxmox + [f"qm stop {vmid}"],
                capture_output=True, text=True, timeout=_ssh_proxmox_cmd_timeout_s)
            if r.returncode != 0:
                yield _sse_tok(f"  ✗ {vmname} erreur : {(r.stderr or r.stdout).strip()[:100]}\n")
                continue
        except Exception as e:
            yield _sse_tok(f"  ✗ {vmname} exception : {str(e)[:100]}\n")
            continue
        vm_stopped = False
        for _ in range(10):
            time.sleep(6)
            try:
                rs = subprocess.run(
                    _ssh_proxmox + [f"qm status {vmid}"],
                    capture_output=True, text=True, timeout=8)
                if "stopped" in rs.stdout.lower():
                    vm_stopped = True
                    break
            except Exception:
                pass
        yield _sse_tok(f"  ✓ {vmname} arrêtée.\n" if vm_stopped else f"  ⚠ {vmname} timeout — statut non confirmé.\n")
    yield _sse_tok("\n")


def reboot_machine_sse(pending):
    """Exécute le reboot différé. Si Proxmox : arrêt propre de toutes les VMs avant reboot."""
    host   = pending["host"]
    ssh_fn = pending["ssh_fn"]
    is_pve = pending.get("is_proxmox", False)
    _pending_reboot.clear()
    running = []
    if is_pve:
        state = _pve_fetch_state()
        running = [
            (v["vmid"], v.get("name", f"vm{v['vmid']}"))
            for v in (state or {}).get("vms", [])
            if v.get("status") == "running" and v.get("vmid") not in _bypass_pve.PVE_STOP_BLACKLIST
        ]
        if running:
            yield from pve_stop_vms_before_reboot(running)
        else:
            yield _sse_tok("Aucune VM en cours d'exécution — redémarrage direct.\n\n")
    yield _sse_tok(f"Redémarrage de **{host}**...\n")
    try:
        ssh_fn("reboot", timeout=8)
    except Exception:
        pass
    yield _sse_tok("Commande reboot envoyée. Vérification en cours...\n")
    yield from post_start_verify_sse(host, ssh_fn)
    if is_pve and running:
        vm_names = ", ".join(f"**{name}**" for _, name in running)
        yield _sse_tok(
            f"\n⚠ Les VMs arrêtées ne redémarrent pas automatiquement.\n"
            f"Redémarre manuellement : {vm_names}\n")
        tts = "Redémarrage Proxmox terminé. Les VMs devront être redémarrées manuellement."
    else:
        tts = f"Redémarrage de {host} terminé, services vérifiés."
    yield _sse_tok("", done=True)
    yield "data: " + json.dumps({"type": "speak", "text": tts}) + "\n\n"


def service_restart_sse(host_label, ssh_func, svc_name):
    """Restart service SSH — bypass LLM. systemctl restart → is-active → TTS garanti."""
    intro = "Redémarrage " + svc_name + " sur " + host_label + "...\n"
    yield "data: " + json.dumps({"type": "token", "token": intro, "done": False}) + "\n\n"
    try:
        ok_restart, err_restart = ssh_func(f"systemctl restart {svc_name}", timeout=_systemctl_restart_timeout_s)
    except Exception as e:
        err_msg = "Erreur SSH : " + str(e) + "\n"
        tts_err = "Erreur SSH lors du redémarrage de " + svc_name + "."
        yield "data: " + json.dumps({"type": "token", "token": err_msg, "done": True}) + "\n\n"
        yield "data: " + json.dumps({"type": "speak", "text": tts_err}) + "\n\n"
        return
    try:
        _, state_out = ssh_func(f"systemctl is-active {svc_name}", timeout=_systemctl_status_timeout_s)
        state = (state_out or "").strip().lower()
    except Exception:
        state = "inconnu"
    if state == "active":
        msg = "**" + svc_name + " actif.**\n"
        tts = svc_name + " redémarré avec succès."
    elif not ok_restart:
        err_detail = (err_restart or "").strip()[:200]
        msg = "**Échec redémarrage " + svc_name + "** — état : " + (state or "inconnu") + ".\n"
        if err_detail:
            msg += "Erreur : " + err_detail + "\n"
        tts = "Échec du redémarrage de " + svc_name + ". Service " + (state or "inactif") + "."
    else:
        msg = "**" + svc_name + "** — état : " + (state or "inconnu") + ". Vérifier les logs.\n"
        tts = svc_name + " redémarré. État " + (state or "inconnu") + "."
    yield "data: " + json.dumps({"type": "token", "token": msg, "done": False}) + "\n\n"
    yield "data: " + json.dumps({"type": "token", "token": "", "done": True}) + "\n\n"
    yield "data: " + json.dumps({"type": "speak", "text": tts}) + "\n\n"
