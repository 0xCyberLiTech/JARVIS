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


# ── Format compact defense_24h ────────────────────────────────

def _format_defense_block(d: dict) -> str:
    """Sérialise defense_24h.json en bloc texte compact (~400 chars) pour injection
    dans le system prompt phi4. Donne KPI + pic horaire + top 5 pays/AS/scénarios."""
    k = d.get("kpi", {}) or {}
    heat = d.get("heatmap_24h", []) or []
    peak_h, peak_v = (-1, 0)
    for i, v in enumerate(heat):
        if v > peak_v:
            peak_h, peak_v = i, v
    peak_lbl = f"h-{len(heat) - 1 - peak_h}" if peak_h >= 0 else "n/a"
    top = lambda lst, n=5: " ".join(  # noqa: E731 — formatage local court
        f"{(x.get('value') or '?')[:14]}({x.get('count', 0)})" for x in (lst or [])[:n]
    )
    return (
        f"[DÉFENSE 24H AGRÉGÉE — {d.get('generated_at', '?')}]\n"
        f"Actions totales: {k.get('total_actions', 0)} · "
        f"Bans CrowdSec: {k.get('bans_24h', 0)} · "
        f"WAF CLT: {k.get('waf_clt_24h', 0)} · WAF PA85: {k.get('waf_pa85_24h', 0)} · "
        f"Suricata: {k.get('ids_sev1', 0)} sev1/{k.get('ids_sev2', 0)} sev2 · "
        f"GeoBlock: {k.get('geo_24h', 0)} · F2B actifs: {k.get('fail2ban_active', 0)} · "
        f"UFW: {k.get('ufw_24h', 0)}\n"
        f"Pic horaire: {peak_lbl} ({peak_v} actions)\n"
        f"Top pays: {top(d.get('top_country'))}\n"
        f"Top AS: {top(d.get('top_as'))}\n"
        f"Top scénarios: {top(d.get('top_scenario'))}"
    )


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
    fetch_defense_fn=None,
) -> tuple[str, bool]:
    """Enrichit le prompt système avec les données SOC si la question l'exige.

    Retourne (system_prompt_modifié, soc_trigger_bool).

    `force_soc` : déclenche l'injection même sans mot-clé SOC — utilisé quand
    l'appelant cible explicitement le mode SOC (model_override='soc', ex. le
    chat du dashboard SOC où chaque message est une question SOC par nature).
    `fetch_monitoring_fn(force: bool) -> (ok, raw_json)` : récupère monitoring.json
    `build_monitoring_context_fn(data: dict) -> str` : formate pour injection LLM
    `fetch_defense_fn(force: bool) -> (ok, raw_json)` : optionnel — récupère
       defense_24h.json (résumé KPI + top + heatmap). Si fourni et SOC déclenché,
       ajoute un bloc compact `[DÉFENSE 24H AGRÉGÉE]` au system prompt.
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
        # Bloc compact agrégé 24h (chiffres pré-calculés — répond aux questions
        # « combien de bans ? quel est le pic horaire ? top pays ? » sans calcul)
        if fetch_defense_fn is not None:
            ok_d, raw_d = fetch_defense_fn(force=False)
            if ok_d and raw_d:
                try:
                    system += "\n\n" + _format_defense_block(json.loads(raw_d))
                except Exception:
                    pass  # bloc défense est optionnel — pas bloquant
    return system, soc_trigger
