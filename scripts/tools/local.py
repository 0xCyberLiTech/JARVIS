"""3 outils LLM exécutés en local Windows.

Extrait de jarvis.py étape 33 (2026-05-23). Trois fonctions appelées par le
dispatcher chat quand le LLM émet un tool_call :

1. `executer_code(args)`           — exécute du Python via `subprocess.run`
   Pré-vérification stricte : blocs hard (`shutil.rmtree`) + args dangereux
   (rm -rf, format c:, qm destroy, systemctl stop nginx/crowdsec/fail2ban/ssh…)
   → refusé + audité via `sec_log`. Timeout configurable (défaut 15 s).

2. `soc_status()`                   — wrapper qui appelle `fetch_monitoring` +
   formate via `build_monitoring_context` avec header "=== SOC STATUS ===".
   Utilisé par phi4 SOC pour récupérer un snapshot dashboard live à la demande.

3. `executer_script_windows(args)`  — exécute un script PowerShell whitelist
   stricte (clé `script` → chemin dans `allowed_scripts`). Timeout `proc_timeout_s`.

DI via `init(...)` :
- `blocked_hard`, `blocked_args`  : whitelists sécurité executer_code
- `sec_log`                       : logger événements sécurité (refus)
- `fetch_monitoring`              : callable (force: bool) → (ok, raw_json)
- `build_monitoring_context`      : callable (d: dict, header: str) → str
- `allowed_scripts`               : dict {clé: chemin .ps1}
- `proc_timeout_s`                : int (timeout subprocess script Windows)
"""
import json
import subprocess
import sys

# ── DI placeholders ───────────────────────────────────────────────────────────
_blocked_hard: list = []
_blocked_args: list = []
_sec_log = None
_fetch_monitoring = None
_build_monitoring_context = None
_allowed_scripts: dict = {}
_proc_timeout_s: int = 300


def init(
    *,
    blocked_hard: list,
    blocked_args: list,
    sec_log,
    fetch_monitoring,
    build_monitoring_context,
    allowed_scripts: dict,
    proc_timeout_s: int = 300,
) -> None:
    """Injecte les deps des 3 outils LLM locaux."""
    global _blocked_hard, _blocked_args, _sec_log
    global _fetch_monitoring, _build_monitoring_context
    global _allowed_scripts, _proc_timeout_s
    _blocked_hard = blocked_hard
    _blocked_args = blocked_args
    _sec_log = sec_log
    _fetch_monitoring = fetch_monitoring
    _build_monitoring_context = build_monitoring_context
    _allowed_scripts = allowed_scripts
    _proc_timeout_s = proc_timeout_s


def executer_code(args):
    """Exécute du Python via subprocess.run. Whitelist hard + args avant lancement."""
    code    = args["code"]
    timeout = int(args.get("timeout", 15))
    for pattern in _blocked_hard:
        if pattern in code:
            _sec_log("hard", pattern, code)
            return f"Erreur : opération refusée par sécurité ({pattern})"
    code_lower = code.lower()
    for pattern in _blocked_args:
        if pattern.lower() in code_lower:
            _sec_log("args", pattern, code)
            return f"Erreur : argument de commande refusé par sécurité ({pattern})"
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=timeout
        )
        out = result.stdout[:3000] if result.stdout else ""
        err = result.stderr[:1000] if result.stderr else ""
        if err and not out:
            return f"ERREUR:\n{err}"
        if err:
            return f"SORTIE:\n{out}\nAVERTISSEMENT:\n{err}"
        return out or "(aucune sortie)"
    except subprocess.TimeoutExpired:
        return f"Erreur : timeout dépassé ({timeout}s)"


def soc_status():
    """Snapshot SOC formaté pour injection LLM (header '=== SOC STATUS ===')."""
    ok, raw = _fetch_monitoring(force=True)
    if not ok:
        return f"Erreur SSH srv-ngix : {raw}"
    try:
        return _build_monitoring_context(json.loads(raw), header="=== SOC STATUS ===")
    except Exception as e:
        return f"monitoring.json brut (parse error: {e}):\n{raw[:3000]}"


def executer_script_windows(args):
    """Exécute un script PowerShell local (whitelist stricte sur clé `script`)."""
    script_key = args.get("script", "").strip()
    script_path = _allowed_scripts.get(script_key)
    if not script_path:
        return f"Erreur : script '{script_key}' non autorisé. Scripts disponibles : {', '.join(_allowed_scripts)}"
    try:
        proc = subprocess.Popen(
            ["powershell.exe", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", script_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace"
        )
        out, _ = proc.communicate(timeout=_proc_timeout_s)
        rc = proc.returncode
        result = out.strip()[:3000] if out else "(aucune sortie)"
        return f"Script '{script_key}' terminé (code {rc}).\n{result}"
    except subprocess.TimeoutExpired:
        proc.kill()
        return f"Script '{script_key}' : timeout dépassé ({_proc_timeout_s}s)"
    except Exception as e:
        return f"Erreur exécution script '{script_key}' : {e}"
