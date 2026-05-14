# RUNBOOK — 0xCyberLiTech
<!-- Document maître — reconstruction infrastructure complète -->
<!-- Mis à jour : 2026-05-14 — Chantier dette technique : git initialisé + pre-commit hooks + ruff.toml + CSS 8 fichiers + audio_dsp.py · 31 modules Python · jarvis.py 4633L · score honnête 75/100 -->

---

## Infrastructure

| Machine | IP | Rôle | SSH |
|---------|----|------|-----|
| Proxmox VE | 192.168.1.20 | Hyperviseur physique | `ssh -i ~/.ssh/id_proxmox -p 2272 root@192.168.1.20` |
| srv-ngix (VM 108) | 192.168.1.50 | Reverse proxy + SOC + CrowdSec | `ssh -i ~/.ssh/id_nginx -p 2272 root@192.168.1.50` |
| clt (VM 106) | 192.168.1.12 | Apache + site CLT | `ssh -i ~/.ssh/id_clt -p 2272 root@192.168.1.12` |
| pa85 (VM 107) | 192.168.1.13 | Apache + site PA85 | `ssh -i ~/.ssh/id_pa85 -p 2272 root@192.168.1.13` |
| Routeur ASUS GT-BE98 | 192.168.50.1 | Routeur LAN/WAN | `ssh -i ~/.ssh/id_router -p 2272 admin-clt@192.168.50.1` |
| JARVIS | localhost:5000 | Assistant IA Flask | `cd JARVIS\scripts && python jarvis.py` |
| Dashboard SOC | 192.168.1.50:8080 | Monitoring sécurité | http://192.168.1.50:8080 |

---

## Index documentation

| Dossier | Contenu | Usage |
|---------|---------|-------|
| `CLES_SSH_0xcyberlitech/` | Clés SSH + fingerprints + maillage | Accès à une machine reconstruite |
| `CLES_API_0xcyberlitech/` | Clés API (NVD, abuse.ch, AbuseIPDB, SMTP, Proxmox, Freebox) | Reconfigurer les intégrations après rebuild |
| `ACLs_UFW_0xcyberlitech/` | Règles firewall UFW + restauration | Reconstruire le firewall |
| `FAIL2BAN_0xcyberlitech/` | Jails fail2ban + paramètres + restauration | Reconstruire la protection brute-force |
| `CRONS_0xcyberlitech/` | Tâches planifiées + restauration | Remettre en route le monitoring automatique |
| `SERVICES_0xcyberlitech/` | Services systemd actifs/désactivés | Vérifier l'état des services après rebuild |
| `CROWDSEC_0xcyberlitech/` | Collections, bouncers, AppSec WAF, restauration | Reconstruire CrowdSec après rebuild srv-ngix |
| `SURICATA_0xcyberlitech/` | Version, sources règles, intégration CrowdSec, restauration | Reconstruire Suricata IDS après rebuild srv-ngix |
| `0xCyberLiTech\NGINX\` | Configs nginx, vhosts, CrowdSec | Reconfigurer le reverse proxy |
| `0xCyberLiTech\SOC\scripts\` | Scripts monitoring srv-ngix | Redéployer les scripts SOC |

---

## Checklist reconstruction par machine

### Proxmox VE (192.168.1.20)

```
[ ] Réinstaller Proxmox VE
[ ] SSH port 2272 — /etc/ssh/sshd_config : Port 2272, PasswordAuthentication no
[ ] Copier clé publique id_proxmox (Windows) → authorized_keys
[ ] Copier clé publique id_proxmox_sync (srv-ngix) → authorized_keys
[ ] Copier clé privée id_pve_monitor → /root/.ssh/ + command= pve-monitor-write
[ ] UFW → ACLs_UFW_0xcyberlitech/proxmox/README.md
[ ] fail2ban → FAIL2BAN_0xcyberlitech/proxmox/README.md
[ ] Crons push → CRONS_0xcyberlitech/proxmox/README.md
[ ] Services → SERVICES_0xcyberlitech/proxmox/README.md (rpcbind disabled)
[ ] Vérifier pve-firewall actif (cluster.fw enable: 1)
```

### srv-ngix (192.168.1.50)

```
[ ] Créer VM 108 dans Proxmox, restaurer backup vzdump si dispo
[ ] SSH port 2272 — PasswordAuthentication no
[ ] Copier clé publique id_nginx (Windows) → authorized_keys
[ ] Copier clés id_clt_sync + id_pa85_sync + id_proxmox_sync → /root/.ssh/
[ ] UFW → ACLs_UFW_0xcyberlitech/srv-ngix/README.md
[ ] fail2ban → FAIL2BAN_0xcyberlitech/srv-ngix/README.md
[ ] Crons → CRONS_0xcyberlitech/srv-ngix/README.md (monitoring, proto-live, CVE...)
[ ] Services → SERVICES_0xcyberlitech/srv-ngix/README.md (nftables disabled)
[ ] nginx configs → 0xCyberLiTech\NGINX\
[ ] Scripts SOC → 0xCyberLiTech\SOC\scripts\ → /opt/clt/
[ ] CrowdSec + bouncer → CROWDSEC_0xcyberlitech/srv-ngix/README.md
[ ] Suricata IDS → SURICATA_0xcyberlitech/srv-ngix/README.md (8 sources, 106K règles)
[ ] Clés API → CLES_API_0xcyberlitech/ (NVD, abuse.ch, AbuseIPDB, SMTP, Freebox)
[ ] Vérifier : cd /opt/clt && python3 monitoring_gen.py
```

### clt (192.168.1.12)

```
[ ] Créer VM 106, restaurer backup si dispo
[ ] SSH port 2272 — PasswordAuthentication no
[ ] Copier clé publique id_clt (Windows) → authorized_keys
[ ] Copier clé publique id_clt_sync (srv-ngix) → authorized_keys
[ ] UFW → ACLs_UFW_0xcyberlitech/clt/README.md
[ ] fail2ban → FAIL2BAN_0xcyberlitech/clt/README.md
[ ] Apache2 + site CLT → 0xCyberLiTech\CLT\
[ ] Pas de crons métier — crons système auto via apt
```

### pa85 (192.168.1.13)

```
[ ] Créer VM 107, restaurer backup si dispo
[ ] SSH port 2272 — PasswordAuthentication no
[ ] Copier clé publique id_pa85 (Windows) → authorized_keys
[ ] Copier clé publique id_pa85_sync (srv-ngix) → authorized_keys
[ ] UFW → ACLs_UFW_0xcyberlitech/pa85/README.md
[ ] fail2ban → FAIL2BAN_0xcyberlitech/pa85/README.md
[ ] Services → SERVICES_0xcyberlitech/pa85/README.md (exim4 enabled)
[ ] Apache2 + site PA85 → 0xCyberLiTech\PA85\
[ ] Pas de crons métier — crons système auto via apt
```

### Windows 11 — JARVIS (localhost:5000)

```
[ ] Réinstaller Python 3.11 (python.org)
[ ] Réinstaller Ollama (ollama.com) — garder C:\Users\mmsab\.ollama\models\ si le disque survive
[ ] Réinstaller CUDA / drivers RTX 5080

[ ] Tirer les 5 modèles Ollama (ordre recommandé — ~40 GB total) :
    ollama pull phi4:14b                 # 9.1 GB — SOC (défaut)
    ollama pull phi4-reasoning:plus      # 11 GB  — CODE REASONING Pass 1
    ollama pull qwen2.5-coder:14b        # 9.0 GB — CODE + CODE REASONING Pass 2
    ollama pull gemma4:latest            # 9.6 GB — GÉNÉRAL / VOCAL
    ollama pull mxbai-embed-large        # 0.7 GB — RAG embeddings (permanent)

[ ] Installer dépendances Python JARVIS :
    pip install flask flask-limiter requests faster-whisper edge-tts kokoro numpy

[ ] Vérifier configs JARVIS (fichiers JSON — survivent à la réinstall) :
    scripts\jarvis_llm_params.json    ← temp / num_ctx / num_predict par mode
    scripts\jarvis_model.json         ← modèle actif
    scripts\jarvis_dsp_params.json    ← moteur TTS + DSP audio
    scripts\jarvis_prompt_profiles.json ← prompts système par mode

[ ] Lancer JARVIS : cd scripts && python jarvis.py → http://localhost:5000
[ ] Vérifier MCP : scripts\jarvis_mcp_server.py (10 outils)
[ ] Recréer raccourcis bureau : JARVIS Dashboard.lnk + JARVIS - Arrêt.lnk
```

> Si `.ollama\models\` est conservé sur le même disque : les 5 pull sont inutiles, Ollama retrouve les modèles automatiquement.

---

## Commandes de vérification rapide

```bash
# État global — monitoring SOC
ssh -i ~/.ssh/id_nginx -p 2272 root@192.168.1.50 "cd /opt/clt && python3 monitoring_gen.py"

# Vérifier services critiques srv-ngix
ssh -i ~/.ssh/id_nginx -p 2272 root@192.168.1.50 \
  "systemctl is-active nginx crowdsec crowdsec-firewall-bouncer suricata fail2ban"

# Vérifier crons srv-ngix
ssh -i ~/.ssh/id_nginx -p 2272 root@192.168.1.50 "ls /etc/cron.d/"

# Vérifier fail2ban toutes machines
for host in "192.168.1.50:id_nginx" "192.168.1.12:id_clt" "192.168.1.13:id_pa85" "192.168.1.20:id_proxmox"; do
  IP=${host%%:*}; KEY=${host##*:}
  echo "=== $IP ===" && ssh -i ~/.ssh/$KEY -p 2272 root@$IP "fail2ban-client status" 2>/dev/null
done

# Vérifier push Proxmox (crons actifs ?)
ssh -i ~/.ssh/id_proxmox -p 2272 root@192.168.1.20 "ls -la /etc/cron.d/fail2ban-monitor /etc/cron.d/ufw-monitor"
```

---

## Sauvegardes VMs

```
D:\BACKUP-PROXMOX\
├── manual\   ← déclenchées depuis proxmox-backup.ps1 (bureau)
└── auto\     ← tâche planifiée ProxmoxBackup-Samedi23h (samedi 23h)
```

Quota : 300 Go | Rotation : 10 backups par VM | Format : `.vma.zst`
