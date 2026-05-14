"""Chat system prompt — orchestre l'assemblage du system prompt complet.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 21 (Chat/LLM core).

Enchaîne 5 helpers d'injection :
1. Facts persistants (jarvis_facts.json)
2. RAG (statique + live SOC) si question longue ou keywords RAG match
3. Web search (si web_enabled)
4. SOC live (monitoring.json) si keywords SOC match
5. Proxmox API (si keywords PVE match)

Dependency injection complète : tous les helpers + constantes sont passés en kwargs
(les implémentations restent dans jarvis.py et les modules déjà extraits).
"""


def build(
    last_user: str,
    web_enabled: bool,
    soc_ctx_injected: bool,
    is_vocal: bool,
    *,
    system_prompt: str,
    facts_inject_fn,
    rag_relevant_re,
    rag_inject_fn,
    web_search_fn,
    soc_inject_fn,
    pve_inject_fn,
) -> tuple[str, bool]:
    """Construit le system prompt complet : faits + RAG + web + SOC/PVE live.

    Retourne (system_prompt_complet, soc_trigger).
    `soc_trigger` indique si le SOC a été déclenché (utilisé pour stats/log côté appelant).
    """
    system = facts_inject_fn(system_prompt)
    if len(last_user.strip()) >= 60 or rag_relevant_re.search(last_user):
        system = rag_inject_fn(system, last_user)
    if web_enabled and last_user:
        system += (
            "\n\nTu as accès à internet. Voici les résultats de recherche web "
            f"pour la question de l'utilisateur:\n{web_search_fn(last_user)}\n"
            "Utilise ces informations pour enrichir ta réponse si pertinent."
        )
    system, soc_trigger = soc_inject_fn(system, last_user, is_vocal, soc_ctx_injected)
    system = pve_inject_fn(system, last_user)
    return system, soc_trigger
