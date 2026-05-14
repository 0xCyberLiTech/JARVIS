"""Chat routing — sélection du modèle Ollama selon mode + flags requête (zéro IO).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 15 (premier sous-module Chat/LLM core).

Fonction pure : prend le mode actif + flags + override → retourne (model, route_label).
Aucun side effect, aucun appel réseau, aucun état partagé.

Dependency injection : `general_model`, `code_model`, `current_mode` passés en argument
(les valeurs réelles sont dans jarvis.py).

Voir aussi : `docs/ROUTING-JARVIS.md` pour la stratégie de routing complète (4 modes + bypass).
"""


def resolve_model(
    is_vocal: bool,
    no_tools: bool,
    model_override: str | None,
    general_model: str,
    code_model: str,
    current_mode: str,
) -> tuple[str | None, str]:
    """Retourne (active_model, route_label) selon le mode actif et les flags de la requête.

    Logique de routing :
    - `model_override='soc'`     → None (utilise MODEL défaut phi4:14b — dashboard SOC force le routing)
    - `model_override='general'` → general_model (override externe explicite)
    - `no_tools=True`            → code_model (terminal CODE direct)
    - `current_mode='code'`      → code_model (mode CODE manuel)
    - `is_vocal` ou mode='general' → general_model (conversation/VOCAL)
    - Sinon                      → None (MODEL défaut phi4:14b SOC)

    Retour route_label : "SOC" / "GENERAL" / "CODE" / "CODE-TERM" / "VOCAL"
    """
    if model_override == "soc":
        return None, "SOC"  # phi4:14b — dashboard SOC force le bon modèle
    if model_override == "general":
        return general_model, "GENERAL"
    if no_tools:
        return code_model, "CODE-TERM"
    if current_mode == "code":
        return code_model, "CODE"
    if is_vocal or current_mode == "general":
        return general_model, "VOCAL" if is_vocal else "GENERAL"
    return None, "SOC"  # None = MODEL par défaut (phi4:14b)
