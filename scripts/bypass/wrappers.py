"""Wrappers de bypass — délégation vers sous-modules avec DI couplée jarvis.

Extrait de jarvis.py étape 27 (2026-05-23) — 11 wrappers + 3 constantes
couplées aux fonctions SSH locales. Ces wrappers existent parce que les
modules bypass purs (proxmox/code/backup) ne connaissent ni les fonctions
SSH (`_ssh_nginx`, ...), ni `_pve_fetch_state`, ni le `_pending_infra_cmd`
global. Les wrappers servent de glue : ils injectent les deps puis délèguent.

Architecture :
- `init(...)`           : DI complet (5 SSH fns + 3 modules bypass + 4 callables/dicts)
- 3 détecteurs Proxmox  : `detect_service_restart`, `detect_vm_command`,
                          `detect_reboot_command`, `detect_update_command`
- 2 wrappers code       : `detect_code_command`, `code_scp_exec_sse`
- 4 wrappers backup     : `detect_backup_command`, `backup_sse`,
                          `jarvis_backup_log_sse`, `jarvis_backup_sse`
- 1 SSE apt upgrade     : `apt_upgrade_bypass_sse` (logique réelle, pas wrapper)

Constantes calculées dans `init()` car couplées aux fns SSH :
- `_VM_START_SSH_MAP`   : {vmid: (host_label, ssh_fn)} pour post-start verify
- `_UPDATE_REBOOT_HOSTS`: liste tuples (aliases, label, ssh_fn, is_proxmox)
- `_SVC_RESTART_RE`     : regex construite via `proxmox.make_svc_restart_re(bouncer)`
"""
import json
import re

import security_whitelists as _sec

from . import learn as _learn
from . import morning_brief as _morning_brief
from . import system_ctrl as _system_ctrl

# ── Module-level DI placeholders (rempli par init()) ──────────────────────────
_rag_refresh_fn         = None   # () → {"chunks_added": n, ...}
_memory_clear_fn        = None   # () → None
_rag_clear_fn           = None   # () → None
_lesson_save_fn         = None   # (lesson: str) → None
_lesson_index_fn        = None   # (lesson: str) → None
_morning_brief_soc_fn   = None   # () → {"threat_level", "bans_24h", "alerts_24h", ...}
_morning_brief_pve_fn   = None   # () → {"vms": [...], ...}
_ssh_nginx = None
_ssh_proxmox = None
_ssh_clt = None
_ssh_pa85 = None
_ssh_dev1 = None
_bypass_pve = None
_bypass_code = None
_bypass_bk = None
_pve_fetch_state = None
_sse_tok = None
_log = None
_pending_infra_cmd: dict = {}
_allowed_scripts: dict = {}
_ssh_apt_timeout_s = 180
_svc_bouncer = "crowdsec-firewall-bouncer"

# ── Tables/regex calculées dans init() ────────────────────────────────────────
VM_START_SSH_MAP: dict[int, tuple] = {}
UPDATE_REBOOT_HOSTS: list = []
SVC_RESTART_RE = None


def init(
    *,
    ssh_nginx,
    ssh_proxmox,
    ssh_clt,
    ssh_pa85,
    ssh_dev1,
    bypass_pve,
    bypass_code,
    bypass_bk,
    pve_fetch_state,
    sse_tok,
    log,
    pending_infra_cmd: dict,
    allowed_scripts: dict,
    ssh_apt_timeout_s: int = 180,
    svc_bouncer: str = "crowdsec-firewall-bouncer",
    rag_refresh_fn=None,
    memory_clear_fn=None,
    rag_clear_fn=None,
    lesson_save_fn=None,
    lesson_index_fn=None,
    morning_brief_soc_fn=None,
    morning_brief_pve_fn=None,
) -> None:
    """Injecte les deps couplées à jarvis.py et calcule les tables/regex."""
    global _ssh_nginx, _ssh_proxmox, _ssh_clt, _ssh_pa85, _ssh_dev1
    global _bypass_pve, _bypass_code, _bypass_bk
    global _pve_fetch_state, _sse_tok, _log
    global _pending_infra_cmd, _allowed_scripts, _ssh_apt_timeout_s, _svc_bouncer
    global VM_START_SSH_MAP, UPDATE_REBOOT_HOSTS, SVC_RESTART_RE
    global _rag_refresh_fn, _memory_clear_fn, _rag_clear_fn
    global _lesson_save_fn, _lesson_index_fn
    global _morning_brief_soc_fn, _morning_brief_pve_fn
    _rag_refresh_fn          = rag_refresh_fn
    _memory_clear_fn         = memory_clear_fn
    _rag_clear_fn            = rag_clear_fn
    _lesson_save_fn          = lesson_save_fn
    _lesson_index_fn         = lesson_index_fn
    _morning_brief_soc_fn    = morning_brief_soc_fn
    _morning_brief_pve_fn    = morning_brief_pve_fn

    _ssh_nginx = ssh_nginx
    _ssh_proxmox = ssh_proxmox
    _ssh_clt = ssh_clt
    _ssh_pa85 = ssh_pa85
    _ssh_dev1 = ssh_dev1
    _bypass_pve = bypass_pve
    _bypass_code = bypass_code
    _bypass_bk = bypass_bk
    _pve_fetch_state = pve_fetch_state
    _sse_tok = sse_tok
    _log = log
    _pending_infra_cmd = pending_infra_cmd
    _allowed_scripts = allowed_scripts
    _ssh_apt_timeout_s = ssh_apt_timeout_s
    _svc_bouncer = svc_bouncer

    VM_START_SSH_MAP = {
        101: ("srv-dev-1", _ssh_dev1),
        106: ("srv-clt",   _ssh_clt),
        107: ("srv-pa85",  _ssh_pa85),
        108: ("srv-nginx",  _ssh_nginx),
    }
    UPDATE_REBOOT_HOSTS = [
        (["srv-nginx", "srv-ngix"],          "srv-nginx",  _ssh_nginx,    False),
        (["srv-clt",  "clt"],                "srv-clt",   _ssh_clt,     False),
        (["srv-pa85", "pa85"],               "srv-pa85",  _ssh_pa85,    False),
        (["srv-dev-1", "srv-dev", "dev-1"],  "srv-dev-1", _ssh_dev1,    False),
        (["proxmox",  "pve", "hyperviseur"], "proxmox",   _ssh_proxmox, True),
    ]
    SVC_RESTART_RE = _bypass_pve.make_svc_restart_re(_svc_bouncer)


# ── Détecteurs Proxmox ────────────────────────────────────────────────────────

def detect_service_restart(text):
    """Retourne (host_label, ssh_func, svc_name) si restart service détecté."""
    m = SVC_RESTART_RE.search(text)
    if not m:
        return None
    svc_raw = m.group(2).lower()
    if svc_raw == "nginx":
        return ("srv-nginx", _ssh_nginx, "nginx")
    if svc_raw == "crowdsec":
        return ("srv-nginx", _ssh_nginx, "crowdsec")
    if svc_raw == _svc_bouncer:
        return ("srv-nginx", _ssh_nginx, _svc_bouncer)
    if svc_raw == "suricata":
        return ("srv-nginx", _ssh_nginx, "suricata")
    if svc_raw == "fail2ban":
        return ("srv-nginx", _ssh_nginx, "fail2ban")
    svc_name = "php" if svc_raw == "php" else "apache2"
    if re.search(r'\bclt\b', text, re.I):
        return ("clt", _ssh_clt, svc_name)
    if re.search(r'\bpa85\b', text, re.I):
        return ("pa85", _ssh_pa85, svc_name)
    return ("ambiguous", None, svc_name)


def detect_vm_command(text):
    """Wrapper — injecte vms_api depuis pve_fetch_state() puis délègue."""
    state = _pve_fetch_state()
    vms_api = state.get("vms", []) if state else []
    return _bypass_pve.detect_vm_command(text, vms_api)


def detect_reboot_command(text: str):
    """Wrapper — injecte UPDATE_REBOOT_HOSTS puis délègue."""
    return _bypass_pve.detect_reboot_command(text, UPDATE_REBOOT_HOSTS)


def detect_update_command(text: str):
    """Wrapper — injecte UPDATE_REBOOT_HOSTS puis délègue."""
    return _bypass_pve.detect_update_command(text, UPDATE_REBOOT_HOSTS)


def detect_routine_postmaj_command(text: str):
    """Wrapper — injecte UPDATE_REBOOT_HOSTS puis délègue (FAIL-CLOSED)."""
    return _bypass_pve.detect_routine_postmaj_command(text, UPDATE_REBOOT_HOSTS)


def routine_postmaj_re_matches(text: str) -> bool:
    """True si la phrase matche la routine post-MAJ (même sans hôte nommé). Sert au
    dispatcher à distinguer 'ambigu → demander' de 'pas une routine → LLM'."""
    return bool(_bypass_pve.ROUTINE_POSTMAJ_RE.search(text))


# ── Wrappers code ─────────────────────────────────────────────────────────────

def detect_code_command(text: str):
    """Wrapper — délègue à bypass_code."""
    return _bypass_code.detect_code_command(text)


def code_scp_exec_sse(filename: str, exec_it: bool):
    """Wrapper — injecte ssh_dev1 puis délègue à bypass_code."""
    yield from _bypass_code.code_scp_exec_sse(filename, exec_it, _ssh_dev1)


# ── Wrappers backup ───────────────────────────────────────────────────────────

def detect_backup_command(text: str):
    """Wrapper — délègue à bypass_bk."""
    return _bypass_bk.detect_backup_command(text)


def backup_sse(script_key: str):
    """Wrapper — résout script_path depuis allowed_scripts puis délègue."""
    script_path = _allowed_scripts.get(script_key, "")
    yield from _bypass_bk.backup_sse(script_path, script_key)


def jarvis_backup_log_sse():
    """Wrapper — délègue (lit Desktop\\jarvis-backup.log)."""
    yield from _bypass_bk.jarvis_backup_log_sse()


def jarvis_backup_sse():
    """Wrapper — résout script_path puis délègue."""
    script_path = _allowed_scripts.get("backup-jarvis", "")
    yield from _bypass_bk.jarvis_backup_sse(script_path)


# ── Apt upgrade SSE (logique réelle, pas wrapper) ─────────────────────────────

def apt_upgrade_bypass_sse(pending: dict):
    """Exécute l'apt upgrade en attente via SSH direct — zéro LLM."""
    host    = pending["host"]
    ssh_fn  = pending["ssh_fn"]
    pkgs    = pending["packages"]
    _pending_infra_cmd.clear()
    pkg_str = " ".join(pkgs)
    cmd     = f"DEBIAN_FRONTEND=noninteractive apt-get upgrade -y {pkg_str}"
    yield _sse_tok(f"Mise à jour de {len(pkgs)} paquet(s) sur **{host}** :\n")
    for p in pkgs:
        yield _sse_tok(f"  → {p}\n")
    yield _sse_tok("\n")
    _log.info(f"[BYPASS_APT] {host} → {cmd}")
    ok, output = ssh_fn(cmd, timeout=_ssh_apt_timeout_s)
    # Traçage forensique : write-op SSH réelle via bypass UI → audit_writeops.jsonl.
    _sec.audit_writeop(host, cmd, allowed=ok, output=output or "")
    if ok:
        updated = sum(1 for ln in output.splitlines() if "Paramétrage de" in ln or "Setting up" in ln)
        yield _sse_tok(f"✓ {updated} paquet(s) mis à jour sur **{host}**.")
        tts_msg = f"Mise à jour Apache réussie sur {host}, {updated} paquets installés."
    else:
        yield _sse_tok(f"✗ Erreur sur **{host}** :\n{output[:400]}")
        tts_msg = f"Erreur lors de la mise à jour sur {host}."
    yield _sse_tok("", done=True)
    yield "data: " + json.dumps({"type": "speak", "text": tts_msg}) + "\n\n"


# ── Routine post-MAJ : déclencheur VOCAL LECTURE-SEULE (JARVIS = lecteur) ──────
# JARVIS exécute UNIQUEMENT un probe SSH read-only (smoke/health-audit) et LIT le
# verdict. L'exécution réelle (apt/reboot/rebaseline) reste le MENU
# (Invoke-PostMajRoutine, option [m]). Aucune écriture, aucun reboot, aucun pending.

# Smoke web read-only clt/pa85 (miroir de Test-HostWebSmoke côté menu) : apache
# actif + config valide + répond (HTTP non-5xx, non-000) → [VERDICT GO|NO-GO].
_WEB_SMOKE_CMD = (
    "A=$(systemctl is-active apache2 2>/dev/null); "
    "apache2ctl -t >/dev/null 2>&1; C=$?; "
    "H=$(curl -s -o /dev/null -m 8 -w '%{http_code}' http://localhost/ 2>/dev/null); "
    "if [ \"$A\" = active ] && [ \"$C\" = 0 ] && [ \"$H\" -ge 100 ] && [ \"$H\" -lt 500 ]; "
    "then echo \"[VERDICT GO] apache=$A http=$H\"; "
    "else echo \"[VERDICT NO-GO] apache=$A cfg=$C http=$H\"; fi"
)

# Probe SSH LECTURE-SEULE par rôle (miroir de Invoke-PostMajSmokeCheck). Aucune
# commande destructive (rien dans BLOCKED_SSH_PATTERNS) : bash audit, systemctl
# is-active, apache2ctl -t, curl, cut /proc/uptime.
_POSTMAJ_PROBE = {
    "srv-nginx": "bash /opt/clt/health-audit-srv-nginx.sh 2>&1",
    "srv-clt":   _WEB_SMOKE_CMD,
    "srv-pa85":  _WEB_SMOKE_CMD,
    "srv-dev-1": ("U=$(cut -d. -f1 /proc/uptime 2>/dev/null); "
                  "if [ -n \"$U\" ]; then echo \"[VERDICT GO] uptime=${U}s\"; "
                  "else echo '[VERDICT NO-GO] injoignable'; fi"),
}

_POSTMAJ_VERDICT_RE = re.compile(r'\[VERDICT\s+(GO|NO-GO)\]', re.I)
# Codes couleur ANSI emis par health-audit-srv-nginx.sh -> retires a l'affichage.
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')
_POSTMAJ_OK_RE = re.compile(r'\[OK\]')
_POSTMAJ_KO_RE = re.compile(r'\[(?:KO|NO-GO|ERREUR|FAIL|ECHEC)\]', re.I)
# En-tete de section "=== N. Titre ===" (health-audit nginx) -> 1 etape affichee.
# Le titre exige >=1 caractere NON-'=' ([^=]) -> les bordures decoratives pur '='
# (=========) ne sont PAS prises pour des sections.
_POSTMAJ_SECTION_RE = re.compile(r'^={2,}\s*([^=].*?)\s*={2,}$')


def _postmaj_sections(out: str):
    """Sections '=== N. Titre ===' d'un health-audit -> [(titre, ok)]. ok = aucune
    ligne KO/NO-GO dans la section. [] si pas de sections (smoke court clt/pa85/dev-1)."""
    sections, title, fail = [], None, False
    for ln in out.splitlines():
        m = _POSTMAJ_SECTION_RE.match(ln.strip())
        if m:
            if title is not None:
                sections.append((title, not fail))
            title, fail = m.group(1), False
        elif _POSTMAJ_KO_RE.search(ln):
            fail = True
    if title is not None:
        sections.append((title, not fail))
    return sections


def _postmaj_apt_count(ssh_fn) -> int:
    """Nombre de MAJ apt en attente — LECTURE SEULE (index en cache, AUCUN apt-get
    update → zéro écriture, zéro pollution AIDE). Même indicateur que le menu (E1).
    Retourne -1 si la lecture échoue (-> verdict neutre, on ne ment pas)."""
    try:
        _ok, out = ssh_fn("LANG=C apt list --upgradable 2>/dev/null | tail -n +2 | grep -c .", timeout=20)
        mm = re.search(r'(\d+)', out or "")
        return int(mm.group(1)) if mm else -1
    except Exception:
        return -1


def parse_postmaj_verdict(host_label: str, output: str, n_upd: int = -1) -> str:
    """[VERDICT GO/NO-GO] + nb de MAJ apt → phrase TTS explicite (< 280 car). Même
    logique que le menu : sain + N MAJ → exécuter ; sain + 0 → rien à appliquer."""
    m = _POSTMAJ_VERDICT_RE.search(output or "")
    verdict = m.group(1).upper() if m else None
    if verdict == "NO-GO":
        return (f"Attention. Routine post mise à jour {host_label} : l'état n'est pas sain. "
                f"N'exécute pas la routine en réel : ouvre le menu et investigue d'abord.")
    if verdict == "GO":
        if n_upd > 0:
            s = "s" if n_upd > 1 else ""
            return (f"Routine post mise à jour {host_label} : état sain, {n_upd} mise{s} à jour "
                    f"en attente. Tu peux passer sur le menu et l'exécuter en mode réel, "
                    f"l'option deux, pour les appliquer.")
        if n_upd == 0:
            return (f"Routine post mise à jour {host_label} : état sain, et aucune mise à jour "
                    f"système en attente. Rien à appliquer côté apt ; le menu vérifierait "
                    f"quand même l'intégrité si tu veux.")
        return (f"Routine post mise à jour {host_label} : état sain. Tu peux passer sur le "
                f"menu et l'exécuter en mode réel, l'option deux.")
    return (f"Routine post mise à jour {host_label} : verdict illisible. "
            f"Vérifie l'état dans le menu avant d'exécuter.")


def routine_postmaj_sse(host_label: str, ssh_fn, is_proxmox: bool):
    """Déclencheur VOCAL routine post-MAJ — LECTURE-SEULE.

    JARVIS exécute UNIQUEMENT le probe read-only, lit le verdict, puis renvoie
    Marc au MENU pour la partie exécutive. Il N'EXÉCUTE JAMAIS apt/reboot/rebaseline.
    pve : la routine VM ne s'applique pas (reboot coupe les 4 VMs) → renvoi menu.
    """
    if is_proxmox:
        msg = ("La routine post mise à jour ne s'applique pas à Proxmox depuis le chat. "
               "Passe par le menu Proxmox, qui arrête proprement les VMs avant de "
               "redémarrer l'hyperviseur.")
        yield _sse_tok(f"[INFO] {msg}\n", done=True)
        yield "data: " + json.dumps({"type": "speak", "text": msg}) + "\n\n"
        return
    probe = _POSTMAJ_PROBE.get(host_label)
    if not ssh_fn or not probe:
        msg = f"Hôte inconnu pour la routine post mise à jour : {host_label}."
        yield _sse_tok(f"[INFO] {msg}\n", done=True)
        yield "data: " + json.dumps({"type": "speak", "text": msg}) + "\n\n"
        return
    yield _sse_tok(f"[LECTURE-SEULE] **{host_label}** — vérification de l'état…\n\n")
    try:
        ok, output = ssh_fn(probe, timeout=90)
        out = _ANSI_RE.sub("", output or "")  # retire les codes couleur ANSI
        n_upd = _postmaj_apt_count(ssh_fn)  # MAJ apt en attente (read-only, meme logique que le menu)
        speak_msg = parse_postmaj_verdict(host_label, out, n_upd)  # parser = sortie COMPLETE
        # Affichage "chaque étape franchie + résultat final" (accessibilité Marc) :
        # 1 ligne ✓/✗ par SECTION d'audit (jamais le flux brut), puis le verdict.
        for title, sec_ok in _postmaj_sections(out):
            yield _sse_tok(f"{'✓' if sec_ok else '✗'} {title}\n")
        m = _POSTMAJ_VERDICT_RE.search(out)
        verdict_line = next((ln.strip() for ln in out.splitlines() if "[VERDICT" in ln.upper()), "")
        n_ok, n_ko = len(_POSTMAJ_OK_RE.findall(out)), len(_POSTMAJ_KO_RE.findall(out))
        if m:
            sain = m.group(1).upper() == "GO"
            extra = (f"{n_ok} OK, {n_ko} KO" if (n_ok or n_ko)
                     else _POSTMAJ_VERDICT_RE.sub("", verdict_line).strip())
            tail = f" — {extra}" if extra else ""
            yield _sse_tok(f"\n**VERDICT : {host_label} "
                           f"{'✅ SAIN' if sain else '❌ NON SAIN'}{tail}**\n")
            if n_upd > 0:  # MAJ apt en attente (meme logique que le menu)
                yield _sse_tok(f"Mises à jour système : **{n_upd} en attente** → "
                               f"menu, mode réel (option 2) pour les appliquer.\n")
            elif n_upd == 0:
                yield _sse_tok("Mises à jour système : **0 en attente** (rien à appliquer côté apt).\n")
        elif not _postmaj_sections(out):  # ni verdict ni sections → sortie brute (sécurité)
            yield _sse_tok(out[:800])
    except Exception as e:
        yield _sse_tok(f"\n\n**Erreur** : {e}")
        speak_msg = f"Impossible de vérifier {host_label}. Lance le menu manuellement."
    yield _sse_tok("\n_Pour appliquer : menu de la machine, option routine post-MAJ._")
    yield _sse_tok("", done=True)
    yield "data: " + json.dumps({"type": "speak", "text": speak_msg}) + "\n\n"


def routine_postmaj_clarify_sse():
    """Routine demandée sans hôte → demande vocale de préciser (FAIL-CLOSED)."""
    msg = ("Pour quelle machine ? Dis : routine post mise à jour, suivi de "
           "srv-nginx, clt, pa85 ou srv-dev-1.")
    yield _sse_tok(msg, done=True)
    yield "data: " + json.dumps({"type": "speak", "text": msg}) + "\n\n"


# ── System ctrl Hermès (RAG / mémoire) ────────────────────────────────────────

def detect_system_ctrl_command(msg: str) -> str | None:
    """Délègue à system_ctrl.detect_system_ctrl_command."""
    return _system_ctrl.detect_system_ctrl_command(msg)


def system_ctrl_sse(cmd: str):
    """Exécute la commande système cmd et stream le résultat SSE."""
    if cmd == "rag_refresh":
        yield from _system_ctrl.rag_refresh_sse(_rag_refresh_fn)
    elif cmd == "memory_clear":
        yield from _system_ctrl.memory_clear_sse(_memory_clear_fn)
    elif cmd == "rag_clear":
        yield from _system_ctrl.rag_clear_sse(_rag_clear_fn)


# ── Apprentissage Hermès (Brique 4) ───────────────────────────────────────────

def detect_learn_command(msg: str) -> str | None:
    """Extrait la leçon si phrase d'apprentissage détectée, sinon None."""
    return _learn.extract_lesson(msg)


def learn_sse(lesson: str):
    """Wrapper — persiste + indexe la leçon et stream la confirmation SSE."""
    yield from _learn.learn_sse(lesson, _lesson_save_fn, _lesson_index_fn)


# ── Briefing matinal Hermès (Brique 5) ────────────────────────────────────────

def detect_morning_brief(text: str) -> bool:
    """True si le message est un déclencheur de briefing matinal."""
    return _morning_brief.detect_morning_brief(text)


def morning_brief_sse():
    """Wrapper — génère le briefing matinal SSE avec DI injectée."""
    soc_fn = _morning_brief_soc_fn or (lambda: {})
    pve_fn = _morning_brief_pve_fn or (lambda: {})
    yield from _morning_brief.morning_brief_sse(soc_fn, pve_fn)
