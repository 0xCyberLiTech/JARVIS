"""Formatage du contexte SOC pour injection LLM (phi4 mode SOC).

Sous-module chat (refactor jarvis.py étape 26, 2026-05-23). Construit le
texte injecté dans le system prompt phi4 quand un mot-clé SOC est détecté,
à partir du dict monitoring.json parsé.

Composants :
- `_INFRA_IPS`              : liste descriptive des IPs internes (jamais à bannir)
- `_KC_BAN_SIGNAL_MIN_HITS` : seuil au-delà duquel un SCAN/RECON devient FORT
- `kc_ban_signal(ip_e)`     : force du signal pour reco de ban (FORT/faible)
- `pve_context_lines(pve)`  : formatage Proxmox VE pour le contexte
- `build_monitoring_context(d)` : construit tout le texte SOC à injecter
  → Filtre les IPs protégées (LAN + DNS publics + WAN Freebox) depuis
    `active_ips` AVANT envoi à phi4 via `security_whitelists.is_protected_ip()`
    (source unique, ajout 2026-05-25 — comble le trou identifié par l'audit
    Marc : phi4 voyait `192.168.1.110` et `192.168.1.50` dans les top_ips
    et les classait à tort comme menaces).

Dépendance : `init(net_spike_window_s)` — seuil temporel pics réseau récents.
"""
import time

from security_whitelists import is_protected_ip  # source unique whitelist IPs

_KC_BAN_SIGNAL_MIN_HITS = 10

# Listing descriptif (rôles par IP) — utilisé dans le bloc INFRASTRUCTURE SOC
# affiché à phi4 pour qu'il identifie chaque IP interne par son rôle dans ses
# analyses. Doit rester synchronisé avec `INTERNAL_IPS` dans
# `security_whitelists.py` (source maître). Toute évolution = MAJ ici + grep.
_INFRA_IPS = (
    ("192.168.1.20",  "Proxmox VE — hyperviseur"),
    ("192.168.1.50",  "srv-nginx — hôte du SOC lui-même (nginx + CrowdSec + monitoring_gen)"),
    ("192.168.1.12",  "clt — VM Apache site CLT"),
    ("192.168.1.13",  "pa85 — VM Apache site PA85"),
    ("192.168.1.21",  "srv-dev-1 — VM Debian dev/test"),
    ("192.168.1.110", "WAN routeur ASUS — NAT sortant du LAN ASUS (poste Windows/JARVIS)"),
    ("192.168.1.254", "Freebox — gateway LAN"),
    ("192.168.50.1",  "Routeur ASUS ROG BE-19000 AI — gateway LAN ASUS"),
    ("192.168.50.90", "Windows/JARVIS — poste Marc (IP fixe LAN ASUS)"),
)

_net_spike_window_s = 3600


def init(*, net_spike_window_s: int) -> None:
    global _net_spike_window_s
    _net_spike_window_s = net_spike_window_s


def kc_ban_signal(ip_e: dict) -> str:
    """Force du signal d'une IP Kill Chain pour une reco de ban — même logique
    que les seuils de l'auto-engine : EXPLOIT ou UA usurpé sont bannissables
    même sur 1 hit, le reste seulement si l'activité est soutenue."""
    if ip_e.get("stage") == "EXPLOIT" or ip_e.get("spoofed_bot"):
        return "FORT"
    if (ip_e.get("count") or 0) >= _KC_BAN_SIGNAL_MIN_HITS:
        return "FORT"
    return "faible"


def pve_context_lines(pve: dict) -> list:
    """Formate les lignes Proxmox pour le contexte monitoring."""
    if not (pve.get("configured") and not pve.get("error")):
        return []
    lines = [f"Proxmox VE     : {pve.get('vms_running',0)}/{pve.get('vms_total',0)} VMs running"]
    for node in pve.get("nodes", []):
        for vm in node.get("vms", []):
            cpu  = round((vm.get("cpu") or 0) * 100, 1)
            maxm = vm.get("maxmem") or 0
            mem  = vm.get("mem") or 0
            ramp = round(mem / maxm * 100, 1) if maxm else 0
            lines.append(f"  VM {vm.get('vmid','')} {vm.get('name',''):12s}: {vm.get('status','?'):8s} CPU={cpu}% RAM={ramp}%")
    return lines


def build_monitoring_context(d: dict, header: str = "=== DONNÉES SOC EN TEMPS RÉEL (srv-nginx) ===") -> str:
    """Construit le contexte textuel SOC depuis un dict monitoring.json parsé."""
    cs   = d.get("crowdsec", {})
    f2b  = d.get("fail2ban", {})
    sys_ = d.get("system", {})
    mem  = sys_.get("memory", {})
    load = sys_.get("load", {})
    disk = sys_.get("disk", {})
    svc  = d.get("services", {})
    traf = d.get("traffic", {})
    kc   = d.get("kill_chain", {})
    cs_bans  = cs.get("active_decisions", 0)
    f2b_bans = f2b.get("total_banned", 0)
    err_rate = traf.get("error_rate", 0)
    req_24h  = traf.get("total_requests", 0)
    score  = d.get("threat_score", 0)
    threat = d.get("threat_level", "FAIBLE")
    generated_at = d.get('generated_at', '?')
    lines = [
        header,
        f"Généré le      : {generated_at}",
        f"SCORE OFFICIEL : {threat} ({score}/100) au snapshot {generated_at} — valeur LIVE recalculée chaque minute par monitoring_gen.py, source de vérité unique. NE PAS recalculer. Cite TOUJOURS cet horodatage avec le score.",
        f"CrowdSec       : {cs_bans} IP(s) bannies actives | alertes 24h : {cs.get('alerts_24h','?')}",
        f"Fail2ban       : {f2b_bans} IP(s) bannies actives",
        f"RAM            : {mem.get('pct','?')}% ({mem.get('used_mb','?')} Mo / {mem.get('total_mb','?')} Mo)",
        f"Load CPU       : {load.get('1m','?')} (1m) / {load.get('5m','?')} (5m) / {load.get('15m','?')} (15m)",
        f"Disque /var/www: {disk.get('pct','?')}% utilisé",
        f"Requêtes 24h   : {req_24h}",
        f"Erreurs 5xx    : {traf.get('status_5xx','?')} ({err_rate}% taux d'erreur)",
    ]
    for s, v in svc.items():
        status = v if isinstance(v, str) else ("UP" if v else "DOWN")
        lines.append(f"Service {s:12s}: {status}")
    cs_banned = cs.get("decisions_detail", {})
    if cs_banned:
        _neut_stage = {e.get("ip"): e.get("origin_stage")
                       for e in kc.get("neutralized_ips", []) if e.get("ip")}
        shown = sorted(cs_banned.items())[:100]
        lines.append("")
        lines.append(f"IPs DÉJÀ BANNIES par CrowdSec ({len(cs_banned)} au total — déjà neutralisées, NE PAS recommander de les bannir, NE PAS proposer cscli decisions add pour ces IPs) :")
        lines.append("  (champ « maillon-KC » = stade offensif classé par le backend — UTILISE-le tel quel pour situer l'IP dans la Kill Chain · NE déduis JAMAIS le maillon depuis le nom du scénario · 1 IP = 1 seul maillon)")
        for ip, meta in shown:
            lines.append(f"  {ip} — scénario={meta.get('scenario','?')} | maillon-KC={_neut_stage.get(ip) or '?'}")
        if len(cs_banned) > len(shown):
            lines.append(f"  … et {len(cs_banned) - len(shown)} autre(s) IP(s) déjà bannie(s) non listée(s) — TOUTE IP non listée ci-dessus PEUT être déjà bannie, vérifier le total ({len(cs_banned)}) avant d'en recommander une.")
    # Filtre source unique 2026-05-25 (Marc audit whitelist) — exclut les IPs
    # internes LAN + externes protégées (DNS publics, WAN Freebox) AVANT envoi
    # à phi4. Comble le trou identifié : `active_ips` pouvait contenir des IPs
    # internes via certains chemins de collecte SOC, phi4 les classait à tort
    # comme menaces. La whitelist est consultée via `is_protected_ip()` (source
    # unique dans `security_whitelists.py`).
    active_ips_raw = kc.get("active_ips", [])
    active_ips = [ip_e for ip_e in active_ips_raw if not is_protected_ip(ip_e.get("ip", ""))]
    filtered_internal = len(active_ips_raw) - len(active_ips)
    if active_ips:
        exploit_unblocked = sum(1 for ip in active_ips if ip.get("stage") == "EXPLOIT" and not ip.get("cs_decision"))
        exploit_total     = sum(1 for ip in active_ips if ip.get("stage") == "EXPLOIT")
        filtered_note = f" | {filtered_internal} IP(s) interne(s) filtrée(s)" if filtered_internal > 0 else ""
        lines.append(f"IPs actives (Kill Chain) : {len(active_ips)} | EXPLOIT total: {exploit_total} | EXPLOIT non bloquées: {exploit_unblocked}{filtered_note}")
        for ip_e in active_ips[:10]:
            cs_status = "BLOQUÉE-CS" if ip_e.get("cs_decision") else "⚠ NON-BLOQUÉE"
            spoof = f" ⚠UA-USURPÉ:{ip_e['spoofed_bot']}" if ip_e.get("spoofed_bot") else ""
            signal = kc_ban_signal(ip_e)
            lines.append(f"  {ip_e.get('ip','?')} [{ip_e.get('country','-')}] stage={ip_e.get('stage','?')} hits={ip_e.get('count','?')} [{cs_status}] signal={signal}{spoof}")
    verified_bots = kc.get("verified_bots", [])
    if verified_bots:
        names = ", ".join(f"{b.get('ip','?')} ({b.get('bot','?')})" for b in verified_bots[:10])
        lines.append(f"Crawlers légitimes vérifiés FCrDNS ({len(verified_bots)}) — EXCLUS de la Kill Chain, NE JAMAIS recommander de les bannir : {names}")
    net_spikes = d.get("net_spikes", [])
    if net_spikes:
        recent = [s for s in net_spikes if time.time() - s.get("ts", 0) < _net_spike_window_s]
        if recent:
            last_s = recent[-1]
            lines.append(f"Pic réseau récent (<1h) : TX={last_s.get('tx_mbps',0)} Mbps / RX={last_s.get('rx_mbps',0)} Mbps (baseline TX:{last_s.get('avg_tx_mbps',0)} / RX:{last_s.get('avg_rx_mbps',0)} Mbps)")
        lines.append(f"Pics réseau (7j) : {len(net_spikes)} détectés")
    lines.extend(pve_context_lines(d.get("proxmox", {})))
    slow = d.get("slow_campaigns", [])
    if slow:
        top = slow[0]
        lines.append(f"Campagnes lentes /24 (14j) : {len(slow)} subnet(s) | top {top['subnet']} — {top['count']} IPs distinctes ({top['last_seen'][:10]})")
    lines.append("")
    lines.append("=== INFRASTRUCTURE SOC — JAMAIS source d'attaque, JAMAIS à bannir ===")
    lines.append("Les IPs suivantes appartiennent à l'infrastructure du SOC lui-même. Elles ne sont JAMAIS sources d'attaques externes, JAMAIS suspectes, JAMAIS bannissables. Si tu vois un événement avec une de ces IPs, c'est de l'activité interne légitime (SSH d'administration, scripts cron, surveillance, déploiement) — JAMAIS une menace.")
    for ip, role in _INFRA_IPS:
        lines.append(f"  {ip:14s} — {role}")
    lines.append("Plage RFC1918 globale (10.x, 172.16-31.x, 192.168.x, 127.x) : INTERDICTION ABSOLUE de proposer un ban — toute commande 'cscli decisions add' / 'fail2ban-client banip' sur ces plages est refusée 403 par le backend.")
    lines.append("")
    lines.append("⚠ RÈGLE ABSOLUE — FIDÉLITÉ SOC : utilise UNIQUEMENT les IPs, scores, niveaux et services listés ci-dessus. Interdiction formelle d'inventer ou d'extrapoler toute donnée absente de ce contexte. Si une information est manquante, indiquer 'non disponible'. NE JAMAIS attribuer une activité suspecte à une IP d'infrastructure SOC (ci-dessus) ou RFC1918 — toute IP listée ci-dessus comme infra n'est PAS une source d'attaque.")
    cs_total = len(cs_banned) if cs_banned else 0
    lines.append("🚨 RÈGLE ANTI-DOUBLE-BAN (PROCÉDURE OBLIGATOIRE) : AVANT toute recommandation 'cscli decisions add' / 'fail2ban-client set … banip' / 'il est recommandé de bannir' / 'considérer un ban', tu DOIS exécuter cette procédure et l'INCLURE textuellement dans ta réponse :")
    lines.append("  ÉTAPE 1 (obligatoire, à écrire dans la réponse) : 'Vérification ban CrowdSec pour <IP> : scan de la section IPs DÉJÀ BANNIES…'")
    lines.append("  ÉTAPE 2 : Cherche <IP> dans la section ci-dessus. Réponds explicitement :")
    lines.append("    - SI trouvée → 'TROUVÉE — déjà bannie par scénario X (stage Y). Aucune action requise.' STOP, ne recommande PAS de ban.")
    lines.append(f"    - SI ABSENTE et liste complète (pas de mention 'et N autres') → 'ABSENTE de la liste complète ({cs_total} IPs scannées). Ban justifié si menace critique.'")
    lines.append("    - SI ABSENTE mais liste tronquée ('et N autres') → 'NON TROUVÉE dans les 100 premières mais N autres non listées. Vérifier d'abord : cscli decisions list -i <IP>.'")
    lines.append("  ÉTAPE 3 : seulement après ÉTAPE 2 réponse 'ABSENTE liste complète', tu peux recommander un ban.")
    lines.append("  ⚠ Toute recommandation de ban SANS cette procédure visible dans ta réponse est une HALLUCINATION — phi4 tend à ignorer les listes longues, cette procédure force la vérification mécanique.")
    return "\n".join(lines)
