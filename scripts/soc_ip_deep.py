"""Investigation IP approfondie — collecteurs GeoIP / CrowdSec / Fail2ban /
autoban / nginx / rsyslog central.

Extrait de blueprints/soc.py le 2026-05-22 (refactor incrémental, étape 1 —
« couverture d'abord, refactor ensuite »). Cluster cohérent et entièrement
couvert par tests avant extraction.

Dépendance unique injectée par `init()` : la fonction `_ssh_ngix` de soc.py
(exécution SSH sur srv-ngix). Aucun couplage en sens inverse.

Consommé par les routes /api/soc/ip-history et /api/soc/ip-deep (soc.py), qui
appellent les `_deep_*` via des alias légers conservés dans soc.py.
"""
import base64
import json

_F2B_HISTORY_LIMIT = 10        # entrées historique fail2ban dans ip-deep

# Injecté par init() — fonction SSH srv-ngix de soc.py. (ssh_arr → (ok, out))
_ssh_ngix = None


def init(ssh_ngix) -> None:
    """Injecte la dépendance SSH srv-ngix depuis soc.py."""
    global _ssh_ngix
    _ssh_ngix = ssh_ngix


def _b64py(script: str) -> str:
    """Encode un script Python en base64 et retourne la commande SSH distante."""
    return f"echo {base64.b64encode(script.encode()).decode()} | base64 -d | python3"


def _ssh_json_exec(script: str, timeout: int = 10) -> dict:
    """Exécute un script Python via SSH b64, retourne le JSON parsé ou {}."""
    ok, out = _ssh_ngix(_b64py(script), timeout=timeout)
    try:
        return json.loads(out.strip()) if ok and out.strip().startswith('{') else {}
    except Exception:
        return {}


def _deep_geoip(ip: str) -> dict:
    """GeoIP via GeoLite2-City.mmdb."""
    script = (
        "import geoip2.database,json,sys\n"
        "try:\n"
        f"    r=geoip2.database.Reader('/usr/share/GeoIP/GeoLite2-City.mmdb').city('{ip}')\n"
        "    print(json.dumps({'country':r.country.name,'iso':r.country.iso_code or '','city':r.city.name or '','lat':float(r.location.latitude or 0),'lon':float(r.location.longitude or 0)}))\n"
        "except Exception:\n"
        "    print('{}')\n"
    )
    return _ssh_json_exec(script, timeout=10)


def _deep_crowdsec(ip: str) -> dict:
    """CrowdSec — décisions actives + alertes 30j."""
    ok, out = _ssh_ngix(f"cscli decisions list --ip {ip} -o json 2>/dev/null || echo '[]'", timeout=10)
    try:
        cs_raw = json.loads(out) if ok else []
        if not isinstance(cs_raw, list):
            cs_raw = []
    except Exception:
        cs_raw = []
    # cscli decisions list -o json retourne des alertes imbriquées :
    # [{..., "decisions": [{scenario, duration, origin, type, value}]}]
    cs_decisions = []
    for alert in cs_raw:
        for d in (alert.get("decisions") or []):
            cs_decisions.append(d)
    ok, out = _ssh_ngix(
        f"cscli alerts list --ip {ip} --since 720h -o json 2>/dev/null || echo '[]'", timeout=12
    )
    try:
        cs_alerts = json.loads(out) if ok else []
        if not isinstance(cs_alerts, list):
            cs_alerts = []
    except Exception:
        cs_alerts = []
    return {
        "banned":        len(cs_decisions) > 0,
        "count":         len(cs_decisions),
        "decisions":     [
            {
                "id":       d.get("id"),
                "scenario": d.get("scenario", "") or d.get("reason", "") or "ban",
                "duration": d.get("duration", ""),
                "origin":   d.get("origin", ""),
                "type":     d.get("type", "ban"),
            }
            for d in cs_decisions[:5]
        ],
        "alerts_30d":    len(cs_alerts),
        "alerts_detail": [
            {"ts": a.get("created_at", ""), "scenario": a.get("scenario", ""), "count": a.get("events_count", 0)}
            for a in cs_alerts[-10:]
        ],
    }


def _deep_fail2ban(ip: str) -> dict:
    """Fail2ban — bans actifs + historique (sqlite)."""
    script = (
        "import sqlite3,json,time\n"
        "try:\n"
        "    db=sqlite3.connect('/var/lib/fail2ban/fail2ban.sqlite3')\n"
        "    c=db.cursor()\n"
        f"    c.execute('SELECT name,timeofban,bantime,bancount FROM bans WHERE ip=?', ('{ip}',))\n"
        "    rows=c.fetchall()\n"
        "    now=int(time.time())\n"
        "    active=[r[0] for r in rows if r[1]+r[2]>now]\n"
        "    history=[{'jail':r[0],'ts':r[1],'bantime':r[2],'count':r[3]} for r in rows]\n"
        "    print(json.dumps({'active':active,'history':history,'total_records':len(rows)}))\n"
        "except Exception as e:\n"
        "    print(json.dumps({'active':[],'history':[],'total_records':0,'err':str(e)}))\n"
    )
    f2b = _ssh_json_exec(script, timeout=10)
    return {
        "banned":        len(f2b.get("active", [])) > 0,
        "jails":         f2b.get("active", []),
        "total_records": f2b.get("total_records", 0),
        "history":       f2b.get("history", [])[:_F2B_HISTORY_LIMIT],
    }


def _deep_autoban(ip: str) -> dict:
    """autoban-log.json — récidive JARVIS/monitoring_gen."""
    script = (
        "import json\n"
        "try:\n"
        "    d=json.load(open('/var/www/monitoring/autoban-log.json'))\n"
        f"    hits=[e for e in d if e.get('ip')=='{ip}']\n"
        "    print(json.dumps({'count':len(hits),'history':hits}))\n"
        "except Exception:\n"
        "    print('{\"count\":0,\"history\":[]}')\n"
    )
    return _ssh_json_exec(script, timeout=10) or {"count": 0, "history": []}


def _deep_nginx_hits(ip: str) -> int:
    """nginx — hits (log courant + archives gz)."""
    cmd = (
        f"a=$(grep -c ' {ip} ' /var/log/nginx/access.log 2>/dev/null || echo 0);"
        f"b=$(zcat /var/log/nginx/access.log.*.gz 2>/dev/null | grep -c ' {ip} ' 2>/dev/null || echo 0);"
        "echo $((a+b))"
    )
    ok, out = _ssh_ngix(cmd, timeout=15)
    try:
        return int(out.strip()) if ok and out.strip().isdigit() else 0
    except Exception:
        return 0


def _deep_nginx_last(ip: str) -> list:
    """nginx — dernières requêtes (aperçu 5 lignes)."""
    ok, out = _ssh_ngix(
        f"grep ' {ip} ' /var/log/nginx/access.log 2>/dev/null | tail -5", timeout=10
    )
    return [ln.strip() for ln in out.split('\n') if ln.strip()] if ok else []


def _deep_rsyslog(ip: str) -> dict:
    """rsyslog central — grep croisé 30j toutes sources."""
    cmd = (
        f"grep -r '{ip}' /var/log/central/ --include='*.log' -c 2>/dev/null"
        " | grep -v ':0$' | sort -t: -k2 -rn | head -15"
    )
    ok, out = _ssh_ngix(cmd, timeout=25)
    counts = {}
    total  = 0
    if ok:
        for line in out.split('\n'):
            line = line.strip()
            if ':' in line:
                fname, cnt = line.rsplit(':', 1)
                if cnt.isdigit():
                    short = '/'.join(fname.strip().split('/')[-2:])
                    counts[short] = int(cnt)
                    total += int(cnt)
    return {"total": total, "sources": counts}
