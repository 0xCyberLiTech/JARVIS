"""Facts inject — injection date/heure + faits persistants + résumés mémoire dans le system prompt.

Extrait de jarvis.py étape 34b (2026-05-23). Fonction `inject(system)` appelée
au début de `_chat_build_system_prompt` (chat/orchestrator) pour enrichir le
prompt LLM avec :

1. **Date/heure FR temps réel** (toujours injectée) — répond au pattern de
   l'utilisateur qui demande l'heure pendant qu'il chate avec JARVIS
2. **Faits persistants** depuis `jarvis_facts.json` (préférences, contexte
   projet immuable) — gérés via la tuile facts/ HTTP routes GET/POST
3. **Résumés des conversations passées** depuis `jarvis_memory_summary.json`
   (mémoire long terme, rotation 5 résumés max) — fourni par memory/store

DI via `init(facts_file, load_memory_summary_fn, log)` — les deps qui
vivent encore dans jarvis.py (FACTS_FILE Path + memory store loader + log).

Helpers exposés :
- `load_facts()` : charge la liste des faits depuis le fichier JSON
- `now_fr()`     : formatage date/heure FR (« lundi 23 mai 2026 — 14:30 »)
- `inject(s)`    : enrichit le system prompt avec les 3 additions ci-dessus
"""
import json
from datetime import datetime

# ── DI placeholders ───────────────────────────────────────────────────────────
# `_get_facts_file` est un callable () → Path : permet aux tests de monkeypatch
# `jm.FACTS_FILE` et de voir leur changement pris en compte (sinon on aurait
# une copie figée du Path au moment de init() — testabilité cassée).
_get_facts_file = None
_load_memory_summary = None
_log = None

# ── Constantes FR ─────────────────────────────────────────────────────────────
_MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
_JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def init(*, get_facts_file, load_memory_summary, log) -> None:
    """Injecte le getter du fichier facts + le loader de résumés mémoire + log."""
    global _get_facts_file, _load_memory_summary, _log
    _get_facts_file = get_facts_file
    _load_memory_summary = load_memory_summary
    _log = log


def load_facts() -> list:
    """Charge les faits persistants depuis jarvis_facts.json."""
    try:
        fp = _get_facts_file()
        if fp.exists():
            data = json.loads(fp.read_text(encoding="utf-8"))
            return data.get("facts", []) if isinstance(data, dict) else []
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING load_facts: {e}")
    return []


def now_fr() -> str:
    """Date/heure formatées en français (« lundi 23 mai 2026 — 14:30 »)."""
    n = datetime.now()
    return f"{_JOURS_FR[n.weekday()]} {n.day:02d} {_MOIS_FR[n.month-1]} {n.year} — {n.hour:02d}:{n.minute:02d}"


def inject(system: str) -> str:
    """Injecte date/heure, faits persistants et résumés de mémoire dans le system prompt."""
    additions = [f"[SYSTÈME] Date et heure actuelles : {now_fr()}. Tu disposes de cette information en temps réel — réponds directement sans dire que tu n'y as pas accès."]
    facts = load_facts()
    if facts:
        additions.append("[MÉMOIRE PERSISTANTE — faits toujours vrais, priorité absolue]\n" + "\n".join(f"• {f}" for f in facts))
    summary = _load_memory_summary()
    if summary:
        additions.append("[RÉSUMÉS DE CONVERSATIONS PASSÉES — contexte long terme]\n" + summary)
    return system + "\n\n" + "\n\n".join(additions)
