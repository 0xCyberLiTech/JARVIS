"""Tool dispatch dict — résout `tool_name` → fonction Python à appeler.

Extrait de jarvis.py étape 34a (2026-05-23). Centralise la construction du
dict `_TOOL_DISPATCH` consommé par `chat/orchestrator.execute_tool()` quand
le LLM émet un tool_call : le dispatcher fait `_TOOL_DISPATCH[name](args)`.

Les 14 outils répartis dans 4 tuiles sont injectés en DI via
`build(**handlers)` qui renvoie le dict prêt à l'emploi. Le mapping reste
ainsi à un seul endroit (cette tuile `tools/`) au lieu d'être hardcodé
dans jarvis.py qui doit autrement référencer 14 callables hétérogènes.

Outils exposés (par catégorie) :
- files/ (6)  : lire_fichier, ecrire_fichier, modifier_fichier, lister_dossier,
                arborescence_projet, lire_plusieurs_fichiers
- tools/ (4)  : executer_code, rechercher_dans_fichiers, soc_status,
                executer_script_windows
- ssh/ (4)   : commande_ssh_nginx, commande_ssh_proxmox, commande_ssh_clt,
                commande_ssh_pa85

Convention : chaque handler reçoit un dict `args` (JSON décodé du tool_call).
`soc_status` ignore `args` (signature: `() -> str`) mais le lambda dispatch
appelle `handler(args)` uniformément pour ne pas dupliquer le mapping.
"""


def build(
    *,
    lire_fichier,
    ecrire_fichier,
    modifier_fichier,
    lister_dossier,
    arborescence_projet,
    lire_plusieurs_fichiers,
    executer_code,
    rechercher_dans_fichiers,
    soc_status,
    commande_ssh_nginx,
    commande_ssh_proxmox,
    commande_ssh_clt,
    commande_ssh_pa85,
    executer_script_windows,
) -> dict:
    """Construit le dict tool_name → handler, prêt pour le dispatcher chat.

    Renvoie un nouveau dict à chaque appel (pas de singleton global) :
    la DI reste explicite et testable, et le caller assume la durée de vie.
    `soc_status` est wrappé dans un lambda qui ignore `args` (sa signature
    réelle est sans argument)."""
    return {
        "lire_fichier":             lire_fichier,
        "ecrire_fichier":           ecrire_fichier,
        "modifier_fichier":         modifier_fichier,
        "lister_dossier":           lister_dossier,
        "arborescence_projet":      arborescence_projet,
        "lire_plusieurs_fichiers":  lire_plusieurs_fichiers,
        "executer_code":            executer_code,
        "rechercher_dans_fichiers": rechercher_dans_fichiers,
        "soc_status":               lambda args: soc_status(),
        "commande_ssh_nginx":        commande_ssh_nginx,
        "commande_ssh_proxmox":     commande_ssh_proxmox,
        "commande_ssh_clt":         commande_ssh_clt,
        "commande_ssh_pa85":        commande_ssh_pa85,
        "executer_script_windows":  executer_script_windows,
    }
