"""Chat SOC inject — détection mots-clés SOC + injection contexte monitoring.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 22 (Chat/LLM core).

Détecte si la question utilisateur déclenche le besoin de contexte SOC live
(monitoring.json srv-ngix). Si oui, fetch + injecte dans le system prompt.

Listes de keywords distinctes :
- `SOC_KW` : mode chat texte (large)
- `SOC_VOCAL_KW` : mode VOCAL (resserré pour éviter faux positifs en conversation)

Marqueur `[NO_SOC]` dans le system prompt désactive l'injection (override profil).

Dependency injection : `fetch_monitoring_fn` et `build_monitoring_context_fn`
passées en arg (helpers SOC qui restent dans jarvis.py car couplés au cache).
"""
import json

# ── Keywords SOC ──────────────────────────────────────────────

SOC_KW = [
    # Outils sécurité
    "soc", "monitoring", "crowdsec", "fail2ban", "suricata", "ufw", "waf", "bouncer",
    # IPs / décisions
    "ip banni", "ips banni", "ip suspecte", "ip malveillante", "ip bloquée",
    "bannir", "débannir", "bloquer une ip", "débloquer",
    # Événements sécurité — termes suffisamment spécifiques
    "menace", "attaque",
    "alerte", "alert", "threat", "hacker", "incident", "intrusion",
    "ddos", "brute force", "bruteforce", "scan de port", "injection", "cve", "rce", "exploit",
    "comportement suspect",
    # Kill Chain
    "kill chain", "recon",
    # Métriques SOC — phrases composées (mots seuls trop génériques supprimés)
    "score menace", "score de menace", "niveau de menace", "niveau menace", "threat level",
    "sécurité réseau", "sécurité informatique", "sécurité du réseau",
    "trafic réseau", "trafic suspect", "trafic http", "trafic malveillant",
    "anomalie réseau", "anomalie détectée",
    "tentative de connexion", "tentatives de connexion", "tentative d'intrusion",
    "défense réseau", "défense cyber",
    # Phrases composées SOC
    "état du soc", "état soc", "status soc", "rapport soc", "journal sécurité",
    # Requêtes SOC implicites
    "analyse la situation", "analyse le soc", "analyse soc",
    "qui attaque", "sous attaque", "en cours d'attaque",
]

SOC_VOCAL_KW = [
    # Outils sécurité
    "soc", "crowdsec", "fail2ban", "suricata", "ufw", "waf",
    # IPs / décisions
    "banni", "bannir", "débannir", "bloquer", "ip suspecte", "ips",
    # Événements sécurité
    "menace", "attaque", "intrusion", "hacker", "blocage",
    "ddos", "brute force", "bruteforce",
    "cve", "exploit", "injection",
    # Kill Chain
    "kill chain", "reconnaissance",
    # Réseau / sécurité — phrases composées (mots seuls trop génériques supprimés)
    "pare-feu", "firewall",
    "état du réseau", "état réseau",
    "trafic réseau", "trafic suspect",
    "sécurité réseau", "sécurité informatique",
    # Métriques SOC — phrases composées
    "score menace", "score de menace", "niveau de menace", "niveau menace",
    # Phrases composées SOC
    "état soc", "état du soc", "monitoring", "journal sécurité", "rapport sécurité",
]


# ── API publique ──────────────────────────────────────────────

def inject(
    system: str,
    last_user: str,
    is_vocal: bool,
    soc_ctx_injected: bool,
    force_soc: bool = False,
    *,
    fetch_monitoring_fn,
    build_monitoring_context_fn,
) -> tuple[str, bool]:
    """Enrichit le prompt système avec les données SOC si la question l'exige.

    Retourne (system_prompt_modifié, soc_trigger_bool).

    `force_soc` : déclenche l'injection même sans mot-clé SOC — utilisé quand
    l'appelant cible explicitement le mode SOC (model_override='soc', ex. le
    chat du dashboard SOC où chaque message est une question SOC par nature).
    `fetch_monitoring_fn(force: bool) -> (ok, raw_json)` : récupère monitoring.json
    `build_monitoring_context_fn(data: dict) -> str` : formate pour injection LLM
    """
    kw_list = SOC_VOCAL_KW if is_vocal else SOC_KW
    soc_trigger = force_soc or any(kw in last_user.lower() for kw in kw_list)
    if "[NO_SOC]" in system:
        soc_trigger = False
    if last_user and soc_trigger and not soc_ctx_injected:
        ok, raw = fetch_monitoring_fn(force=True)
        if ok and raw:
            try:
                soc_ctx = build_monitoring_context_fn(json.loads(raw))
            except Exception as e:
                soc_ctx = f"Données brutes monitoring.json (parse partiel: {e}):\n{raw[:2000]}"
            system += (
                "\n\nVoici les données SOC actuelles de srv-ngix récupérées en temps réel :\n"
                + soc_ctx
                + "\n\nUtilise ces données pour répondre précisément à la question."
            )
        else:
            # srv-ngix injoignable : garde-fou anti-hallucination — le LLM ne
            # doit JAMAIS inventer un état SOC à partir de rien.
            system += (
                "\n\n[DONNÉES SOC INDISPONIBLES — srv-ngix non joignable au moment "
                "de la requête. INTERDICTION ABSOLUE d'analyser, estimer ou inventer "
                "un état SOC. Répondre uniquement : « Données temps réel SOC non "
                "disponibles — connexion srv-ngix requise. »]"
            )
    return system, soc_trigger
