"""Tuile **commands** — générateurs SSE pour commandes infra (VM/reboot/update/service).

14ème tuile. Pas de routes HTTP — les générateurs sont appelés par le routing
bypass de `_chat_try_bypass`.

Public surface : `init()` + 7 générateurs (vm_command_sse, post_start_verify_sse,
update_machine_sse, pve_stop_vms_before_reboot, reboot_machine_sse,
service_restart_sse, vm_execute_one).
"""
from . import sse

init                       = sse.init
vm_execute_one             = sse.vm_execute_one
vm_command_sse             = sse.vm_command_sse
post_start_verify_sse      = sse.post_start_verify_sse
update_machine_sse         = sse.update_machine_sse
pve_stop_vms_before_reboot = sse.pve_stop_vms_before_reboot
reboot_machine_sse         = sse.reboot_machine_sse
service_restart_sse        = sse.service_restart_sse
