"""Tests chat_pending_bypass — confirmation/annulation commandes infra différées (apt/reboot)."""
import re

from chat_pending_bypass import resolve_pending_bypass


def _captured_args():
    """Capture les arguments passés au sse_response_fn (vérification + retour)."""
    holder = {"called_with": None}

    def sse_resp(gen):
        holder["called_with"] = list(gen)
        return "RESPONSE_OBJ"

    return holder, sse_resp


def _call(**overrides):
    holder, sse_resp = _captured_args()
    args = dict(
        orig_last="oui",
        pending_infra_cmd={},
        pending_reboot={},
        ttl_s=300,
        confirm_re=re.compile(r"^(oui|confirme|ok)\b", re.I),
        cancel_re=re.compile(r"^(non|annule|stop)\b", re.I),
        reboot_now_re=re.compile(r"reboot maintenant", re.I),
        reboot_defer_re=re.compile(r"plus tard|différer", re.I),
        apt_upgrade_sse_fn=lambda d: iter([f"upgrade-sse:{d['host']}"]),
        reboot_machine_sse_fn=lambda d: iter([f"reboot-sse:{d['host']}"]),
        sse_response_fn=sse_resp,
        sse_tok_fn=lambda t, done=False: f"TOK[{t},done={done}]",
        log_info_fn=lambda msg: None,
        now_fn=lambda: 1000.0,
    )
    args.update(overrides)
    return resolve_pending_bypass(args.pop("orig_last"), **args), holder


# ── Cas 1 : aucune commande en attente ────────────────────────────────────


def test_aucune_commande_en_attente_renvoie_none():
    result, _ = _call()
    assert result is None


# ── Cas 2 : apt upgrade en attente ────────────────────────────────────────


def test_oui_confirme_apt_upgrade_en_attente():
    pending = {"host": "srv-ngix", "packages": ["nginx"], "ts": 950.0}
    result, holder = _call(orig_last="oui", pending_infra_cmd=pending)
    assert result == "RESPONSE_OBJ"
    assert holder["called_with"] == ["upgrade-sse:srv-ngix"]


def test_non_annule_apt_upgrade_et_clear_pending():
    pending = {"host": "srv-ngix", "ts": 950.0}
    result, holder = _call(orig_last="non", pending_infra_cmd=pending)
    assert result == "RESPONSE_OBJ"
    assert pending == {}  # cleared
    assert holder["called_with"] == ["TOK[Mise à jour annulée.,done=True]"]


def test_apt_pending_expire_par_ttl_est_clear_et_renvoie_none():
    """ts trop ancien (delta > ttl_s) → cleared + None."""
    pending = {"host": "srv-ngix", "ts": 100.0}  # delta = 900 > 300
    result, _ = _call(orig_last="oui", pending_infra_cmd=pending)
    assert result is None
    assert pending == {}


def test_message_quelconque_avec_apt_pending_renvoie_none():
    """`maybe later` ne match ni confirm ni cancel → None, pending préservé."""
    pending = {"host": "srv-ngix", "ts": 950.0}
    result, _ = _call(orig_last="bonjour", pending_infra_cmd=pending)
    assert result is None
    assert pending == {"host": "srv-ngix", "ts": 950.0}


def test_confirme_apt_passe_une_copie_du_pending_au_handler():
    """Le pending dict ne doit pas être muté par le handler (passé en copie)."""
    pending = {"host": "srv-ngix", "ts": 950.0}

    def handler(d):
        d["mutated"] = True
        yield "x"

    _call(orig_last="oui", pending_infra_cmd=pending, apt_upgrade_sse_fn=handler)
    assert "mutated" not in pending


# ── Cas 3 : reboot en attente ─────────────────────────────────────────────


def test_reboot_maintenant_confirme_reboot_pending():
    pending = {"host": "srv-clt", "ts": 950.0}
    result, holder = _call(orig_last="reboot maintenant", pending_reboot=pending)
    assert result == "RESPONSE_OBJ"
    assert holder["called_with"] == ["reboot-sse:srv-clt"]


def test_plus_tard_diffère_le_reboot_et_clear():
    pending = {"host": "srv-clt", "ts": 950.0}
    result, holder = _call(orig_last="plus tard", pending_reboot=pending)
    assert result == "RESPONSE_OBJ"
    assert pending == {}
    assert "Redémarrage différé" in holder["called_with"][0]


def test_non_annule_aussi_le_reboot_pending():
    """`cancel_re` (non/annule) match aussi le reboot defer path."""
    pending = {"host": "srv-clt", "ts": 950.0}
    result, _ = _call(orig_last="non", pending_reboot=pending)
    assert result == "RESPONSE_OBJ"
    assert pending == {}


def test_reboot_pending_expire_est_clear_et_renvoie_none():
    pending = {"host": "srv-clt", "ts": 100.0}  # delta = 900 > 300
    result, _ = _call(orig_last="reboot maintenant", pending_reboot=pending)
    assert result is None
    assert pending == {}


# ── Combinaisons : les 2 pending peuvent coexister ───────────────────────


def test_apt_pending_traite_en_premier_si_les_deux_actifs():
    """Le code teste apt avant reboot → apt confirm stoppe avant reboot check."""
    apt = {"host": "srv-ngix", "ts": 950.0}
    reboot = {"host": "srv-clt", "ts": 950.0}
    result, holder = _call(
        orig_last="oui",
        pending_infra_cmd=apt,
        pending_reboot=reboot,
    )
    assert result == "RESPONSE_OBJ"
    assert holder["called_with"] == ["upgrade-sse:srv-ngix"]
    # reboot non touché
    assert reboot == {"host": "srv-clt", "ts": 950.0}


# ── Logging ──────────────────────────────────────────────────────────────


def test_log_appele_lors_de_confirm_apt():
    captured = []
    pending = {"host": "srv-ngix", "ts": 950.0}
    _call(orig_last="oui", pending_infra_cmd=pending, log_info_fn=captured.append)
    assert any("[BYPASS_APT] confirmation" in m for m in captured)
    assert any("srv-ngix" in m for m in captured)


def test_log_appele_lors_d_annulation_apt():
    captured = []
    pending = {"host": "srv-ngix", "ts": 950.0}
    _call(orig_last="non", pending_infra_cmd=pending, log_info_fn=captured.append)
    assert any("[BYPASS_APT] annulé" in m for m in captured)
