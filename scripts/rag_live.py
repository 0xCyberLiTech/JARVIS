"""RAG Live — fetch logs SOC SSH (Suricata + CrowdSec + fail2ban + nginx) sans embedding.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 module 13.

Différent du RAG statique (vecteurs+BM25 sur jarvis_rag/) :
- Pas d'embedding → latence quasi-nulle (juste un cache texte)
- Refresh asynchrone toutes les 5 min via SSH srv-nginx
- Injection conditionnelle dans system prompt si la question matche `LIVE_KW`

Dependency injection : `ssh_fn` passée en argument à `refresh()` et `prewarm()`.

Le RAG statique (`_rag_query`, `_rag_load`, embedding mxbai-embed-large) reste
dans `jarvis.py` car couplé numpy + ollama embeddings + BM25 cache.
"""
import logging
import re
import threading
import time

_log = logging.getLogger("jarvis.rag_live")

# ── Constantes ────────────────────────────────────────────────
LIVE_TTL = 300  # secondes — rafraîchissement toutes les 5 min

# Keywords déclenchant l'injection live
LIVE_KW = re.compile(
    r'\b(log|alert|alerte|alertes|suricata|fail2ban|ban|banni|ip|attaque|menace|crowdsec|trafic|'
    r'incident|intrusion|eve|scan|brute|exploit|recon|connexion|tentative|'
    r'bloqué|blocked|suspicious|sécurité|threat|score)\b',
    re.I,
)

# Commande SSH one-liner : Suricata fast.log (avec fallback eve.json) + CrowdSec + fail2ban + nginx
SSH_LOG_CMD = (
    "echo '=== SURICATA (30 alertes) ==='; "
    "{ cat /var/log/suricata/fast.log 2>/dev/null | tail -30; } || "
    "{ grep '\"alert\"' /var/log/suricata/eve.json 2>/dev/null | tail -80 | "
    "python3 -c \"import sys,json; [print(j.get('timestamp','')[:16]+' '+j.get('alert',{}).get('signature','')[:55]+' src='+j.get('src_ip','')) for l in sys.stdin for j in [json.loads(l.strip())] if 'alert' in j]\" 2>/dev/null | tail -30; }; "
    "echo '=== CROWDSEC DECISIONS ACTIVES ==='; "
    "cscli decisions list --limit 20 2>/dev/null | head -25; "
    "echo '=== FAIL2BAN (dernieres actions) ==='; "
    "grep -E 'Ban |Unban |Found ' /var/log/fail2ban.log 2>/dev/null | tail -20; "
    "echo '=== NGINX ERROR.LOG (20 dernieres) ==='; "
    "tail -20 /var/log/nginx/error.log 2>/dev/null"
)

# ── State (module-level cache) ────────────────────────────────
_text: str = ""              # texte brut des logs (pas d'embedding)
_lock = threading.Lock()
_last_refresh: float = 0.0


# ── API publique ──────────────────────────────────────────────

def should_inject(query: str) -> bool:
    """True si la query contient des mots-clés SOC déclenchant l'injection live."""
    return bool(LIVE_KW.search(query))


def get_text() -> str:
    """Retourne le texte brut courant des logs SOC (cache)."""
    with _lock:
        return _text


def refresh(ssh_fn, timeout: int = 18):
    """Rafraîchit le cache texte brut des logs SOC si TTL expiré.
    Thread-safe, sans embedding.

    `ssh_fn` : fonction `_ssh_ngix(cmd, timeout=N) -> (ok, output)` de jarvis.py.
    """
    global _last_refresh, _text
    now = time.time()
    if now - _last_refresh < LIVE_TTL:
        return
    try:
        ok, output = ssh_fn(SSH_LOG_CMD, timeout=timeout)
        if not ok or not output or len(output) < 50:
            return
        with _lock:
            _text = output[:3000]  # 3000 chars max → ~600 tokens
        _last_refresh = now
        _log.info(f"[RAG-LIVE] Cache rafraîchi — {len(output)} chars depuis srv-nginx")
    except Exception as e:
        _log.warning(f"[RAG-LIVE] Erreur refresh: {e}")


def prewarm(ssh_fn, timeout: int = 18):
    """Pré-chauffe le cache live au démarrage JARVIS (à lancer dans un thread daemon)."""
    global _last_refresh
    time.sleep(15)        # laisser Flask démarrer
    _last_refresh = 0.0   # forcer refresh
    refresh(ssh_fn, timeout=timeout)
    _log.info("[RAG-LIVE] Pré-chauffe initiale terminée")


def trigger_async_refresh(ssh_fn, timeout: int = 18):
    """Déclenche un refresh asynchrone (non bloquant) — sert toujours le cache existant."""
    threading.Thread(
        target=refresh,
        args=(ssh_fn,),
        kwargs={"timeout": timeout},
        daemon=True,
    ).start()
