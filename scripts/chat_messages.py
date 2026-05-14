"""Chat messages — assemblage history → liste messages Ollama (zéro IO).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 17 (Chat/LLM core).

Fonction pure : prend (system, history, is_vocal) → retourne list[{"role": str, "content": str}].
Aucun side effect, aucune dépendance externe.

Spécificité mode VOCAL : injecte un override system juste avant le dernier message user
pour forcer un style oral court (1-3 phrases, sans markdown, ton adapté au niveau de menace SOC).
"""


_VOCAL_OVERRIDE = (
    "INSTRUCTION PRIORITAIRE — MODE VOCAL JARVIS ACTIVÉ.\n"
    "Tu es JARVIS. Réponds en 1 à 3 phrases maximum, style oral direct, JAMAIS de markdown, JAMAIS de liste.\n"
    "Adapte ton ton au niveau de menace SOC si présent dans le contexte :\n"
    "  • Niveau CRITIQUE ou ÉLEVÉ → commence par 'Alerte,' ou 'Niveau [NIVEAU],' + chiffre clé + action concrète.\n"
    "  • Niveau FAIBLE ou MOYEN   → une phrase de statut calme, aucune alarme inutile.\n"
    "  • Aucun contexte SOC       → réponds naturellement à la question posée.\n"
    "Cite les chiffres exacts du contexte. Arrête-toi immédiatement après la recommandation — aucune répétition."
)


def build_messages(system: str, history: list, is_vocal: bool) -> list:
    """Construit la liste de messages Ollama avec override vocal si besoin.

    - Mode normal : `[{system}, ...history]`
    - Mode VOCAL avec history : `[{system}, ...history[:-1], {vocal_override}, history[-1]]`
      → l'override est injecté juste avant le dernier message user pour qu'il soit "frais"
        dans le contexte du LLM
    - Mode VOCAL sans history : `[{system + vocal_override}]`
    """
    if not is_vocal:
        return [{"role": "system", "content": system}] + history
    if history:
        return (
            [{"role": "system", "content": system}]
            + history[:-1]
            + [{"role": "system", "content": _VOCAL_OVERRIDE}]
            + [history[-1]]
        )
    return [{"role": "system", "content": system + "\n\n" + _VOCAL_OVERRIDE}]
