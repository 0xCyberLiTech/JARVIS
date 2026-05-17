"""
JARVIS MCP Server — pont Claude Code ↔ JARVIS local (localhost:5000)
Transport : Streamable HTTP (/mcp) + SSE legacy (/sse) — port 5010

12 outils exposés :
  jarvis_chat          — conversation avec JARVIS (phi4:14b via Ollama)
  jarvis_soc_status    — état SOC temps réel (menace, bans, services)
  jarvis_soc_ask       — question SOC avec contexte live injecté (monitoring.json)
  jarvis_stats         — statistiques JARVIS (uptime, sessions, TTS, STT)
  jarvis_infra_status  — état des 4 hôtes SSH (proxmox/ngix/clt/pa85)
  jarvis_proxmox_vms   — liste et état des VMs Proxmox
  jarvis_read_file     — lit un fichier distant sur une VM via JARVIS
  jarvis_model_switch  — change le modèle Ollama actif
  jarvis_last_response — retourne la dernière réponse JARVIS (IPs sanitizées)
  jarvis_code_exec     — écrit + SCP + exécute du code sur srv-dev-1
  jarvis_defense_24h   — défense 24h KPI (heatmap, top attacks, timeline)
  jarvis_ioc_status    — IoC POST-COMPROMISSION (Sprint 18d : 6 signaux)
"""

import argparse
import contextlib
import json
import re

import httpx
import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

_RE_IPV4 = re.compile(r'\b(\d{1,3}(?:\.\d{1,3}){3})\b')
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool

JARVIS_BASE  = "http://127.0.0.1:5000"  # IPv4 explicite — `localhost` résout `::1` en premier sur Windows et fallback timeout ~2s avant IPv4
TIMEOUT_CHAT = 120.0   # génération LLM
TIMEOUT_FAST = 10.0    # endpoints status/stats/health

JARVIS_HEADER = (
    "\n"
    "╔══════════════════════════════════╗\n"
    "║  ◈  JARVIS  —  phi4:14b  ◈  ║\n"
    "╚══════════════════════════════════╝\n"
)

app = Server("jarvis")


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _collect_sse_tokens(url: str, payload: dict) -> str:
    """Appelle un endpoint SSE JARVIS et accumule les tokens.
    Gère les types : token, ssh_file (retourne le contenu brut)."""
    tokens = []
    ssh_file_content = None
    async with httpx.AsyncClient(timeout=TIMEOUT_CHAT) as client:
        async with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[5:].strip()
                if not raw:
                    continue
                try:
                    ev = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if ev.get("type") == "token":
                    tokens.append(ev.get("token", ""))
                elif ev.get("type") == "ssh_file":
                    vm      = ev.get("vm", "?")
                    path    = ev.get("path", "?")
                    content = ev.get("content", "")
                    lines   = content.splitlines()
                    ssh_file_content = (
                        f"[SSH FILE] {vm.upper()} → {path} ({len(lines)} lignes)\n"
                        + "─" * 60 + "\n"
                        + content
                    )
    if ssh_file_content:
        return ssh_file_content
    return "".join(tokens).strip()


async def _get_ip_history(ip: str) -> str:
    """Historique CrowdSec + fail2ban pour une IP via /api/soc/ip-deep.
    Injecté dans jarvis_soc_ask quand la question mentionne une IPv4."""
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(f"{JARVIS_BASE}/api/soc/ip-history", json={"ip": ip})
            if resp.status_code != 200:
                return ""
            data = resp.json()
            cs  = data.get("crowdsec", {})
            f2b = data.get("fail2ban", {})
            alerts_30d = cs.get("alerts_30d", 0)
            f2b_total  = f2b.get("total_records", 0)
            if alerts_30d == 0 and f2b_total == 0:
                return ""
            lines = [f"[HISTORIQUE IP {ip} — 30 jours]"]
            lines.append(f"CrowdSec : {alerts_30d} alertes historiques | actif maintenant : {cs.get('count',0)}")
            for a in cs.get("alerts_detail", [])[-5:]:
                lines.append(f"  {a.get('ts','')[:16]} {a.get('scenario','')}")
            if f2b_total:
                active_f2b = f2b.get("active", [])
                lines.append(f"Fail2ban : {f2b_total} ban(s) historiques | actifs : {len(active_f2b)}")
            return "\n".join(lines)
    except Exception:
        return ""  # JARVIS injoignable ou réponse malformée → contexte IP vide, pas bloquant


async def _get_soc_context_live() -> str:
    """Récupère le contexte SOC complet depuis /api/soc/context (monitoring.json parsé)."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_FAST) as client:
            resp = await client.get(f"{JARVIS_BASE}/api/soc/context")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("ok"):
                    return data.get("context", "")
    except Exception:
        pass  # /api/soc/context injoignable → fallback /api/status ci-dessous
    # Fallback : status basique
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_FAST) as client:
            resp = await client.get(f"{JARVIS_BASE}/api/status")
            if resp.status_code == 200:
                d = resp.json()
                return (
                    f"[CONTEXTE SOC — données partielles]\n"
                    f"Bans 24h: {d.get('bans_24h','?')} | Alertes 24h: {d.get('alerts_24h','?')} | "
                    f"Auto-engine: {'actif' if d.get('soc_engine_active') else 'inactif'}\n"
                )
    except Exception:
        pass  # /api/status injoignable aussi → JARVIS complètement hors ligne, retourne ""
    return ""


# ── Définitions d'outils (module level) ──────────────────────────────────────

_TOOLS_DEFS: list[Tool] = [
    Tool(name="jarvis_chat",
         description=("Envoie un message à JARVIS (IA locale phi4-reasoning via Ollama) "
                      "et retourne sa réponse complète. Utilise pour des questions générales, "
                      "analyses, code, cybersécurité, ou tout sujet où l'avis de JARVIS est utile."),
         inputSchema={"type": "object",
                      "properties": {"message": {"type": "string", "description": "Message à envoyer à JARVIS"}},
                      "required": ["message"]}),
    Tool(name="jarvis_soc_status",
         description=("Retourne l'état SOC temps réel : niveau de menace, IPs bannies CrowdSec/fail2ban, "
                      "services actifs, auto-engine JARVIS. Utilise quand l'utilisateur pose des questions "
                      "sur la sécurité du serveur srv-ngix."),
         inputSchema={"type": "object", "properties": {}}),
    Tool(name="jarvis_soc_ask",
         description=("Pose une question SOC à JARVIS avec injection automatique du contexte live "
                      "(monitoring.json complet : Kill Chain, IPs, scores, services). "
                      "Idéal pour : analyser une attaque, interpréter des alertes, décider d'un ban, "
                      "comprendre un incident réseau. Données SOC réelles, pas de RAG statique."),
         inputSchema={"type": "object",
                      "properties": {"question": {"type": "string", "description": "Question SOC/sécurité pour JARVIS"}},
                      "required": ["question"]}),
    Tool(name="jarvis_stats",
         description=("Retourne les statistiques JARVIS : uptime, sessions de chat, "
                      "appels TTS/STT, modèle actif, état RAG."),
         inputSchema={"type": "object", "properties": {}}),
    Tool(name="jarvis_infra_status",
         description=("Demande à JARVIS un état rapide de toute l'infrastructure : Proxmox VMs, "
                      "srv-ngix (nginx/CrowdSec), clt (Apache), pa85 (Apache). "
                      "Utilise quand l'utilisateur veut un aperçu général de la santé du homelab."),
         inputSchema={"type": "object",
                      "properties": {"focus": {"type": "string",
                                               "description": "Hôte spécifique (optionnel) : 'proxmox', 'ngix', 'clt', 'pa85', ou vide pour tout"}},
                      "required": []}),
    Tool(name="jarvis_proxmox_vms",
         description=("Liste les VMs Proxmox avec leur état (running/stopped), RAM, CPU, uptime. "
                      "Utilise pour savoir quelles VMs tournent, lesquelles sont arrêtées, "
                      "ou obtenir un résumé de l'état du cluster Proxmox."),
         inputSchema={"type": "object", "properties": {}}),
    Tool(name="jarvis_read_file",
         description=("Lit le contenu d'un fichier distant sur une VM via SSH (JARVIS). "
                      "Utilise pendant une session de code pour lire nginx.conf, jail.conf, "
                      "un script, un log, etc. sans quitter VSCode."),
         inputSchema={"type": "object",
                      "properties": {"vm":   {"type": "string", "description": "VM cible : 'ngix', 'clt', 'pa85', 'proxmox', 'srv-dev-1'"},
                                     "path": {"type": "string", "description": "Chemin absolu du fichier sur la VM (ex: /etc/nginx/nginx.conf)"}},
                      "required": ["vm", "path"]}),
    Tool(name="jarvis_model_switch",
         description=("Change le modèle Ollama actif dans JARVIS. "
                      "Modèles installés : phi4:14b (SOC), qwen2.5-coder:14b (CODE), gemma4:latest (GÉNÉRAL)."),
         inputSchema={"type": "object",
                      "properties": {"model": {"type": "string", "description": "Nom exact du modèle Ollama à activer"}},
                      "required": ["model"]}),
    Tool(name="jarvis_last_response",
         description=("Retourne le ou les derniers échanges de la conversation JARVIS "
                      "(message utilisateur + réponse complète). "
                      "Utilise pour vérifier ce que JARVIS vient de répondre sans voir l'interface."),
         inputSchema={"type": "object",
                      "properties": {"n": {"type": "integer", "description": "Nombre d'échanges à retourner (1-5, défaut 1)"}}}),
    Tool(name="jarvis_code_exec",
         description=("Écrit un fichier sur le serveur JARVIS, le transfère sur srv-dev-1 "
                      "via SCP et l'exécute. Retourne la sortie d'exécution. "
                      "Extensions supportées : .py .sh .js .ts .html .css .json .yml .rb .go .php .sql — uniquement srv-dev-1 (192.168.1.21)."),
         inputSchema={"type": "object",
                      "properties": {
                          "filename": {"type": "string", "description": "Nom du fichier à créer (ex: script.py, test.sh)"},
                          "code":     {"type": "string", "description": "Contenu complet du fichier à écrire et exécuter"}},
                      "required": ["filename", "code"]}),
    Tool(name="jarvis_defense_24h",
         description=("Résumé compact des actions défensives 24h sur srv-ngix : KPI agrégés "
                      "(bans CrowdSec, blocks WAF CLT/PA85, alertes Suricata sev1/sev2, GeoBlock, "
                      "fail2ban actifs, UFW), heatmap horaire 24h, top pays/AS/scénarios, timeline "
                      "rétrochrono des derniers événements. Source pré-calculée par "
                      "defense_aggregator.py (cron 60s). 13× plus compact que monitoring.json — "
                      "à privilégier pour 'combien de bans ?', 'quel pays attaque le plus ?', "
                      "'quelle heure de pointe ?' sans avoir à parser le brut."),
         inputSchema={"type": "object", "properties": {}}),
    Tool(name="jarvis_ioc_status",
         description=("Score IoC POST-COMPROMISSION (0-100) + 6 signaux : AIDE drift (modifs "
                      "fichiers système), C2 alerts (Suricata ET-TROJAN/MALWARE/CNC), SSH anomaly "
                      "(connexions hors heures), webshells (POST PHP suspects nginx), AppArmor "
                      "denials (tentatives escalade), sudo events. Détecte si un attaquant est "
                      "DÉJÀ ENTRÉ dans le SOC homelab — vs détecter les tentatives. Niveau "
                      "OK / WARN / CRIT. Source pré-calculée par ioc_collect.py sur srv-ngix "
                      "(cron 60s). À utiliser pour 'quel est le score IoC ?', 'y a-t-il une "
                      "compromission ?', 'JARVIS surveille quoi en post-compro ?'."),
         inputSchema={"type": "object", "properties": {}}),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return _TOOLS_DEFS


# ── Handlers d'outils ─────────────────────────────────────────────────────────

async def _handle_jarvis_chat(a: dict) -> list[TextContent]:
    payload = {"history": [{"role": "user", "content": a.get("message", "")}],
               "web_search": False, "soc_ctx_injected": False}
    r = await _collect_sse_tokens(f"{JARVIS_BASE}/api/chat", payload)
    return [TextContent(type="text", text=JARVIS_HEADER + (r or "[JARVIS] Pas de réponse (timeout ou serveur indisponible)"))]


async def _handle_jarvis_soc_status(a: dict) -> list[TextContent]:
    async with httpx.AsyncClient(timeout=TIMEOUT_FAST) as client:
        resp = await client.get(f"{JARVIS_BASE}/api/status")
        resp.raise_for_status()
        d = resp.json()
    text = (f"JARVIS SOC Status\n"
            f"  Modèle actif    : {d.get('model', '?')}\n"
            f"  Auto-engine SOC : {'actif' if d.get('soc_engine_active') else 'inactif'}\n"
            f"  Bans 24h        : {d.get('bans_24h', '?')}\n"
            f"  Alertes 24h     : {d.get('alerts_24h', '?')}\n")
    return [TextContent(type="text", text=JARVIS_HEADER + text)]


async def _handle_jarvis_soc_ask(a: dict) -> list[TextContent]:
    question   = a.get("question", "")
    soc_ctx    = await _get_soc_context_live()
    ip_match   = _RE_IPV4.search(question)
    ip_history = await _get_ip_history(ip_match.group(1)) if ip_match else ""
    ctx_prefix = (soc_ctx + "\n\n" if soc_ctx else "") + (ip_history + "\n\n" if ip_history else "")
    wrapped = (
        f"{ctx_prefix}{question}\n\n"
        "CONSIGNE DE RÉPONSE OBLIGATOIRE — RESPECTER STRICTEMENT :\n"
        "1. Commence par le niveau de menace EXACT issu du SCORE OFFICIEL fourni dans le contexte "
        "(FAIBLE <30 / MOYEN 30-49 / ÉLEVÉ 50-69 / CRITIQUE ≥70). Ne jamais déduire un niveau différent.\n"
        "2. Maximum 5 points. Pas plus.\n"
        "3. INTERDIT ABSOLU de citer une adresse IP — utilise le pays + stage Kill Chain "
        "(ex: 'CN EXPLOIT', 'RU BRUTE'). Si pays inconnu, écris 'origine inconnue'.\n"
        "4. Termine par une recommandation concrète si ÉLEVÉ ou CRITIQUE, "
        "sinon 'Surveillance normale.' — pas les deux."
    )
    payload = {"history": [{"role": "user", "content": wrapped}],
               "web_search": False, "soc_ctx_injected": bool(soc_ctx)}
    r = await _collect_sse_tokens(f"{JARVIS_BASE}/api/chat", payload)
    return [TextContent(type="text", text=JARVIS_HEADER + (r or "[JARVIS] Pas de réponse (timeout ou serveur indisponible)"))]


async def _handle_jarvis_stats(a: dict) -> list[TextContent]:
    async with httpx.AsyncClient(timeout=TIMEOUT_FAST) as client:
        resp = await client.get(f"{JARVIS_BASE}/api/stats")
        resp.raise_for_status()
        data = resp.json()
    return [TextContent(type="text", text=JARVIS_HEADER + json.dumps(data, indent=2, ensure_ascii=False))]


async def _handle_jarvis_infra_status(a: dict) -> list[TextContent]:
    focus = a.get("focus", "").strip().lower()
    question = (f"Vérifie l'état de {focus} et donne-moi un résumé concis (services, ressources, erreurs récentes)."
                if focus else
                "Vérifie l'état général de l'infrastructure : "
                "Proxmox VE (VMs actives, stockage), srv-ngix (nginx, CrowdSec, fail2ban), "
                "clt (Apache, site CLT), pa85 (Apache, site PA85). "
                "Résumé en 5 points max — signale uniquement ce qui est anormal.")
    payload = {"history": [{"role": "user", "content": question}],
               "web_search": False, "soc_ctx_injected": False}
    r = await _collect_sse_tokens(f"{JARVIS_BASE}/api/chat", payload)
    return [TextContent(type="text", text=JARVIS_HEADER + (r or "[JARVIS] Pas de réponse (timeout ou serveur indisponible)"))]


async def _handle_jarvis_proxmox_vms(a: dict) -> list[TextContent]:
    question = ("Liste toutes les VMs Proxmox avec leur état exact (running/stopped), "
                "VMID, RAM allouée, CPU, et uptime si disponible. "
                "Format tableau : VMID | NOM | ÉTAT | RAM | CPU | UPTIME. "
                "Pas d'analyse, juste les faits bruts.")
    payload = {"history": [{"role": "user", "content": question}],
               "web_search": False, "soc_ctx_injected": False}
    r = await _collect_sse_tokens(f"{JARVIS_BASE}/api/chat", payload)
    return [TextContent(type="text", text=JARVIS_HEADER + (r or "[JARVIS] Pas de réponse (timeout ou Proxmox injoignable)"))]


async def _handle_jarvis_read_file(a: dict) -> list[TextContent]:
    vm, path = a.get("vm", "").strip().lower(), a.get("path", "").strip()
    if not vm or not path:
        return [TextContent(type="text", text="[JARVIS MCP] Erreur : 'vm' et 'path' sont requis.")]
    payload = {"history": [{"role": "user", "content": f"lis le fichier {path} sur vm {vm}"}],
               "web_search": False, "soc_ctx_injected": False}
    r = await _collect_sse_tokens(f"{JARVIS_BASE}/api/chat", payload)
    return [TextContent(type="text", text=JARVIS_HEADER + (r or f"[JARVIS] Impossible de lire {path} sur {vm} (timeout ou SSH KO)"))]


async def _handle_jarvis_model_switch(a: dict) -> list[TextContent]:
    model = a.get("model", "").strip()
    if not model:
        return [TextContent(type="text", text="[JARVIS MCP] Erreur : 'model' est requis.")]
    async with httpx.AsyncClient(timeout=TIMEOUT_FAST) as client:
        resp = await client.post(f"{JARVIS_BASE}/api/models", json={"model": model})
        data = resp.json()
    text = (f"Modèle activé : {data.get('model', model)}\nAuto-profil   : {data.get('auto_profile') or 'aucun'}"
            if data.get("ok") else f"Échec : modèle '{model}' inconnu ou non disponible dans Ollama.")
    return [TextContent(type="text", text=JARVIS_HEADER + text)]


def _sanitize(text: str, max_chars: int = 3000) -> str:
    """Filtre les IPs et tronque — gardefou avant envoi vers Claude."""
    sanitized = _RE_IPV4.sub("[IP]", text)
    if len(sanitized) > max_chars:
        sanitized = sanitized[:max_chars] + f"\n… [tronqué — {len(text)} car. total]"
    return sanitized


async def _handle_jarvis_last_response(a: dict) -> list[TextContent]:
    n = min(max(int(a.get("n", 1)), 1), 5)
    async with httpx.AsyncClient(timeout=TIMEOUT_FAST) as client:
        resp = await client.get(f"{JARVIS_BASE}/api/history/last", params={"n": n})
        resp.raise_for_status()
        data = resp.json()
    exchanges = data.get("exchanges", [])
    if not exchanges:
        return [TextContent(type="text", text="[JARVIS] Aucun échange enregistré depuis le démarrage.")]
    import datetime
    lines = []
    for ex in exchanges:
        ts = datetime.datetime.fromtimestamp(ex["ts"]).strftime("%H:%M:%S")
        lines.append(f"[{ts}] USER: {_sanitize(ex['user'], 300)}")
        lines.append(f"[{ts}] JARVIS: {_sanitize(ex['assistant'])}")
        lines.append("")
    return [TextContent(type="text", text=JARVIS_HEADER + "\n".join(lines).strip())]


async def _handle_jarvis_code_exec(a: dict) -> list[TextContent]:
    filename = (a.get("filename") or "").strip()
    code     = (a.get("code")     or "").strip()
    if not filename or not code:
        return [TextContent(type="text", text="Erreur : filename et code requis")]
    payload = {"filename": filename, "code": code}
    result = await _collect_sse_tokens(f"{JARVIS_BASE}/api/code/exec", payload)
    return [TextContent(type="text", text=_sanitize(result or "Aucune sortie."))]


async def _handle_jarvis_defense_24h(a: dict) -> list[TextContent]:
    """Récupère defense_24h.json via JARVIS et le sérialise en bloc texte compact
    optimisé pour la lecture LLM (KPI + delta vs hier + pic horaire + top 5 pays/AS/scénarios)."""
    async with httpx.AsyncClient(timeout=TIMEOUT_FAST) as client:
        resp = await client.get(f"{JARVIS_BASE}/api/soc/defense")
        resp.raise_for_status()
        data = resp.json()
    if not data.get("ok"):
        return [TextContent(type="text", text=f"[JARVIS DEFENSE] {data.get('error', 'inaccessible')}")]
    k    = data.get("kpi", {}) or {}
    dlt  = data.get("kpi_delta", {}) or {}
    heat = data.get("heatmap_24h", []) or []
    bucket_min = data.get("heatmap_bucket_min") or (60 if len(heat) <= 24 else 15)
    peak_h, peak_v = (-1, 0)
    for i, v in enumerate(heat):
        if v > peak_v:
            peak_h, peak_v = i, v
    if peak_h < 0:
        peak_lbl = "n/a"
    elif peak_h == len(heat) - 1:
        peak_lbl = "tranche courante"
    else:
        m_ago = (len(heat) - 1 - peak_h) * bucket_min
        peak_lbl = (f"il y a {m_ago}min" if m_ago < 60
                    else (f"h-{m_ago // 60}" if m_ago % 60 == 0
                          else f"h-{m_ago // 60} {m_ago % 60}min"))
    def _top(lst, n=5):
        return " · ".join(f"{(x.get('value') or '?')[:14]}({x.get('count', 0)})"
                          for x in (lst or [])[:n])
    def _kvd(key):
        """KPI courant + delta vs hier formaté '50 (+15%)' ou '50' si pas de baseline."""
        val = k.get(key, 0)
        d = (dlt.get(key) or {})
        pct = d.get("pct")
        if pct is None:
            return f"{val}"
        sign = "+" if pct >= 0 else ""
        return f"{val} ({sign}{pct}% vs hier)"
    text = (
        JARVIS_HEADER
        + f"DÉFENSE 24H — généré {data.get('generated_at', '?')}\n"
        + "─" * 60 + "\n"
        + f"  Actions totales       : {_kvd('total_actions')}\n"
        + f"  Bans CrowdSec 24h     : {_kvd('bans_24h')}\n"
        + f"  Décisions CS actives  : {_kvd('cs_active')}\n"
        + f"  WAF CLT / PA85        : {_kvd('waf_clt_24h')} / {_kvd('waf_pa85_24h')}\n"
        + f"  Suricata sev1 / sev2  : {_kvd('ids_sev1')} / {_kvd('ids_sev2')}\n"
        + f"  GeoBlock 24h          : {_kvd('geo_24h')}\n"
        + f"  Fail2ban actifs       : {_kvd('fail2ban_active')}\n"
        + f"  UFW DROP 24h          : {_kvd('ufw_24h')}\n"
        + f"  Pic {bucket_min}min            : {peak_lbl} ({peak_v} actions)\n"
        + "─" * 60 + "\n"
        + f"  Top pays      : {_top(data.get('top_country'))}\n"
        + f"  Top AS        : {_top(data.get('top_as'))}\n"
        + f"  Top scénarios : {_top(data.get('top_scenario'))}\n"
    )
    return [TextContent(type="text", text=_sanitize(text))]


async def _handle_jarvis_ioc_status(a: dict) -> list[TextContent]:
    """Récupère le bloc `ioc` de monitoring.json via JARVIS et le sérialise en
    bloc texte compact LLM-friendly (score 0-100 + 6 signaux + détails si WARN/CRIT)."""
    async with httpx.AsyncClient(timeout=TIMEOUT_FAST) as client:
        resp = await client.get(f"{JARVIS_BASE}/api/soc/ioc")
        resp.raise_for_status()
        data = resp.json()
    if not data.get("ok"):
        return [TextContent(type="text", text=f"[JARVIS IoC] {data.get('error', 'inaccessible')}")]
    ioc   = data.get("ioc") or {}
    score = ioc.get("score", 0)
    level = ioc.get("level", "OK")
    sigs  = ioc.get("signals", {}) or {}
    def _c(k: str) -> int:
        return int((sigs.get(k) or {}).get("count", 0))
    text = (
        JARVIS_HEADER
        + f"IoC POST-COMPROMISSION — généré {ioc.get('generated_at', '?')}\n"
        + "─" * 60 + "\n"
        + f"  Score global   : {score}/100 — niveau {level}\n"
        + f"  AIDE drift     : {_c('aide_drift')}\n"
        + f"  C2 alerts      : {_c('c2_alerts')}\n"
        + f"  SSH anomaly    : {_c('ssh_anomaly')}\n"
        + f"  Webshells      : {_c('webshells')}\n"
        + f"  AppArmor deny  : {_c('apparmor_denials')}\n"
        + f"  Sudo events    : {_c('sudo_events')}\n"
        + "─" * 60 + "\n"
    )
    if level != "OK":
        details = []
        for k, lbl in (("aide_drift", "AIDE"), ("c2_alerts", "C2"),
                       ("ssh_anomaly", "SSH"), ("webshells", "Webshells"),
                       ("apparmor_denials", "AppArmor"), ("sudo_events", "Sudo")):
            s = sigs.get(k) or {}
            if s.get("score", 0) > 0:
                d_list = s.get("detail") or []
                sample = (str(d_list[0])[:80]) if d_list else ""
                details.append(f"  ⚠ {lbl} ({s.get('count', 0)}) — {sample}")
        if details:
            text += "\n".join(details) + "\n"
    return [TextContent(type="text", text=_sanitize(text))]


_TOOL_HANDLERS = {
    "jarvis_chat":           _handle_jarvis_chat,
    "jarvis_soc_status":     _handle_jarvis_soc_status,
    "jarvis_soc_ask":        _handle_jarvis_soc_ask,
    "jarvis_stats":          _handle_jarvis_stats,
    "jarvis_infra_status":   _handle_jarvis_infra_status,
    "jarvis_proxmox_vms":    _handle_jarvis_proxmox_vms,
    "jarvis_read_file":      _handle_jarvis_read_file,
    "jarvis_model_switch":   _handle_jarvis_model_switch,
    "jarvis_last_response":  _handle_jarvis_last_response,
    "jarvis_code_exec":      _handle_jarvis_code_exec,
    "jarvis_defense_24h":    _handle_jarvis_defense_24h,
    "jarvis_ioc_status":     _handle_jarvis_ioc_status,
}


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            return [TextContent(type="text", text=f"Outil inconnu : {name}")]
        return await handler(arguments)
    except httpx.ConnectError:
        return [TextContent(type="text", text=(
            "[JARVIS MCP] JARVIS est hors ligne (localhost:5000 injoignable). "
            "Lance JARVIS puis réessaie."
        ))]
    except Exception as exc:
        return [TextContent(type="text", text=f"[JARVIS MCP] Erreur : {exc}")]


def _build_starlette_app(port: int) -> Starlette:
    # ── Legacy SSE transport (backward compat) ────────────────────────────────
    sse_transport = SseServerTransport("/messages/")

    async def handle_sse(request: Request):
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    # ── Streamable HTTP transport (MCP 1.6+ / Claude Code extension actuel) ──
    session_manager = StreamableHTTPSessionManager(app=app, stateless=True)

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette):
        async with session_manager.run():
            yield

    async def handle_mcp(scope, receive, send):
        await session_manager.handle_request(scope, receive, send)

    async def handle_mcp_endpoint(request: Request):
        await session_manager.handle_request(request.scope, request.receive, request._send)

    async def health(request: Request):
        return JSONResponse({"ok": True, "service": "jarvis-mcp", "port": port})

    return Starlette(
        lifespan=lifespan,
        routes=[
            Route("/health",    endpoint=health),
            Route("/sse",       endpoint=handle_sse),
            Mount("/messages/", app=sse_transport.handle_post_message),
            Route("/mcp",       endpoint=handle_mcp_endpoint, methods=["GET", "POST", "DELETE"]),
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5010)
    args = parser.parse_args()
    uvicorn.run(
        _build_starlette_app(args.port),
        host="127.0.0.1",
        port=args.port,
        log_level="error",
    )
