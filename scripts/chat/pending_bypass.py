"""Chat pending bypass — confirme/annule commandes infra différées.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 26 (Chat/LLM core).

Quand JARVIS détecte "apt list --upgradable" sur une VM, il met les paquets
en attente de confirmation. À la réponse suivante de l'utilisateur :
- "oui" / "confirme" → lance `apt upgrade` réellement
- "non" / "annule"   → vide la queue
- TTL 5 min sinon expire automatiquement

Idem pour reboot différé après upgrade : "reboot maintenant" ou "plus tard".

Dependency injection : pending dicts + regex + SSE generators (apt_upgrade, reboot_machine)
+ helpers SSE passés en kwargs.
"""


def resolve_pending_bypass(
    orig_last: str,
    *,
    pending_infra_cmd: dict,
    pending_reboot: dict,
    ttl_s: int,
    confirm_re,
    cancel_re,
    reboot_now_re,
    reboot_defer_re,
    apt_upgrade_sse_fn,
    reboot_machine_sse_fn,
    sse_response_fn,
    sse_tok_fn,
    log_info_fn,
    now_fn,
):
    """Confirme ou annule une commande infra en attente (apt upgrade / reboot différé).

    Retourne une Response Flask SSE si match, sinon None.
    """
    # ── Apt upgrade en attente ────────────────────────────────
    if pending_infra_cmd and (now_fn() - pending_infra_cmd.get("ts", 0)) < ttl_s:
        if confirm_re.match(orig_last):
            log_info_fn(f"[BYPASS_APT] confirmation '{orig_last.strip()}' → {pending_infra_cmd['host']}")
            return sse_response_fn(apt_upgrade_sse_fn(dict(pending_infra_cmd)))
        if cancel_re.match(orig_last):
            pending_infra_cmd.clear()
            log_info_fn("[BYPASS_APT] annulé par l'utilisateur")

            def _cancel_gen():
                yield sse_tok_fn("Mise à jour annulée.", done=True)

            return sse_response_fn(_cancel_gen())
    elif pending_infra_cmd:
        pending_infra_cmd.clear()  # TTL expiré

    # ── Reboot en attente (différé après upgrade) ─────────────
    if pending_reboot and (now_fn() - pending_reboot.get("ts", 0)) < ttl_s:
        if reboot_now_re.search(orig_last):
            log_info_fn(f"[BYPASS_REBOOT] reboot confirmé → {pending_reboot['host']}")
            return sse_response_fn(reboot_machine_sse_fn(dict(pending_reboot)))
        if reboot_defer_re.search(orig_last) or cancel_re.match(orig_last):
            pending_reboot.clear()
            log_info_fn("[BYPASS_REBOOT] reboot différé par l'utilisateur")

            def _defer_gen():
                yield sse_tok_fn("Redémarrage différé. Pense à redémarrer manuellement.", done=True)

            return sse_response_fn(_defer_gen())
    elif pending_reboot:
        pending_reboot.clear()  # TTL expiré

    return None
