"""Tests cœur sécurité JARVIS — construction du contexte SOC + garde-fous.

Cible l'audit dette E1 : _build_monitoring_context / _kc_ban_signal /
_pve_context_lines portent l'injection du contexte SOC dans phi4
(anti-hallucination IP, signal de ban proportionné) et n'étaient pas couverts.

Couvre aussi les régressions des correctifs d'audit :
- M4 : stream_llm ignore une ligne Ollama JSON malformée sans casser le flux ;
- E2 : whitelist de services consolidée dans security_whitelists ;
- M1 : srv-dev-1 rattaché au pattern soc_config (plus de hardcode).
"""
import jarvis as jm
import security_whitelists as sw
from blueprints import soc as soc_module

# ════════════════════════════════════════════════════════════════════════
#  _kc_ban_signal — force du signal de ban d'une IP Kill Chain
# ════════════════════════════════════════════════════════════════════════

def test_kc_ban_signal_exploit_toujours_fort():
    """EXPLOIT = bannissable même sur 1 hit."""
    assert jm._kc_ban_signal({"stage": "EXPLOIT", "count": 1}) == "FORT"


def test_kc_ban_signal_ua_usurpe_toujours_fort():
    """UA de crawler usurpé = FORT quel que soit le stage."""
    assert jm._kc_ban_signal({"stage": "SCAN", "spoofed_bot": "Googlebot", "count": 1}) == "FORT"


def test_kc_ban_signal_scan_isole_faible():
    """SCAN isolé sous le seuil = faible (bruit de fond, à surveiller)."""
    assert jm._kc_ban_signal({"stage": "SCAN", "count": 3}) == "faible"


def test_kc_ban_signal_activite_soutenue_fort():
    """Activité ≥ seuil de hits = FORT même hors EXPLOIT."""
    assert jm._kc_ban_signal({"stage": "RECON", "count": jm._KC_BAN_SIGNAL_MIN_HITS}) == "FORT"


def test_kc_ban_signal_count_absent_faible():
    assert jm._kc_ban_signal({"stage": "RECON"}) == "faible"


def test_kc_ban_signal_count_none_faible():
    """count=None ne doit pas lever — fallback 0."""
    assert jm._kc_ban_signal({"stage": "RECON", "count": None}) == "faible"


# ════════════════════════════════════════════════════════════════════════
#  _pve_context_lines — résumé Proxmox injecté dans le contexte LLM
# ════════════════════════════════════════════════════════════════════════

def test_pve_context_lines_non_configure_vide():
    assert jm._pve_context_lines({}) == []
    assert jm._pve_context_lines({"configured": False}) == []


def test_pve_context_lines_erreur_vide():
    """Erreur API Proxmox → aucune ligne (pas de données partielles)."""
    assert jm._pve_context_lines({"configured": True, "error": "timeout"}) == []


def test_pve_context_lines_configure_resume():
    pve = {"configured": True, "vms_running": 3, "vms_total": 4,
           "nodes": [{"vms": [
               {"vmid": 108, "name": "srv-nginx", "status": "running",
                "cpu": 0.12, "mem": 2_000_000, "maxmem": 4_000_000}]}]}
    lines = jm._pve_context_lines(pve)
    assert any("3/4 VMs running" in ln for ln in lines)
    assert any("srv-nginx" in ln and "running" in ln for ln in lines)


def test_pve_context_lines_maxmem_zero_pas_de_division():
    """maxmem=0 ne doit pas lever ZeroDivisionError."""
    pve = {"configured": True, "vms_running": 1, "vms_total": 1,
           "nodes": [{"vms": [{"vmid": 1, "name": "x", "status": "stopped",
                               "cpu": None, "mem": 0, "maxmem": 0}]}]}
    lines = jm._pve_context_lines(pve)
    assert any("RAM=0%" in ln for ln in lines)


# ════════════════════════════════════════════════════════════════════════
#  _build_monitoring_context — bloc de contexte SOC pour phi4
# ════════════════════════════════════════════════════════════════════════

def test_build_context_dict_vide_ne_crashe_pas():
    """Robustesse : un monitoring.json vide ne doit jamais lever."""
    out = jm._build_monitoring_context({})
    assert "DONNÉES SOC EN TEMPS RÉEL" in out
    assert "SCORE OFFICIEL" in out


def test_build_context_header_personnalise():
    out = jm._build_monitoring_context({}, header="=== CUSTOM HEADER ===")
    assert out.startswith("=== CUSTOM HEADER ===")


def test_build_context_score_niveau_et_horodatage():
    out = jm._build_monitoring_context(
        {"threat_score": 73, "threat_level": "ÉLEVÉ", "generated_at": "2026-05-22 10:00"})
    assert "73/100" in out
    assert "ÉLEVÉ" in out
    assert "2026-05-22 10:00" in out


def test_build_context_ips_bannies_crowdsec_listees():
    """Les IPs déjà bannies sont injectées avec leur maillon KC backend."""
    d = {"crowdsec": {"active_decisions": 1,
                      "decisions_detail": {"1.2.3.4": {"scenario": "http-probing"}}},
         "kill_chain": {"neutralized_ips": [{"ip": "1.2.3.4", "origin_stage": "EXPLOIT"}]}}
    out = jm._build_monitoring_context(d)
    assert "1.2.3.4" in out
    assert "DÉJÀ BANNIES" in out
    assert "maillon-KC=EXPLOIT" in out


def test_build_context_active_ip_exploit_non_bloquee_signal_fort():
    d = {"kill_chain": {"active_ips": [
        {"ip": "9.9.9.9", "stage": "EXPLOIT", "count": 5, "country": "CN"}]}}
    out = jm._build_monitoring_context(d)
    assert "9.9.9.9" in out
    assert "NON-BLOQUÉE" in out
    assert "signal=FORT" in out


def test_build_context_verified_bots_exclus_du_ban():
    d = {"kill_chain": {"verified_bots": [{"ip": "66.249.1.1", "bot": "Googlebot"}]}}
    out = jm._build_monitoring_context(d)
    assert "66.249.1.1" in out
    assert "Googlebot" in out
    assert "NE JAMAIS recommander de les bannir" in out


def test_build_context_infra_ips_anti_hallucination():
    """Les IPs d'infra SOC sont toujours injectées (garde anti-hallucination)."""
    out = jm._build_monitoring_context({})
    assert "192.168.1.50" in out
    assert "RFC1918" in out
    assert "JAMAIS source d'attaque" in out


def test_build_context_slow_campaigns():
    d = {"slow_campaigns": [{"subnet": "45.146.165.0/24", "count": 12,
                             "last_seen": "2026-05-20T08:00:00"}]}
    out = jm._build_monitoring_context(d)
    assert "45.146.165.0/24" in out
    assert "Campagnes lentes" in out


# ════════════════════════════════════════════════════════════════════════
#  M4 — stream_llm résiste à une ligne Ollama JSON malformée
# ════════════════════════════════════════════════════════════════════════

class _FakeResp:
    """Réponse streaming factice — context manager + iter_lines."""

    def __init__(self, lines):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *_a):
        return False

    def iter_lines(self):
        return iter(self._lines)


def test_stream_llm_ignore_ligne_json_malformee(monkeypatch):
    """M4 — une ligne malformée est sautée, le flux continue."""
    lines = [
        b'{ ceci nest pas du json',
        b'{"message": {"content": "bonjour"}, "done": false}',
        b'{"message": {"content": ""}, "done": true}',
    ]
    monkeypatch.setattr(jm._ollama_circuit, "call", lambda *a, **k: _FakeResp(lines))
    out = list(jm.stream_llm([{"role": "user", "content": "test"}]))
    text = "".join(chunk for chunk, _done in out)
    assert "bonjour" in text
    assert out[-1][1] is True


def test_stream_llm_circuit_ouvert_message_clair(monkeypatch):
    """Circuit breaker ouvert → message [JARVIS] + done, sans exception."""
    def _raise(*_a, **_k):
        raise jm.OllamaUnavailable("circuit ouvert")

    monkeypatch.setattr(jm._ollama_circuit, "call", _raise)
    out = list(jm.stream_llm([{"role": "user", "content": "test"}]))
    assert len(out) == 1
    assert out[0][1] is True
    assert "[JARVIS]" in out[0][0]


# ════════════════════════════════════════════════════════════════════════
#  E2 — whitelist de services consolidée (source unique)
# ════════════════════════════════════════════════════════════════════════

def test_soc_allowed_services_pointe_sur_source_unique():
    """soc._ALLOWED_SERVICES EST security_whitelists.ALLOWED_SOC_RESTART_SVCS."""
    assert soc_module._ALLOWED_SERVICES is sw.ALLOWED_SOC_RESTART_SVCS


def test_soc_restart_whitelist_contenu_reel():
    """Contenu aligné sur les services réels de srv-nginx (vérif SSH 2026-05-22).
    `suricata` inclus : l'auto-engine SOC doit pouvoir le redémarrer (déclencheur #10)."""
    assert sw.ALLOWED_SOC_RESTART_SVCS == {"nginx", "crowdsec", "fail2ban", "suricata"}


def test_les_deux_whitelists_services_vivent_dans_le_meme_module():
    """Toute la politique de whitelist de services est dans security_whitelists."""
    assert hasattr(sw, "ALLOWED_RESTART_SVCS")
    assert hasattr(sw, "ALLOWED_SOC_RESTART_SVCS")


def test_aucune_whitelist_ne_contient_php_fpm():
    """Garde-fou : aucun hôte ne tourne php-fpm (vérif SSH 2026-05-22 — mod_php
    sur clt/pa85, pas de PHP sur srv-nginx). Empêche de réintroduire une entrée morte."""
    for svc in (sw.ALLOWED_RESTART_SVCS | sw.ALLOWED_SOC_RESTART_SVCS):
        assert "fpm" not in svc


# ════════════════════════════════════════════════════════════════════════
#  M1 — srv-dev-1 rattaché au pattern soc_config (plus de hardcode)
# ════════════════════════════════════════════════════════════════════════

def test_soc_config_dev1_dans_les_defauts():
    import soc_config_loader
    assert soc_config_loader.DEFAULTS["dev1_host"] == "192.168.1.21"
    assert soc_config_loader.DEFAULTS["dev1_ssh_port"] == "2272"
    assert "id_dev" in soc_config_loader.DEFAULTS["dev1_ssh_key"]


def test_ssh_dev1_construit_depuis_la_config():
    """_SSH_DEV1 est dérivé de _SOC_CFG, comme les 4 autres hôtes."""
    assert "root@192.168.1.21" in soc_module._SSH_DEV1
    assert "2272" in soc_module._SSH_DEV1
