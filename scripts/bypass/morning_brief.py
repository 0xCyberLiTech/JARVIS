"""Bypass briefing matinal Hermès — récapitulatif vocal quotidien.

Déclenché par :
  - "bonjour JARVIS", "bonjour", "salut JARVIS"
  - "briefing", "briefing du matin"
  - "rapport du matin / matinal"
  - "bilan du jour / du matin"
  - "quoi de neuf"
  - "donne-moi un bilan / point / résumé"

Fonctionne AVANT le gate is_vocal → vocal ET chat.

Scheduler automatique : start_scheduler() démarre un thread daemon qui
déclenche le brief à l'heure configurée dans jarvis_hermes.json :
  { "morning_brief_time": "08:30", "morning_brief_enabled": true }

Module pur — zéro import vers jarvis.py.
Les callables get_soc_fn / get_pve_fn / speak_fn sont injectés.
"""
import json
import re
import threading
import time

# ── Regex de détection ────────────────────────────────────────────────────────

BRIEF_RE = re.compile(
    r'\b(?:'
    r'briefing(?:\s+(?:du\s+)?matin)?'
    r'|rapport\s+(?:du\s+)?matin(?:al)?'
    r'|bilan\s+(?:du\s+)?(?:jour|matin)'
    r'|quoi\s+de\s+neuf'
    r'|(?:donne(?:r)?(?:[\s-]+moi)?|fais(?:[\s-]+moi)?)\s+(?:un\s+)?(?:bilan|point|r[eé]sum[eé])'
    r')\b',
    re.I | re.U,
)

# "bonjour" / "salut" seuls ou suivis de "JARVIS" = message court complet
GREET_RE = re.compile(
    r'^\s*(?:bonjour|salut|hey)\s*(?:jarvis)?\s*[!.,]?\s*$',
    re.I | re.U,
)

_JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MOIS  = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]


def detect_morning_brief(msg: str) -> bool:
    """True si le message est un déclencheur de briefing matinal."""
    stripped = msg.strip()
    return bool(BRIEF_RE.search(stripped)) or bool(GREET_RE.match(stripped))


# ── Construction du texte ─────────────────────────────────────────────────────

def _format_date() -> str:
    import datetime
    n = datetime.datetime.now()
    return f"{_JOURS[n.weekday()]} {n.day} {_MOIS[n.month - 1]} {n.year}"


def _build_text(get_soc_fn, get_pve_fn) -> tuple:
    """Retourne (texte_affichage_markdown, texte_tts_plain)."""
    date_str = _format_date()
    md  = [f"Bonjour Marc. Voici votre briefing du **{date_str}**.\n\n"]
    tts = [f"Bonjour Marc. Voici votre briefing du {date_str}. "]

    # ── SOC ───────────────────────────────────────────────────────────────────
    try:
        soc    = get_soc_fn() or {}
        level  = soc.get("threat_level", "INCONNU")
        bans   = soc.get("bans_24h",    0)
        alerts = soc.get("alerts_24h",  0)
        sb = "s" if bans   > 1 else ""
        sa = "s" if alerts > 1 else ""
        md.append(
            f"**SOC** : niveau **{level}**. "
            f"{bans} bannissement{sb} et {alerts} alerte{sa} sur 24h.\n"
        )
        tts.append(
            f"SOC : niveau {level}. "
            f"{bans} bannissement{sb} et {alerts} alerte{sa} sur les dernières 24 heures. "
        )
        if level.upper().replace("É", "E").replace("È", "E") in ("CRITIQUE", "ELEVE"):
            warn = f"Attention : niveau de menace {level}. Consultez le dashboard SOC. "
            md.append(f"⚠ **{warn}**\n")
            tts.append(warn)
    except Exception as e:
        md.append(f"SOC : données indisponibles ({e}).\n")
        tts.append("SOC : données indisponibles. ")

    # ── Proxmox VMs ───────────────────────────────────────────────────────────
    try:
        pve     = get_pve_fn() or {}
        vms     = pve.get("vms", [])
        running = [v for v in vms if v.get("status") == "running"]
        total   = len(vms)
        n_run   = len(running)
        names   = ", ".join(
            v.get("name", f"VM{v.get('vmid', '')}") for v in running
        )
        sv = "s" if total > 1 else ""
        sr = "s" if n_run > 1 else ""
        pve_md  = f"**Proxmox** : {n_run}/{total} machine{sv} active{sr}"
        pve_tts = f"Proxmox : {n_run} machine{sr} active{sr} sur {total}"
        if names:
            pve_md  += f" — {names}"
            pve_tts += f" : {names}"
        md.append(pve_md  + ".\n")
        tts.append(pve_tts + ". ")
    except Exception as e:
        md.append(f"Proxmox : données indisponibles ({e}).\n")
        tts.append("Proxmox : données indisponibles. ")

    md.append("\nBonne journée.")
    tts.append("Bonne journée.")

    return "".join(md), "".join(tts)


# ── Générateur SSE (bypass on-demand) ─────────────────────────────────────────

def morning_brief_sse(get_soc_fn, get_pve_fn):
    """Stream le briefing matinal — token affichage + event TTS."""
    try:
        text_md, text_tts = _build_text(get_soc_fn, get_pve_fn)
    except Exception as e:
        text_md = text_tts = f"Erreur lors du briefing : {e}"
    yield f"data: {json.dumps({'type': 'token', 'token': text_md, 'done': True})}\n\n"
    yield f"data: {json.dumps({'type': 'speak', 'text': text_tts})}\n\n"


# ── Scheduler automatique (cron job) ──────────────────────────────────────────

def _scheduler_loop(speak_fn, soc_fn, pve_fn, config_path: str) -> None:
    """Thread daemon : lit jarvis_hermes.json toutes les 30s.
    À l'heure configurée (morning_brief_time, ex. "08:30"), déclenche le brief
    une seule fois par jour via speak_fn(text)."""
    from pathlib import Path
    triggered_day = None
    while True:
        time.sleep(30)
        try:
            p = Path(config_path)
            if not p.exists():
                continue
            cfg = json.loads(p.read_text(encoding="utf-8"))
            if not cfg.get("morning_brief_enabled", False):
                continue
            brief_time = cfg.get("morning_brief_time", "")
            if not brief_time:
                continue
            parts = brief_time.split(":")
            if len(parts) != 2:
                continue
            h, m = int(parts[0]), int(parts[1])
            import datetime
            now   = datetime.datetime.now()
            today = now.date()
            if now.hour == h and now.minute == m and triggered_day != today:
                triggered_day = today
                _, tts_text = _build_text(soc_fn, pve_fn)
                speak_fn(tts_text)
        except Exception:
            pass  # scheduler silencieux — ne doit jamais crasher le thread


def start_scheduler(speak_fn, soc_fn, pve_fn, config_path: str) -> None:
    """Démarre le thread planificateur du briefing matinal (daemon).
    Appelé une seule fois au démarrage de JARVIS."""
    threading.Thread(
        target=_scheduler_loop,
        args=(speak_fn, soc_fn, pve_fn, config_path),
        daemon=True,
        name="hermes-morning-brief",
    ).start()
