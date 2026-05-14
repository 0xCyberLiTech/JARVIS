"""Bypass simples — détection regex + génération SSE pure (zéro IO).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 6a.

Contient les bypass LLM les plus légers : datetime (heure/jour/date).
Couplage zéro — pure regex + datetime stdlib.

Les bypass plus lourds (SSH/VM/backup/code) restent dans jarvis.py car couplés
à paramiko, subprocess, Proxmox API et constantes de timeout.
"""
import json
import re
from datetime import datetime

# ── Regex de détection ────────────────────────────────────────
DATETIME_RE = re.compile(
    r'\b(quel(?:le)?\s+heure|il\s+est\s+(?:quel(?:le)?\s+)?heure|quel\s+jour|quel(?:le)?\s+date|'
    r'on\s+est\s+(?:le\s+)?(?:combien|quel)|aujourd.hui\s+(?:on\s+est|c.?est)|'
    r'sommes.nous|c.?est\s+(?:quel|quelle?)\s+(?:jour|date|heure))\b',
    re.I | re.U,
)

_JOURS = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
_MOIS  = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
          'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']


def datetime_sse():
    """Génère un bypass SSE datetime (réponse instantanée, zéro LLM).

    Yields : 2 events SSE (token done + speak) au format `data: {json}\\n\\n`.
    """
    n = datetime.now()
    rep = f"Il est {n.hour:02d}h{n.minute:02d}. Nous sommes le {_JOURS[n.weekday()]} {n.day} {_MOIS[n.month-1]} {n.year}."
    yield f"data: {json.dumps({'type':'token','token':rep,'done':True})}\n\n"
    yield f"data: {json.dumps({'type':'speak','text':rep})}\n\n"
