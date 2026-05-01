<div align="center">

  <br></br>

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=50&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS_" alt="Titre dynamique JARVIS" />
  </a>

  <br></br>

  <h2>Assistant IA local · voix · interface holographique · automatisation SOC 24/7</h2>

  <p align="center">
    <a href="https://0xcyberlitech.github.io/">
      <img src="https://img.shields.io/badge/Portfolio-0xCyberLiTech-181717?logo=github&style=flat-square" alt="Portfolio" />
    </a>
    <a href="https://github.com/0xCyberLiTech">
      <img src="https://img.shields.io/badge/Profil-GitHub-181717?logo=github&style=flat-square" alt="Profil GitHub" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/releases/latest">
      <img src="https://img.shields.io/github/v/release/0xCyberLiTech/JARVIS?label=version&style=flat-square&color=blue" alt="Dernière version" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/blob/main/CHANGELOG.md">
      <img src="https://img.shields.io/badge/📄%20Changelog-JARVIS-blue?style=flat-square" alt="Changelog" />
    </a>
    <a href="https://github.com/0xCyberLiTech?tab=repositories">
      <img src="https://img.shields.io/badge/Dépôts-publics-blue?style=flat-square" alt="Dépôts publics" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/graphs/contributors">
      <img src="https://img.shields.io/badge/👥%20Contributeurs-cliquez%20ici-007ec6?style=flat-square" alt="Contributeurs" />
    </a>
  </p>

</div>

<div align="center">
  <img src="https://img.icons8.com/fluency/96/000000/cyber-security.png" alt="CyberSec" width="80"/>
</div>

<div align="center">
  <p>
    <strong>IA 100% locale</strong> <img src="https://img.icons8.com/color/24/000000/lock--v1.png"/> &nbsp;•&nbsp; <strong>Voix naturelle · STT · TTS</strong> <img src="https://img.icons8.com/color/24/000000/linux.png"/> &nbsp;•&nbsp; <strong>Automatisation SOC</strong> <img src="https://img.icons8.com/color/24/000000/shield-security.png"/>
  </p>
</div>

---

# Étape 5 — Intégration SOC

## Objectif
JARVIS devient le **bras armé** du dashboard SOC :
- Il lit les métriques de sécurité en temps réel
- Il déclenche des actions défensives (ban-IP, restart service)
- Il envoie des alertes vocales si le niveau de menace monte

```
Dashboard SOC (monitoring.json)
    ↓ fetch HTTP (30s)
JARVIS analyse
    ↓ si menace détectée
Action SSH sur srv-ngix (ban-IP / restart)
    ↓
Alerte vocale TTS
```

---

## Étape 5.1 — Lecture des données SOC

```python
import requests, json

# URL du monitoring.json (servi par nginx sur le serveur SOC)
SOC_MONITORING_URL = "http://VOTRE_IP:8080/monitoring.json"

_last_soc_data = {}

def fetch_soc_data():
    """Récupère les données SOC depuis monitoring.json."""
    global _last_soc_data
    try:
        resp = requests.get(SOC_MONITORING_URL, timeout=5)
        if resp.ok:
            _last_soc_data = resp.json()
            return _last_soc_data
    except Exception:
        pass
    return _last_soc_data


def _get_soc_context() -> str:
    """
    Construit un contexte textuel depuis les données SOC
    pour enrichir les prompts LLM.
    """
    data = _last_soc_data
    if not data:
        return ""

    lines = []
    cs = data.get("crowdsec", {})
    if cs.get("active_decisions"):
        lines.append(f"CrowdSec : {cs['active_decisions']} IPs bannies actives")

    f2b = data.get("fail2ban", {})
    if f2b.get("total_banned"):
        lines.append(f"fail2ban : {f2b['total_banned']} bans total (4 hôtes)")

    sur = data.get("suricata", {})
    if sur.get("sev1"):
        lines.append(f"Suricata : {sur['sev1']} alertes critiques (sév.1) en 24h")

    return "\n".join(lines) if lines else ""
```

---

## Étape 5.2 — Actions SSH (ban-IP, restart service)

```python
import paramiko, threading

# Verrou SSH — évite les connexions simultanées
_ssh_lock = threading.Lock()

def ssh_exec(command: str, host: str, port: int, ssh_key_path: str,
             user: str = "root", timeout: int = 15) -> dict:
    """
    Exécute une commande SSH sur le serveur SOC.
    Retourne {"success": bool, "stdout": str, "stderr": str}
    """
    with _ssh_lock:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        try:
            client.connect(
                host,
                port=port,
                username=user,
                key_filename=ssh_key_path,
                timeout=timeout,
                banner_timeout=timeout,
                allow_agent=False,
                look_for_keys=False,
            )
            _, stdout, stderr = client.exec_command(command, timeout=timeout)
            return {
                "success": True,
                "stdout":  stdout.read().decode().strip(),
                "stderr":  stderr.read().decode().strip(),
            }
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e)}
        finally:
            client.close()


def ban_ip(ip: str) -> dict:
    """Bannit une IP via CrowdSec sur le serveur SOC."""
    # Valider l'IP avant de l'envoyer en SSH
    import re
    if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", ip):
        return {"success": False, "error": "Format IP invalide"}

    cmd = f"cscli decisions add --ip {ip} --duration 24h --reason 'JARVIS-ban'"
    result = ssh_exec(cmd, host=SOC_HOST, port=SOC_PORT, ssh_key_path=SOC_SSH_KEY)

    if result["success"]:
        speak(f"IP {ip} bannie via CrowdSec pour 24 heures.")
        _log_soc_action("ban_ip", ip, success=True)
    else:
        speak(f"Échec du ban pour {ip}.")
        _log_soc_action("ban_ip", ip, success=False, error=result["stderr"])

    return result


def unban_ip(ip: str) -> dict:
    """Lève le ban d'une IP."""
    cmd = f"cscli decisions delete --ip {ip}"
    return ssh_exec(cmd, host=SOC_HOST, port=SOC_PORT, ssh_key_path=SOC_SSH_KEY)


def restart_service(service: str) -> dict:
    """Redémarre un service sur le serveur SOC."""
    # Liste blanche des services autorisés (sécurité)
    ALLOWED_SERVICES = {"nginx", "crowdsec", "fail2ban", "suricata"}
    if service not in ALLOWED_SERVICES:
        return {"success": False, "error": f"Service '{service}' non autorisé"}

    cmd = f"systemctl restart {service}"
    result = ssh_exec(cmd, host=SOC_HOST, port=SOC_PORT, ssh_key_path=SOC_SSH_KEY)

    if result["success"]:
        speak(f"Service {service} redémarré avec succès.")
    return result
```

---

## Étape 5.3 — Actions proactives automatiques

```python
import time, threading

_proactive_running = False
SOC_CHECK_INTERVAL = 30  # secondes

# Seuils d'alerte
THRESHOLDS = {
    "crowdsec_bans_spike": 50,   # Bans/heure pour déclencher analyse
    "suricata_sev1":        5,    # Alertes sév.1 pour alerte vocale
    "threat_score_high":   60,   # Score menace pour alerte
    "threat_score_crit":   80,   # Score menace pour alerte critique
}

def start_proactive_monitoring():
    """Démarre la surveillance proactive en arrière-plan."""
    global _proactive_running
    _proactive_running = True
    threading.Thread(target=_proactive_loop, daemon=True).start()


def _proactive_loop():
    """Boucle de surveillance — vérifie les métriques SOC toutes les 30s."""
    prev_score = 0
    while _proactive_running:
        try:
            data  = fetch_soc_data()
            score = _compute_threat_score(data)

            # Alerte si score monte significativement
            if score >= THRESHOLDS["threat_score_crit"] and prev_score < THRESHOLDS["threat_score_crit"]:
                speak(f"ALERTE CRITIQUE — Score de menace : {score} sur 100. Intervention recommandée.")
                _log_soc_action("threat_alert", f"score={score}", success=True)

            elif score >= THRESHOLDS["threat_score_high"] and prev_score < THRESHOLDS["threat_score_high"]:
                speak(f"Niveau de menace élevé — Score : {score}.")

            # Auto-ban si pic de bans CrowdSec
            cs = data.get("crowdsec", {})
            if cs.get("spike") and cs.get("available"):
                _handle_crowdsec_spike(cs)

            # Restart service si détecté DOWN
            for svc in data.get("services", []):
                if svc.get("status") != "active" and svc.get("name") in {"nginx", "crowdsec"}:
                    restart_service(svc["name"])

            prev_score = score

        except Exception as e:
            logging.error(f"Proactive loop error: {e}")

        time.sleep(SOC_CHECK_INTERVAL)


def _compute_threat_score(data: dict) -> int:
    """Version simplifiée du calcul de score — voir doc SOC pour la version complète."""
    score = 0
    cs  = data.get("crowdsec", {})
    f2b = data.get("fail2ban", {})
    sur = data.get("suricata", {})

    score += min((cs.get("active_decisions", 0) // 10), 20)
    score += min((f2b.get("total_banned", 0) // 5), 15)
    score += min((sur.get("sev1", 0) * 3), 15)

    return min(score, 100)
```

---

## Étape 5.4 — Routes Flask pour le dashboard SOC

```python
@app.route("/soc/ban", methods=["POST"])
def soc_ban():
    """Route appelée par le bouton 'Ban IP' du dashboard."""
    data = request.get_json() or {}
    ip   = data.get("ip", "").strip()
    if not ip:
        return jsonify({"error": "IP manquante"}), 400
    return jsonify(ban_ip(ip))


@app.route("/soc/unban", methods=["POST"])
def soc_unban():
    data = request.get_json() or {}
    ip   = data.get("ip", "").strip()
    return jsonify(unban_ip(ip))


@app.route("/soc/restart", methods=["POST"])
def soc_restart():
    data    = request.get_json() or {}
    service = data.get("service", "").strip()
    return jsonify(restart_service(service))


@app.route("/soc/actions", methods=["GET"])
def soc_actions_log():
    """Retourne le journal des actions SOC (affiché dans l'onglet SOC de JARVIS)."""
    return jsonify(_get_soc_action_log())


@app.route("/soc/data", methods=["GET"])
def soc_data():
    """Retourne les données SOC actuelles."""
    return jsonify(fetch_soc_data())
```

---

## Étape 5.5 — Intégration dans le dashboard SOC

Le dashboard SOC affiche l'état de JARVIS dans une tuile dédiée  
et utilise ses routes pour les actions rapides :

```javascript
// Dans monitoring-index.html
// Vérifier que JARVIS est en ligne
fetch('http://localhost:5000/status')
    .then(r => r.json())
    .then(d => {
        var online = d.status === 'online';
        document.getElementById('jarvis-status').textContent =
            online ? '⬡ JARVIS ONLINE' : '⬡ JARVIS OFFLINE';
    });

// Bouton Ban IP rapide
function banIpViaJarvis(ip) {
    fetch('http://localhost:5000/soc/ban', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ip: ip})
    }).then(r => r.json()).then(d => console.log(d));
}
```

---

## Sécurité

| Mesure | Implémentation |
|--------|---------------|
| Bind loopback uniquement | `host=127.0.0.1` dans Flask |
| Liste blanche services | Seuls nginx/crowdsec/fail2ban/suricata restartables |
| Validation IP avant ban | Regex + format check |
| Clé SSH dédiée SOC | Pas de réutilisation des clés personnelles |
| Pas de root Flask | L'utilisateur Flask n'a pas sudo sauf pour les commandes listées |

---

**JARVIS est opérationnel.** Pour démarrer :

```bash
cd scripts
python jarvis.py
# → http://localhost:5000
```

---

<div align="center">

<table>
<tr>
<td align="center"><b>🖥️ Infrastructure &amp; Sécurité</b></td>
<td align="center"><b>💻 Développement &amp; Web</b></td>
<td align="center"><b>🤖 Intelligence Artificielle</b></td>
</tr>
<tr>
<td align="center">
  <a href="https://www.kernel.org/"><img src="https://skillicons.dev/icons?i=linux" width="48" title="Linux" /></a>
  <a href="https://www.debian.org"><img src="https://skillicons.dev/icons?i=debian" width="48" title="Debian" /></a>
  <a href="https://www.gnu.org/software/bash/"><img src="https://skillicons.dev/icons?i=bash" width="48" title="Bash" /></a>
  <br/>
  <a href="https://nginx.org"><img src="https://skillicons.dev/icons?i=nginx" width="48" title="Nginx" /></a>
  <a href="https://git-scm.com"><img src="https://skillicons.dev/icons?i=git" width="48" title="Git" /></a>
</td>
<td align="center">
  <a href="https://www.python.org"><img src="https://skillicons.dev/icons?i=python" width="48" title="Python" /></a>
  <a href="https://flask.palletsprojects.com"><img src="https://skillicons.dev/icons?i=flask" width="48" title="Flask" /></a>
  <a href="https://developer.mozilla.org/docs/Web/HTML"><img src="https://skillicons.dev/icons?i=html" width="48" title="HTML5" /></a>
  <br/>
  <a href="https://developer.mozilla.org/docs/Web/CSS"><img src="https://skillicons.dev/icons?i=css" width="48" title="CSS3" /></a>
  <a href="https://developer.mozilla.org/docs/Web/JavaScript"><img src="https://skillicons.dev/icons?i=js" width="48" title="JavaScript" /></a>
  <a href="https://code.visualstudio.com"><img src="https://skillicons.dev/icons?i=vscode" width="48" title="VS Code" /></a>
</td>
<td align="center">
  <a href="https://ollama.com"><img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" /></a>
  <br/><br/>
  <a href="https://anthropic.com"><img src="https://img.shields.io/badge/Anthropic-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic" /></a>
</td>
</tr>
</table>

<br/>

<sub>🔒 Projets proposés par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · Développés en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🔒</sub>

</div>
