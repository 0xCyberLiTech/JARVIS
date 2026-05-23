"""Bypass backup — détection + exécution scripts PowerShell de sauvegarde (zéro LLM).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 9.

Couvre :
- Détection regex : sauvegarde Proxmox / disk-report / backup JARVIS / log JARVIS
- Parsing résumé sauvegarde (VMs + quota)
- Exécution streaming PowerShell `proxmox-backup-auto.ps1`, `windows-disk-report.ps1`,
  `backup-jarvis.ps1`
- Lecture log `Desktop\\jarvis-backup.log`

Dependency injection : `script_path` est passé en argument (au lieu d'aller chercher
dans `_ALLOWED_SCRIPTS` couplé à `_WORKSPACE_ROOT` côté jarvis.py).
"""
import json
import os
import re
import subprocess

# ── Timeouts ──────────────────────────────────────────────────
BACKUP_PROC_TIMEOUT_S      = 300   # backup-auto / disk-report (5 min max)
BACKUP_PROC_LONG_TIMEOUT_S = 3600  # backup JARVIS complet (1h max)

# ── Regex publiques ───────────────────────────────────────────
BACKUP_RE = re.compile(
    r'\b(sauvegarde[rz]?\b|backup\b|sauvegarder?\b|lance[rz]?\s+(?:une\s+)?sauvegarde[rz]?\b)'
    r'.{0,60}(?:vm[s]?\b|proxmox\b|machines?\s+virtuelles?\b)',
    re.I,
)
DISKREPORT_RE = re.compile(
    r'\b(disk[- ]?report\b|rapport\s+disque\b|windows[- ]?disk\b|rapport\s+windows\b)',
    re.I,
)
JARVIS_BACKUP_RE = re.compile(
    r'\b(sauvegarde[rz]?\b|backup\b|lance[rz]?\s+(?:une\s+)?sauvegarde[rz]?\b)'
    r'.{0,40}\bjarvis\b',
    re.I,
)
JARVIS_BACKUP_LOG_RE = re.compile(
    r'\b(log|[eé]tat|avanc[eé]|o[uù]\s+en\s+est|progression|avancement|statut|progr[eè]s)'
    r'.{0,40}\bjarvis\b|\bjarvis\b.{0,40}\b(log|[eé]tat|avanc[eé]|statut)\b',
    re.I,
)

# Parser résumé sauvegarde Proxmox
_VM_LINE_RE = re.compile(
    r'^\s*([\w][\w.-]*)\s+(\d{2}:\d{2}:\d{2})\s+([\d.]+\s*Go)\s+(OK|ECHEC)\b',
    re.I,
)
_QUOTA_LINE_RE = re.compile(
    r'QUOTA\s*\[.*?\]\s*([\d.]+\s*Go\s*/\s*\d+\s*Go\s*\([\d.]+%\))',
    re.I,
)


# ── Helpers ───────────────────────────────────────────────────

def _sse_tok(t: str, done: bool = False) -> str:
    """Helper SSE token (dupliqué de jarvis.py pour autonomie du module)."""
    return f"data: {json.dumps({'type':'token','token':t,'done':done})}\n\n"


def parse_backup_summary(lines: list) -> tuple:
    """Retourne (résumé_markdown, texte_tts) depuis la sortie du script backup."""
    vms, quota = [], ""
    for line in lines:
        m = _VM_LINE_RE.match(line)
        if m:
            vm, _, taille, statut = m.groups()
            icon = "✅" if statut.upper() == "OK" else "❌"
            vms.append((icon, vm, taille.strip(), statut.upper()))
        q = _QUOTA_LINE_RE.search(line)
        if q:
            quota = q.group(1).strip()  # dernière occurrence gagne
    if not vms:
        return "", ""
    md = "\n".join(f"{icon} **{vm}** — {taille}" for icon, vm, taille, _ in vms)
    if quota:
        md += f"\nQuota : {quota}"
    ok_vms = [vm for _, vm, _, s in vms if s == "OK"]
    fail_vms = [vm for _, vm, _, s in vms if s != "OK"]
    if fail_vms:
        tts = (f"Sauvegarde terminée avec erreurs. "
               f"{', '.join(ok_vms)} sauvegardées avec succès. "
               f"Échec sur {', '.join(fail_vms)}.")
    else:
        details = ", ".join(f"{vm} {taille}" for _, vm, taille, _ in vms)
        tts = f"Sauvegarde terminée. {details}. Toutes les machines sont protégées."
    return md, tts


# ── Détecteur ─────────────────────────────────────────────────

def detect_backup_command(text: str) -> str | None:
    """Retourne ('backup-auto'|'disk-report'|'backup-jarvis'|'backup-jarvis-log') ou None."""
    if JARVIS_BACKUP_LOG_RE.search(text):
        return "backup-jarvis-log"
    if JARVIS_BACKUP_RE.search(text):
        return "backup-jarvis"
    if BACKUP_RE.search(text):
        return "backup-auto"
    if DISKREPORT_RE.search(text):
        return "disk-report"
    return None


# ── Générateurs SSE ───────────────────────────────────────────

def backup_sse(script_path: str, script_key: str):
    """Exécute proxmox-backup-auto.ps1 ou windows-disk-report.ps1 — bypass LLM.

    `script_path` : chemin absolu PowerShell (résolu par jarvis.py via _ALLOWED_SCRIPTS).
    `script_key` : 'backup-auto' ou 'disk-report' (pour label + parser).
    """
    if not script_path:
        yield _sse_tok(f"Erreur : script '{script_key}' inconnu.", done=True)
        return

    labels = {
        "backup-auto": ("Sauvegarde Proxmox", "proxmox-backup-auto.ps1", "Sauvegarde terminée."),
        "disk-report": ("Rapport disque Windows", "windows-disk-report.ps1", "Rapport disque envoyé au SOC."),
    }
    label, fname, speak_msg = labels.get(script_key, (script_key, script_key, "Script terminé."))
    yield _sse_tok(f"[LOCAL] Exécution : `{fname}`…\n\n")

    buf = []
    try:
        proc = subprocess.Popen(
            ["powershell.exe", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", script_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        for line in proc.stdout:
            buf.append(line)
            yield _sse_tok(line)
        proc.wait(timeout=BACKUP_PROC_TIMEOUT_S)
        rc = proc.returncode
        status = "✓ Succès" if rc == 0 else f"✗ Code {rc}"
        if script_key == "backup-auto":
            summary_md, summary_tts = parse_backup_summary(buf)
            if summary_md:
                yield _sse_tok(f"\n\n{summary_md}")
                speak_msg = summary_tts or speak_msg
        yield _sse_tok(f"\n\n**{status}**")
    except subprocess.TimeoutExpired:
        proc.kill()
        yield _sse_tok(f"\n\n**✗ Timeout** — {label} dépasse 300s.")
        speak_msg = "Timeout dépassé pour la sauvegarde."
    except Exception as e:
        yield _sse_tok(f"\n\n**✗ Erreur** : {e}")
        speak_msg = "Erreur lors de la sauvegarde."

    yield _sse_tok("", done=True)
    yield f"data: {json.dumps({'type':'speak','text':speak_msg})}\n\n"


def jarvis_backup_log_sse():
    """Lit Desktop\\jarvis-backup.log et affiche les dernières lignes — bypass LLM."""
    log_path = os.path.join(os.path.expanduser("~"), "Desktop", "jarvis-backup.log")
    if not os.path.isfile(log_path):
        yield _sse_tok("Aucun log trouvé — la sauvegarde n'a pas encore démarré.", done=True)
        yield "data: " + json.dumps({"type": "speak", "text": "Aucun log de sauvegarde trouvé."}) + "\n\n"
        return

    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        yield _sse_tok("Erreur lecture log : " + str(e), done=True)
        return

    last_lines = lines[-30:] if len(lines) > 30 else lines
    last_line = (lines[-1].strip() if lines else "").lower()
    done_kw = ["sauvegarde terminée", "=== sauvegarde terminee ==="]
    finished = any(kw in last_line for kw in done_kw)

    yield _sse_tok("**Log sauvegarde JARVIS** — 30 dernières lignes :\n\n```\n")
    for line in last_lines:
        yield _sse_tok(line)
    yield _sse_tok("```\n")

    if finished:
        speak = "Sauvegarde JARVIS terminée."
        yield _sse_tok("\n**Sauvegarde terminée.**")
    else:
        speak = "Sauvegarde JARVIS en cours."
        yield _sse_tok("\n**En cours…**")

    yield _sse_tok("", done=True)
    yield "data: " + json.dumps({"type": "speak", "text": speak}) + "\n\n"


def jarvis_backup_sse(script_path: str):
    """Exécute backup-jarvis.ps1 en streaming — bypass LLM, annonce TTS à la fin.

    `script_path` : chemin absolu vers backup-jarvis.ps1 (résolu côté jarvis.py).
    """
    if not script_path or not os.path.isfile(script_path):
        yield _sse_tok("Erreur : `backup-jarvis.ps1` introuvable.", done=True)
        return

    yield _sse_tok("[LOCAL] Sauvegarde JARVIS démarrée…\n\n")
    speak_msg = "Sauvegarde JARVIS terminée. Toutes les données sont protégées."
    try:
        proc = subprocess.Popen(
            ["powershell.exe", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", script_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        )
        for line in proc.stdout:
            yield _sse_tok(line)
        proc.wait(timeout=BACKUP_PROC_LONG_TIMEOUT_S)
        rc = proc.returncode
        if rc == 0:
            status = "✓ Sauvegarde terminée"
        else:
            status = "✗ Code " + str(rc)
            speak_msg = "Sauvegarde JARVIS terminée avec des erreurs. Code " + str(rc) + "."
        yield _sse_tok("\n\n**" + status + "**")
    except subprocess.TimeoutExpired:
        proc.kill()
        yield _sse_tok("\n\n**✗ Timeout** — dépasse 60 min.")
        speak_msg = "Timeout dépassé pour la sauvegarde JARVIS."
    except Exception as e:
        yield _sse_tok("\n\n**✗ Erreur** : " + str(e))
        speak_msg = "Erreur lors de la sauvegarde JARVIS."

    yield _sse_tok("", done=True)
    yield "data: " + json.dumps({"type": "speak", "text": speak_msg}) + "\n\n"
