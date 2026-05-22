# SCHÉMA — ARCHITECTURE IA LOCALE 0xCyberLiTech
<!-- Mise à jour : 2026-05-22 — v9 — routing 4 branches SOC/GÉNÉRAL/CODE/CR · phi4:14b + qwen3:8b · mxbai-embed · score honnête global 88/100 (audit dette complet 2026-05-22) · 31 modules Python (jarvis.py 4814L) · refactor JS terminé jarvis_main.js 7828→148L (−98,1%) -->

---

## VUE D'ENSEMBLE — Les briques et leur rôle

```
┌─────────────────────────────────────────────────────────────────────────┐
│  TOI  →  tu parles ou tu tapes                                          │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
          ┌──────────────▼──────────────┐
          │     BRIQUE 1                │
          │     VSCode + Claude Code    │  ← ton éditeur de code
          │                             │    Claude Code = moi, ici
          │  • tu poses une question    │
          │  • je lis ton code          │
          │  • je réponds en texte      │
          └──────────────┬──────────────┘
                         │ protocole MCP (tuyau de communication)
          ┌──────────────▼──────────────┐
          │     BRIQUE 2                │
          │     MCP SERVER              │  ← pont entre moi et JARVIS
          │     jarvis_mcp_server.py    │
          │                             │
          │  Je peux demander à JARVIS: │
          │  • l'état du SOC            │
          │  • l'historique d'une IP    │
          │  • l'état de l'infra        │
          │  • envoyer un message chat  │
          └──────────────┬──────────────┘
                         │ HTTP vers localhost:5000
          ┌──────────────▼──────────────────────────────────────────────┐
          │     BRIQUE 3 — JARVIS (jarvis.py + soc.py)                  │
          │     Le cerveau central — http://localhost:5000              │
          │                                                             │
          │  ┌──────────────────────────────────────────────────────┐   │
          │  │  PIPELINE api_chat() — ordre strict                  │   │
          │  │                                                      │   │
          │  │  1. BYPASS instantané (zéro LLM)                     │   │
          │  │     heure/date → Python direct                       │   │
          │  │     VM start/stop → SSH Proxmox direct               │   │
          │  │     backup/service restart → SSH direct              │   │
          │  │     lecture fichier → SSH direct                     │   │
          │  │                                                      │   │
          │  │  2. facts_inject  (date, mémoire persistante)        │   │
          │  │                                                      │   │
          │  │  3. RAG conditionnel                                 │   │
          │  │     ≥ 60 chars ou mot-clé doc/knowledge              │   │
          │  │     → skip pour le chat conversationnel              │   │
          │  │                                                      │   │
          │  │  4. SOC inject (si mots-clés sécurité détectés)      │   │
          │  │                                                      │   │
          │  │  5. ROUTING — 3 branches, switch manuel              │   │
          │  │   mode GÉNÉRAL ou VOCAL → gemma4:latest              │   │
          │  │   mode CODE             → qwen2.5-coder:14b          │   │
          │  │   mode SOC (défaut)     → phi4:14b (chaud)           │   │
          │  │   Bouton SOC/GÉNÉRAL/CODE · /api/mode POST           │   │
          │  └──────────────────────────────────────────────────────┘   │
          │                                                             │
          │  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐   │
          │  │  RAG          │  │  SOC ENGINE  │  │  AUTO-ENGINE    │   │
          │  │  (mémoire)    │  │  (sécurité)  │  │  (vigilance)    │   │
          │  │               │  │              │  │                 │   │
          │  │ 599 chunks    │  │ Surveille    │  │ > 500 req/h     │   │
          │  │ indexés       │  │ les logs en  │  │ → ban auto      │   │
          │  │ BM25 + vecteur│  │ temps réel   │  │                 │   │
          │  │ cache 5 min   │  │ Détecte les  │  │ Service down    │   │
          │  │               │  │ menaces      │  │ → restart auto  │   │
          │  │ Skip si court │  │              │  │                 │   │
          │  │ ou hors doc   │  │              │  │ Alerte vocale   │   │
          │  └──────┬────────┘  └──────┬───────┘  └────────┬────────┘   │
          └─────────╪──────────────────╪───────────────────╪────────────┘
                    │                  │                   │
     ┌──────────────▼──┐   ┌───────────▼────────┐   ┌──────▼────────────┐
     │  BRIQUE 4       │   │  BRIQUE 5          │   │  BRIQUE 6         │
     │  OLLAMA         │   │  DONNÉES SOC       │   │  VOIX             │
     │  (les modèles)  │   │  (sécurité live)   │   │  STT + TTS        │
     │                 │   │                    │   │                   │
     │ phi4:14b        │   │ monitoring.json    │   │ STT = oreille     │
     │ 9.1 GB — SOC    │   │ mis à jour         │   │ faster-whisper    │
     │ mode SOC défaut │   │ toutes les 30s     │   │ large-v3-turbo    │
     │ TOUJOURS CHAUD  │   │                    │   │ → transcrit ta    │
     │                 │   │ CrowdSec           │   │   voix en texte   │
     │ gemma4:latest   │   │ fail2ban           │   │                   │
     │ ~9.6 GB         │   │ (sur srv-ngix)     │   │ TTS = voix        │
     │ GÉNÉRAL + VOCAL │   │                    │   │ edge-tts (défaut) │
     │ + VISION native │   │ Historique IP 30j  │   │ → Kokoro (CUDA)   │
     │ (swap au switch)│   │ /api/soc/          │   │ → Piper           │
     │                 │   │ ip-history         │   │ → SAPI5           │
     │ qwen2.5-coder   │   │                    │   │                   │
     │ 9.0 GB — CODE   │   │                    │   │ XTTS v2           │
     │ dev srv-dev-1   │   │                    │   │ 58 voix clonées   │
     │                 │   │                    │   │                   │
     │ mxbai-embed     │   │                    │   │                   │
     │ 0.7 GB — RAG    │   │                    │   │                   │
     │ 1024 dims       │   │                    │   │                   │
     │                 │   │                    │   │                   │
     │ supprimés :     │   │                    │   │                   │
     │ phi4-reasoning  │   │                    │   │                   │
     │ qwen2.5:14b     │   │                    │   │                   │
     │ deepseek-r1:14b │   │                    │   │                   │
     │ llava-phi3      │   │                    │   │                   │
     └─────────────────┘   └────────┬───────────┘   └───────────────────┘
                                    │
          ┌─────────────────────────▼───────────────────────────────────┐
          │     BRIQUE 7 — INFRASTRUCTURE LAN (tes serveurs)            │
          │                                                             │
          │  Proxmox       192.168.1.20  ← hyperviseur, héberge les VMs │
          │    ├── srv-ngix 192.168.1.50  ← nginx, CrowdSec, dashboard  │
          │    ├── clt      192.168.1.12  ← site cybersécurité CLT      │
          │    └── pa85     192.168.1.13  ← site associatif PA85        │
          │                                                             │
          │  JARVIS peut lire l'état de ces serveurs via SSH            │
          │  (lecture seule — 29 commandes dangereuses bloquées)        │
          └─────────────────────────────────────────────────────────────┘
```

---

## ROUTING — Logique de décision

```
  Question reçue
       │
       ▼
  ┌────────────────────────────────────────────────────┐
  │  BYPASS ? (zéro LLM, réponse Python directe)       │
  │  • "quelle heure est-il ?"  → horloge système      │
  │  • "démarre srv-ngix"       → SSH Proxmox          │
  │  • "sauvegarde jarvis"      → script local         │
  │  • "redémarre nginx"        → SSH srv-ngix         │
  │  • "lis /etc/nginx.conf"    → SSH + cat            │
  └─────────────────────┬──────────────────────────────┘
                        │ Non → LLM nécessaire
                        ▼
  ┌────────────────────────────────────────────────────┐
  │  facts_inject — date/heure + mémoire persistante   │
  └─────────────────────┬──────────────────────────────┘
                        │
                        ▼
  ┌────────────────────────────────────────────────────┐
  │  RAG conditionnel                                  │
  │  • requête ≥ 60 chars  OU  mot-clé documentation   │
  │  → injecte chunks pertinents (BM25 + vecteur)      │
  │  • sinon : SKIP (économise 200-500ms)              │
  └─────────────────────┬──────────────────────────────┘
                        │
                        ▼
  ┌────────────────────────────────────────────────────┐
  │  ROUTING — switch manuel (boutons UI SOC/GÉNÉRAL/CODE)
  │                                                    │
  │  mode GÉNÉRAL ou requête VOCAL ?                   │
  │  → gemma4:latest (conversation fluide · vision)    │
  │    swap VRAM unique à la bascule                   │
  │                                                    │
  │  mode CODE ?                                       │
  │  → qwen2.5-coder:14b (dev srv-dev-1 · SCP · exec) │
  └─────────────────────┬──────────────────────────────┘
                        │ Non (mode SOC par défaut)
                        ▼
  ┌────────────────────────────────────────────────────┐
  │  mode SOC → phi4:14b (toujours chaud · 9.1 GB)     │
  │  • SOC keywords → + injection monitoring.json live │
  │  • question texte → phi4 répond directement        │
  │  → /api/mode GET/POST · reset SOC au redémarrage   │
  └────────────────────────────────────────────────────┘

  ⚠ Infra SSH (VMs, disque, services) : routing automatique
    _INFRA_KW → gemma4 · bypass direct → SSH sans LLM
```

---

## VRAM — Stratégie de charge (RTX 5080 16 GB)

```
  ┌─────────────────────────────────────────────────────┐
  │  mode SOC — état permanent (défaut au démarrage)    │
  │                                                     │
  │  phi4:14b              ████████████████   9.1 GB    │
  │  mxbai-embed-large     ▌                  0.7 GB    │
  │                                           ──────    │
  │                                           9.8 GB    │
  └─────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────┐
  │  mode GÉNÉRAL — swap unique à la bascule manuelle   │
  │                                                     │
  │  gemma4:latest   ← switch SOC→GÉNÉRAL  ~9.6 GB      │
  │                                                     │
  │  → swap inévitable (phi4 9.1GB + gemma4 9.6GB > 16) │
  │  → accepté car switch manuel = intention explicite  │
  │  → un seul modèle actif à la fois                   │
  └─────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────┐
  │  mode CODE — swap unique à la bascule manuelle      │
  │                                                     │
  │  qwen2.5-coder:14b ← switch SOC→CODE   9.0 GB       │
  │                                                     │
  │  → swap inévitable · accepté car switch explicite   │
  │  → SSH direct vers srv-dev-1 (192.168.1.21:2272)    │
  └─────────────────────────────────────────────────────┘
```

---

## MÉCANISME MCP — Comment je parle à JARVIS

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  PROTOCOLE MCP (Model Context Protocol)                             │
  │  Inventé par Anthropic — standard ouvert pour connecter des IA      │
  │  à des outils externes                                              │
  └─────────────────────────────────────────────────────────────────────┘

  COMMENT ÇA MARCHE :

  Claude Code (moi)            MCP Server                  JARVIS
  ─────────────────            ──────────                  ──────
       │                           │                          │
       │  1. Tu me poses           │                          │
       │     une question          │                          │
       │                           │                          │
       │  2. Je décide d'utiliser  │                          │
       │     un outil MCP          │                          │
       │                           │                          │
        ──── appel outil ─────────▶             
       │     (stdio JSON-RPC)      │                          │
       │                            ──── HTTP POST ──────────▶
       │                           │     /api/soc/context     │
       │                           │     /api/soc/ip-history  │
       │                           │     /api/chat            │
       │                           │     /api/stats           │
       │                            ◀─── JSON réponse ────────
        ◀─── résultat ─────────────                           
       │                           │                          │
       │  3. J'intègre les données │                          │
       │     dans ma réponse       │                          │
       │     et je te réponds      │                          │


  LES 10 OUTILS MCP disponibles :
  ┌────────────────────────┬──────────────────────────────────────────────┐
  │ jarvis_chat            │ Envoyer un message à JARVIS (chat complet)   │
  │ jarvis_soc_status      │ État temps réel : bans, ThreatScore, alertes │
  │ jarvis_soc_ask         │ Poser une question SOC avec contexte + IP    │
  │                        │ → si IPv4 détectée : historique 30j injecté  │
  │ jarvis_stats           │ Stats système : CPU, GPU, VRAM, RAM          │
  │ jarvis_infra_status    │ État des 4 serveurs SSH                      │
  │ jarvis_proxmox_vms     │ État des VMs Proxmox (qm list live)          │
  │ jarvis_read_file       │ Lire un fichier SSH sur un serveur           │
  │ jarvis_model_switch    │ Changer le modèle Ollama actif               │
  │ jarvis_last_response   │ Derniers échanges de la conversation JARVIS  │
  │ jarvis_code_exec       │ Écrit + SCP + exécute un fichier sur srv-dev-1│
  └────────────────────────┴──────────────────────────────────────────────┘

  QUI LANCE LE MCP SERVER ?
  → Le fichier .mcp.json dans le projet indique à Claude Code :
    "lance jarvis_mcp_server.py avec pythonw au démarrage"
  → Le server tourne en arrière-plan tant que VSCode est ouvert
  → Il écoute les appels de Claude Code via stdin/stdout (stdio)
```

---

## MÉCANISME AGENT IA — Comment un LLM "agit"

```
  ┌─────────────────────────────────────────────────────────────────────┐
  │  Un LLM seul = générateur de texte                                  │
  │  Un LLM + outils = AGENT (peut agir sur le monde)                   │
  └─────────────────────────────────────────────────────────────────────┘

  BOUCLE AGENT (ReAct — Reason + Act) :

  ┌─────────────────────────────────────────────┐
  │                                             │
  │   Question reçue                            │
  │        │                                    │
  │        ▼                                    │
  │   ┌─────────────┐                           │
  │   │  RÉFLÉCHIT  │  "pour répondre j'ai      │
  │   │  (think)    │   besoin de l'état SSH"   │
  │   └──────┬──────┘                           │
  │          │                                  │
  │          ▼                                  │
  │   ┌─────────────┐                           │
  │   │  APPELLE    │  → commande_ssh_ngix()    │
  │   │  UN OUTIL   │    commande_ssh_proxmox() │
  │   └──────┬──────┘    commande_ssh_clt()     │
  │          │            commande_ssh_pa85()   │
  │          ▼                                  │
  │   ┌─────────────┐                           │
  │   │  REÇOIT     │  → résultat SSH réel      │
  │   │  LE RÉSULTAT│    (pas inventé)          │
  │   └──────┬──────┘                           │
  │          │                                  │
  │          ▼                                  │
  │   ┌─────────────┐                           │
  │   │  RÉPOND     │  avec les vraies          │
  │   │  (answer)   │  données                  │
  │   └─────────────┘                           │
  │                                             │
  │   → peut boucler (appeler plusieurs         │
  │     outils)                                 │
  │   → RÈGLE N°3 : 1 seul appel par            │
  │     question                                │
  └─────────────────────────────────────────────┘
```

---

## FLUX COMPLET — De ta voix à la réponse

```
  SCÉNARIO : "quel est l'état de srv-ngix ?"

  TOI (voix, mode SOC)
    │
    ▼ STT faster-whisper large-v3-turbo (CUDA) → texte FR
    │
    ▼ JARVIS reçoit la question (:5000)
    │
    ▼ Bypass ? Non → pipeline LLM (mode SOC actif)
    │
    ▼ facts_inject (date/heure, mémoire)
    │
    ▼ RAG : "srv-ngix" → chunks pertinents injectés
    │
    ▼ ROUTING mode SOC → phi4:14b (déjà chaud)
    │
    ▼ phi4 RÉFLÉCHIT → décide d'appeler commande_ssh_ngix()
    │
    ▼ SSH srv-ngix 192.168.1.50 : "systemctl status nginx crowdsec"
    │
    ▼ Résultat SSH réel reçu par phi4
    │
    ▼ phi4 génère la réponse avec les vraies données
    │
    ▼ SSE streaming → tokens envoyés au navigateur en temps réel
    │
    ▼ TTS edge-tts Antoine → JARVIS te parle
    │
  RÉPONSE VOCALE (phi4 → TTS)


  SCÉNARIO : "analyse les alertes CrowdSec"

  TOI (texte)
    │
    ▼ Bypass ? Non (question complexe)
    │
    ▼ facts_inject + RAG (mot-clé CrowdSec → chunks doc)
    │
    ▼ SOC inject → monitoring.json live injecté dans le contexte
    │
    ▼ ROUTING : SOC keywords → phi4:14b (déjà chaud)
    │
    ▼ phi4 analyse avec raisonnement <think> interne
    │
    ▼ SSE streaming → réponse structurée
    │
  RÉPONSE TEXTE (< 3s si phi4 déjà chaud)


  SCÉNARIO : "quelle heure est-il ?"

  TOI (texte)
    │
    ▼ BYPASS détecté → Python datetime.now() direct
    │
    ▼ "Il est 14h32. Nous sommes le jeudi 7 mai 2026."
    │
  RÉPONSE INSTANTANÉE (< 100ms — zéro LLM)
```

---

## LES 7 BRIQUES — résumé

| Brique | Nom | Rôle en une phrase |
|--------|-----|--------------------|
| 1 | VSCode + Claude Code | Ton éditeur + moi (l'IA de Anthropic) |
| 2 | MCP Server | Pont qui me permet d'interroger JARVIS |
| 3 | JARVIS Flask | Cerveau central qui orchestre tout |
| 4 | Ollama (modèles) | Les IA locales qui génèrent les réponses |
| 5 | Données SOC | L'état en temps réel de ta sécurité |
| 6 | STT / TTS | Les oreilles et la voix de JARVIS |
| 7 | Infrastructure LAN | Tes serveurs physiques et VMs |

---

## LES AGENTS IA — qui fait quoi

| Agent | Modèle | Rôle |
|-------|--------|------|
| **Claude Code** (moi) | Cloud Anthropic | Lire/écrire du code · appeler MCP · raisonner sur ton projet |
| **phi4:14b** | Ollama local — mode SOC | SOC + raisonnement · toujours chaud · 9.1 GB |
| **gemma4:latest** | Ollama local — mode GÉNÉRAL | Conversation fluide + vocal + vision native · ~9.6 GB |
| **qwen2.5-coder:14b** | Ollama local — mode CODE | Dev srv-dev-1 · SCP · exec · 9.0 GB |
| **mxbai-embed-large** | Ollama local — RAG | Convertir texte en vecteurs · 1024 dims · 0.7 GB |

---

## CE QUI EST 100% LOCAL (zéro cloud)

```
  Ollama      → tourne sur ton PC (RTX 5080 CUDA)
  JARVIS      → tourne sur ton PC (localhost:5000)
  STT/TTS     → tourne sur ton PC (CUDA)
  Serveurs    → dans ton LAN (192.168.1.x)
  Données SOC → dans ton LAN
  MCP Server  → tourne sur ton PC (pythonw)

  Seul moi (Claude Code / Anthropic) suis dans le cloud.
  JARVIS ne m'envoie jamais tes données brutes — uniquement
  les escalades que tu valides.
  Principe : JARVIS filtre → Claude voit uniquement l'escalade.
```

---

*SCHEMA-IA-LOCAL.md · 0xCyberLiTech · 2026-05-14 — v8*
