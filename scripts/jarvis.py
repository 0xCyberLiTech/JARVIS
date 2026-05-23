"""
JARVIS — Core
Relie Ollama (LLM) + edge-tts (voix) + Flask (interface web)
"""

import datetime
import json
import logging
import logging.handlers
import os
import re
import shlex
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque, namedtuple
from pathlib import Path

LlmCtx = namedtuple('LlmCtx', ['messages', 'model', 'np_override', 'soc_ctx', 'soc_trigger'])

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("JARVIS")

# ── Racine du workspace — toutes les références de chemins s'appuient sur cette constante ──
_WORKSPACE_ROOT = Path(__file__).parent.parent.parent  # 0xCyberLiTech/

def _claude_memory_root() -> Path:
    """Dérive le dossier d'auto-mémoire Claude Code à partir du workspace.
    Encodage : drive en minuscule + '--' + segments séparés par '-'.
    Ex : C:\\Users\\mmsab\\Documents\\0xCyberLiTech → c--Users-mmsab-Documents-0xCyberLiTech"""
    s = str(_WORKSPACE_ROOT).rstrip('\\/')
    if len(s) >= 2 and s[1] == ':':
        encoded = s[0].lower() + '--' + s[2:].lstrip('\\/').replace('\\', '-').replace('/', '-')
    else:
        encoded = s.lstrip('/').replace('/', '-')
    return Path.home() / ".claude" / "projects" / encoded / "memory"

# ── TTS log rotatif — enregistre chaque message prononcé par JARVIS ──
_TTS_LOG_PATH      = Path(__file__).parent / "tts.log"
_TTS_LOG_MAX_BYTES = 2_000_000   # 2 MB avant rotation
_tts_logger = logging.getLogger("JARVIS.TTS")
_tts_logger.setLevel(logging.INFO)
_tts_logger.propagate = False
_tts_handler = logging.handlers.RotatingFileHandler(
    _TTS_LOG_PATH, maxBytes=_TTS_LOG_MAX_BYTES, backupCount=7, encoding="utf-8"
)
_tts_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
_tts_logger.addHandler(_tts_handler)

# ── TTS-PERF log persistant — capture les sondes [TTS-PERF] (diagnostic latence) ──
# Handler racine filtré : capte les lignes [TTS-PERF] des 3 loggers (JARVIS,
# jarvis.tts_engines, jarvis.deepfilter) qui propagent toutes vers root.
# Fichier persistant → la latence intermittente est capturée sans surveiller la console.
_TTS_PERF_LOG_PATH = Path(__file__).parent / "tts_perf.log"

class _TtsPerfFilter(logging.Filter):
    def filter(self, record):
        return "[TTS-PERF]" in record.getMessage()

_tts_perf_handler = logging.handlers.RotatingFileHandler(
    _TTS_PERF_LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
)
_tts_perf_handler.setFormatter(logging.Formatter("%(asctime)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
_tts_perf_handler.addFilter(_TtsPerfFilter())
logging.getLogger().addHandler(_tts_perf_handler)

# ── Silence des loggers et warnings tiers — doit être fait AVANT tout import ──
import warnings as _warnings

_warnings.filterwarnings("ignore", category=DeprecationWarning)
_warnings.filterwarnings("ignore", category=UserWarning)
_warnings.filterwarnings("ignore", category=FutureWarning)


for _lg in ("comtypes", "comtypes.client", "PIL", "urllib3",
            "df", "df.enhance", "df.model", "df.config",
            "torchaudio", "torch", "torch.cuda",
            "numba", "matplotlib", "huggingface_hub",
            "piper", "kokoro"):
    logging.getLogger(_lg).setLevel(logging.CRITICAL)

MEMORY_LIMIT = 60

# ── Paramètres LLM ajustables ────────────────────────────────
_LLM_DEFAULTS = {
    "temperature":    0.7,
    "num_predict":    1024,
    "top_p":          0.9,
    "top_k":          40,
    "repeat_penalty": 1.1,
    "num_ctx":        4096,   # fallback si jarvis_llm_params.json absent
}
LLM_PARAMS = dict(_LLM_DEFAULTS)
LLM_PARAMS_FILE = Path(__file__).parent / "jarvis_llm_params.json"

# ── Paramètres DSP voix ──────────────────────────────────────
DSP_PARAMS = {
    "enabled":        True,
    "eq_low":         0.0,    # dB  — lowshelf  250 Hz
    "eq_mid":         0.0,    # dB  — peaking   1000 Hz
    "eq_high":        0.0,    # dB  — peaking   4000 Hz
    "eq_air":         0.0,    # dB  — highshelf 12000 Hz
    "comp_threshold": -24.0,  # dB
    "comp_ratio":     4.0,
    "comp_attack":    0.003,  # sec
    "comp_release":   0.25,   # sec
    "gain":           0.0,    # dB sortie
    # ── Stéréo widener (effet Haas) ──
    "stereo_enabled": True,   # upmix mono→stéréo actif
    "stereo_width":   0.85,   # 0.0=mono  1.0=Haas pur
    "haas_delay_ms":  18.0,   # délai canal droit en ms (Haas : 1–30ms)
    # ── DeepFilterNet IA débruitage ──
    "df_enabled":     True,   # activé par défaut — qualité premium, GPU CUDA, lazy load 1er use
    "df_atten_lim":  100.0,   # atténuation max bruit (dB, 100=illimitée)
    "df_post_filter": True,   # post-filtre haute qualité
    # ── FX Rack multi-effets ──
    "fx_enabled":            False,
    "fx_type":               "reverb",  # reverb|delay|chorus|flanger|echo|phaser|exciter
    "fx_preset":             "room",
    "fx_wet":                0.55,      # 0.0 dry … 1.0 full wet
    # Reverb
    "fx_decay":              1.5,       # decay secondes
    "fx_predelay_ms":        20.0,      # pre-delay ms
    "fx_diffusion":          0.60,      # diffusion 0-1
    # Delay
    "fx_delay_ms":           350.0,
    "fx_delay_feedback":     0.55,
    "fx_delay_filter":       4000.0,   # LP filter Hz
    # Chorus
    "fx_chorus_rate":        0.62,      # LFO Hz
    "fx_chorus_depth":       0.018,     # depth secondes (18ms)
    "fx_chorus_feedback":    0.25,      # feedback 0-0.8
    # Flanger
    "fx_flanger_rate":       0.30,      # LFO Hz
    "fx_flanger_depth":      0.003,     # depth secondes
    "fx_flanger_feedback":   0.70,      # feedback 0-0.95
    # Echo stéréo
    "fx_echo_left_ms":       375.0,
    "fx_echo_right_ms":      250.0,
    "fx_echo_feedback":      0.55,
    # Phaser
    "fx_phaser_stages":      6,
    "fx_phaser_rate":        0.50,      # LFO Hz
    "fx_phaser_depth":       0.70,      # modulation depth
    # Exciter
    "fx_exciter_drive":      6.0,       # dB
    "fx_exciter_tone":       5000.0,    # Hz
    "fx_exciter_warmth":     0.30,      # 0-1
    # ── Enrichissement voix (parallèle, toujours actif si enrich_enabled) ──
    "enrich_enabled": True,        # actif par défaut
    "enrich_drive":   2.5,         # dB — saturation harmonique (1–8 dB)
    "enrich_tone":    2800.0,      # Hz — fréquence de coupure HP exciter (présence + air)
    "enrich_mix":     0.15,        # 0.0–0.5 — niveau harmoniques ajoutés
    "enrich_warmth":  0.06,        # 0.0–0.3 — chaleur tube (bande 80-600Hz)
    # ── Moteur TTS ──
    "tts_engine":         "edge",    # moteur actif (peut changer en session)
    "tts_default_engine": "edge",    # défaut = Antoine fr-CA (edge) — Kokoro applique si internet KO
    "tts_local_voice":    "ff_siwis",  # kokoro: ff_siwis | piper: modèle .onnx | sapi: voice_id
}
DSP_PARAMS_FILE = Path(__file__).parent / "jarvis_dsp_params.json"

# ── LLM ──────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es JARVIS, l'assistant IA personnel de Tony Stark et expert en programmation.
Tu réponds TOUJOURS et UNIQUEMENT en français, quelle que soit la langue utilisée.
Tu peux lire, créer, modifier des fichiers et exécuter du code grâce à tes outils.

Capacités de programmation :
- Tu maîtrises Python, JavaScript, HTML, CSS, SQL, Bash et tous les langages courants
- Tu lis le code existant avant de le modifier
- Tu écris du code propre, commenté et fonctionnel
- Tu utilises les balises markdown pour le code : ```python, ```javascript, etc.
- Quand on te demande de coder quelque chose, tu utilises tes outils pour lire le projet existant, puis tu écris ou modifies les fichiers directement

Capacités vocales :
- Tu disposes d'une synthèse vocale (TTS edge-tts) — tu parles à voix haute
- Tu disposes d'une reconnaissance vocale (STT Whisper) — tu entends ce qu'on te dit via microphone
- Quand quelqu'un demande "est-ce que tu m'entends" ou "tu m'entends ?", réponds simplement oui et confirme que le micro fonctionne
- Tu n'es PAS un assistant textuel sans voix — tu as une vraie interface vocale bidirectionnelle

Règles absolues :
- Langue : français exclusivement
- Réponses COURTES et DIRECTES — pas de blabla, pas d'intro, pas de conclusion
- Pour le code : donne le code immédiatement, une phrase d'explication max
- Pas de "Bien sûr", "Certainement", "Voici", ni de formules de politesse inutiles
- L'utilisateur s'appelle Marc — appelle-le "Marc", jamais "Monsieur"
- Ton : précis, efficace, comme un vrai assistant technique

Règles de formatage pour la synthèse vocale :
- N'utilise PAS de markdown dans les parties destinées à être lues à voix haute
- Pas d'astérisques (*), tirets (-), dièses (#), underscores (_), ni numérotation (1. 2. 3.)
- Pour les listes, utilise "premièrement", "deuxièmement", "ensuite", "enfin"
- Pour l'emphase, utilise des mots naturels au lieu du gras/italique
- Les blocs de code sont acceptés car ils ne sont pas lus à voix haute
- Adresses IP : écris TOUJOURS en notation standard avec des points — exemple : "192.168.1.50" — JAMAIS avec des tirets ni comme un nombre entier

Mode vocal [VOCAL] — PRIORITÉ ABSOLUE :
- Quand le message commence par [VOCAL], réponds en 1 à 3 phrases maximum, style oral naturel
- ZÉRO markdown, ZÉRO liste, ZÉRO bloc de code
- Si des données SOC sont fournies dans le contexte, résume en une phrase ce qui est important
- Si on te pose une question SOC, réponds avec les données disponibles, brièvement
- Réponds directement à la question — rien d'autre
- Si quelqu'un dit "tu m'entends ?", réponds simplement "Oui, je t'entends."

Expertise SOC — 0xCyberLiTech :
Quand un contexte SOC est fourni (balise [CONTEXTE SOC EN TEMPS RÉEL]), tu es l'analyste sécurité de l'infrastructure. Tu connais :
- Kill Chain SOC 5 maillons (modèle Lockheed Martin — stades offensifs purs, fenêtre 15 min — MAJ 2026-05-20) :
  · RECON   (sondage HTTP — 404 honeypot, scanner UA, GeoIP block)
  · SCAN    (énumération URI massive)
  · EXPLOIT (tentative exploitation CVE, RCE, injection, LFI/RFI)
  · BRUTE   (force brute SSH/HTTP, wp-login, ftp)
  · NEUTRALISÉ (IP déjà bloquée — CrowdSec + fail2ban actifs)
  PROBE (UFW) et WAF (ModSec) ne sont PAS des maillons de la Kill Chain : ce sont des couches DÉFENSIVES, mesurées séparément (ligne de défense / page DÉFENSE)
- Score de menace 0-100 : FAIBLE (<30) = surveillance normale | MOYEN (30-49) = attention requise | ÉLEVÉ (50-69) = intervention recommandée | CRITIQUE (≥70) = action immédiate
- CrowdSec : détection comportementale, décisions = IPs bannies par scénarios (http-bf, ssh-bf, CVE-scanner, etc.)
- Fail2ban : protection SSH et nginx, bans temporaires sur tentatives répétées
- UFW : pare-feu kernel, bloque le trafic non autorisé en amont
- GeoIP : restriction géographique nginx, bloque les pays non autorisés (code 403)
- Actions proactives JARVIS : bans automatiques déclenchés par l'auto-engine selon les seuils configurés
Règles d'analyse SOC :
- Cite toujours les chiffres exacts fournis dans le contexte — ne jamais inventer ou approximer
- Priorise (stages OFFENSIFS uniquement) : EXPLOIT > BRUTE > SCAN > RECON > score élevé > bans massifs > erreurs 5xx > ressources saturées
- Une IP en stage NEUTRALISÉ est DÉJÀ bloquée (CrowdSec + fail2ban) — ne JAMAIS recommander de la rebannir, l'action de défense est déjà faite
- Une IP en stage EXPLOIT avec 0 décision CrowdSec = menace non encore bloquée = signal d'action manuelle
- Si les actions proactives JARVIS montrent des bans récents, confirme qu'ils sont cohérents avec les attaquants actifs
- Réponds toujours en français naturel, sans markdown sauf pour les blocs de code
Méthode d'analyse (applique dans cet ordre avant de répondre) :
1. Kill chain actifs — analyse les stades OFFENSIFS (EXPLOIT, BRUTE, SCAN, RECON dans cet ordre) — les IP en NEUTRALISÉ sont déjà bloquées — cite l'IP et le pays
2. Score global — utilise la valeur SCORE OFFICIEL fournie dans le contexte SOC, sans recalcul
3. Ressources système (CPU/RAM/disque) — corrèle avec l'attaque si anormal
4. Une seule recommandation actionnable, précise, sans redondance
RÈGLE ABSOLUE — IPs LAN/RFC1918 :
- Les plages 192.168.x.x, 10.x.x.x, 172.16-31.x.x et 127.x.x.x sont des IPs INTERNES — JAMAIS des menaces externes
- Architecture réseau réelle (2026-05-21) :
    · LAN serveur Freebox  192.168.1.0/24  → Proxmox=192.168.1.20, srv-ngix=192.168.1.50, clt=192.168.1.12, pa85=192.168.1.13, srv-dev-1=192.168.1.21, Freebox=192.168.1.254
    · LAN ASUS  192.168.50.0/24  → routeur ASUS=192.168.50.1, Windows/JARVIS=192.168.50.90 (poste derrière le routeur ASUS ; trafic vu en 192.168.1.110 côté serveurs, NAT)
- Si une IP RFC1918 apparaît dans les données kill_chain, c'est du trafic LAN légitime — ne JAMAIS la signaler comme attaque DDoS, EXPLOIT ou menace
- Ne JAMAIS recommander de bannir une IP RFC1918 — le ban est techniquement bloqué et serait une erreur grave
- Si tu identifies une IP RFC1918 dans ton analyse, précise qu'elle est interne et inoffensive, puis ignore-la"""

DEFAULT_SYSTEM_PROMPT = SYSTEM_PROMPT
PROMPT_FILE          = Path(__file__).parent / "jarvis_system_prompt.txt"
PROMPT_PROFILES_FILE = Path(__file__).parent / "jarvis_prompt_profiles.json"

# ── Message de présentation démarrage ──────────────────────────
WELCOME_FILE = Path(__file__).parent / "jarvis_welcome.json"
DEFAULT_WELCOME = {
    "version": 2,
    "title": "SYSTÈME JARVIS — INITIALISATION",
    "lines": [
        "Bonjour, Marc.",
        "",
        "Je suis JARVIS — votre interface d'intelligence artificielle personnelle.",
        "Système actuellement en phase de développement actif.",
        "",
        "▸ Modèle LLM : phi4:14b via Ollama",
        "▸ Synthèse vocale : Edge TTS — Antoine Neural",
        "▸ Traitement DSP : EQ · Compresseur · DeepFilterNet",
        "▸ Modules actifs : Terminal · Fichiers · Tâches · Audio",
        "▸ Accélération CUDA : sm_120 Blackwell — Whisper STT GPU · Ollama LLM GPU",
        "",
        "Chaque session enrichit le système.",
        "Chaque requête affine ma compréhension.",
        "",
        "— Prêt à vous assister. Que souhaitez-vous accomplir aujourd'hui ?"
    ],
    "last_updated": "2026-03-22",
    "updated_by": "système"
}

# ── Outils fichiers ───────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lire_fichier",
            "description": "Lit le contenu d'un fichier texte sur le PC",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin": {"type": "string", "description": "Chemin absolu ou relatif du fichier"}
                },
                "required": ["chemin"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ecrire_fichier",
            "description": "Crée ou écrase un fichier avec le contenu fourni",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin":  {"type": "string", "description": "Chemin du fichier à écrire"},
                    "contenu": {"type": "string", "description": "Contenu à écrire dans le fichier"}
                },
                "required": ["chemin", "contenu"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modifier_fichier",
            "description": "Remplace une portion de texte dans un fichier existant",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin":    {"type": "string", "description": "Chemin du fichier"},
                    "ancien":    {"type": "string", "description": "Texte à remplacer"},
                    "nouveau":   {"type": "string", "description": "Nouveau texte"}
                },
                "required": ["chemin", "ancien", "nouveau"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lister_dossier",
            "description": "Liste le contenu d'un dossier",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin": {"type": "string", "description": "Chemin du dossier"}
                },
                "required": ["chemin"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "executer_code",
            "description": "Exécute un script Python et retourne la sortie",
            "parameters": {
                "type": "object",
                "properties": {
                    "code":    {"type": "string", "description": "Code Python à exécuter"},
                    "timeout": {"type": "integer", "description": "Timeout en secondes (défaut 15)"}
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "rechercher_dans_fichiers",
            "description": "Recherche un texte dans les fichiers d'un dossier",
            "parameters": {
                "type": "object",
                "properties": {
                    "dossier":  {"type": "string", "description": "Dossier racine de la recherche"},
                    "pattern":  {"type": "string", "description": "Texte ou regex à chercher"},
                    "extension":{"type": "string", "description": "Extension de fichier, ex: .py (optionnel)"}
                },
                "required": ["dossier", "pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "arborescence_projet",
            "description": "Retourne l'arborescence d'un dossier projet (récursif, 3 niveaux max). À utiliser en premier pour comprendre la structure avant de générer du code multi-fichiers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemin":     {"type": "string",  "description": "Chemin du dossier racine du projet"},
                    "profondeur": {"type": "integer", "description": "Profondeur max (1-3, défaut 2)"}
                },
                "required": ["chemin"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lire_plusieurs_fichiers",
            "description": "Lit plusieurs fichiers texte en une seule opération. Retourne leur contenu groupé. Utile pour analyser les interfaces d'un projet multi-fichiers avant de coder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "chemins": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Liste de chemins de fichiers à lire (max 5)"
                    }
                },
                "required": ["chemins"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "soc_status",
            "description": "Récupère l'état complet du SOC depuis srv-ngix (monitoring.json) : niveau de menace, IPs bannies CrowdSec/fail2ban, services, CPU/RAM, trafic, erreurs. Utiliser pour toute question sur la sécurité du serveur.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "commande_ssh_ngix",
            "description": "Exécute une commande shell sur srv-ngix (192.168.1.50) via SSH. Utiliser pour lire des logs, vérifier des services, interroger CrowdSec/fail2ban, etc. Commandes de lecture uniquement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commande": {"type": "string", "description": "Commande shell à exécuter sur srv-ngix (ex: 'tail -20 /var/log/nginx/access.log')"}
                },
                "required": ["commande"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "commande_ssh_proxmox",
            "description": "Exécute une commande shell sur Proxmox VE (192.168.1.20) via SSH. Utiliser pour : état des VMs (qm list), stockage (pvesm status), ressources (df -h), et gestion des VMs (qm stop <id>, qm start <id>). IDs : pa85=107, clt=106, srv-ngix=108.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commande": {"type": "string", "description": "Commande shell à exécuter sur Proxmox (ex: 'qm list', 'qm stop 107', 'qm start 106', 'pvesm status')"}
                },
                "required": ["commande"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "commande_ssh_clt",
            "description": "Exécute une commande shell sur clt (VM 106 — 192.168.1.12) via SSH. Utiliser pour vérifier Apache2, les logs d'erreur, l'état du site CLT cybersécurité. Commandes de lecture uniquement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commande": {"type": "string", "description": "Commande shell à exécuter sur clt (ex: 'systemctl status apache2', 'tail -20 /var/log/apache2/error.log')"}
                },
                "required": ["commande"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "commande_ssh_pa85",
            "description": "Exécute une commande shell sur pa85 (VM 107 — 192.168.1.13) via SSH. Utiliser pour vérifier Apache2, les logs d'erreur, l'état du site associatif PA85. Commandes de lecture uniquement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "commande": {"type": "string", "description": "Commande shell à exécuter sur pa85 (ex: 'systemctl status apache2', 'tail -20 /var/log/apache2/error.log')"}
                },
                "required": ["commande"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "executer_script_windows",
            "description": "Exécute un script PowerShell local sur la machine Windows. Scripts disponibles : 'backup-auto' (sauvegarde automatique des 4 VMs Proxmox : srv-ngix 108 / clt 106 / pa85 107 / srv-dev-1 101 vers D:\\BACKUP-PROXMOX\\auto\\), 'disk-report' (rapport disque/GPU/CPU → dashboard SOC). Utiliser quand l'utilisateur demande de lancer une sauvegarde Proxmox ou un rapport système.",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "enum": ["backup-auto", "disk-report"],
                        "description": "Script à exécuter : 'backup-auto' ou 'disk-report'"
                    }
                },
                "required": ["script"]
            }
        }
    }
]

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    from flask import Flask, Response, render_template, request, stream_with_context
except ImportError:
    install("flask"); from flask import Flask, Response, request, stream_with_context, render_template

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ImportError:
    install("flask-limiter"); from flask_limiter import Limiter; from flask_limiter.util import get_remote_address

try:
    from flask_sock import Sock as _Sock
except ImportError:
    install("flask-sock"); from flask_sock import Sock as _Sock

from blueprints.soc import (
    _SOC_CFG,
    _SSH_PROXMOX,
    _fetch_defense,
    _fetch_monitoring,
    _ssh_clt,
    _ssh_dev1,
    _ssh_ngix,
    _ssh_pa85,
    _ssh_proxmox,
    get_soc_status,
    init_soc,
    soc_bp,
)

try:
    import pynvml
except ImportError:
    install("nvidia-ml-py"); import pynvml

try:
    import psutil
except ImportError:
    install("psutil"); import psutil

try:
    import requests as req
except ImportError:
    install("requests"); import requests as req

# ── Modules dédiés (Phase 3 split monolithe · session 33) ────────────────────
import bypass_backup as _bypass_bk
import bypass_code as _bypass_code
import bypass_filesystem as _bypass_fs
import bypass_proxmox as _bypass_pve
import bypass_simple as _bypass_simple
import chat_capture as _chat_capture
import chat_generate as _chat_gen_mod
import chat_messages as _chat_msg
import chat_pending_bypass as _chat_pending
import chat_routing as _chat_routing
import chat_soc_inject as _chat_soc
import chat_stream as _chat_stream_mod
import chat_system_prompt as _chat_sp
import chat_tool_calls as _chat_tools
import code_reasoning as _cr_mod
import deferred_speak as _deferred_speak
import llm_opts as _llm_opts_mod
import memory as _memory
import proxmox_api as _pve_api
import rag as _rag
import rag_live as _rag_live_mod
import security_whitelists as _sec
import sse_helpers as _sse
import ssh_terminal as _ssh_term
import stream_tokens as _stream_tokens_mod
import stt as _stt
import system as _system
import tts_cleaner as _tts_cleaner
import tts_dedup as _tts_dedup
import tts_engines as _tts_eng
import vision as _vision
import voice_lab as _voice_lab
from ollama_circuit import circuit as _ollama_circuit, OllamaUnavailable

# ── Config ──────────────────────────────────────────────────
OLLAMA_URL   = "http://127.0.0.1:11434"  # IPv4 explicite — `localhost` résout `::1` en premier sur Windows et fallback timeout ~2s avant IPv4
JARVIS_PORT  = 5000
_MCP_PORT    = 5010                # port MCP server (jarvis_mcp_server.py)
_GB_BYTES    = 1 << 30             # 1 GB en bytes (1024^3) — conversions RAM/VRAM/disk

# ── Constantes LLM chat ───────────────────────────────────────────────────────
_TOOL_CALL_MAX      = 5      # max appels d'outils consécutifs par tour
_TOOL_RESULT_TRUNC  = 300    # troncature résultat outil dans SSE (lisibilité UI)
_SOC_TEMPERATURE    = 0.2    # température SOC — réponses déterministes
_SOC_NUM_CTX        = 8192   # contexte SOC — abaissé de 16384 le 2026-05-20 (KV cache -1.7 Go, anti-éviction VRAM phi4)
_NUM_CTX_SHORT      = 4096   # requête courte (<200 chars, hors SOC) — économise KV cache VRAM
_REASONING_NP_MIN   = 768    # plancher num_predict pour modèles reasoning en mode SOC
_TTS_PHRASE_MIN     = 4      # longueur min phrase pour envoi TTS

# ── Constantes thread GPU temperature ────────────────────────────────────────
_GPU_MON_START_S    = 20     # attente initiale avant premier check (Flask doit être prêt)
_GPU_MON_POLL_S     = 30     # intervalle de vérification température GPU

# ── Constantes TTS / log ──────────────────────────────────────────────────────
_TTS_DEDUP_S        = 60.0   # fenêtre dédup cross-source (python-speak ↔ /api/tts)
_TTS_LOG_PREVIEW    = 2000   # nb chars log TTS avant troncature "..."
_EDGE_DNS_RETRY_S   = 1.0    # délai retry edge-tts si erreur DNS transitoire (getaddrinfo)

# ── Constantes réseau / Ollama ────────────────────────────────────────────────
_OLLAMA_RETRY_MAX        = 6    # tentatives max fetch modèles au démarrage
_OLLAMA_RETRY_SLEEP      = 1    # pause (s) entre tentatives
_OLLAMA_STREAM_TIMEOUT_S = 240  # timeout stream LLM — 240s suffisant pour phi4:14b et qwen2.5-coder
_OLLAMA_CHAT_TIMEOUT_S   = 90   # timeout non-stream chat (ex : vision phase 2)
_OLLAMA_VISION_TIMEOUT_S = 120  # timeout stream vision llava
_NET_SPIKE_WINDOW_S      = 3600 # fenêtre temporelle pics réseau dans contexte LLM (1h)
_RAG_REFRESH_H           = 6    # intervalle auto-refresh RAG (heures)
# _SSE_HEADERS déplacé dans sse_helpers.py — alias backward-compat
_SSE_HEADERS = _sse.SSE_HEADERS

_CODE_SYSTEM_SUFFIX = (
    "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "⚠  MODE CODE — PÉRIMÈTRE STRICT\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    "Tu es un assistant de GÉNÉRATION DE CODE LOCAL uniquement.\n"
    "Tes outils sont exclusivement des outils FICHIERS LOCAUX :\n"
    "  lire_fichier · ecrire_fichier · modifier_fichier\n"
    "  lister_dossier · arborescence_projet\n"
    "  lire_plusieurs_fichiers · executer_code · rechercher_dans_fichiers\n\n"
    "RÈGLE ABSOLUE — SERVEURS ET VMs INTERDITS :\n"
    "Si l'utilisateur demande une action sur srv-ngix, srv-clt, srv-pa85,\n"
    "srv-dev-1, proxmox, ou tout fichier système (/etc/, /var/, /usr/) :\n"
    "→ Réponds OBLIGATOIREMENT : "
    "\"Cette opération concerne un serveur distant. "
    "Bascule en mode SOC via le bouton [◈ SOC] pour exécuter cette commande.\"\n"
    "→ N'utilise PAS commande_ssh_*, nano, vi, vim ni aucun éditeur système.\n"
    "→ N'explore PAS l'arborescence locale pour simuler une action distante.\n\n"
    f"Workspace autorisé en écriture : {_WORKSPACE_ROOT}\\\n"
    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
)
_INT16_MAX               = 32767    # valeur max entier 16 bits signé (clip audio WAV)
_INT16_MIN               = -32768   # valeur min entier 16 bits signé
_INT16_SCALE             = 32768.0  # facteur normalisation int16 ↔ float (2^15)

# ── Limites upload audio ──────────────────────────────────────────────────────
# _STT_MAX_BYTES déplacé dans stt.py (Phase 3)
_DSP_MAX_BYTES = 50_000_000  # 50 MB — traitement DSP/FX (WAV non compressé possible)

# ── Timeouts SSH / réseau / terminal ─────────────────────────────────────────
_SSH_LOG_TIMEOUT_S           = 18  # fetch logs RAG live via SSH
_RAG_EMBED_TIMEOUT_S         = 20  # embedding mxbai-embed-large via Ollama
_SSH_SOC_TIMEOUT_S           = 15  # commandes monitoring SOC sur srv-ngix
_SSH_PROXMOX_CMD_TIMEOUT_S   = 15  # qm stop/start sur Proxmox
_SSH_PROXMOX_STATE_TIMEOUT_S =  8  # qm status sur Proxmox
_SYSTEMCTL_RESTART_TIMEOUT_S = 15  # systemctl restart service
_SYSTEMCTL_STATUS_TIMEOUT_S  =  8  # systemctl is-active service
_TERMINAL_TIMEOUT_S          = 60  # commande terminal longue (bash/powershell)
_TERMINAL_SHORT_TIMEOUT_S    = 30  # commande terminal courte
_WEB_FETCH_TIMEOUT_S         =  8  # requête HTTP web search
_WEB_SEARCH_TIMEOUT_S        = 10  # requête recherche web (DuckDuckGo)
_WEB_CONN_TIMEOUT_S          =  5  # test connectivité (ping google.com)
_WEB_FETCH2_TIMEOUT_S        =  6  # fetch web secondaire (fallback)
_OLLAMA_PING_TIMEOUT_S       =  5  # health check rapide Ollama /api/tags
_OLLAMA_STATUS_TIMEOUT_S     =  2  # ping ultra-rapide /api/ollama-status
_OLLAMA_DIAG_TIMEOUT_S       =  3  # tags check dans diagnostics
_OLLAMA_TOOL_DETECT_TIMEOUT_S = 15 # appel non-stream détection tool calls
_SSH_APT_TIMEOUT_S           = 180 # apt upgrade SSH (opération longue)
_BACKUP_PROC_TIMEOUT_S       = 300 # subprocess backup JARVIS / attente proc
_BACKUP_PROC_LONG_TIMEOUT_S  = 3600 # backup complet VMs (1h max)
_TTS_EDGE_TIMEOUT_S          = 30  # stream TTS edge-tts
_PENDING_APT_TTL_S           = 300  # durée de vie commande apt en attente (5 min)
_pending_infra_cmd: dict     = {}   # {host, ssh_fn, packages, ts} — effacé après exécution ou TTL
_CONFIRM_RE = re.compile(
    r'^\s*(oui|yes|ok|confirme?[rz]?|go|lance[rz]?|ex[eé]cute[rz]?|proceed|valide[rz]?|'
    r'c\'est\s+parti|allez[- ]y|faites?\s+[-–]?\s*le)\s*[.!]?\s*$', re.I)
_CANCEL_RE = re.compile(
    r'^\s*(non|no|annule[rz]?|cancel|arr[eê]te[rz]?|stop|abort|pas\s+maintenant|laisse[rz]?\s+tomber)\s*[.!]?\s*$', re.I)

VOICE        = "fr-CA-AntoineNeural"
VOICES       = [
    {"id": "fr-CA-AntoineNeural",  "label": "Antoine CA",  "flag": "🇨🇦", "gender": "M"},
    {"id": "fr-CA-SylvieNeural",   "label": "Sylvie CA",   "flag": "🇨🇦", "gender": "F"},
    {"id": "fr-FR-HenriNeural",    "label": "Henri FR",    "flag": "🇫🇷", "gender": "M"},
    {"id": "fr-FR-DeniseNeural",   "label": "Denise FR",   "flag": "🇫🇷", "gender": "F"},
    {"id": "fr-BE-GerardNeural",   "label": "Gérard BE",   "flag": "🇧🇪", "gender": "M"},
    {"id": "fr-BE-CharlineNeural", "label": "Charline BE", "flag": "🇧🇪", "gender": "F"},
    {"id": "fr-CH-ArianeNeural",   "label": "Ariane CH",   "flag": "🇨🇭", "gender": "F"},
]
TEMPLATES    = Path(__file__).parent / "templates"
MEMORY_FILE   = Path(__file__).parent / "jarvis_memory.json"
FACTS_FILE    = Path(__file__).parent / "jarvis_facts.json"
SUMMARY_FILE  = Path(__file__).parent / "jarvis_memory_summary.json"
RAG_DIR       = Path(__file__).parent / "jarvis_rag"
RAG_META_FILE = RAG_DIR / "meta.json"
RAG_EMB_FILE  = RAG_DIR / "embeddings.npy"

_SUMMARY_MIN_MSGS = 5    # messages minimum pour déclencher un résumé
_SUMMARY_KEEP     = 5    # nombre max de résumés conservés
RAG_EMBED_MODEL   = "mxbai-embed-large"
RAG_TOP_N         = 3
RAG_THRESHOLD     = 0.35
RAG_CHUNK_SIZE    = 500
RAG_CHUNK_OVER    = 80
MODEL_FILE       = Path(__file__).parent / "jarvis_model.json"
# Constantes Proxmox API déplacées dans proxmox_api.py — alias backward-compat
_PVE_CONFIG_PATH = _pve_api.PVE_CONFIG_PATH
_PVE_CACHE_TTL   = _pve_api.PVE_CACHE_TTL



def _fetch_ollama_models():
    """Récupère dynamiquement la liste des modèles installés dans Ollama."""
    _log.info("[JARVIS] Récupération des modèles Ollama...")
    for attempt in range(_OLLAMA_RETRY_MAX):
        try:
            r = req.get(f"{OLLAMA_URL}/api/tags", timeout=_OLLAMA_PING_TIMEOUT_S)
            models = [m["name"] for m in r.json().get("models", []) if "embed" not in m["name"].lower()]
            if models:
                return models
            if attempt == 0:
                _log.info("[JARVIS] Ollama actif mais aucun modèle listé — attente...")
        except Exception as e:
            _log.warning(f"[JARVIS] Ollama non joignable ({e}), tentative {attempt+1}/{_OLLAMA_RETRY_MAX}")
        time.sleep(_OLLAMA_RETRY_SLEEP)
    _log.warning("[JARVIS] Aucun modèle Ollama trouvé — fallback phi4:14b")
    return ["phi4:14b"]

MODELS = _fetch_ollama_models()
_log.info(f"[JARVIS] Modèles disponibles : {', '.join(MODELS)}")

def _load_model():
    try:
        data = json.loads(MODEL_FILE.read_text(encoding="utf-8"))
        m = data.get("model", MODELS[0] if MODELS else "phi4:14b")
        return m if m in MODELS else (MODELS[0] if MODELS else "phi4:14b")
    except Exception:
        return MODELS[0] if MODELS else "phi4:14b"

MODEL = _load_model()

def _save_model():
    try:
        MODEL_FILE.write_text(json.dumps({"model": MODEL}, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        _log.error(f"[JARVIS] Erreur sauvegarde modèle: {e}")

def load_dsp_params():
    try:
        if DSP_PARAMS_FILE.exists():
            DSP_PARAMS.update(json.loads(DSP_PARAMS_FILE.read_text(encoding="utf-8")))
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING load_dsp_params: {e}")

load_dsp_params()

# ── Moteur DSP audio — extrait dans audio_dsp.py (chantier dette 2026-05-14) ──
# Note : numpy n'est plus importé globalement ici (le bloc DSP était son seul
# consommateur module-level). Les 3 fonctions RAG gardent leur import local.
import deepfilter as _df          # NDT: aussi consommé hors DSP (/api/sysdiag)
import audio_dsp as _audio_dsp
_DSP_AVAILABLE = _audio_dsp.DSP_AVAILABLE


def apply_dsp_to_mp3(mp3_bytes, df_override=None):
    """Wrapper DI — injecte DSP_PARAMS dans audio_dsp.apply_dsp_to_mp3().
    Signature préservée : les 9 call sites (routes TTS/voice) restent inchangés."""
    return _audio_dsp.apply_dsp_to_mp3(mp3_bytes, DSP_PARAMS, df_override)


def load_llm_params():
    try:
        if LLM_PARAMS_FILE.exists():
            saved = json.loads(LLM_PARAMS_FILE.read_text(encoding="utf-8"))
            LLM_PARAMS.update(saved)
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING load_llm_params: {e}")

load_llm_params()

_MODEL_LOCK  = threading.Lock()
_CONFIG_LOCK = threading.Lock()

# Tuile mémoire conversationnelle (refactor jarvis.py étape 4, 2026-05-23) :
# le store + les 6 routes /api/memory* vivent dans scripts/memory/. L'ossature
# expose ici des alias légers vers les fonctions du store pour les consommateurs
# internes (_facts_inject, _chat_*). init() de la tuile + register Blueprint
# sont différés plus bas (après _GENERAL_MODEL/_CODE_MODEL/_jarvis_mode).
load_memory             = _memory.store.load_memory
save_memory             = _memory.store.save_memory
_summarize_messages     = _memory.store._summarize_messages
_append_memory_summary  = _memory.store._append_memory_summary
_load_memory_summary    = _memory.store._load_memory_summary
_background_summarize   = _memory.store._background_summarize

# ── RAG — Retrieval Augmented Generation local ────────────────────────────────

# Tuile RAG (refactor jarvis.py étape 5, 2026-05-23) : moteur + 5 routes
# /api/rag/* vivent dans scripts/rag/. L'ossature expose ici des alias légers
# vers les fonctions du moteur (consommateurs internes : _facts_inject,
# _rag_embed_prewarm, _rag_auto_refresh_loop, _chat_*). init() de la tuile +
# register Blueprint sont plus bas, après la déclaration de _WORKSPACE_ROOT.
_rag_mem_cache  = _rag.engine._rag_mem_cache   # alias dict (mutable partagé)
_bm25_obj_cache = _rag.engine._bm25_obj_cache  # alias dict (mutable partagé)
_RAG_CACHE_TTL  = _rag.engine._RAG_CACHE_TTL
_rag_embed         = _rag.engine._rag_embed
_rag_chunk         = _rag.engine._rag_chunk
_get_bm25_cached   = _rag.engine._get_bm25_cached
_rag_load          = _rag.engine._rag_load
_rag_save          = _rag.engine._rag_save
_rag_index_text    = _rag.engine._rag_index_text
_rag_live_refresh  = _rag.engine._rag_live_refresh
_rag_live_prewarm  = _rag.engine._rag_live_prewarm
_rag_query         = _rag.engine._rag_query
_rag_inject        = _rag.engine._rag_inject
_rag_live_cache: list = []  # conservé pour compatibilité ascendante

def _load_facts() -> list:
    """Charge les faits persistants depuis jarvis_facts.json."""
    try:
        if FACTS_FILE.exists():
            data = json.loads(FACTS_FILE.read_text(encoding="utf-8"))
            return data.get("facts", []) if isinstance(data, dict) else []
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING load_facts: {e}")
    return []

_MOIS_FR = ["janvier","février","mars","avril","mai","juin",
            "juillet","août","septembre","octobre","novembre","décembre"]
_JOURS_FR = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]

def _now_fr() -> str:
    from datetime import datetime as _dt
    n = _dt.now()
    return f"{_JOURS_FR[n.weekday()]} {n.day:02d} {_MOIS_FR[n.month-1]} {n.year} — {n.hour:02d}:{n.minute:02d}"

def _facts_inject(system: str) -> str:
    """Injecte date/heure, faits persistants et résumés de mémoire dans le system prompt."""
    additions = [f"[SYSTÈME] Date et heure actuelles : {_now_fr()}. Tu disposes de cette information en temps réel — réponds directement sans dire que tu n'y as pas accès."]
    facts = _load_facts()
    if facts:
        additions.append("[MÉMOIRE PERSISTANTE — faits toujours vrais, priorité absolue]\n" + "\n".join(f"• {f}" for f in facts))
    summary = _load_memory_summary()
    if summary:
        additions.append("[RÉSUMÉS DE CONVERSATIONS PASSÉES — contexte long terme]\n" + summary)
    return system + "\n\n" + "\n\n".join(additions)

app = Flask(__name__, template_folder=str(TEMPLATES))
app.jinja_env.auto_reload = True   # recharge les templates modifiés sans redémarrer
app.jinja_env.autoescape = True    # XSS — autoescape forcé sur tous les templates
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # désactive le cache navigateur des fichiers statiques
# SECRET_KEY — charge depuis fichier persistant ou génère à la première exécution
_SK_FILE = Path(__file__).parent / "jarvis_secret.key"
if _SK_FILE.exists():
    app.secret_key = _SK_FILE.read_bytes()
else:
    import secrets as _sec
    _k = _sec.token_bytes(32)
    _SK_FILE.write_bytes(_k)
    app.secret_key = _k
_JARVIS_BOOT_ID = str(int(time.time()))

limiter = Limiter(get_remote_address, app=app, default_limits=[], storage_uri="memory://")
sock    = _Sock(app)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 Mo — DAT recorder + voice/analyse (WAV 192kHz)

# ── Sécurité — journal des tentatives bloquées (en mémoire, max 100) ─────────
_SEC_EVENTS   = []   # [{ts, level, pattern, snippet}]
_SEC_MAX      = 100
_SEC_LOCK     = threading.Lock()

def _sec_log(level, pattern, code_snippet=""):
    """Enregistre une tentative bloquée (thread-safe)."""
    with _SEC_LOCK:
        _SEC_EVENTS.append({
            "ts":      time.strftime("%Y-%m-%d %H:%M:%S"),
            "level":   level,          # "hard" | "args" | "terminal"
            "pattern": pattern,
            "snippet": code_snippet[:120],
        })
        if len(_SEC_EVENTS) > _SEC_MAX:
            _SEC_EVENTS.pop(0)

# ── CORS + Private Network Access — autorise le dashboard SOC (LAN) ──────────
SOC_ORIGINS = {"http://192.168.1.50", "http://192.168.1.50:8080", "http://localhost", f"http://localhost:{JARVIS_PORT}", "http://127.0.0.1", f"http://127.0.0.1:{JARVIS_PORT}"}

def _cors_origin(origin: str) -> str:
    """Retourne l'Origin autorisée ou la valeur de repli localhost."""
    return origin if origin in SOC_ORIGINS else "http://localhost"

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        origin = request.headers.get("Origin", "")
        resp = app.make_response("")
        resp.headers["Access-Control-Allow-Origin"] = _cors_origin(origin)
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
        resp.headers["Access-Control-Allow-Private-Network"] = "true"
        resp.headers["Access-Control-Max-Age"] = "86400"
        return resp, 204

@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin", "")
    response.headers["Access-Control-Allow-Origin"] = _cors_origin(origin)
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Requested-With"
    response.headers["Access-Control-Allow-Private-Network"] = "true"
    response.headers["X-Frame-Options"]        = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers.remove("Server")
    return response

# ── GPU stats ────────────────────────────────────────────────
_net_prev    = {"t": time.time(), "s": psutil.net_io_counters()}
_disk_prev   = {"t": time.time(), "d": psutil.disk_io_counters()}
_STATS_LOCK  = threading.Lock()
_stats_cache = {"data": None, "ts": 0.0}
_STATS_TTL   = 5.0  # secondes — évite les appels pynvml concurrents (stats GPU changent lentement)
# Tracker état Ollama pour alerte vocale au changement d'état (J34)
# _ollama_prev_ok déplacé dans sys_diag.py (refactor incrémental jarvis.py
# étape 1, 2026-05-23) — était l'unique consommateur de la variable.

# Initialisation nvml une seule fois (nvmlInit/nvmlShutdown coûteux à répéter)
_nvml_handle = None
try:
    pynvml.nvmlInit()
    _nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
except Exception as _e:
    _log.info(f"[NVML] Init échouée: {_e}")

def _gpu_cuda_procs(handle):
    """Retourne (count, label) des processus CUDA en cours sur le GPU."""
    try:
        procs = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)
        _names = []
        for p in procs:
            try:
                import psutil as _ps2
                _names.append(f"{_ps2.Process(p.pid).name()} ({round(p.usedGpuMemory/1024**2)}MB)")
            except Exception:
                _names.append(f"PID {p.pid}")
        return len(procs), " | ".join(_names[:3]) if _names else "—"
    except Exception:
        return 0, "—"


def _gpu_extended_stats(handle):
    try:    fan = pynvml.nvmlDeviceGetFanSpeed(handle)
    except Exception: fan = None
    try:
        clk_gpu = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
        clk_mem = pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM)
    except Exception: clk_gpu = clk_mem = 0
    try:
        enc_util = pynvml.nvmlDeviceGetEncoderUtilization(handle)[0]
        dec_util = pynvml.nvmlDeviceGetDecoderUtilization(handle)[0]
    except Exception: enc_util = dec_util = 0
    try:
        p_state = int(pynvml.nvmlDeviceGetPerformanceState(handle))
    except Exception: p_state = None
    try:
        throttle = pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(handle)
        throttle_active = bool(throttle & ~0x3)  # masque idle(1)+appclocks(2)
    except Exception: throttle_active = False
    try:
        pcie_gen   = pynvml.nvmlDeviceGetCurrPcieLinkGeneration(handle)
        pcie_width = pynvml.nvmlDeviceGetCurrPcieLinkWidth(handle)
    except Exception: pcie_gen = pcie_width = None
    try:
        cv = pynvml.nvmlSystemGetCudaDriverVersion()
        cuda_ver = f"{cv // 1000}.{(cv % 1000) // 10}"
    except Exception: cuda_ver = "N/A"
    try:
        dv = pynvml.nvmlSystemGetDriverVersion()
        driver_ver = dv.decode() if isinstance(dv, bytes) else dv
    except Exception: driver_ver = "N/A"
    try:
        max_clk_gpu = pynvml.nvmlDeviceGetMaxClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
        max_clk_mem = pynvml.nvmlDeviceGetMaxClockInfo(handle, pynvml.NVML_CLOCK_MEM)
    except Exception: max_clk_gpu = max_clk_mem = None
    try:
        temp_slow = pynvml.nvmlDeviceGetTemperatureThreshold(handle, 1)  # SLOWDOWN
        temp_shut = pynvml.nvmlDeviceGetTemperatureThreshold(handle, 0)  # SHUTDOWN
    except Exception: temp_slow = temp_shut = None
    try:
        traw = pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(handle)
        _tr = [(0x1,"IDLE"),(0x2,"APPCLOCKS"),(0x4,"SYNC"),(0x8,"POWER"),
               (0x10,"THERMAL"),(0x20,"RELIABILITY"),(0x40,"HW_LIMIT"),(0x100,"DISPLAY")]
        reasons = [label for mask, label in _tr if traw & mask]
        throttle_reason = ", ".join(reasons) if reasons else "NONE"
    except Exception: throttle_reason = None
    cuda_proc_count, cuda_procs_str = _gpu_cuda_procs(handle)
    return {
        "fan": fan, "clk_gpu": clk_gpu, "clk_mem": clk_mem,
        "enc_util": enc_util, "dec_util": dec_util,
        "p_state": p_state, "throttle": throttle_active,
        "pcie_gen": pcie_gen, "pcie_width": pcie_width,
        "cuda_ver": cuda_ver, "driver_ver": driver_ver,
        "max_clk_gpu": max_clk_gpu, "max_clk_mem": max_clk_mem,
        "temp_slow": temp_slow, "temp_shut": temp_shut,
        "throttle_reason": throttle_reason,
        "cuda_proc_count": cuda_proc_count, "cuda_procs": cuda_procs_str,
    }

def get_stats():
    global _net_prev, _disk_prev
    if _nvml_handle is None:
        raise RuntimeError("NVML non disponible")
    handle = _nvml_handle
    name       = pynvml.nvmlDeviceGetName(handle)
    temp       = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
    util       = pynvml.nvmlDeviceGetUtilizationRates(handle)
    mem        = pynvml.nvmlDeviceGetMemoryInfo(handle)
    power_draw = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000
    power_lim  = pynvml.nvmlDeviceGetPowerManagementLimit(handle) / 1000
    ext = _gpu_extended_stats(handle)

    ram = psutil.virtual_memory()
    with _STATS_LOCK:
        net_now  = psutil.net_io_counters()
        net_t    = time.time()
        dt       = max(net_t - _net_prev["t"], 0.001)
        net_up   = (net_now.bytes_sent - _net_prev["s"].bytes_sent) / dt / 1024**2
        net_dn   = (net_now.bytes_recv - _net_prev["s"].bytes_recv) / dt / 1024**2
        _net_prev = {"t": net_t, "s": net_now}
        disk_now = psutil.disk_io_counters()
        disk_t   = time.time()
        dt2      = max(disk_t - _disk_prev["t"], 0.001)
        disk_r   = (disk_now.read_bytes  - _disk_prev["d"].read_bytes)  / dt2 / 1024**2
        disk_w   = (disk_now.write_bytes - _disk_prev["d"].write_bytes) / dt2 / 1024**2
        _disk_prev = {"t": disk_t, "d": disk_now}

    uptime_s = int(time.time() - psutil.boot_time())
    h, r = divmod(uptime_s, 3600); m, s = divmod(r, 60)
    cpu_freq = psutil.cpu_freq()

    return {
        "name": name if isinstance(name, str) else name.decode(),
        "temp": temp, "gpu_util": util.gpu, "mem_util": util.memory,
        "mem_used": mem.used/1024**3, "mem_total": mem.total/1024**3, "mem_free": mem.free/1024**3,
        "power_draw": power_draw, "power_limit": power_lim,
        **ext,
        "temp_warn": _GPU_TEMP_WARN,
        "cpu": psutil.cpu_percent(interval=None),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_freq": int(cpu_freq.current) if cpu_freq else 0,
        "ram_used": ram.used/1024**3, "ram_total": ram.total/1024**3,
        "net_up": round(net_up, 2), "net_dn": round(net_dn, 2),
        "disk_r": round(disk_r, 2), "disk_w": round(disk_w, 2),
        "uptime": f"{h}h {m:02d}m {s:02d}s",
        "model": MODEL,
    }

# ── TTS ──────────────────────────────────────────────────────
import queue as _queue_mod

_speak_queue    = _queue_mod.Queue(maxsize=8)  # textes en attente → browser joue via Web Audio
# Guard anti double-flux : quand un stream SSE chatbot est actif, les speak() background
# sont différés dans _speak_deferred et rejoués via SSE après le dernier token.
# Évite la superposition audio chatbot + autoban/monitoring.
_chat_stream_active = threading.Event()          # set() pendant generate()
_speak_deferred     = _queue_mod.Queue(maxsize=8) # messages en attente du stream
# Dedup guard : évite de rejouer le même texte deux fois en moins de 3s (race condition
# entre _speak_deferred → SSE et _speak_queue → polling)
_speak_last_text: str   = ''
_speak_last_time: float = 0.0
# Dedup global cross-source déplacé dans tts_dedup.py (Phase 3 sous-module 19)
# Utiliser _tts_dedup.check_and_register(text, time.monotonic())

# _ip_octet, _replace_ips, _clean_for_tts déplacés dans tts_cleaner.py — alias backward-compat
_clean_for_tts = _tts_cleaner.clean_for_tts

def speak(text, blocking=False):
    """Enfile le texte dans _speak_queue — le browser le récupère via GET /api/speak/queue
    et le joue via queueSpeech() → Web Audio (fader JARVIS + DSP + mixer).
    Si un stream SSE chatbot est actif (_chat_stream_active), le message est différé dans
    _speak_deferred et sera injecté comme événement SSE à la fin du stream → playback séquentiel."""
    global _speak_last_text, _speak_last_time
    text = _clean_for_tts(text)
    if not text:
        return
    # Dedup : même texte répété en moins de 3s → ignoré (race condition deferred↔queue)
    now = time.monotonic()
    if text == _speak_last_text and (now - _speak_last_time) < 3.0:
        _log.debug(f"[TTS] Dedup skip (même texte < 3s) : {text[:80]}")
        return
    _speak_last_text = text
    _speak_last_time = now
    # Dedup global cross-source (60s) — bloque le doublon JS si Python parle en premier
    if _tts_dedup.check_and_register(text, now):
        _log.debug(f"[TTS] Dedup global skip (python-speak, même texte < {_TTS_DEDUP_S}s) : {text[:80]}")
        return
    preview = text[:_TTS_LOG_PREVIEW].replace("\n", " ")
    suffix  = "..." if len(text) > _TTS_LOG_PREVIEW else ""
    _tts_logger.info("source=%-20s | %s%s", "python-speak", preview, suffix)
    try:
        if _chat_stream_active.is_set():
            # Stream chatbot actif → différer pour éviter superposition audio
            # Si queue pleine : drop le plus ancien (alerte récente = plus pertinente)
            if _speak_deferred.full():
                try: _speak_deferred.get_nowait()
                except _queue_mod.Empty: pass  # get_nowait() raises Empty when queue is drained — expected
            _speak_deferred.put_nowait(text)
            _log.info(f"[TTS] Différé (stream SSE actif) : {text[:80]}")
        else:
            # Si queue pleine : drop le plus ancien (alerte récente = plus pertinente)
            if _speak_queue.full():
                try: _speak_queue.get_nowait()
                except _queue_mod.Empty: pass  # get_nowait() raises Empty when queue is drained — expected
            _speak_queue.put_nowait(text)
    except _queue_mod.Full:
        _log.info(f"[TTS] Queue pleine — message ignoré : {text[:80]}")

def _load_welcome():
    if WELCOME_FILE.exists():
        try:
            return json.loads(WELCOME_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            _log.warning(f"[JARVIS] WARNING load_welcome: {e}")
    # Créer le fichier avec le message par défaut
    WELCOME_FILE.write_text(json.dumps(DEFAULT_WELCOME, indent=2, ensure_ascii=False), encoding="utf-8")
    return DEFAULT_WELCOME

_welcome_data = _load_welcome()

def _load_system_prompt():
    global SYSTEM_PROMPT
    with _CONFIG_LOCK:
        try:
            if PROMPT_FILE.exists():
                SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8")
        except Exception as e:
            _log.warning(f"[JARVIS] WARNING load_system_prompt: {e}")

_load_system_prompt()

# ── Mode JARVIS — commuté par /api/mode ──────────────────────────────────────
# "soc"            → phi4:14b             (cybersécurité — jarvis_model.json)
# "code"            → qwen2.5-coder:14b   (code + infogérance)
# "code_reasoning"  → qwen3:8b            (code + reasoning natif)
# "general" → gemma4:latest        (conversation générale, réponses rapides)
_GENERAL_MODEL: str  = "gemma4:latest"
_CODE_MODEL:                    str = "qwen2.5-coder:14b"
_CODE_REASONING_ANALYSIS_MODEL: str = "qwen3:8b"              # reasoning natif · ~5 GB VRAM · thinking tokens <think>
_CODE_REASONING_MODE                = "code_reasoning"         # single-pass qwen3:8b streaming (thinking masqué)
_jarvis_mode:   str = "soc"
# Init différé de la tuile memory + register Blueprint (refactor jarvis.py
# étape 4). Placé ici car nécessite _GENERAL_MODEL/_CODE_MODEL/_jarvis_mode
# déclarés au-dessus.
_memory.init(
    limiter          = limiter,
    ollama_url       = OLLAMA_URL,
    ollama_circuit   = _ollama_circuit,
    log              = _log,
    get_memory_file  = lambda: MEMORY_FILE,
    get_summary_file = lambda: SUMMARY_FILE,
    get_model        = lambda: MODEL,
    get_mode         = lambda: _jarvis_mode,
    memory_limit     = MEMORY_LIMIT,
    summary_keep     = _SUMMARY_KEEP,
    summary_min_msgs = _SUMMARY_MIN_MSGS,
    general_model    = _GENERAL_MODEL,
    code_model       = _CODE_MODEL,
)
app.register_blueprint(_memory.bp)

# Init différé de la tuile rag + register Blueprint (refactor jarvis.py
# étape 5). _WORKSPACE_ROOT / _claude_memory_root() définis tôt → init OK ici.
_rag.init(
    limiter           = limiter,
    log               = _log,
    ollama_circuit    = _ollama_circuit,
    ollama_url        = OLLAMA_URL,
    embed_model       = RAG_EMBED_MODEL,
    embed_timeout_s   = _RAG_EMBED_TIMEOUT_S,
    chunk_size        = RAG_CHUNK_SIZE,
    chunk_over        = RAG_CHUNK_OVER,
    top_n             = RAG_TOP_N,
    threshold         = RAG_THRESHOLD,
    rag_dir           = RAG_DIR,
    rag_meta_file     = RAG_META_FILE,
    rag_emb_file      = RAG_EMB_FILE,
    live_mod          = _rag_live_mod,
    ssh_ngix          = _ssh_ngix,
    ssh_log_timeout_s = _SSH_LOG_TIMEOUT_S,
    get_refresh_paths = lambda: [
        str(_WORKSPACE_ROOT / "JARVIS"  / "MEMORY.md"),
        str(_WORKSPACE_ROOT / "SOC"     / "MEMORY.md"),
        str(_WORKSPACE_ROOT / "PROXMOX" / "MEMORY.md"),
        str(_WORKSPACE_ROOT / "NGINX"   / "MEMORY.md"),
        str(_claude_memory_root() / "MEMORY.md"),
    ],
)
app.register_blueprint(_rag.bp)
_vram_model:    str | None = None   # modèle actuellement chargé en VRAM (tracké par JARVIS)
_last_toks_per_sec: float = 0.0     # vitesse dernière génération (tok/s)
_dev_cwd:       str = "/root"   # répertoire courant de la session terminal DEV (srv-dev-1)


# _DATETIME_RE déplacé dans bypass_simple.py (Phase 3 module 6a)

# RAG déclenché seulement sur requêtes documentaires/techniques — skip pour le chat conversationnel
_RAG_RELEVANT_KW = re.compile(
    r'\b(comment|pourquoi|qu.est.ce|explique|architecture|documentation|'
    r'config|configur|fonctionne|fonctionnement|install|setup|d[eé]ploie|'
    r'mitre|att.?ck|cve|vuln|menace|attaque|protocole|certificat|ssl|tls|'
    r'crowdsec|fail2ban|suricata|ids|ips|waf|firewall|r[eè]gle|rule|'
    r'jarvis|proxmox|docker|ansible|nginx|apache|ssh|scp|rsync|'
    r'sauvegarde|backup|restaur|snapshot)\b', re.I)


# Modèle ayant déclenché un auto-profil (pour restauration au switch)
_AUTO_PROFILE_MODEL: str | None = None

def _get_model_profile(model: str) -> tuple[str, str] | tuple[None, None]:
    """Retourne (nom_profil, contenu) lié au modèle, ou (None, None)."""
    try:
        if PROMPT_PROFILES_FILE.exists():
            profiles = json.loads(PROMPT_PROFILES_FILE.read_text(encoding="utf-8-sig"))
            for name, entry in profiles.items():
                if entry.get("model_binding") == model:
                    return name, entry.get("content", "")
    except (OSError, ValueError):
        pass  # fichier absent ou JSON malformé — retourne (None, None)
    return None, None

def _pve_context_lines(pve: dict) -> list:
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


# Seuil de hits (fenêtre Kill Chain 15 min) au-delà duquel un SCAN/BRUTE/RECON
# devient un signal FORT digne d'une reco de ban. Plancher aligné sur le
# banMinCount de l'auto-engine (10-50 selon profil de menace) : en-dessous,
# c'est du bruit de fond Internet permanent — à surveiller, pas à bannir.
_KC_BAN_SIGNAL_MIN_HITS = 10


def _kc_ban_signal(ip_e: dict) -> str:
    """Force du signal d'une IP Kill Chain pour une reco de ban — même logique
    que les seuils de l'auto-engine : EXPLOIT ou UA usurpé sont bannissables
    même sur 1 hit, le reste seulement si l'activité est soutenue."""
    if ip_e.get("stage") == "EXPLOIT" or ip_e.get("spoofed_bot"):
        return "FORT"
    if (ip_e.get("count") or 0) >= _KC_BAN_SIGNAL_MIN_HITS:
        return "FORT"
    return "faible"


# ── Infrastructure SOC — JAMAIS source d'attaque, JAMAIS bannissable ──
# Liste d'IPs internes appartenant à l'infrastructure SOC elle-même. Injectée
# textuellement dans le contexte LLM pour empêcher phi4 d'inventer ces IPs
# comme "source d'événements suspects" par hallucination d'association
# (incident 2026-05-18 : LLM a attribué +10 events à 192.168.1.50 = srv-ngix).
_INFRA_IPS = (
    ("192.168.1.20",  "Proxmox VE — hyperviseur"),
    ("192.168.1.50",  "srv-ngix — hôte du SOC lui-même (nginx + CrowdSec + monitoring_gen)"),
    ("192.168.1.12",  "clt — VM Apache site CLT"),
    ("192.168.1.13",  "pa85 — VM Apache site PA85"),
    ("192.168.1.21",  "srv-dev-1 — VM Debian dev/test"),
    ("192.168.1.110", "Windows/JARVIS via routeur ASUS — trafic NATé du poste de travail (cette IA elle-même)"),
    ("192.168.1.254", "Freebox — gateway LAN"),
)


def _build_monitoring_context(d: dict, header: str = "=== DONNÉES SOC EN TEMPS RÉEL (srv-ngix) ===") -> str:
    """Construit le contexte textuel SOC depuis un dict monitoring.json parsé.
    Utilisé par execute_tool('soc_status') et api_chat() pour injection LLM."""
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
        # Maillon KC par IP bannie = stade offensif le plus profond classé par le
        # backend (kc.neutralized_ips[].origin_stage — source unique scenario_stage
        # de soc_infra.yaml). Évite que phi4 re-déduise le maillon depuis le NOM du
        # scénario (erreurs constatées : 1 IP placée dans 2 maillons, alerte
        # "binsh in URI" prise pour du RECON au lieu d'EXPLOIT).
        _neut_stage = {e.get("ip"): e.get("origin_stage")
                       for e in kc.get("neutralized_ips", []) if e.get("ip")}
        # Limite portée à 100 (était 25 — provoquait des faux "pas dans la liste"
        # quand la liste prod dépassait 25 IPs et que phi4 oubliait la mention "N autres").
        shown = sorted(cs_banned.items())[:100]
        lines.append("")
        lines.append(f"IPs DÉJÀ BANNIES par CrowdSec ({len(cs_banned)} au total — déjà neutralisées, NE PAS recommander de les bannir, NE PAS proposer cscli decisions add pour ces IPs) :")
        lines.append("  (champ « maillon-KC » = stade offensif classé par le backend — UTILISE-le tel quel pour situer l'IP dans la Kill Chain · NE déduis JAMAIS le maillon depuis le nom du scénario · 1 IP = 1 seul maillon)")
        for ip, meta in shown:
            lines.append(f"  {ip} — scénario={meta.get('scenario','?')} | maillon-KC={_neut_stage.get(ip) or '?'}")
        if len(cs_banned) > len(shown):
            lines.append(f"  … et {len(cs_banned) - len(shown)} autre(s) IP(s) déjà bannie(s) non listée(s) — TOUTE IP non listée ci-dessus PEUT être déjà bannie, vérifier le total ({len(cs_banned)}) avant d'en recommander une.")
    active_ips = kc.get("active_ips", [])
    if active_ips:
        exploit_unblocked = sum(1 for ip in active_ips if ip.get("stage") == "EXPLOIT" and not ip.get("cs_decision"))
        exploit_total     = sum(1 for ip in active_ips if ip.get("stage") == "EXPLOIT")
        lines.append(f"IPs actives (Kill Chain) : {len(active_ips)} | EXPLOIT total: {exploit_total} | EXPLOIT non bloquées: {exploit_unblocked}")
        for ip_e in active_ips[:10]:
            cs_status = "BLOQUÉE-CS" if ip_e.get("cs_decision") else "⚠ NON-BLOQUÉE"
            spoof = f" ⚠UA-USURPÉ:{ip_e['spoofed_bot']}" if ip_e.get("spoofed_bot") else ""
            signal = _kc_ban_signal(ip_e)
            lines.append(f"  {ip_e.get('ip','?')} [{ip_e.get('country','-')}] stage={ip_e.get('stage','?')} hits={ip_e.get('count','?')} [{cs_status}] signal={signal}{spoof}")
    verified_bots = kc.get("verified_bots", [])
    if verified_bots:
        names = ", ".join(f"{b.get('ip','?')} ({b.get('bot','?')})" for b in verified_bots[:10])
        lines.append(f"Crawlers légitimes vérifiés FCrDNS ({len(verified_bots)}) — EXCLUS de la Kill Chain, NE JAMAIS recommander de les bannir : {names}")
    net_spikes = d.get("net_spikes", [])
    if net_spikes:
        recent = [s for s in net_spikes if time.time() - s.get("ts", 0) < _NET_SPIKE_WINDOW_S]
        if recent:
            last_s = recent[-1]
            lines.append(f"Pic réseau récent (<1h) : TX={last_s.get('tx_mbps',0)} Mbps / RX={last_s.get('rx_mbps',0)} Mbps (baseline TX:{last_s.get('avg_tx_mbps',0)} / RX:{last_s.get('avg_rx_mbps',0)} Mbps)")
        lines.append(f"Pics réseau (7j) : {len(net_spikes)} détectés")
    lines.extend(_pve_context_lines(d.get("proxmox", {})))
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


def _tool_lire_fichier(args):
    path = Path(args["chemin"])
    if not path.exists():
        return f"Erreur : fichier introuvable → {path}"
    return path.read_text(encoding="utf-8", errors="replace")[:8000]

_BLOCKED_LOCAL_WRITE = [
    "windows", "system32", "syswow64", "program files",
    "drivers\\etc", "drivers/etc",
    "\\appdata\\roaming\\microsoft", "/appdata/roaming/microsoft",
    "\\programdata\\", "/programdata/",
]
_WORKSPACE_ROOTS = [
    _WORKSPACE_ROOT,
    Path.home() / "AppData" / "Local" / "Temp",
]

def _check_local_write_path(path: Path) -> str | None:
    resolved = str(path.resolve()).lower().replace("\\", "/")
    for blocked in _BLOCKED_LOCAL_WRITE:
        if blocked.lower() in resolved:
            return f"[JARVIS] Accès refusé : chemin système protégé → {path}"
    try:
        r = path.resolve()
        if not any(r == root.resolve() or r.is_relative_to(root.resolve()) for root in _WORKSPACE_ROOTS):
            return f"[JARVIS] Accès refusé : chemin hors workspace → {path}"
    except Exception:
        return f"[JARVIS] Accès refusé : chemin invalide → {path}"
    return None

def _tool_ecrire_fichier(args):
    path = Path(args["chemin"])
    err = _check_local_write_path(path)
    if err:
        return err
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(args["contenu"], encoding="utf-8")
    return f"Fichier écrit avec succès : {path}"

def _tool_modifier_fichier(args):
    path = Path(args["chemin"])
    err = _check_local_write_path(path)
    if err:
        return err
    if not path.exists():
        return f"Erreur : fichier introuvable → {path}"
    content = path.read_text(encoding="utf-8", errors="replace")
    if args["ancien"] not in content:
        return "Erreur : texte introuvable dans le fichier."
    path.write_text(content.replace(args["ancien"], args["nouveau"], 1), encoding="utf-8")
    return f"Fichier modifié avec succès : {path}"

def _tool_lister_dossier(args):
    path = Path(args["chemin"])
    if not path.exists():
        return f"Erreur : dossier introuvable → {path}"
    items = [("📁" if p.is_dir() else "📄") + " " + p.name for p in sorted(path.iterdir())]
    return "\n".join(items) if items else "(dossier vide)"

def _tool_arborescence_projet(args):
    root = Path(args["chemin"])
    depth = min(int(args.get("profondeur", 2)), 3)
    if not root.exists():
        return f"Erreur : dossier introuvable → {root}"
    lines = [f"📁 {root.name}/"]
    def _walk(p, lvl):
        if lvl > depth:
            return
        indent = "  " * lvl
        for item in sorted(p.iterdir()):
            if item.name.startswith('.') or item.name == '__pycache__':
                continue
            if item.is_dir():
                lines.append(f"{indent}📁 {item.name}/")
                _walk(item, lvl + 1)
            else:
                lines.append(f"{indent}📄 {item.name}")
    _walk(root, 1)
    return "\n".join(lines)

def _tool_lire_plusieurs_fichiers(args):
    chemins = args.get("chemins", [])[:5]
    parts = []
    for c in chemins:
        p = Path(c)
        if p.exists():
            content = p.read_text(encoding="utf-8", errors="replace")[:4000]
            parts.append(f"=== {p.name} ({p}) ===\n{content}")
        else:
            parts.append(f"=== {p.name} === [INTROUVABLE : {p}]")
    return "\n\n".join(parts) if parts else "Aucun fichier spécifié."

_BLOCKED_HARD = ["shutil.rmtree"]
_BLOCKED_ARGS = [
    "rm -rf", "rm -r /", "rm -fr",
    "del /f /s", "del /s /f", "del /f/s",
    "rd /s /q", "rd /q /s", "rmdir /s /q",
    "Remove-Item -Recurse -Force", "remove-item -recurse -force",
    "format c:", "format d:", "format e:", "diskpart",
    "qm destroy", "qm stop", "qm reset", "qm suspend",
    "pvesh delete", "virsh destroy", "virsh undefine",
    "systemctl stop", "systemctl disable", "systemctl mask",
    "nginx -s stop", "nginx -s quit",
    "service nginx stop", "service crowdsec stop",
    "service fail2ban stop", "service ssh stop",
]

def _tool_executer_code(args):
    code    = args["code"]
    timeout = int(args.get("timeout", 15))
    for pattern in _BLOCKED_HARD:
        if pattern in code:
            _sec_log("hard", pattern, code)
            return f"Erreur : opération refusée par sécurité ({pattern})"
    code_lower = code.lower()
    for pattern in _BLOCKED_ARGS:
        if pattern.lower() in code_lower:
            _sec_log("args", pattern, code)
            return f"Erreur : argument de commande refusé par sécurité ({pattern})"
    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=timeout
        )
        out = result.stdout[:3000] if result.stdout else ""
        err = result.stderr[:1000] if result.stderr else ""
        if err and not out:
            return f"ERREUR:\n{err}"
        if err:
            return f"SORTIE:\n{out}\nAVERTISSEMENT:\n{err}"
        return out or "(aucune sortie)"
    except subprocess.TimeoutExpired:
        return f"Erreur : timeout dépassé ({timeout}s)"

_RGLOB_EXCLUDED = {".git", ".ssh", "node_modules", "__pycache__", ".venv", "venv", ".env", "dist", "build"}
_RGLOB_MAX_DEPTH = 5

def _tool_rechercher_dans_fichiers(args):
    dossier = Path(args["dossier"])
    pattern = args["pattern"]
    ext     = args.get("extension", "")
    if not dossier.exists():
        return f"Erreur : dossier introuvable → {dossier}"
    results = []
    glob_pat = f"*{ext}" if ext else "*"
    for f in dossier.rglob(glob_pat):
        # Exclure dossiers sensibles et limiter la profondeur
        try:
            rel = f.relative_to(dossier)
        except ValueError:
            continue
        parts = rel.parts
        if any(p in _RGLOB_EXCLUDED for p in parts) or len(parts) > _RGLOB_MAX_DEPTH:
            continue
        if not f.is_file(): continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.lower() in line.lower():
                    results.append(f"{f}:{i}: {line.strip()}")
                    if len(results) >= 30: break
        except OSError:
            continue
        if len(results) >= 30: break
    return "\n".join(results) if results else "Aucun résultat trouvé."

def _tool_soc_status():
    ok, raw = _fetch_monitoring(force=True)
    if not ok:
        return f"Erreur SSH srv-ngix : {raw}"
    try:
        return _build_monitoring_context(json.loads(raw), header="=== SOC STATUS ===")
    except Exception as e:
        return f"monitoring.json brut (parse error: {e}):\n{raw[:3000]}"

# _BLOCKED_SSH, _ALLOWED_RESTART_SVCS, _ALLOWED_APT_PKGS, _check_write_op,
# _parse_upgradable_packages : déplacés dans security_whitelists.py (Phase 3 module 6b)
_SVC_BOUNCER = "crowdsec-firewall-bouncer"  # constante encore utilisée localement (ban TTL, etc.)


def _tool_commande_ssh_run(ssh_fn, label, args):
    """Exécute une commande SSH après validation sécurité — mutualisé pour tous les hôtes.

    Logique 3 couches (corrigee 2026-05-17 — fix faille defense-en-profondeur) :
    1. Aucun pattern BLOCKED matche → exec direct (lecture/diagnostic standard)
    2. Pattern BLOCKED matche ET commande est une write op reconnue
       (is_known_write_op) ET whitelistee (check_write_op None) → exec + audit
    3. Pattern BLOCKED matche ET commande PAS une write op reconnue
       (ex: rm/mkfs/dd/shutdown/qm destroy) → REFUS par defaut + audit
    4. Pattern BLOCKED matche ET write op reconnue MAIS refusee
       (ex: systemctl restart docker, apt install evilpkg) → REFUS + audit

    Audit log : write ops (autorisees OU refusees) tracees dans logs/audit_writeops.jsonl
    via _sec.audit_writeop() — best-effort, ne bloque jamais l'execution.
    """
    cmd = args.get("commande", "").strip()
    if not cmd:
        return "Erreur : commande vide"
    cmd_lower = cmd.lower()
    is_writeop = False
    for pattern in _sec.BLOCKED_SSH_PATTERNS:
        if pattern.lower() in cmd_lower:
            is_writeop = True
            # Gardien : si pattern destructif matche MAIS commande pas reconnue
            # comme write op whitelistable (rm/mkfs/dd/shutdown/...) → REFUS strict.
            # Ne JAMAIS se fier au seul check_write_op qui retourne None pour ces cas.
            if not _sec.is_known_write_op(cmd):
                msg = f"commande destructive non whitelistée (pattern: {pattern})"
                _sec.audit_writeop(label, cmd, allowed=False, output=msg)
                return f"Erreur : commande refusée par sécurité ({pattern}) — {msg}"
            err = _sec.check_write_op(cmd)
            if err is not None:
                _sec.audit_writeop(label, cmd, allowed=False, output=err)
                return f"Erreur : commande refusée par sécurité ({pattern}) — {err}"
            break
    ok, output = ssh_fn(cmd, timeout=_ssh_timeout(cmd))
    if is_writeop:
        _sec.audit_writeop(label, cmd, allowed=True, output=output or "")
    if not ok and not output:
        return f"Erreur SSH {label} : pas de réponse"
    return output[:4000] if output else "(aucune sortie)"

def _tool_commande_ssh_ngix(args):    return _tool_commande_ssh_run(_ssh_ngix,    "ngix",    args)
def _tool_commande_ssh_proxmox(args): return _tool_commande_ssh_run(_ssh_proxmox, "proxmox", args)

def _ssh_timeout(cmd: str, default: int = 15) -> int:
    """Timeout adaptatif — apt/dpkg peuvent durer plusieurs minutes."""
    if any(k in cmd.lower() for k in ("apt", "dpkg", "apt-get")):
        return 180
    return default

def _tool_commande_ssh_clt(args):  return _tool_commande_ssh_run(_ssh_clt,  "clt",  args)
def _tool_commande_ssh_pa85(args): return _tool_commande_ssh_run(_ssh_pa85, "pa85", args)

_ALLOWED_SCRIPTS = {
    "backup-auto":   str(_WORKSPACE_ROOT / "PROXMOX" / "proxmox-backup-auto.ps1"),
    "disk-report":   str(_WORKSPACE_ROOT / "PROXMOX" / "windows-disk-report.ps1"),
    "backup-jarvis": str(_WORKSPACE_ROOT / "JARVIS" / "scripts" / "backup-jarvis.ps1"),
}

def _tool_executer_script_windows(args):
    """Exécute un script PowerShell local (whitelist stricte)."""
    script_key = args.get("script", "").strip()
    script_path = _ALLOWED_SCRIPTS.get(script_key)
    if not script_path:
        return f"Erreur : script '{script_key}' non autorisé. Scripts disponibles : {', '.join(_ALLOWED_SCRIPTS)}"
    try:
        proc = subprocess.Popen(
            ["powershell.exe", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", script_path],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace"
        )
        out, _ = proc.communicate(timeout=_BACKUP_PROC_TIMEOUT_S)
        rc = proc.returncode
        result = out.strip()[:3000] if out else "(aucune sortie)"
        return f"Script '{script_key}' terminé (code {rc}).\n{result}"
    except subprocess.TimeoutExpired:
        proc.kill()
        return f"Script '{script_key}' : timeout dépassé (300s)"
    except Exception as e:
        return f"Erreur exécution script '{script_key}' : {e}"

_TOOL_DISPATCH = {
    "lire_fichier":             lambda args: _tool_lire_fichier(args),
    "ecrire_fichier":           lambda args: _tool_ecrire_fichier(args),
    "modifier_fichier":         lambda args: _tool_modifier_fichier(args),
    "lister_dossier":           lambda args: _tool_lister_dossier(args),
    "arborescence_projet":      lambda args: _tool_arborescence_projet(args),
    "lire_plusieurs_fichiers":  lambda args: _tool_lire_plusieurs_fichiers(args),
    "executer_code":            lambda args: _tool_executer_code(args),
    "rechercher_dans_fichiers": lambda args: _tool_rechercher_dans_fichiers(args),
    "soc_status":               lambda args: _tool_soc_status(),
    "commande_ssh_ngix":        lambda args: _tool_commande_ssh_ngix(args),
    "commande_ssh_proxmox":     lambda args: _tool_commande_ssh_proxmox(args),
    "commande_ssh_clt":         lambda args: _tool_commande_ssh_clt(args),
    "commande_ssh_pa85":        lambda args: _tool_commande_ssh_pa85(args),
    "executer_script_windows":  lambda args: _tool_executer_script_windows(args),
}

def execute_tool(name, args):
    """Exécute un outil fichier et retourne le résultat."""
    try:
        handler = _TOOL_DISPATCH.get(name)
        if handler is None:
            return f"Outil inconnu : {name}"
        return handler(args)
    except Exception as e:
        return f"Erreur lors de l'exécution : {e}"

def call_llm_with_tools(messages, model_override=None):
    """Appel non-streamé pour détecter les tool calls (Ollama)."""
    payload = {
        "model": model_override or MODEL,
        "messages": messages,
        "tools": TOOLS,
        "stream": False,
        "options": {
            "temperature": _LLM_DEFAULTS["temperature"],
            "num_predict": 256,   # limité : on détecte juste les tool calls, pas de réponse complète
            "num_ctx": max(LLM_PARAMS.get("num_ctx", _LLM_DEFAULTS["num_ctx"]), 8192),
        }
    }
    resp = _ollama_circuit.call(req.post, f"{OLLAMA_URL}/api/chat", json=payload, timeout=_OLLAMA_TOOL_DETECT_TIMEOUT_S)
    return resp.json()

def _think_filter_step(tbuf: str, in_think: bool):
    """Un pas du filtre <think>…</think> sur le buffer courant.
    Retourne (chars_à_émettre, nouveau_tbuf, nouveau_in_think, stop).
    Gère les tags à cheval sur plusieurs tokens (buffer partiel en fin).
    Gère aussi les </think> orphelins (émis sans <think> précédent par phi4-reasoning).
    """
    if not in_think:
        idx = tbuf.find('<think>')
        if idx == -1:
            ci = tbuf.find('</think>')
            if ci != -1:
                return tbuf[:ci] + tbuf[ci + 8:], "", False, True
            for plen in range(min(7, len(tbuf)), 0, -1):
                if tbuf[-plen:] == '<think>'[:plen]:
                    return tbuf[:-plen], tbuf[-plen:], False, True
            return tbuf, "", False, True
        return tbuf[:idx], tbuf[idx + 7:], True, False
    idx = tbuf.find('</think>')
    if idx == -1:
        return "", "", True, True   # tout le buffer est du thinking — jeter
    return "", tbuf[idx + 8:], False, False


def stream_llm(messages, model_override=None, options_override=None):
    """Generator — stream de tokens (Ollama local).
    options_override : dict partiel pour surcharger LLM_PARAMS (ex: {"num_predict": 512}).
    Filtre les blocs <think>...</think> des modèles de raisonnement (phi4-reasoning, deepseek-r1).
    """
    messages_with_prefill = messages + [{"role": "assistant", "content": ""}]
    opts = {
        "temperature":    LLM_PARAMS["temperature"],
        "num_predict":    LLM_PARAMS["num_predict"],
        "top_p":          LLM_PARAMS["top_p"],
        "top_k":          LLM_PARAMS["top_k"],
        "repeat_penalty": LLM_PARAMS["repeat_penalty"],
        "num_ctx":        LLM_PARAMS.get("num_ctx", 2048),
    }
    if options_override:
        opts.update(options_override)
    active_model_name = model_override or MODEL
    payload = {
        "model":      active_model_name,
        "messages":   messages_with_prefill,
        "stream":     True,
        "keep_alive": "30m",
        "options":    opts,
        "think":      LLM_PARAMS.get("think", False),
    }
    _in_think = False
    _tbuf     = ""
    # Circuit breaker : si Ollama est down (3 erreurs récentes), refus immédiat (1ms au lieu de 30s timeout)
    try:
        resp = _ollama_circuit.call(req.post, f"{OLLAMA_URL}/api/chat", json=payload, stream=True, timeout=_OLLAMA_STREAM_TIMEOUT_S)
    except OllamaUnavailable as e:
        yield f"[JARVIS] {e}", True
        return
    with resp:
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue  # ligne Ollama malformée — on saute sans casser le flux
            msg   = chunk.get("message", {})
            done  = chunk.get("done", False)
            if done:
                ec = chunk.get("eval_count", 0)
                ed = chunk.get("eval_duration", 0)
                if ec and ed:
                    global _last_toks_per_sec
                    _last_toks_per_sec = round(ec / (ed / 1e9), 1)
            # Nouveau API Ollama : champ .thinking séparé → ignorer
            if msg.get("thinking"):
                if done:
                    yield "", True
                continue
            raw = msg.get("content", "")
            if not raw:
                if done:
                    yield "", True
                continue
            _tbuf += raw
            out = ""
            while _tbuf:
                chunk_out, _tbuf, _in_think, stop = _think_filter_step(_tbuf, _in_think)
                out += chunk_out
                if stop:
                    break
            if out or done:
                yield out, done

# ── Routes ───────────────────────────────────────────────────
init_soc(speak, limiter)
app.register_blueprint(soc_bp)

@app.route("/")
def index():
    return render_template("jarvis.html", boot_id=_JARVIS_BOOT_ID,
                           dev_ip=_CODE_DEV_IP, dev_port=_CODE_DEV_PORT,
                           mon_endpoint=_SOC_CFG.get("monitoring_url", "http://192.168.1.50:8080/monitoring.json"))

@app.route("/favicon.ico")
def favicon():
    return Response("", status=204)

@limiter.limit("60 per minute")
@app.route("/api/boot-id")
def api_boot_id():
    return Response(json.dumps({"boot_id": _JARVIS_BOOT_ID}), mimetype="application/json")

@limiter.limit("5 per minute")
@app.route("/api/debug/inject-pending", methods=["POST"])
def api_debug_inject_pending():
    """TEST ONLY — injecte un _pending_infra_cmd factice pour valider le bypass 'oui'."""
    _pending_infra_cmd.update({
        "host":     "clt",
        "ssh_fn":   _ssh_clt,
        "packages": ["__test-bypass__"],
        "ts":       time.time(),
    })
    # Remplace la ssh_fn par une lambda inoffensive (apt-cache stats)
    def _test_ssh(cmd, timeout=_SSH_SOC_TIMEOUT_S):
        return True, "[TEST] bypass apt confirmé — aucune commande réelle exécutée."
    _pending_infra_cmd["ssh_fn"] = _test_ssh
    _log.info("[DEBUG] _pending_infra_cmd injecté pour test bypass")
    return Response(json.dumps({"ok": True, "pending": "clt → __test-bypass__"}),
                    mimetype="application/json")

@limiter.limit("120 per minute")
@app.route("/api/health", methods=["GET"])
def api_health():
    """Health check léger — répond en <10ms, sans appel Ollama. Utilisé par watchdog et MCP."""
    return Response(json.dumps({
        "status": "ok",
        "model": MODEL,
        "ts": __import__("datetime").datetime.utcnow().isoformat() + "Z"
    }), mimetype="application/json")

@limiter.limit("30 per minute")
@app.route("/api/soc/context", methods=["GET"])
def api_soc_context():
    """Retourne le contexte SOC complet formaté pour injection LLM (monitoring.json parsé)."""
    ok, raw = _fetch_monitoring(force=False)
    if not ok:
        return Response(json.dumps({"ok": False, "context": raw or "monitoring.json indisponible"},
                                   ensure_ascii=False), mimetype="application/json")
    try:
        ctx = _build_monitoring_context(json.loads(raw))
    except Exception as e:
        ctx = f"monitoring.json brut (parse error: {e}):\n{raw[:3000]}"
    return Response(json.dumps({"ok": True, "context": ctx}, ensure_ascii=False),
                    mimetype="application/json")

@limiter.limit("60 per minute")
@app.route("/api/status")
def api_status():
    """État JARVIS — utilisé par la defense chain SOC (_dcPollJarvis)."""
    soc = get_soc_status()
    return Response(json.dumps({
        "available":          True,
        "model":              MODEL,
        "soc_engine_active":  soc["soc_engine_active"],
        "bans_24h":           soc["bans_24h"],
        "alerts_24h":         soc["alerts_24h"],
    }), mimetype="application/json")

@limiter.limit("60 per minute")
@app.route("/api/stats")
def api_stats():
    now = time.time()
    if _stats_cache["data"] is not None and (now - _stats_cache["ts"]) < _STATS_TTL:
        return Response(json.dumps(_stats_cache["data"]), mimetype="application/json")
    data = get_stats()
    _stats_cache["data"] = data
    _stats_cache["ts"] = now
    return Response(json.dumps(data), mimetype="application/json")

# Routes /api/memory* + /api/memory-summary* + /api/memory/summarize-session
# déménagées dans la tuile scripts/memory/routes.py (étape 4).
# /api/facts reste ici — la tuile « facts » sera son propre Blueprint plus tard.

@limiter.limit("60 per minute")
@app.route("/api/facts", methods=["GET"])
def api_facts_get():
    try:
        data = json.loads(FACTS_FILE.read_text(encoding="utf-8")) if FACTS_FILE.exists() else {"facts": []}
    except Exception:
        data = {"facts": []}
    return Response(json.dumps(data, ensure_ascii=False), mimetype="application/json")

# Routes /api/rag/* déménagées dans la tuile scripts/rag/routes.py (étape 5).

@limiter.limit("10 per minute")
@app.route("/api/code/exec", methods=["POST"])
def api_code_exec():
    """Écrit un fichier code localement, SCP sur srv-dev-1, exécute, retourne SSE."""
    data     = request.get_json(force=True, silent=True) or {}
    filename = (data.get("filename") or "").strip()
    code     = (data.get("code")     or "").strip()
    if not filename or not code:
        return Response(json.dumps({"error": "filename et code requis"}), status=400, mimetype="application/json")
    if not re.match(r'^[\w.-]+\.(py|sh|js|ts|html|css|json|yml|yaml|rb|go|php|sql|txt)$', filename) or ".." in filename:
        return Response(json.dumps({"error": "filename invalide"}), status=400, mimetype="application/json")
    local_path = Path.home() / "Documents" / filename
    local_path.write_text(code, encoding="utf-8")
    _log.info(f"[CODE/EXEC] Fichier écrit : {local_path}")
    def _gen_and_cleanup():
        yield from _code_scp_exec_sse(filename, exec_it=True)
        try:
            local_path.unlink(missing_ok=True)
            _log.info(f"[CODE/EXEC] Fichier temp supprimé : {local_path}")
        except Exception:
            pass  # PermissionError ou race — non bloquant
    return _sse_response(_gen_and_cleanup())

# Route /api/rag/refresh déménagée dans la tuile scripts/rag/routes.py (étape 5).

@limiter.limit("30 per minute")
@app.route("/api/facts", methods=["POST"])
def api_facts_save():
    payload = request.json if isinstance(request.json, dict) else {}
    facts = payload.get("facts", [])
    if not isinstance(facts, list):
        return Response('{"error":"facts must be a list"}', status=400, mimetype="application/json")
    data = {"updated_at": __import__("datetime").date.today().isoformat(), "facts": facts}
    try:
        FACTS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")
    return Response('{"ok":true}', mimetype="application/json")

@limiter.limit("60 per minute")
@app.route("/api/llm-params", methods=["GET"])
def api_llm_params_get():
    return Response(json.dumps({"params": LLM_PARAMS, "defaults": _LLM_DEFAULTS,
                                "system_prompt": SYSTEM_PROMPT}),
                    mimetype="application/json")

@limiter.limit("20 per minute")
@app.route("/api/llm-params", methods=["POST"])
def api_llm_params_set():
    global LLM_PARAMS, SYSTEM_PROMPT
    data = request.json or {}
    if "params" in data:
        for k, v in data["params"].items():
            if k in LLM_PARAMS:
                LLM_PARAMS[k] = v
        LLM_PARAMS_FILE.write_text(json.dumps(LLM_PARAMS, indent=2), encoding="utf-8")
    if "system_prompt" in data:
        SYSTEM_PROMPT = data["system_prompt"]
        PROMPT_FILE.write_text(SYSTEM_PROMPT, encoding="utf-8")
    return Response('{"ok":true}', mimetype="application/json")

@limiter.limit("10 per minute")
@app.route("/api/llm-params/reset-prompt", methods=["POST"])
def api_reset_prompt():
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT
    PROMPT_FILE.write_text(SYSTEM_PROMPT, encoding="utf-8")
    return Response(json.dumps({"ok": True, "system_prompt": SYSTEM_PROMPT}),
                    mimetype="application/json")

def _ensure_vram(next_model: str):
    """Décharge le modèle actuellement en VRAM si différent du prochain.
    Évite les collisions VRAM lors du routing automatique inter-modes."""
    global _vram_model
    effective = next_model or MODEL
    if _vram_model and _vram_model != effective:
        _log.info(f"[VRAM] Routing switch : {_vram_model} → {effective} — unload forcé")
        _ollama_swap(_vram_model, effective)
    _vram_model = effective


def _ollama_swap(unload_model: str, load_model: str):
    """Décharge unload_model (keep_alive=0) de façon SYNCHRONE, puis preload load_model en background.
    Synchrone pour garantir VRAM libre avant le chargement du modèle suivant (évite le split VRAM/RAM)."""
    import threading as _th
    import urllib.request as _ur
    # 1. Unload synchrone — on attend la confirmation avant de continuer
    try:
        payload = json.dumps({
            "model": unload_model, "prompt": "", "stream": False, "keep_alive": 0
        }).encode()
        req_u = _ur.Request("http://127.0.0.1:11434/api/generate",
                            data=payload, method="POST")
        req_u.add_header("Content-Type", "application/json")
        with _ur.urlopen(req_u, timeout=8): pass
        _log.info(f"[VRAM] {unload_model} déchargé (sync)")
    except Exception as e:
        _log.warning(f"[VRAM] unload {unload_model}: {e}")
    # 2. Preload du nouveau modèle en background — VRAM est maintenant libre
    def _preload():
        try:
            payload = json.dumps({
                "model": load_model, "prompt": "", "stream": False, "keep_alive": "30m"
            }).encode()
            req_p = _ur.Request("http://127.0.0.1:11434/api/generate",
                                data=payload, method="POST")
            req_p.add_header("Content-Type", "application/json")
            with _ur.urlopen(req_p, timeout=180): pass
            _log.info(f"[VRAM] {load_model} préchargé (plein VRAM)")
        except Exception as e:
            _log.warning(f"[VRAM] preload {load_model}: {e}")
    _th.Thread(target=_preload, daemon=True).start()

@limiter.limit("30 per minute")
@app.route("/api/mode", methods=["GET", "POST"])
def api_mode():
    global _jarvis_mode
    if request.method == "POST":
        data = request.json or {}
        new_mode = data.get("mode", "").lower()
        if new_mode not in ("soc", "general", "code", "code_reasoning"):
            return Response(json.dumps({"error": "mode invalide (soc|general|code|code_reasoning)"}), status=400,
                            mimetype="application/json")
        prev_mode = _jarvis_mode
        if new_mode != prev_mode:
            _jarvis_mode = new_mode
            _log.info(f"[JARVIS] Mode {prev_mode} → {new_mode}")
            _model_prev = {"soc": MODEL, "general": _GENERAL_MODEL, "code": _CODE_MODEL, "code_reasoning": _CODE_REASONING_ANALYSIS_MODEL}.get(prev_mode, MODEL)
            _model_next = {"soc": MODEL, "general": _GENERAL_MODEL, "code": _CODE_MODEL, "code_reasoning": _CODE_REASONING_ANALYSIS_MODEL}.get(new_mode, MODEL)
            if _model_prev != _model_next:
                _ollama_swap(_model_prev, _model_next)
                global _vram_model; _vram_model = _model_next
    _model_map = {"soc": MODEL, "general": _GENERAL_MODEL, "code": _CODE_MODEL, "code_reasoning": _CODE_REASONING_ANALYSIS_MODEL}
    return Response(json.dumps({"mode": _jarvis_mode, "model": _model_map.get(_jarvis_mode, MODEL)}),
                    mimetype="application/json")

@limiter.limit("60 per minute")
@app.route("/api/dev/exec", methods=["POST"])
def api_dev_exec():
    data = request.get_json(silent=True) or {}
    cmd  = data.get("cmd", "").strip()
    if not cmd:
        return Response(json.dumps({"error": "cmd requis"}), status=400, mimetype="application/json")
    return Response(stream_with_context(_dev_exec_sse(cmd)), content_type="text/event-stream")

@app.route("/api/dev/stats")
@limiter.limit("30/minute")
def dev_stats():
    """Stats système srv-dev-1 via SSH · cache 12s · TTY-free."""
    import time as _t

    from flask import jsonify
    now = _t.time()
    if now - _dev_stats_cache["ts"] < 12 and _dev_stats_cache["data"]:
        return jsonify(_dev_stats_cache["data"])
    try:
        import paramiko as _pm
        cl = _pm.SSHClient()
        cl.set_missing_host_key_policy(_pm.AutoAddPolicy())
        cl.connect(hostname=_CODE_DEV_IP, port=_CODE_DEV_PORT, username="root",
                   key_filename=_CODE_DEV_KEY, timeout=5,
                   look_for_keys=False, allow_agent=False)
        _, out, _ = cl.exec_command(_STATS_CMD, timeout=8)
        raw = out.read().decode().strip()
        cl.close()
        data = json.loads(raw)
        _dev_stats_cache["ts"]   = _t.time()
        _dev_stats_cache["data"] = data
        return jsonify(data)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


def _ws_ssh_reader(channel, out_queue, data_ready, running):
    """Lit le channel SSH et pousse dans la queue (thread dédié)."""
    import select as _sel
    while running[0]:
        try:
            r, _, _ = _sel.select([channel], [], [], 0.1)
            if r:
                data = channel.recv(4096)
                if not data:
                    running[0] = False
                    break
                out_queue.put(data.decode("utf-8", errors="replace"))
                data_ready.set()
        except Exception:
            running[0] = False
            break


def _ws_ssh_connect(cfg: dict):
    """Établit une connexion SSH PTY — retourne (client, channel, None) ou (None, None, err_msg)."""
    import paramiko as _pm
    client = _pm.SSHClient()
    client.set_missing_host_key_policy(_pm.AutoAddPolicy())
    try:
        client.connect(
            hostname     = cfg["ip"],
            port         = cfg["port"],
            username     = cfg.get("user", "root"),
            key_filename = cfg["key"],
            timeout      = 10,
            look_for_keys= False,
            allow_agent  = False,
        )
    except Exception as exc:
        return None, None, str(exc)
    channel = client.invoke_shell(term="xterm-256color", width=220, height=50)
    channel.setblocking(False)
    return client, channel, None


def _ws_ssh_handler(ws, cfg: dict):
    """Corps commun WebSocket PTY SSH — terminal interactif (xterm.js)."""
    import queue as _queue
    import threading as _wth

    client, channel, err = _ws_ssh_connect(cfg)
    if err:
        try:
            ws.send(f"\r\n\x1b[31m✗ SSH {cfg['label']} impossible : {err}\x1b[0m\r\n")
        except Exception:
            pass  # WebSocket déjà fermé côté client
        return

    running    = [True]
    out_queue  = _queue.Queue()
    data_ready = _wth.Event()

    _wth.Thread(target=_ws_ssh_reader, args=(channel, out_queue, data_ready, running), daemon=True).start()

    try:
        while running[0]:
            while not out_queue.empty():
                try:
                    ws.send(out_queue.get_nowait())
                except Exception:
                    running[0] = False
                    break
            if not running[0]:
                break
            data_ready.clear()
            try:
                msg = ws.receive(timeout=0.3)
            except Exception:
                tr = channel.get_transport()
                if not tr or not tr.is_active() or not running[0]:
                    break
                data_ready.wait(timeout=0.05)
                continue
            if msg is None:
                continue
            if isinstance(msg, str) and msg.startswith('{"type":"resize"'):
                try:
                    _r = json.loads(msg)
                    channel.resize_pty(width=int(_r["cols"]), height=int(_r["rows"]))
                except Exception:
                    pass  # channel déjà fermé ou PTY non supporté
            else:
                try:
                    channel.sendall(msg if isinstance(msg, bytes) else msg.encode())
                except Exception:
                    break
    finally:
        running[0] = False
        try: channel.close()
        except Exception: pass  # channel may already be closed — ignore
        try: client.close()
        except Exception: pass  # client may already be closed — ignore


@sock.route("/ws/ssh/<host>")
def ws_ssh_host(ws, host):
    """WebSocket PTY SSH — terminal interactif générique vers n'importe quel hôte de _SSH_TERMINAL_MAP."""
    cfg = _SSH_TERMINAL_MAP.get(host)
    if cfg is None:
        try:
            ws.send(f"\r\n\x1b[31m✗ Hôte inconnu : {host}\x1b[0m\r\n")
        except Exception:
            pass  # WebSocket déjà fermé côté client
        return
    _ws_ssh_handler(ws, cfg)


@sock.route("/ws/dev")
def ws_dev(ws):
    """WebSocket PTY SSH — terminal CODE srv-dev-1 (alias de /ws/ssh/dev1)."""
    _ws_ssh_handler(ws, _SSH_TERMINAL_MAP["dev1"])

@limiter.limit("30 per minute")
@limiter.limit("10 per minute")
@app.route("/api/save-code", methods=["POST"])
def api_save_code():
    import re as _re
    data     = request.get_json(silent=True) or {}
    filename = data.get("filename", "untitled.py")
    code     = data.get("code", "")
    if not _re.match(r'^[\w\-. ]+$', filename):
        return Response(json.dumps({"error": "filename invalide"}), status=400, mimetype="application/json")
    save_dir = Path(__file__).parent / "generated_code"
    save_dir.mkdir(exist_ok=True)
    filepath = save_dir / filename
    filepath.write_text(code, encoding="utf-8")
    _log.info(f"[CODE] Fichier sauvegardé : {filepath}")
    return Response(json.dumps({"saved": str(filepath)}), mimetype="application/json")

@limiter.limit("60 per minute")
@app.route("/api/ollama-status", methods=["GET"])
def api_ollama_status():
    import urllib.request as _ur
    try:
        with _ur.urlopen("http://127.0.0.1:11434/api/tags", timeout=_OLLAMA_STATUS_TIMEOUT_S) as r:
            running = r.status == 200
    except Exception:
        running = False
    # Enrichi avec l'état du circuit breaker (closed/open/half_open + retry_in_s)
    circuit_status = _ollama_circuit.get_status()
    return Response(json.dumps({"running": running, **circuit_status}), mimetype="application/json")

@limiter.limit("30 per minute")
@app.route("/api/vram", methods=["GET"])
def api_vram():
    """Retourne les modèles Ollama chargés en VRAM via /api/ps."""
    import urllib.request as _ur
    # VRAM totale réelle via pynvml
    try:
        import pynvml as _nv
        _nv.nvmlInit()
        _h = _nv.nvmlDeviceGetHandleByIndex(0)
        vram_cap = _nv.nvmlDeviceGetMemoryInfo(_h).total
    except Exception:
        vram_cap = 0
    try:
        with _ur.urlopen("http://127.0.0.1:11434/api/ps", timeout=3) as r:
            data = json.loads(r.read())
        models = []
        total_vram = 0
        total_swap = 0
        for m in data.get("models", []):
            sv       = m.get("size_vram", 0)
            st       = m.get("size", 0)
            swap     = max(0, st - sv)
            name     = m.get("name", "?")
            nl       = name.lower()
            is_embed = "embed" in nl
            details  = m.get("details", {})
            quant    = details.get("quantization_level", "")
            params   = details.get("parameter_size", "")
            expires  = m.get("expires_at", "")
            if is_embed:
                role = "RAG"
            elif _CODE_REASONING_ANALYSIS_MODEL.lower().split(":")[0] in nl:
                role = "C·R"
            elif _CODE_MODEL.lower().split(":")[0] in nl:
                role = "CODE"
            elif _GENERAL_MODEL.lower().split(":")[0] in nl:
                role = "GÉNÉRAL"
            else:
                role = "SOC"
            pct = round(sv / vram_cap * 100, 1) if vram_cap else 0
            total_vram += sv
            if not is_embed:
                total_swap += swap
            models.append({"name": name, "size_vram": sv, "size_swap": swap,
                           "is_embed": is_embed, "role": role,
                           "pct": pct, "quant": quant, "params": params, "expires_at": expires})
        return Response(json.dumps({
            "models": models, "total_vram": total_vram,
            "total_swap": total_swap, "vram_total_bytes": vram_cap,
            "active_model": MODEL,
            "tokens_per_sec": _last_toks_per_sec,
            "num_ctx": LLM_PARAMS.get("num_ctx", 0),
        }), mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"models": [], "total_vram": 0, "total_swap": 0,
                                    "vram_total_bytes": vram_cap, "active_model": MODEL, "error": str(e)}),
                        mimetype="application/json")

@limiter.limit("60 per minute")
@app.route("/api/prompt-profiles", methods=["GET"])
def api_prompt_profiles_get():
    try:
        profiles = json.loads(PROMPT_PROFILES_FILE.read_text(encoding="utf-8-sig")) if PROMPT_PROFILES_FILE.exists() else {}
    except (OSError, ValueError):
        profiles = {}
    return Response(json.dumps(profiles), mimetype="application/json")

@limiter.limit("20 per minute")
@app.route("/api/prompt-profiles", methods=["POST"])
def api_prompt_profiles_save():
    data = request.json or {}
    name    = data.get("name", "").strip()
    content = data.get("content", "")
    if not name:
        return Response('{"error":"name required"}', status=400, mimetype="application/json")
    try:
        profiles = json.loads(PROMPT_PROFILES_FILE.read_text(encoding="utf-8-sig")) if PROMPT_PROFILES_FILE.exists() else {}
    except (OSError, ValueError):
        profiles = {}
    entry = {"content": content, "saved_at": time.strftime("%Y-%m-%d %H:%M")}
    locked = data.get("locked_provider", "")
    if locked:
        entry["locked_provider"] = locked
    profiles[name] = entry
    PROMPT_PROFILES_FILE.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    return Response('{"ok":true}', mimetype="application/json")

@limiter.limit("10 per minute")
@app.route("/api/prompt-profiles/<name>", methods=["DELETE"])
def api_prompt_profiles_delete(name):
    try:
        profiles = json.loads(PROMPT_PROFILES_FILE.read_text(encoding="utf-8-sig")) if PROMPT_PROFILES_FILE.exists() else {}
        profiles.pop(name, None)
        PROMPT_PROFILES_FILE.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING delete_prompt_profile: {e}")
    return Response('{"ok":true}', mimetype="application/json")

# ── Message de bienvenue ──────────────────────────────────────
@limiter.limit("60 per minute")
@app.route("/api/welcome", methods=["GET"])
def api_welcome_get():
    global _welcome_data
    _welcome_data = _load_welcome()
    return Response(json.dumps(_welcome_data, ensure_ascii=False), mimetype="application/json")

@limiter.limit("20 per minute")
@app.route("/api/welcome", methods=["POST"])
def api_welcome_post():
    global _welcome_data
    data = request.get_json(force=True)
    _welcome_data.update(data)
    _welcome_data["last_updated"] = datetime.date.today().isoformat()
    WELCOME_FILE.write_text(json.dumps(_welcome_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return Response('{"ok":true}', mimetype="application/json")

@limiter.limit("10 per minute")
@app.route("/api/welcome/reset", methods=["POST"])
def api_welcome_reset():
    global _welcome_data
    _welcome_data = dict(DEFAULT_WELCOME)
    WELCOME_FILE.write_text(json.dumps(_welcome_data, indent=2, ensure_ascii=False), encoding="utf-8")
    return Response('{"ok":true}', mimetype="application/json")

@limiter.limit("5 per minute")
@app.route("/api/welcome/evolve", methods=["POST"])
def api_welcome_evolve():
    """Demande à l'IA d'enrichir le message en fonction des nouveautés."""
    global _welcome_data
    data = request.get_json(force=True)
    context = data.get("context", "")
    current = "\n".join(_welcome_data.get("lines", []))
    prompt = (
        f"Tu es JARVIS, IA personnelle de Marc. "
        f"Voici le message d'accueil actuel:\n{current}\n\n"
        f"Nouveauté à intégrer: {context}\n\n"
        f"Réécris le message d'accueil en JSON avec la clé 'lines' (liste de strings). "
        f"Garde le ton JARVIS: sobre, technique, immersif, en français. "
        f"Max 15 lignes. Réponds UNIQUEMENT avec le JSON."
    )
    try:
        resp = _ollama_circuit.call(req.post, f"{OLLAMA_URL}/api/generate",
                        json={"model": MODEL, "prompt": prompt, "stream": False, "keep_alive": 0},
                        timeout=60)
        text = resp.json().get("response", "")
        m = re.search(r'\{[\s\S]*"lines"[\s\S]*\}', text)
        if m:
            parsed = json.loads(m.group())
            _welcome_data["lines"] = parsed["lines"]
            _welcome_data["last_updated"] = datetime.date.today().isoformat()
            _welcome_data["updated_by"] = "IA"
            WELCOME_FILE.write_text(json.dumps(_welcome_data, indent=2, ensure_ascii=False), encoding="utf-8")
            return Response(json.dumps({"ok": True, "data": _welcome_data}, ensure_ascii=False), mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"ok": False, "error": str(e)}), mimetype="application/json")
    return Response('{"ok":false,"error":"parse failed"}', mimetype="application/json")

# ── Tuile system — diagnostics matériel/OS/LLM /api/sysdiag ───────────────
# Refactor jarvis.py étape 3 (2026-05-23) : passage à l'architecture par
# tuiles. La route, les fonctions _diag_* et l'agrégation transverse vivent
# désormais dans scripts/system/ (tuile autoportante, zéro import vers
# jarvis). Ici, l'ossature se contente d'injecter les dépendances + enregistrer
# le Blueprint.
_system.init(
    speak          = lambda *a, **k: speak(*a, **k),
    limiter        = limiter,
    ollama_url     = OLLAMA_URL,
    memory_file    = MEMORY_FILE,
    nvml_handle    = _nvml_handle,
    memory_limit   = MEMORY_LIMIT,
    get_model      = lambda: MODEL,
    get_voice      = lambda: VOICE,
    get_dsp_avail  = lambda: _DSP_AVAILABLE,
    get_dsp_params = lambda: DSP_PARAMS,
    get_df_status  = _df.get_status,
)
app.register_blueprint(_system.bp)

TERMINAL_CWD  = [str(Path(__file__).parent)]  # liste pour mutabilité — utilisé par tâches planifiées
TASKS_FILE    = Path(__file__).parent / "jarvis_tasks.json"

# ── STT — Transcription vocale locale (Whisper) ───────────────
# Logique métier dans `stt.py` (Phase 3 split monolithe · session 33)
@limiter.limit("10 per minute")
@app.route("/api/stt", methods=["POST"])
def api_stt():
    """Transcription audio → texte via Whisper local (hors-ligne)."""
    if request.content_length and request.content_length > _stt.get_max_bytes():
        return Response(json.dumps({"error": "Fichier trop volumineux (max 25 MB)"}), status=413, mimetype="application/json")
    if _stt.is_available() is False:
        return Response(json.dumps({"error": "faster-whisper non installé. Lancez: pip install faster-whisper"}),
                        status=503, mimetype="application/json")
    f = request.files.get("audio")
    if not f:
        return Response(json.dumps({"error": "Aucun fichier audio"}), status=400, mimetype="application/json")
    lang = request.form.get("lang", "fr")
    raw_ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else "webm"
    suffix = "." + (raw_ext if raw_ext in _stt.get_allowed_ext() else "webm")
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        os.close(tmp_fd)
        f.save(tmp_path)
        text, language = _stt.transcribe(tmp_path, lang=lang)
        return Response(json.dumps({"text": text, "language": language}, ensure_ascii=False),
                        mimetype="application/json")
    except RuntimeError as e:
        return Response(json.dumps({"error": str(e)}), status=503, mimetype="application/json")
    except Exception as e:
        _log.error(f"[STT] Erreur: {e}")
        return Response(json.dumps({"error": "Erreur interne serveur"}), status=500, mimetype="application/json")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # fichier temporaire déjà supprimé ou accès refusé — non bloquant

@limiter.limit("60 per minute")
@app.route("/api/stt/status")
def api_stt_status():
    """État du module STT."""
    return Response(json.dumps({
        "available": _stt.is_available(),
        "loaded": _stt.is_loaded(),
        "model": _stt.get_model_size() if _stt.is_available() else None
    }), mimetype="application/json")

# ── Vision — logique métier dans `vision.py` (Phase 3 module 5) ──────────────
@limiter.limit("5 per minute")
@app.route("/api/vision", methods=["POST"])
def api_vision():
    """Pipeline vision gemma4 multimodal — analyse image en un seul passage.
    Body: {image_b64, prompt, pipeline=true}.
    pipeline=false : mode direct (prompt simple)."""
    data      = request.json or {}
    image_b64 = data.get("image_b64", "")
    prompt    = data.get("prompt", "").strip()
    pipeline  = data.get("pipeline", True)
    if not image_b64:
        return Response(json.dumps({"error": "image_b64 manquante"}), status=400, mimetype="application/json")
    if "," in image_b64:
        header, image_b64 = image_b64.split(",", 1)
        allowed_mime = ("image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp")
        if not any(m in header for m in allowed_mime):
            return Response(json.dumps({"error": "Format image non supporté (jpeg/png/gif/webp/bmp)"}), status=400, mimetype="application/json")
    if pipeline:
        user_q = prompt or "Analyse cette image et donne tes observations détaillées."
        system = _rag_inject(_vision.DEFAULT_PIPELINE_SYSTEM, user_q)
        gen = _vision.stream_pipeline(OLLAMA_URL, image_b64, system, user_q, _OLLAMA_VISION_TIMEOUT_S)
    else:
        gen = _vision.stream_direct(OLLAMA_URL, image_b64, prompt, _OLLAMA_VISION_TIMEOUT_S)
    return Response(gen, mimetype="text/event-stream", headers=_SSE_HEADERS)

# ── CODE REASONING — endpoint polling ────────────────────────
@app.route("/api/cr-poll/<task_id>")
@limiter.limit("120 per minute")
def cr_poll(task_id):
    task = _cr_tasks.get(task_id)
    if not task:
        return Response('{"error":"not found"}', status=404, mimetype="application/json")
    return Response(json.dumps({"status": task["status"], "text": task["text"]}),
                    mimetype="application/json")

# ── Gestionnaire de tâches ────────────────────────────────────
import uuid as _uuid


def _load_tasks():
    try:
        if TASKS_FILE.exists():
            return json.loads(TASKS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING load_tasks: {e}")
    return []

def _save_tasks(tasks):
    TASKS_FILE.write_text(json.dumps(tasks, indent=2, ensure_ascii=False), encoding="utf-8")

@limiter.limit("60 per minute")
@app.route("/api/tasks", methods=["GET"])
def api_tasks_get():
    return Response(json.dumps(_load_tasks(), ensure_ascii=False), mimetype="application/json")

@limiter.limit("30 per minute")
@app.route("/api/tasks", methods=["POST"])
def api_tasks_post():
    data  = request.json or {}
    tasks = _load_tasks()
    tid   = data.get("id") or str(_uuid.uuid4())[:8]
    # Limiter la longueur du cmd et supprimer les null bytes (protection injection)
    raw_cmd = str(data.get("cmd", "")).replace('\x00', '').strip()[:500]
    if "cmd" in data and not raw_cmd:
        return Response('{"error":"Commande vide"}', status=400, mimetype="application/json")
    task  = next((t for t in tasks if t["id"] == tid), None)
    if task:
        if "cmd" in data:
            data["cmd"] = raw_cmd
        task.update({k: v for k, v in data.items() if k != "id"})
    else:
        tasks.append({
            "id":       tid,
            "name":     data.get("name", "Tâche"),
            "cmd":      raw_cmd,
            "schedule": data.get("schedule", ""),  # "*/5 * * * *" ou "manual"
            "enabled":  data.get("enabled", True),
            "notify":   data.get("notify", True),  # notifier dans le chat
            "last_run": None,
            "last_out": "",
            "last_err": "",
            "status":   "idle",
        })
    _save_tasks(tasks)
    return Response(json.dumps({"ok": True, "id": tid}), mimetype="application/json")

@limiter.limit("20 per minute")
@app.route("/api/tasks/<tid>", methods=["DELETE"])
def api_tasks_delete(tid):
    tasks = [t for t in _load_tasks() if t["id"] != tid]
    _save_tasks(tasks)
    return Response('{"ok":true}', mimetype="application/json")

@limiter.limit("10 per minute")
@app.route("/api/tasks/<tid>/run", methods=["POST"])
def api_tasks_run(tid):
    tasks = _load_tasks()
    task  = next((t for t in tasks if t["id"] == tid), None)
    if not task:
        return Response('{"error":"Tâche introuvable"}', status=404, mimetype="application/json")
    cmd = task.get("cmd", "").strip()
    if not cmd:
        return Response('{"error":"Commande vide"}', status=400, mimetype="application/json")
    task["status"]   = "running"
    task["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_tasks(tasks)
    try:
        # shell=True intentionnel : les commandes utilisateur peuvent contenir pipes/redirections
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           cwd=TERMINAL_CWD[0], timeout=_TERMINAL_TIMEOUT_S, encoding="utf-8", errors="replace")
        task["last_out"] = r.stdout[:4000]
        task["last_err"] = r.stderr[:2000]
        if r.returncode != 0:
            _log.error(f"[JARVIS] tasks_run '{task.get('name',tid)}' — returncode={r.returncode} err={r.stderr[:200]!r}")
        task["status"]   = "ok" if r.returncode == 0 else "error"
    except Exception as e:
        _log.error(f"[JARVIS] tasks_run error: {e}")
        task["last_err"] = "Erreur d'exécution"
        task["status"]   = "error"
    _save_tasks(tasks)
    return Response(json.dumps({"ok": True, "output": task["last_out"], "error": task["last_err"], "status": task["status"]}, ensure_ascii=False), mimetype="application/json")

# ── Web Search (DuckDuckGo HTML) ──────────────────────────────
_WEB_HEADERS = {
    "User-Agent": "JARVIS/3.0 (personal-assistant; fr)",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

def _web_search_ddg(query: str, max_results: int) -> list:
    """DuckDuckGo Instant Answer API — pas de scraping HTML."""
    try:
        r = req.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_redirect": "1",
                    "no_html": "1", "skip_disambig": "1", "kl": "fr-fr"},
            headers=_WEB_HEADERS, timeout=_WEB_SEARCH_TIMEOUT_S
        )
        d = r.json()
        results = []
        abstract = (d.get("AbstractText") or d.get("Abstract") or "").strip()
        if abstract:
            results.append(f"[{d.get('AbstractSource','DDG')}] {abstract[:400]}")
        answer = d.get("Answer", "").strip()
        if answer and answer not in abstract:
            results.append(f"[Réponse directe] {answer}")
        definition = d.get("Definition", "").strip()
        if definition and definition not in abstract:
            results.append(f"[Définition] {definition}")
        for topic in d.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                txt = topic["Text"].strip()
                if txt and len(results) < max_results + 2:
                    results.append(f"• {txt[:200]}")
        return results
    except Exception:
        return []  # Fallback Wikipedia


def web_search(query: str, max_results: int = 5) -> str:
    """Recherche web combinée : DuckDuckGo + Wikipedia FR fallback."""
    results = _web_search_ddg(query, max_results)

    try:
        r2 = req.get(
            "https://fr.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": query, "limit": max_results,
                    "namespace": "0", "format": "json"},
            headers=_WEB_HEADERS, timeout=_WEB_FETCH_TIMEOUT_S
        )
        data = r2.json()
        titles   = data[1] if len(data) > 1 else []
        snippets = data[2] if len(data) > 2 else []
        for t, s in zip(titles, snippets, strict=False):
            if t and t not in str(results):
                entry = f"[Wikipedia] {t}"
                if s: entry += f": {s}"
                results.append(entry)
                if len(results) >= max_results + 3:
                    break
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING web_search Wikipedia: {e}")

    if not results:
        return f"[Aucun résultat web trouvé pour: {query}]"
    return (
        f"=== RÉSULTATS WEB ({len(results)} sources) ===\n"
        + "\n".join(results[:max_results + 2])
        + "\n====================="
    )


@limiter.limit("10 per minute")
@app.route("/api/web-test", methods=["GET"])
def api_web_test():
    """Teste la connectivité web et les moteurs de recherche."""
    result = {"connectivity": False, "ddg": False, "wikipedia": False,
              "latency_ms": None, "results_count": 0, "search_ok": False, "error": None}

    # Connectivité générale
    try:
        t0 = time.time()
        r = req.get("https://www.google.com", timeout=_WEB_CONN_TIMEOUT_S, allow_redirects=True)
        result["connectivity"] = r.status_code < 500
        result["latency_ms"] = round((time.time() - t0) * 1000)
    except Exception as e:
        result["error"] = str(e)

    # DDG Instant Answer API (celui qu'on utilise réellement)
    try:
        r2 = req.get("https://api.duckduckgo.com/",
                     params={"q": "intelligence artificielle", "format": "json",
                             "no_redirect": "1", "no_html": "1"},
                     headers=_WEB_HEADERS, timeout=_WEB_FETCH_TIMEOUT_S)
        d2 = r2.json()
        result["ddg"] = bool(d2.get("AbstractText") or d2.get("RelatedTopics") or d2.get("Answer"))
    except Exception as e:
        result["ddg_error"] = str(e)

    # Wikipedia FR
    try:
        r3 = req.get("https://fr.wikipedia.org/w/api.php",
                     params={"action": "opensearch", "search": "intelligence artificielle",
                             "limit": 2, "format": "json"},
                     headers=_WEB_HEADERS, timeout=_WEB_FETCH2_TIMEOUT_S)
        data = r3.json()
        result["wikipedia"] = len(data[1]) > 0 if len(data) > 1 else False
    except Exception as e:
        result["wikipedia_error"] = str(e)

    # Test de recherche réelle avec web_search()
    try:
        res = web_search("intelligence artificielle", max_results=3)
        result["search_ok"] = not res.startswith("[Aucun") and len(res) > 40
        result["results_count"] = res.count("\n") if result["search_ok"] else 0
        result["sample"] = res[:250]
    except Exception as e:
        result["search_error"] = str(e)

    return Response(json.dumps(result, ensure_ascii=False), mimetype="application/json")

# Listes SOC keywords déplacées dans chat_soc_inject.py — alias backward-compat
_CHAT_SOC_KW       = _chat_soc.SOC_KW
_CHAT_SOC_VOCAL_KW = _chat_soc.SOC_VOCAL_KW

_CHAT_PVE_KW = _pve_api.CHAT_PVE_KW  # alias backward-compat

# Fonctions Proxmox API déplacées dans proxmox_api.py — alias backward-compat
_pve_fetch_state     = _pve_api.fetch_state
_pve_context_summary = _pve_api.context_summary
_chat_inject_pve     = _pve_api.chat_inject


def _chat_inject_soc(system, last_user, is_vocal, soc_ctx_injected, force_soc=False):
    """Wrapper DI — délègue à chat_soc_inject.inject() avec les helpers monitoring
    + l'agrégat defense_24h.json (bloc compact KPI/top/heatmap pré-calculé)."""
    return _chat_soc.inject(
        system, last_user, is_vocal, soc_ctx_injected, force_soc,
        fetch_monitoring_fn=_fetch_monitoring,
        build_monitoring_context_fn=_build_monitoring_context,
        fetch_defense_fn=_fetch_defense,
    )

# _chat_build_messages déplacé dans chat_messages.py — alias backward-compat
_chat_build_messages = _chat_msg.build_messages

# Mapping tool name → (host_label, ssh_fn) — pour capture pending APT (couplage _ssh_*)
_APT_HOST_MAP = {
    "commande_ssh_clt":     ("clt",      _ssh_clt),
    "commande_ssh_pa85":    ("pa85",     _ssh_pa85),
    "commande_ssh_ngix":    ("srv-ngix", _ssh_ngix),
    "commande_ssh_proxmox": ("proxmox",  _ssh_proxmox),
}

def _run_tool_calls(messages: list, active_model):
    """Wrapper DI — délègue à chat_tool_calls.run_tool_calls() avec runtime deps."""
    yield from _chat_tools.run_tool_calls(
        messages, active_model,
        call_llm_with_tools_fn=call_llm_with_tools,
        execute_tool_fn=execute_tool,
        tool_dispatch=_TOOL_DISPATCH,
        apt_host_map=_APT_HOST_MAP,
        pending_infra_cmd=_pending_infra_cmd,
        parse_upgradable_packages_fn=_sec.parse_upgradable_packages,
        log_info_fn=_log.info,
        now_fn=time.time,
        tool_call_max=_TOOL_CALL_MAX,
        tool_result_trunc=_TOOL_RESULT_TRUNC,
    )


def _build_llm_opts(np_override, soc_ctx_injected: bool, soc_trigger: bool, active_model, msg_len: int = 0):
    """Wrapper DI — délègue à llm_opts.build_llm_opts() avec constantes runtime."""
    return _llm_opts_mod.build_llm_opts(
        np_override, soc_ctx_injected, soc_trigger, active_model, msg_len,
        default_model=MODEL,
        llm_params=LLM_PARAMS,
        soc_temperature=_SOC_TEMPERATURE,
        soc_num_ctx=_SOC_NUM_CTX,
        num_ctx_short=_NUM_CTX_SHORT,
        reasoning_np_min=_REASONING_NP_MIN,
    )


def _stream_tokens_tts(messages: list, active_model, opts):
    """Wrapper DI — délègue à stream_tokens.stream_tokens_tts() avec stream_llm + _clean_for_tts."""
    yield from _stream_tokens_mod.stream_tokens_tts(
        messages, active_model, opts,
        stream_llm_fn=stream_llm,
        clean_text_fn=_clean_for_tts,
        phrase_min=_TTS_PHRASE_MIN,
    )


def _flush_deferred_speak():
    """Wrapper DI — délègue à deferred_speak.flush_deferred_speak() avec la queue runtime."""
    yield from _deferred_speak.flush_deferred_speak(_speak_deferred)


# ── CODE REASONING — pipeline polling (tâches background) ────────────────────
# Code Reasoning déplacé dans code_reasoning.py — alias backward-compat
_cr_tasks = _cr_mod.tasks  # state partagé (utilisé par /api/cr-poll/<task_id>)

def _code_reasoning_gen(messages, np_override):
    """Wrapper DI — délègue à code_reasoning.code_reasoning_gen() avec deps runtime."""
    return _cr_mod.code_reasoning_gen(
        messages, np_override,
        ensure_vram_fn=_ensure_vram,
        model=_CODE_REASONING_ANALYSIS_MODEL,
        system_suffix=_CODE_SYSTEM_SUFFIX,
        ollama_url=OLLAMA_URL,
        llm_params=LLM_PARAMS,
    )


def _chat_stream_inner(ctx: "LlmCtx", no_tools=False, temp_override=None):
    """Wrapper DI — délègue à chat_stream.stream_inner() avec runtime helpers."""
    yield from _chat_stream_mod.stream_inner(
        ctx, no_tools, temp_override,
        ensure_vram_fn=_ensure_vram,
        run_tool_calls_fn=_run_tool_calls,
        build_llm_opts_fn=_build_llm_opts,
        stream_tokens_tts_fn=_stream_tokens_tts,
        flush_deferred_speak_fn=_flush_deferred_speak,
    )

# ── Détection commandes VM Proxmox (bypass LLM) ───────────────
# Lookup dynamique via API Proxmox — plus de liste hardcodée
# ── Bypass Proxmox/VM/reboot/update — logique dans bypass_proxmox.py (Phase 3 module 8) ──
# Mappings COUPLÉS aux fonctions SSH (restent ici)
_pending_reboot: dict = {}  # {host, ssh_fn, is_proxmox, ts} — reboot différé après upgrade

# Mapping VMID → (host_label, ssh_fn) pour vérification post-start (couplage _ssh_*)
_VM_START_SSH_MAP: dict[int, tuple] = {
    101: ("srv-dev-1", _ssh_dev1),
    106: ("srv-clt",   _ssh_clt),
    107: ("srv-pa85",  _ssh_pa85),
    108: ("srv-ngix",  _ssh_ngix),
}

# Hôtes pour update/reboot — couplé _ssh_*
_UPDATE_REBOOT_HOSTS = [
    (["srv-nginx", "srv-ngix"],          "srv-ngix",  _ssh_ngix,    False),
    (["srv-clt",  "clt"],                "srv-clt",   _ssh_clt,     False),
    (["srv-pa85", "pa85"],               "srv-pa85",  _ssh_pa85,    False),
    (["srv-dev-1", "srv-dev", "dev-1"],  "srv-dev-1", _ssh_dev1,    False),
    (["proxmox",  "pve", "hyperviseur"], "proxmox",   _ssh_proxmox, True),
]

# Regex restart service — construite avec _SVC_BOUNCER local
_SVC_RESTART_RE = _bypass_pve.make_svc_restart_re(_SVC_BOUNCER)

def _detect_service_restart(text):
    """Retourne (host_label, ssh_func, svc_name) si restart service détecté, sinon None.
    Couplage _ssh_* → reste dans jarvis.py."""
    m = _SVC_RESTART_RE.search(text)
    if not m:
        return None
    svc_raw = m.group(2).lower()
    if svc_raw == "nginx":
        return ("srv-ngix", _ssh_ngix, "nginx")
    if svc_raw == "crowdsec":
        return ("srv-ngix", _ssh_ngix, "crowdsec")
    if svc_raw == _SVC_BOUNCER:
        return ("srv-ngix", _ssh_ngix, _SVC_BOUNCER)
    if svc_raw == "suricata":
        return ("srv-ngix", _ssh_ngix, "suricata")
    if svc_raw == "fail2ban":
        return ("srv-ngix", _ssh_ngix, "fail2ban")
    # apache / apache2 / php — host requis
    svc_name = "php" if svc_raw == "php" else "apache2"
    if re.search(r'\bclt\b', text, re.I):
        return ("clt", _ssh_clt, svc_name)
    if re.search(r'\bpa85\b', text, re.I):
        return ("pa85", _ssh_pa85, svc_name)
    return ("ambiguous", None, svc_name)


def _detect_vm_command(text):
    """Wrapper qui injecte vms_api depuis _pve_fetch_state() puis délègue."""
    state = _pve_fetch_state()
    vms_api = state.get("vms", []) if state else []
    return _bypass_pve.detect_vm_command(text, vms_api)


def _detect_reboot_command(text: str):
    """Wrapper qui injecte _UPDATE_REBOOT_HOSTS puis délègue."""
    return _bypass_pve.detect_reboot_command(text, _UPDATE_REBOOT_HOSTS)


def _detect_update_command(text: str):
    """Wrapper qui injecte _UPDATE_REBOOT_HOSTS puis délègue."""
    return _bypass_pve.detect_update_command(text, _UPDATE_REBOOT_HOSTS)


def _vm_execute_one(action, vmid, vmname):
    """Exécute qm action sur une VM et vérifie l'état post-commande."""
    try:
        r  = subprocess.run(_SSH_PROXMOX + [f"qm {action} {vmid}"],
                            capture_output=True, text=True, timeout=_SSH_PROXMOX_CMD_TIMEOUT_S)
        ok = r.returncode == 0
        output = r.stdout.strip() or r.stderr.strip() or ""
    except Exception as e:
        ok, output = False, str(e)
    real_state = ""
    try:
        rs = subprocess.run(_SSH_PROXMOX + [f"qm status {vmid}"],
                            capture_output=True, text=True, timeout=_SSH_PROXMOX_STATE_TIMEOUT_S)
        real_state = rs.stdout.strip().lower()  # ex: "status: stopped"
    except Exception:
        pass  # vérification post-action facultative
    if ok:
        verb  = "arrêtée" if action == "stop" else "démarrée"
        state = real_state.replace("status:", "").strip() if real_state else ("stopped" if action == "stop" else "running")
        return ok, f"VM {vmname} ({vmid}) {verb}. État : {state}\n", verb, state
    return False, f"Erreur SSH {vmname} : {output[:200]}\n", "", ""


def _vm_command_sse(action, vm_list):
    """Exécute qm stop/start sur Proxmox pour une ou plusieurs VMs — bypass LLM.
    SSH direct sans _SSH_LOCK pour éviter les blocages du monitoring concurrent."""
    if vm_list == "dynamic":
        state = _pve_fetch_state()
        if not state:
            _err = json.dumps({"type": "token", "token": "Erreur : API Proxmox inaccessible — commande annulée.\n", "done": True})
            yield "data: " + _err + "\n\n"
            return
        target_status = "running" if action == "stop" else "stopped"
        vm_list = [
            (v["vmid"], v.get("name", f"vm{v['vmid']}"))
            for v in state.get("vms", [])
            if v.get("status") == target_status and v.get("vmid") not in _bypass_pve.PVE_STOP_BLACKLIST
        ]
        if not vm_list:
            _txt = "Aucune VM en cours d'exécution à arrêter.\n" if action == "stop" else "Aucune VM arrêtée à démarrer.\n"
            yield "data: " + json.dumps({"type": "token", "token": _txt, "done": True}) + "\n\n"
            return
    results = []
    for vmid, vmname in vm_list:
        intro = f"Exécution : qm {action} {vmid} ({vmname})...\n"
        yield f"data: {json.dumps({'type': 'token', 'token': intro, 'done': False})}\n\n"
        ok, result, verb, state = _vm_execute_one(action, vmid, vmname)
        results.append((vmname, ok, verb, state))
        yield f"data: {json.dumps({'type': 'token', 'token': result, 'done': False})}\n\n"
        if action == "start" and ok:
            check = _VM_START_SSH_MAP.get(vmid)
            if check:
                host_lbl, ssh_fn_vm = check
                yield from _post_start_verify_sse(host_lbl, ssh_fn_vm)
    ok_parts   = [f"VM {n} {v}, état {s}" for n, ok, v, s in results if ok]
    fail_parts = [f"VM {n} en erreur"     for n, ok, v, s in results if not ok]
    summary    = ". ".join(ok_parts + fail_parts) + "." if (ok_parts or fail_parts) else "Opération terminée."
    yield f"data: {json.dumps({'type': 'token', 'token': '', 'done': True})}\n\n"
    yield f"data: {json.dumps({'type': 'speak', 'text': summary})}\n\n"


def _post_start_verify_sse(host_label: str, ssh_fn):
    """Polling SSH + vérification services après start ou reboot — fonction commune."""
    time.sleep(20)
    ssh_ok = False
    for _ in range(12):
        try:
            ok_ping, _ = ssh_fn("echo OK", timeout=6)
            if ok_ping:
                ssh_ok = True
                break
        except Exception:
            pass  # VM pas encore accessible — retry dans la boucle
        time.sleep(8)
    if not ssh_ok:
        yield _sse_tok(f"✗ **{host_label}** inaccessible après 2 minutes — vérification manuelle requise.\n", done=True)
        return
    _, uptime_out = ssh_fn("uptime -p 2>/dev/null || uptime", timeout=8)
    svcs = _bypass_pve.REBOOT_SVC_CHECKS.get(host_label, [])
    yield _sse_tok(f"**{host_label}** accessible — {(uptime_out or '').strip()}\n")
    if svcs:
        yield _sse_tok("Vérification des services :\n\n")
    all_ok = True
    for svc in svcs:
        _, svc_out = ssh_fn(f"systemctl is-active {svc}", timeout=10)
        status = (svc_out or "").strip().lower()
        if status == "active":
            icon = "✓"
        elif status == "activating":
            icon = "⟳"
        else:
            icon = "✗"
            all_ok = False
        yield _sse_tok(f"  {icon} **{svc}** : {status}\n")
    if all_ok and svcs:
        yield _sse_tok("\nTous les services sont actifs.\n")
    elif svcs:
        yield _sse_tok("\nCertains services sont en échec — vérification requise.\n")


def _update_machine_sse(host_label: str, ssh_fn, is_proxmox: bool = False):
    """apt-get update + upgrade -y sur un hôte SSH — bypass LLM. Détecte reboot requis."""
    global _pending_reboot
    if is_proxmox:
        yield _sse_tok("Mise à jour de l'hyperviseur **Proxmox** — VMs actives non affectées.\n\n")
    yield _sse_tok(f"apt-get update sur **{host_label}**...\n")
    ok_upd, out_upd = ssh_fn("apt-get update 2>&1 | tail -3", timeout=60)
    if not ok_upd:
        yield _sse_tok(f"Erreur apt-get update :\n{(out_upd or '')[:300]}\n", done=True)
        return
    yield _sse_tok("Index mis à jour.\n\napt-get dist-upgrade -y...\n")
    ok_upg, out_upg = ssh_fn(
        "DEBIAN_FRONTEND=noninteractive apt-get dist-upgrade -y 2>&1", timeout=_SSH_APT_TIMEOUT_S)
    if not ok_upg:
        yield _sse_tok(f"Erreur apt-get upgrade :\n{(out_upg or '')[:400]}\n", done=True)
        return
    updated = sum(1 for ln in (out_upg or "").splitlines()
                  if "Paramétrage de" in ln or "Setting up" in ln)
    yield _sse_tok(f"**{updated} paquet(s) mis à jour** sur **{host_label}**.\n\n")
    _, rb_out = ssh_fn(
        "test -f /var/run/reboot-required && echo REBOOT_NEEDED || echo NO_REBOOT", timeout=10)
    needs_reboot = "REBOOT_NEEDED" in (rb_out or "")
    if needs_reboot:
        _pending_reboot = {"host": host_label, "ssh_fn": ssh_fn, "is_proxmox": is_proxmox, "ts": time.time()}
        warn = "Proxmox — toutes les VMs s'arrêteront au reboot.\n" if is_proxmox else ""
        yield _sse_tok(
            f"**Redémarrage requis** sur **{host_label}**.\n{warn}"
            f"Réponds **`reboot maintenant`** ou **`reporter`**.\n", done=True)
        tts = f"Mise à jour de {host_label} terminée. Redémarrage requis. Reboot maintenant ou reporter ?"
    else:
        yield _sse_tok(f"Pas de redémarrage nécessaire. **{host_label}** est à jour.\n", done=True)
        tts = f"Mise à jour de {host_label} terminée, {updated} paquets installés."
    yield "data: " + json.dumps({"type": "speak", "text": tts}) + "\n\n"


def _pve_stop_vms_before_reboot(running):
    """Arrêt propre des VMs Proxmox avec polling confirmation — avant reboot hyperviseur."""
    yield _sse_tok(f"Arrêt propre de **{len(running)} VM(s)** avant redémarrage Proxmox...\n\n")
    for vmid, vmname in running:
        yield _sse_tok(f"  qm stop {vmid} ({vmname})...\n")
        try:
            r = subprocess.run(
                _SSH_PROXMOX + [f"qm stop {vmid}"],
                capture_output=True, text=True, timeout=_SSH_PROXMOX_CMD_TIMEOUT_S)
            if r.returncode != 0:
                yield _sse_tok(f"  ✗ {vmname} erreur : {(r.stderr or r.stdout).strip()[:100]}\n")
                continue
        except Exception as e:
            yield _sse_tok(f"  ✗ {vmname} exception : {str(e)[:100]}\n")
            continue
        vm_stopped = False
        for _ in range(10):
            time.sleep(6)
            try:
                rs = subprocess.run(
                    _SSH_PROXMOX + [f"qm status {vmid}"],
                    capture_output=True, text=True, timeout=8)
                if "stopped" in rs.stdout.lower():
                    vm_stopped = True
                    break
            except Exception:
                pass  # qm status non disponible — timeout géré après
        yield _sse_tok(f"  ✓ {vmname} arrêtée.\n" if vm_stopped else f"  ⚠ {vmname} timeout — statut non confirmé.\n")
    yield _sse_tok("\n")


def _reboot_machine_sse(pending: dict):
    """Exécute le reboot différé. Si Proxmox : arrêt propre de toutes les VMs avant reboot."""
    global _pending_reboot
    host   = pending["host"]
    ssh_fn = pending["ssh_fn"]
    is_pve = pending.get("is_proxmox", False)
    _pending_reboot.clear()
    running = []
    if is_pve:
        state = _pve_fetch_state()
        running = [
            (v["vmid"], v.get("name", f"vm{v['vmid']}"))
            for v in (state or {}).get("vms", [])
            if v.get("status") == "running" and v.get("vmid") not in _bypass_pve.PVE_STOP_BLACKLIST
        ]
        if running:
            yield from _pve_stop_vms_before_reboot(running)
        else:
            yield _sse_tok("Aucune VM en cours d'exécution — redémarrage direct.\n\n")
    yield _sse_tok(f"Redémarrage de **{host}**...\n")
    try:
        ssh_fn("reboot", timeout=8)
    except Exception:
        pass  # SSH se coupe pendant le reboot — comportement normal
    yield _sse_tok("Commande reboot envoyée. Vérification en cours...\n")
    yield from _post_start_verify_sse(host, ssh_fn)
    if is_pve and running:
        vm_names = ", ".join(f"**{name}**" for _, name in running)
        yield _sse_tok(
            f"\n⚠ Les VMs arrêtées ne redémarrent pas automatiquement.\n"
            f"Redémarre manuellement : {vm_names}\n")
        tts = "Redémarrage Proxmox terminé. Les VMs devront être redémarrées manuellement."
    else:
        tts = f"Redémarrage de {host} terminé, services vérifiés."
    yield _sse_tok("", done=True)
    yield "data: " + json.dumps({"type": "speak", "text": tts}) + "\n\n"


def _service_restart_sse(host_label, ssh_func, svc_name):
    """Restart service SSH — bypass LLM. systemctl restart → is-active → TTS garanti."""
    intro = "Redémarrage " + svc_name + " sur " + host_label + "...\n"
    yield "data: " + json.dumps({"type": "token", "token": intro, "done": False}) + "\n\n"
    try:
        ok_restart, err_restart = ssh_func(f"systemctl restart {svc_name}", timeout=_SYSTEMCTL_RESTART_TIMEOUT_S)
    except Exception as e:
        err_msg = "Erreur SSH : " + str(e) + "\n"
        tts_err = "Erreur SSH lors du redémarrage de " + svc_name + "."
        yield "data: " + json.dumps({"type": "token", "token": err_msg, "done": True}) + "\n\n"
        yield "data: " + json.dumps({"type": "speak", "text": tts_err}) + "\n\n"
        return
    try:
        _, state_out = ssh_func(f"systemctl is-active {svc_name}", timeout=_SYSTEMCTL_STATUS_TIMEOUT_S)
        state = (state_out or "").strip().lower()
    except Exception:
        state = "inconnu"
    if state == "active":
        msg = "**" + svc_name + " actif.**\n"
        tts = svc_name + " redémarré avec succès."
    elif not ok_restart:
        err_detail = (err_restart or "").strip()[:200]
        msg = "**Échec redémarrage " + svc_name + "** — état : " + (state or "inconnu") + ".\n"
        if err_detail:
            msg += "Erreur : " + err_detail + "\n"
        tts = "Échec du redémarrage de " + svc_name + ". Service " + (state or "inactif") + "."
    else:
        msg = "**" + svc_name + "** — état : " + (state or "inconnu") + ". Vérifier les logs.\n"
        tts = svc_name + " redémarré. État " + (state or "inconnu") + "."
    yield "data: " + json.dumps({"type": "token", "token": msg, "done": False}) + "\n\n"
    yield "data: " + json.dumps({"type": "token", "token": "", "done": True}) + "\n\n"
    yield "data: " + json.dumps({"type": "speak", "text": tts}) + "\n\n"


# _sse_tok et _sse_response déplacés dans sse_helpers.py — alias backward-compat
_sse_tok = _sse.sse_tok
_sse_response = _sse.sse_response


# ── Historique des échanges (API /api/history/last) ──────────────────────────
_LAST_EXCHANGES: deque = deque(maxlen=10)

def _capture_gen(gen, user_msg: str):
    """Wrapper DI — délègue à chat_capture.capture_gen() avec _LAST_EXCHANGES."""
    return _chat_capture.capture_gen(gen, user_msg, _LAST_EXCHANGES)


# ── Bypass : lecture/édition fichier sur VM ───────────────────────────────────
_FILE_VM_SSH = {
    "clt":      ("clt",      _ssh_clt),
    "srv-clt":  ("clt",      _ssh_clt),
    "pa85":     ("pa85",     _ssh_pa85),
    "srv-pa85": ("pa85",     _ssh_pa85),
    "ngix":     ("srv-ngix", _ssh_ngix),
    "nginx":    ("srv-ngix", _ssh_ngix),
    "srv-ngix": ("srv-ngix", _ssh_ngix),
    "proxmox":  ("proxmox",  _ssh_proxmox),
    "dev":      ("srv-dev-1",_ssh_dev1),
    "dev-1":    ("srv-dev-1",_ssh_dev1),
    "srv-dev":  ("srv-dev-1",_ssh_dev1),
    "srv-dev-1":("srv-dev-1",_ssh_dev1),
}
# Regex filesystem (FPATH_RE, FNAME_RE, FREAD_RE, FCORR_RE) déplacées dans bypass_filesystem.py
# Alias backward-compat pour _FCORR_RE (utilisé hors filesystem dans _detect_file_corrections)
_FCORR_RE = _bypass_fs.FCORR_RE

# ── Directives protégées contre les faux positifs LLM ────────────────────────
# Valeurs présentes dans l'original qui ne doivent JAMAIS être modifiées par le LLM.
# Extensible : ajouter ici tout nouveau faux positif découvert.
_PROTECTED_DIRECTIVES = {
    'ssl_prefer_server_ciphers',   # off = correct avec TLS 1.3 (Mozilla modern)
    # ssl_protocols retiré : le LLM améliore correctement (supprime TLSv1/TLSv1.1)
    # Ajouter ici tout nouveau faux positif découvert lors des tests
}

def _validate_protect_directives(original_content: str, llm_code: str):
    """Compare llm_code avec original_content et restaure les directives protégées.
    Retourne (code_corrigé, liste_descriptions_changements)."""
    changes = []
    result = llm_code
    for directive in _PROTECTED_DIRECTIVES:
        orig_m = re.search(
            r'^\s*' + re.escape(directive) + r'\s+(.+?)\s*;',
            original_content, re.M | re.I)
        if not orig_m:
            continue
        orig_value = orig_m.group(1).strip()
        llm_m = re.search(
            r'^(\s*' + re.escape(directive) + r'\s+)(.+?)(\s*;.*)$',
            result, re.M | re.I)
        if not llm_m:
            continue
        llm_value = llm_m.group(2).strip()
        if llm_value.lower() != orig_value.lower():
            result = (result[:llm_m.start(1)]
                      + llm_m.group(1) + orig_value + llm_m.group(3)
                      + result[llm_m.end():])
            changes.append(f'{directive} : `{llm_value}` → `{orig_value}` (restauré)')
    return result, changes

# _detect_file_command, _detect_multi_file_command, _file_command_sse :
# déplacés dans bypass_filesystem.py (Phase 3 module 7) — appelés via _bypass_fs.*
# Regex FEDIT_RE, FADD_RE, SUR_VM_RE sont maintenant dans bypass_filesystem.py


def _file_correct_gen(f_vm, f_ssh_fn, f_path, ctx: "LlmCtx"):
    """Lit un fichier SSH, affiche dans l'UI, puis génère la correction via LLM en un seul shot."""
    basename = f_path.rstrip('/').rsplit('/', 1)[-1]
    is_dir = f_path.endswith('/') or ('.' not in basename and basename != '')
    cmd = f"ls -la {f_path}" if is_dir else f"cat {f_path}"
    ok, content = f_ssh_fn(cmd)
    if not ok or not content:
        yield _sse_tok(f"Erreur : impossible de lire `{f_path}` sur {f_vm}.", done=True)
        return
    # 1. Signal mode "lis+corrige" → JS sait qu'un header ORIGINAL/CORRIGÉE doit être affiché
    yield f"data: {json.dumps({'type':'file_correct_start','path':f_path,'vm':f_vm})}\n\n"
    # 1b. Affiche le fichier dans l'UI (modal holographique)
    yield f"data: {json.dumps({'type':'ssh_file','vm':f_vm,'path':f_path,'content':content.rstrip(),'action':'read'})}\n\n"
    # 2. Injecte le contenu dans le dernier message utilisateur
    for i in range(len(ctx.messages) - 1, -1, -1):
        if ctx.messages[i].get("role") == "user":
            ctx.messages[i] = dict(ctx.messages[i])
            ctx.messages[i]["content"] = (
                ctx.messages[i]["content"]
                + f"\n\n[Contenu actuel de `{f_path}` sur {f_vm}, lu via SSH :]\n```\n{content.rstrip()}\n```"
                + "\n\nIMPORTANT : propose le fichier COMPLET corrigé, pas de résumé ni d'extrait. Reproduis l'intégralité du fichier avec les corrections appliquées. Décommente les directives qui sont commentées à tort (ex: gzip, multi_accept) si elles ont une valeur correcte."
                + "\nRÈGLE ABSOLUE : conserve TOUTES les valeurs existantes à l'identique sauf si elles contiennent une erreur de syntaxe ou une incohérence évidente avec le reste du fichier. NE MODIFIE PAS les paramètres selon tes préférences ou recommandations générales — ce fichier est une config de production délibérément choisie. Si une valeur te semble non-optimale mais est cohérente et fonctionnelle, reproduis-la EXACTEMENT telle quelle. Signale à la fin (hors du bloc de code) les seules modifications que tu as faites et pourquoi."
                + "\nEXCLUSIONS CRITIQUES (ne jamais modifier ces directives) : ssl_prefer_server_ciphers (off est délibéré et conforme Mozilla modern TLS 1.3), worker_processes si valeur numérique explicite (ne pas remplacer par auto)."
            )
            break
    # 3. Génère la réponse LLM — stream + accumulation pour validation post-génération
    original_content = content  # référence pour la validation
    full_llm_text = ""
    _chat_stream_active.set()
    try:
        for _sse in _chat_stream_inner(ctx, temp_override=0.15):
            yield _sse
            if _sse.startswith("data: "):
                try:
                    _d = json.loads(_sse[6:].strip())
                    if _d.get("type") == "token":
                        full_llm_text += _d.get("token", "")
                except Exception:
                    pass  # chunk SSE non-JSON — ignoré
    except Exception as exc:
        import traceback as _tb
        _log.error(f"[file_correct] stream error: {_tb.format_exc()}")
        yield f"data: {json.dumps({'type':'token','token':f'[JARVIS] Erreur interne : {exc}','done':True})}\n\n"
        return
    finally:
        _chat_stream_active.clear()
    # 4. Validation post-génération — restaure les directives protégées si le LLM les a modifiées
    code_blocks = re.findall(r'```(?:\w+)?\n?([\s\S]*?)```', full_llm_text)
    if code_blocks:
        llm_code = code_blocks[-1]
        fixed_code, changes = _validate_protect_directives(original_content, llm_code)
        if changes:
            _log.warning(f"[FILE_CORRECT_FIX] {len(changes)} faux positif(s) restauré(s) : {changes}")
            yield f"data: {json.dumps({'type':'file_correct_fix','code':fixed_code,'changes':changes})}\n\n"


def _file_correct_multi_inject(files, f_vm, ctx):
    """Injecte le contenu multi-fichiers dans le dernier message user du contexte LLM."""
    injected = f"\n\n[MULTI-FICHIERS — {len(files)} fichiers interconnectés sur {f_vm}]\n"
    injected += "Corrige chaque fichier en tenant compte de leurs dépendances (classes CSS partagées, IDs HTML ciblés par JS, chemins de ressources, etc.).\n\n"
    for f_path, content in files:
        ext = f_path.rsplit('.', 1)[-1].lower() if '.' in f_path else ''
        injected += f"### {f_path}\n```{ext}\n{content}\n```\n\n"
    injected += "\nIMPORTANT : pour chaque fichier, propose le contenu COMPLET corrigé dans un bloc de code séparé, dans le même ordre que ci-dessus."
    injected += "\nRÈGLE ABSOLUE : conserve les valeurs cohérentes et fonctionnelles. Corrige uniquement les bugs, failles de sécurité et mauvaises pratiques. Respecte les dépendances entre fichiers."
    injected += "\nEXCLUSIONS CRITIQUES (ne jamais modifier) : ssl_prefer_server_ciphers, worker_processes si valeur numérique explicite."
    for i in range(len(ctx.messages) - 1, -1, -1):
        if ctx.messages[i].get("role") == "user":
            ctx.messages[i] = dict(ctx.messages[i])
            ctx.messages[i]["content"] = ctx.messages[i]["content"] + injected
            break


def _file_correct_multi_gen(f_vm, f_ssh_fn, f_paths, ctx: "LlmCtx"):
    """Lit N fichiers SSH interconnectés, les affiche, puis génère les corrections en un shot."""
    files = []
    for f_path in f_paths:
        basename = f_path.rstrip('/').rsplit('/', 1)[-1]
        cmd = f"cat {f_path}" if '.' in basename else f"ls -la {f_path}"
        ok, content = f_ssh_fn(cmd)
        if ok and content:
            files.append((f_path, content.rstrip()))
        else:
            yield _sse_tok(f"⚠ Impossible de lire `{f_path}` sur {f_vm} — ignoré.\n", done=False)
    if not files:
        yield _sse_tok("Aucun fichier lu.", done=True)
        return
    # 1. Signal multi-fichiers → JS prépare l'affichage multi-sections
    yield f"data: {json.dumps({'type':'file_correct_start','path':f_paths[0],'vm':f_vm,'multi':True,'count':len(files)})}\n\n"
    # 2. Émettre chaque fichier original
    for f_path, content in files:
        yield f"data: {json.dumps({'type':'ssh_file','vm':f_vm,'path':f_path,'content':content,'action':'read'})}\n\n"
    # 3. Injecter contexte LLM multi-fichiers
    _file_correct_multi_inject(files, f_vm, ctx)
    # 4. Stream LLM + accumulation
    full_llm_text = ""
    _chat_stream_active.set()
    try:
        for _sse in _chat_stream_inner(ctx, temp_override=0.15):
            yield _sse
            if _sse.startswith("data: "):
                try:
                    _d = json.loads(_sse[6:].strip())
                    if _d.get("type") == "token":
                        full_llm_text += _d.get("token", "")
                except Exception:
                    pass  # chunk SSE non-JSON — ignoré
    except Exception as exc:
        _log.error(f"[file_correct_multi] stream error: {exc}")
        yield _sse_tok(f"Erreur : {exc}", done=True)
        return
    finally:
        _chat_stream_active.clear()
    # 5. Validation post-génération par fichier
    code_blocks = re.findall(r'```(?:\w+)?\n?([\s\S]*?)```', full_llm_text)
    all_changes = []
    for idx, (f_path, orig_content) in enumerate(files):
        if idx < len(code_blocks):
            _, changes = _validate_protect_directives(orig_content, code_blocks[idx])
            all_changes.extend([f'[{f_path.rsplit("/",1)[-1]}] {c}' for c in changes])
    if all_changes:
        _log.warning(f"[FILE_CORRECT_MULTI_FIX] {all_changes}")
        yield f"data: {json.dumps({'type':'file_correct_fix','code':'','changes':all_changes})}\n\n"


# ── Exécution de code sur srv-dev-1 (VM dev — CODE mode) ─────────────────────
# Règle absolue : uniquement _CODE_DEV_IP — zéro autre hôte
# Constantes srv-dev-1 déplacées dans bypass_code.py — alias backward-compat
_CODE_DEV_VM     = _bypass_code.CODE_DEV_VM
_CODE_DEV_IP     = _bypass_code.CODE_DEV_IP
_CODE_DEV_PORT   = _bypass_code.CODE_DEV_PORT
_CODE_DEV_KEY    = _bypass_code.CODE_DEV_KEY
_CODE_REMOTE_DIR = _bypass_code.CODE_REMOTE_DIR

# Carte SSH terminal déplacée dans ssh_terminal.py — alias backward-compat (utilisée par _ws_ssh_handler)
_SSH_TERMINAL_MAP = _ssh_term.TERMINAL_MAP
_dev_stats_cache: dict = {"ts": 0.0, "data": {}}

_STATS_CMD = r"""python3 -c '
import json, shutil
la = open("/proc/loadavg").read().split()
m = {}
for l in open("/proc/meminfo"):
    if ":" in l:
        k, v = l.split(":", 1)
        try: m[k.strip()] = int(v.strip().split()[0])
        except Exception: pass  # ligne /proc/meminfo non numérique — skip
mt = m.get("MemTotal",0)//1024
mf = (m.get("MemFree",0)+m.get("Buffers",0)+m.get("Cached",0)+m.get("SReclaimable",0))//1024
mu = mt-mf; mp = int(mu*100/mt) if mt else 0
du = shutil.disk_usage("/")
up = float(open("/proc/uptime").read().split()[0])
d=int(up//86400); h=int((up%86400)//3600); mn=int((up%3600)//60)
ut = f"{d}j {h}h" if d else f"{h}h {mn}m"
rx=tx=0
for l in open("/proc/net/dev"):
    if ":" not in l: continue
    iface,cols=l.strip().split(":",1); cols=cols.split()
    if iface.strip()=="lo": continue
    rx+=int(cols[0]); tx+=int(cols[8])
def hb(b): return f"{b//2**30}G" if b>=2**30 else f"{b//2**20}M" if b>=2**20 else f"{b//2**10}K"
print(json.dumps({"load1":la[0],"load5":la[1],"ram_used":mu,"ram_total":mt,"ram_pct":mp,
"disk_used":du.used//2**30,"disk_total":du.total//2**30,"disk_pct":int(du.used*100/du.total),
"uptime":ut,"net_rx":hb(rx),"net_tx":hb(tx)}))
'"""

# Regex/helpers code déplacés dans bypass_code.py (Phase 3 module 10)


# ── Bypass SSH terminal — regexes par hôte ────────────────────────────────────
# Regex + générateur SSH terminal déplacés dans ssh_terminal.py
_SSH_TERMINAL_RE = _ssh_term.TERMINAL_RE
_ssh_terminal_sse = _ssh_term.terminal_sse


# Wrappers DI vers bypass_code.py
def _detect_code_command(text: str):
    """Wrapper — délègue au module bypass_code."""
    return _bypass_code.detect_code_command(text)

def _code_scp_exec_sse(filename: str, exec_it: bool):
    """Wrapper — injecte _ssh_dev1 puis délègue au module bypass_code."""
    yield from _bypass_code.code_scp_exec_sse(filename, exec_it, _ssh_dev1)


# ── Bypass sauvegarde — logique dans bypass_backup.py (Phase 3 module 9) ──
# Wrappers DI : injectent _ALLOWED_SCRIPTS (couplé _WORKSPACE_ROOT)

def _detect_backup_command(text: str):
    """Wrapper — délègue au module bypass_backup."""
    return _bypass_bk.detect_backup_command(text)

def _backup_sse(script_key: str):
    """Wrapper — résout script_path depuis _ALLOWED_SCRIPTS puis délègue."""
    script_path = _ALLOWED_SCRIPTS.get(script_key, "")
    yield from _bypass_bk.backup_sse(script_path, script_key)

def _jarvis_backup_log_sse():
    """Wrapper — délègue au module (lit Desktop\\jarvis-backup.log)."""
    yield from _bypass_bk.jarvis_backup_log_sse()

def _jarvis_backup_sse():
    """Wrapper — résout script_path puis délègue."""
    script_path = _ALLOWED_SCRIPTS.get("backup-jarvis", "")
    yield from _bypass_bk.jarvis_backup_sse(script_path)


# _datetime_bypass_sse déplacé dans bypass_simple.py → utiliser _bypass_simple.datetime_sse()


def _apt_upgrade_bypass_sse(pending: dict):
    """Exécute l'apt upgrade en attente via SSH direct — zéro LLM."""
    host    = pending["host"]
    ssh_fn  = pending["ssh_fn"]
    pkgs    = pending["packages"]
    _pending_infra_cmd.clear()
    pkg_str = " ".join(pkgs)
    cmd     = f"DEBIAN_FRONTEND=noninteractive apt-get upgrade -y {pkg_str}"
    yield _sse_tok(f"Mise à jour de {len(pkgs)} paquet(s) sur **{host}** :\n")
    for p in pkgs:
        yield _sse_tok(f"  → {p}\n")
    yield _sse_tok("\n")
    _log.info(f"[BYPASS_APT] {host} → {cmd}")
    ok, output = ssh_fn(cmd, timeout=_SSH_APT_TIMEOUT_S)
    if ok:
        updated = sum(1 for ln in output.splitlines() if "Paramétrage de" in ln or "Setting up" in ln)
        yield _sse_tok(f"✓ {updated} paquet(s) mis à jour sur **{host}**.")
        tts_msg = f"Mise à jour Apache réussie sur {host}, {updated} paquets installés."
    else:
        yield _sse_tok(f"✗ Erreur sur **{host}** :\n{output[:400]}")
        tts_msg = f"Erreur lors de la mise à jour sur {host}."
    yield _sse_tok("", done=True)
    yield "data: " + json.dumps({"type": "speak", "text": tts_msg}) + "\n\n"


def _dev_exec_sse(cmd: str):
    """Mode terminal DEV — exécute une commande sur srv-dev-1, maintient _dev_cwd.
    Émet des events dev_output (rendu <pre> côté JS) — jamais de blocs markdown ``` ."""
    global _dev_cwd
    cmd = cmd.strip()
    if not cmd:
        yield _sse_tok("", done=True)
        return

    # cd : mise à jour cwd sans sortie visible
    cd_m = re.match(r'^cd\s*(.*)', cmd)
    if cd_m:
        target = cd_m.group(1).strip() or "/root"
        ok, out = _ssh_dev1(
            f"cd {shlex.quote(_dev_cwd)} 2>/dev/null && cd {target} 2>&1 && pwd",
            timeout=10)
        if ok and out and out.strip().startswith('/'):
            _dev_cwd = out.strip()
            yield f"data: {json.dumps({'type':'dev_cwd','cwd':_dev_cwd})}\n\n"
            yield f"data: {json.dumps({'type':'dev_output','prompt':f'root@srv-dev-1:{_dev_cwd} $','cmd':cmd,'output':''})}\n\n"
        else:
            err = (out or "").strip() or f"bash: cd: {target}: No such file or directory"
            yield f"data: {json.dumps({'type':'dev_output','prompt':f'root@srv-dev-1:{_dev_cwd} $','cmd':cmd,'output':err})}\n\n"
        yield _sse_tok("", done=True)
        return

    # Commande générale — capture le nouveau cwd via marqueur
    full_cmd = (
        f"cd {shlex.quote(_dev_cwd)} 2>/dev/null; "
        f"{cmd}; "
        "echo '__JARVIS_PWD__'\"$(pwd)\""
    )
    ok, out = _ssh_dev1(full_cmd, timeout=30)

    new_cwd = _dev_cwd
    if out and '__JARVIS_PWD__' in out:
        parts = out.rsplit('__JARVIS_PWD__', 1)
        out = parts[0].rstrip('\n')
        new_cwd = parts[1].strip() or _dev_cwd
    _dev_cwd = new_cwd

    output_text = out if ok else (out or "✗ Erreur SSH.")
    yield f"data: {json.dumps({'type':'dev_output','prompt':f'root@srv-dev-1:{_dev_cwd} $','cmd':cmd,'output':output_text})}\n\n"
    yield f"data: {json.dumps({'type':'dev_cwd','cwd':_dev_cwd})}\n\n"
    yield _sse_tok("", done=True)


def _chat_resolve_pending_bypass(orig_last: str):
    """Wrapper DI — délègue à chat_pending_bypass.resolve_pending_bypass() avec runtime deps."""
    return _chat_pending.resolve_pending_bypass(
        orig_last,
        pending_infra_cmd=_pending_infra_cmd,
        pending_reboot=_pending_reboot,
        ttl_s=_PENDING_APT_TTL_S,
        confirm_re=_CONFIRM_RE,
        cancel_re=_CANCEL_RE,
        reboot_now_re=_bypass_pve.REBOOT_NOW_RE,
        reboot_defer_re=_bypass_pve.REBOOT_DEFER_RE,
        apt_upgrade_sse_fn=_apt_upgrade_bypass_sse,
        reboot_machine_sse_fn=_reboot_machine_sse,
        sse_response_fn=_sse_response,
        sse_tok_fn=_sse_tok,
        log_info_fn=_log.info,
        now_fn=time.time,
    )


def _chat_try_bypass(orig_last: str, is_vocal: bool):
    """Retourne une Response SSE si un bypass LLM est applicable, sinon None."""
    pending = _chat_resolve_pending_bypass(orig_last)
    if pending:
        return pending
    # Datetime — bypass instantané même en vocal
    if _bypass_simple.DATETIME_RE.search(orig_last):
        _log.info("[BYPASS] datetime → réponse directe (zéro LLM)")
        return _sse_response(_bypass_simple.datetime_sse())
    if is_vocal:
        return None
    backup_cmd = _detect_backup_command(orig_last)
    if backup_cmd:
        if backup_cmd == "backup-jarvis":
            return _sse_response(_jarvis_backup_sse())
        if backup_cmd == "backup-jarvis-log":
            return _sse_response(_jarvis_backup_log_sse())
        return _sse_response(_backup_sse(backup_cmd))
    vm_cmd = _detect_vm_command(orig_last)
    if vm_cmd:
        action, vm_list = vm_cmd
        return _sse_response(_vm_command_sse(action, vm_list))
    reboot_cmd = _detect_reboot_command(orig_last)
    if reboot_cmd:
        host_label, ssh_fn, is_proxmox = reboot_cmd
        _log.info(f"[BYPASS_REBOOT_DIRECT] reboot {host_label}")
        pending = {"host": host_label, "ssh_fn": ssh_fn, "is_proxmox": is_proxmox, "ts": time.time()}
        return _sse_response(_reboot_machine_sse(pending))
    upd_cmd = _detect_update_command(orig_last)
    if upd_cmd:
        host_label, ssh_fn, is_proxmox = upd_cmd
        _log.info(f"[BYPASS_UPDATE] mise à jour {host_label}")
        return _sse_response(_update_machine_sse(host_label, ssh_fn, is_proxmox))
    svc_cmd = _detect_service_restart(orig_last)
    if svc_cmd:
        host_label, ssh_func, svc_name = svc_cmd
        if host_label != "ambiguous":
            return _sse_response(_service_restart_sse(host_label, ssh_func, svc_name))
    file_cmd = _bypass_fs.detect_file_command(orig_last, _FILE_VM_SSH)
    if file_cmd:
        f_action, f_vm, f_ssh_fn, f_path = file_cmd
        # Si lecture + intention correction → pas de bypass (mode "lis+corrige en un shot")
        if f_action == "read" and not _FCORR_RE.search(orig_last):
            return _sse_response(_bypass_fs.file_command_sse(f_action, f_vm, f_ssh_fn, f_path))
    code_cmd = _detect_code_command(orig_last)
    if code_cmd:
        action, filename = code_cmd
        exec_it = (action == "exec")
        _log.info(f"[BYPASS_CODE] {action} `{filename}` → {_CODE_DEV_VM}")
        return _sse_response(_code_scp_exec_sse(filename, exec_it))
    for _hkey, _hrx in _SSH_TERMINAL_RE.items():
        if _hrx.search(orig_last):
            _hcfg  = _SSH_TERMINAL_MAP[_hkey]
            _hlabel = _hcfg["label"]
            _huser  = _hcfg.get("user", "root")
            _log.info(f"[BYPASS_SSH_{_hkey.upper()}] connexion {_hlabel} → open_ssh_terminal")
            return _sse_response(_ssh_terminal_sse(_hkey, _hlabel, _huser))
    return None


def _chat_generate(ctx: "LlmCtx", no_tools=False):
    """Wrapper DI — délègue à chat_generate.chat_generate() avec runtime deps."""
    yield from _chat_gen_mod.chat_generate(
        ctx, no_tools,
        deferred_queue=_speak_deferred,
        stream_active_event=_chat_stream_active,
        stream_inner_fn=_chat_stream_inner,
        log_error_fn=_log.error,
    )


def _chat_build_system_prompt(last_user: str, web_enabled: bool,
                              soc_ctx_injected: bool, is_vocal: bool,
                              force_soc: bool = False) -> tuple[str, bool]:
    """Wrapper DI — délègue à chat_system_prompt.build() avec les helpers runtime."""
    return _chat_sp.build(
        last_user, web_enabled, soc_ctx_injected, is_vocal,
        system_prompt=SYSTEM_PROMPT,
        facts_inject_fn=_facts_inject,
        rag_relevant_re=_RAG_RELEVANT_KW,
        rag_inject_fn=_rag_inject,
        web_search_fn=web_search,
        soc_inject_fn=_chat_inject_soc,
        pve_inject_fn=_chat_inject_pve,
        force_soc=force_soc,
    )


def _chat_resolve_model(is_vocal: bool, no_tools: bool, model_override: str | None = None) -> tuple[str | None, str]:
    """Wrapper DI — délègue à chat_routing.resolve_model() avec les constantes runtime."""
    return _chat_routing.resolve_model(
        is_vocal, no_tools, model_override,
        general_model=_GENERAL_MODEL,
        code_model=_CODE_MODEL,
        current_mode=_jarvis_mode,
    )


def _detect_file_corrections(orig_last, is_vocal):
    """Détecte les commandes mono/multi fichier + correction LLM."""
    file_corr_cmd = file_corr_multi = None
    if not is_vocal:
        _fmc = _bypass_fs.detect_multi_file_command(orig_last, _FILE_VM_SSH)
        if _fmc and _FCORR_RE.search(orig_last):
            file_corr_multi = _fmc
        else:
            _fc = _bypass_fs.detect_file_command(orig_last, _FILE_VM_SSH)
            if _fc and _fc[0] == "read" and _FCORR_RE.search(orig_last):
                file_corr_cmd = _fc
    return file_corr_cmd, file_corr_multi


@limiter.limit("60 per minute")
@app.route("/api/chat", methods=["POST"])
def api_chat():
    data             = request.json or {}
    history          = data.get("history", [])
    web_enabled      = data.get("web_search", False)
    soc_ctx_injected = data.get("soc_ctx_injected", False)
    np_override      = data.get("num_predict")
    no_tools         = data.get("no_tools", False)
    model_override   = data.get("model_override")   # 'soc' | 'general' | None

    last_user  = next((m["content"] for m in reversed(history) if m.get("role") == "user"), "")
    is_vocal   = last_user.startswith("[VOCAL]")
    # Message original avant injection SOC — évite la contamination des mots-clés routing
    _orig_last = last_user.split("\n\n", 1)[-1] if soc_ctx_injected and "\n\n" in last_user else last_user

    # ── 1. Bypass instantané — AVANT tout calcul coûteux ─────────────────────
    bypass = _chat_try_bypass(_orig_last, is_vocal)
    if bypass:
        return bypass

    # ── 1b. Détection "lis + corrige" mono ou multi-fichiers ─────────────────
    _file_corr_cmd, _file_corr_multi = _detect_file_corrections(_orig_last, is_vocal)

    # ── 2. Routing C·R — sortie anticipée avant injection SOC/PVE ────────────
    if _jarvis_mode == _CODE_REASONING_MODE:
        messages = _chat_build_messages(_facts_inject(SYSTEM_PROMPT), history, is_vocal)
        _log.info(f"[ROUTE] CODE-REASONING | q={repr(_orig_last[:80])}")
        return Response(
            stream_with_context(_capture_gen(_code_reasoning_gen(messages, np_override), _orig_last)),
            mimetype="text/event-stream", headers=_SSE_HEADERS)

    # ── 3. System prompt + RAG + web + SOC/PVE live ───────────────────────────
    # model_override='soc' (chat du dashboard SOC) → injection SOC forcée même
    # sans mot-clé : chaque message y est une question SOC par nature.
    system, soc_trigger = _chat_build_system_prompt(
        last_user, web_enabled, soc_ctx_injected, is_vocal,
        force_soc=(model_override == "soc"))

    # ── 4. Routing modèle ─────────────────────────────────────────────────────
    active_model, route = _chat_resolve_model(is_vocal, no_tools, model_override)
    if active_model == _CODE_MODEL:
        system += _CODE_SYSTEM_SUFFIX
    _log.info(f"[ROUTE] {route}/{active_model or MODEL} | soc={soc_trigger} | q={repr(_orig_last[:80])}")

    messages = _chat_build_messages(system, history, is_vocal)

    # ── 5. Dispatch "lis + corrige" mono ou multi-fichiers ───────────────────
    _llm_ctx = LlmCtx(messages, active_model, np_override, soc_ctx_injected, soc_trigger)
    if _file_corr_multi:
        _, f_vm, f_ssh_fn, f_paths = _file_corr_multi
        _log.info(f"[FILE_CORRECT_MULTI] {f_vm}:{f_paths} → LLM {active_model or MODEL}")
        return Response(
            stream_with_context(_capture_gen(_file_correct_multi_gen(f_vm, f_ssh_fn, f_paths, _llm_ctx), _orig_last)),
            mimetype="text/event-stream", headers=_SSE_HEADERS)
    if _file_corr_cmd:
        _, f_vm, f_ssh_fn, f_path = _file_corr_cmd
        _log.info(f"[FILE_CORRECT] {f_vm}:{f_path} → LLM {active_model or MODEL}")
        return Response(
            stream_with_context(_capture_gen(_file_correct_gen(f_vm, f_ssh_fn, f_path, _llm_ctx), _orig_last)),
            mimetype="text/event-stream", headers=_SSE_HEADERS)

    return Response(
        stream_with_context(_capture_gen(_chat_generate(_llm_ctx, no_tools), _orig_last)),
        mimetype="text/event-stream", headers=_SSE_HEADERS)

@app.route("/api/history/last", methods=["GET"])
def api_history_last():
    """Retourne les N derniers échanges chat (user + assistant). Utilisé par le MCP."""
    n = min(int(request.args.get("n", 3)), 10)
    entries = list(_LAST_EXCHANGES)[-n:]
    return Response(json.dumps({"ok": True, "count": len(entries), "exchanges": entries}),
                    mimetype="application/json")


@limiter.limit("60 per minute")
@app.route("/api/security", methods=["GET"])
def api_security():
    """Journal sécurité — tentatives bloquées depuis le démarrage."""
    with _SEC_LOCK:
        total  = len(_SEC_EVENTS)
        by_lvl = {"hard": 0, "args": 0, "terminal": 0}
        for e in _SEC_EVENTS:
            by_lvl[e["level"]] = by_lvl.get(e["level"], 0) + 1
        snapshot = _SEC_EVENTS[-10:][::-1]
    return Response(json.dumps({
        "total":         total,
        "by_level":      by_lvl,
        "last":          snapshot,
        "uptime_events": total,
    }, ensure_ascii=False), mimetype="application/json")

@limiter.limit("10 per minute")
@app.route("/api/security/clear", methods=["POST"])
def api_security_clear():
    """Vide le journal sécurité."""
    with _SEC_LOCK:
        _SEC_EVENTS.clear()
    return Response('{"ok":true}', mimetype="application/json")

@limiter.limit("30 per minute")
@app.route("/api/dsp/process-audio", methods=["POST"])
def api_dsp_process_audio():
    """Reçoit bytes audio (WAV/MP3/OGG), applique la chaîne DSP+FX complète, retourne audio traité."""
    cl = request.content_length or 0
    if cl > _DSP_MAX_BYTES:
        return Response('{"error":"audio trop volumineux (max 50 MB)"}', status=413, mimetype="application/json")
    audio_bytes = request.data
    if not audio_bytes:
        return Response('{"error":"no data"}', status=400, mimetype="application/json")
    try:
        result, mime = apply_dsp_to_mp3(audio_bytes)
        return Response(result, mimetype=mime)
    except Exception as e:
        _log.error(f"[DSP/process-audio] Erreur: {e}")
        return Response(audio_bytes, mimetype="audio/wav")

@limiter.limit("20 per minute")
@app.route("/api/speak", methods=["POST"])
def api_speak():
    data = request.json or {}
    text = data.get("text", "")
    if text:
        source = data.get("source", request.headers.get("Referer", "unknown"))
        preview = text[:_TTS_LOG_PREVIEW].replace("\n", " ")
        suffix = "..." if len(text) > _TTS_LOG_PREVIEW else ""
        _tts_logger.info("source=%-20s | %s%s", source, preview, suffix)
        speak(text, blocking=False)   # retour immédiat — TTS joue en background
    return Response("{}", mimetype="application/json")

@limiter.limit("20 per minute")
@app.route("/api/ping", methods=["POST"])
def api_ping():
    """Ping une IP/host depuis la machine Windows et retourne le résultat."""
    host = (request.json or {}).get("host", "")
    if not host or not re.match(r'^[a-zA-Z0-9.\-_]+$', host):
        return Response('{"error":"host invalide"}', mimetype="application/json", status=400)
    try:
        result = subprocess.run(
            ["ping", "-n", "4", host],
            capture_output=True, text=True, timeout=_SSH_PROXMOX_CMD_TIMEOUT_S, encoding="cp850", errors="replace"
        )
        output = result.stdout or result.stderr or ""
        # Extraire les stats clés
        lines  = [ln.strip() for ln in output.splitlines() if ln.strip()]
        ok     = result.returncode == 0
        return Response(
            json.dumps({"ok": ok, "host": host, "output": output, "lines": lines}, ensure_ascii=False),
            mimetype="application/json"
        )
    except Exception as e:
        return Response(json.dumps({"ok": False, "host": host, "error": str(e)}), mimetype="application/json")

@limiter.limit("30 per minute")
@app.route("/api/speak/stop", methods=["POST"])
def api_speak_stop():
    """Arrête immédiatement la lecture TTS en cours (WinMM) et vide les queues."""
    try:
        import ctypes
        winmm = ctypes.WinDLL("winmm")
        winmm.mciSendStringW("stop all", None, 0, None)
        winmm.mciSendStringW("close all", None, 0, None)
    except Exception as e:
        _log.info(f"[TTS-stop] {e}")
    # Vide les queues pour éviter que le browser rejoue en arrière-plan
    drained = 0
    for q in (_speak_queue, _speak_deferred):
        try:
            while True:
                q.get_nowait()
                drained += 1
        except _queue_mod.Empty:
            pass  # get_nowait() raises Empty when queue is drained — expected
    return Response(json.dumps({"ok": True, "drained": drained}), mimetype="application/json")

@limiter.limit("60 per minute")
@app.route("/api/speak/status", methods=["GET"])
def api_speak_status():
    """État complet TTS : queue principale, deferred et stream SSE actif."""
    queued   = _speak_queue.qsize()
    deferred = _speak_deferred.qsize()
    streaming = _chat_stream_active.is_set()
    return Response(json.dumps({
        "speaking":       queued > 0 or deferred > 0 or streaming,
        "queued":         queued,
        "deferred":       deferred,
        "stream_active":  streaming,
    }), mimetype="application/json")

@limiter.limit("60 per minute")
@app.route("/api/speak/queue", methods=["GET"])
def api_speak_queue():
    """Retourne et vide la queue TTS Python — le browser joue chaque item via queueSpeech."""
    items = []
    try:
        while True:
            items.append(_speak_queue.get_nowait())
    except _queue_mod.Empty:
        pass  # get_nowait() raises Empty when queue is drained — expected
    return Response(json.dumps({"items": items}), mimetype="application/json")

@limiter.limit("60 per minute")
@app.route("/api/tts-log", methods=["GET"])
def api_tts_log():
    """Retourne les N dernières lignes du log TTS rotatif."""
    try:
        n = min(int(request.args.get("n", 50)), 500)
    except (ValueError, TypeError):
        n = 50
    lines = []
    if _TTS_LOG_PATH.exists():
        try:
            with open(_TTS_LOG_PATH, encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            pass  # log TTS absent — retourne liste vide
    tail = [ln.rstrip("\n") for ln in lines[-n:]]
    return Response(json.dumps({"lines": tail, "total": len(lines), "file": str(_TTS_LOG_PATH)}, ensure_ascii=False), mimetype="application/json")

@app.route("/api/tts/status", methods=["GET"])
def api_tts_status():
    """État opérationnel de chaque moteur TTS — dérivé des variables runtime, aucun hardcode."""
    _kok = _tts_eng.is_kokoro_available()
    _pip = _tts_eng.is_piper_available()
    _sap = _tts_eng.is_sapi_available()
    return Response(json.dumps({
        "edge":   {"ok": bool(_tts_internet_was_up), "label": "EN SERVICE" if _tts_internet_was_up else "ARRÊTÉ"},
        "kokoro": {"ok": _kok is True, "label": "EN SERVICE" if _kok is True else ("CHARGEMENT" if _kok is None else "ARRÊTÉ")},
        "piper":  {"ok": bool(_pip), "label": "EN SERVICE" if _pip else "ARRÊTÉ"},
        "sapi":   {"ok": bool(_sap), "label": "EN SERVICE" if _sap else "ARRÊTÉ"},
    }, ensure_ascii=False), mimetype="application/json")

def _tts_wav_response(wav, mime):
    return Response(wav, mimetype=mime,
                    headers={"Content-Length": str(len(wav)), "Cache-Control": "no-cache"})

def _tts_local_response(engine, text, local_voice):
    """Tente un moteur TTS local. Retourne Response ou None si moteur indisponible."""
    try:
        if engine == "kokoro" and _tts_eng.is_kokoro_available() is not False:
            _spd = float(DSP_PARAMS.get("tts_kokoro_speed", 1.0))
            try:
                wav, mime = apply_dsp_to_mp3(_tts_eng.kokoro_synth(text, local_voice, _spd))
                return _tts_wav_response(wav, mime)
            except Exception as ke:
                _log.warning(f"[Kokoro] Echec synthese ({type(ke).__name__}: {ke}) — fallback edge-tts")
                return None
        if engine == "piper" and _tts_eng.is_piper_available():
            wav, mime = apply_dsp_to_mp3(_tts_eng.piper_synth(text, local_voice or None))
            return _tts_wav_response(wav, mime)
        if engine == "sapi" and _tts_eng.is_sapi_available():
            wav, mime = apply_dsp_to_mp3(_tts_eng.sapi5_synth(text, local_voice or None))
            return _tts_wav_response(wav, mime)
    except Exception as e:
        _log.error(f"[JARVIS] Erreur interne: {e}")
        return Response(json.dumps({"error": "Erreur interne serveur"}), status=500, mimetype="application/json")
    return None

def _tts_edge_fallback(text, local_voice):
    """Chaîne de fallback après échec edge-tts : Kokoro → Piper → SAPI5 → erreur 503."""
    if _tts_eng.is_kokoro_available() is not False:
        try:
            _spd = float(DSP_PARAMS.get("tts_kokoro_speed", 1.0))
            wav, mime = apply_dsp_to_mp3(_tts_eng.kokoro_synth(text, local_voice, _spd))
            _tts_logger.warning("[FALLBACK] Kokoro utilisé à la place de edge-tts (internet KO)")
            return _tts_wav_response(wav, mime)
        except Exception as ke:
            _log.info(f"[JARVIS] Kokoro fallback échoué: {ke}")
    if _tts_eng.is_piper_available():
        try:
            wav, mime = apply_dsp_to_mp3(_tts_eng.piper_synth(text, local_voice or None))
            _tts_logger.warning("[FALLBACK] Piper utilisé à la place de edge-tts")
            return _tts_wav_response(wav, mime)
        except Exception as pe:
            _log.info(f"[JARVIS] Piper fallback échoué: {pe}")
    if _tts_eng.is_sapi_available():
        try:
            wav, mime = apply_dsp_to_mp3(_tts_eng.sapi5_synth(text, None))
            _tts_logger.warning("[FALLBACK] SAPI5 (Microsoft) utilisé à la place de edge-tts")
            return _tts_wav_response(wav, mime)
        except Exception as se:
            _log.info(f"[JARVIS] SAPI5 fallback échoué: {se}")
    return Response(
        json.dumps({"error": "TTS indisponible — edge-tts hors ligne, aucun moteur local actif"}),
        status=503, mimetype="application/json"
    )

@limiter.limit("20 per minute")
@app.route("/api/tts", methods=["POST"])
def api_tts():
    _perf_t0 = time.monotonic()
    data = request.json or {}
    text = _clean_for_tts(data.get("text", ""))
    if not text:
        return Response("{}", mimetype="application/json", status=400)
    source = data.get("source", request.headers.get("Referer", "unknown"))
    # Dedup global cross-source (60s) — évite superposition avec python-speak SOC engine
    now = time.monotonic()
    if _tts_dedup.check_and_register(text, now):
        _log.debug(f"[TTS] Dedup global skip (/api/tts, même texte < {_TTS_DEDUP_S}s) : {text[:80]}")
        return Response('{"dedup":true}', mimetype="application/json", status=200)
    preview = text[:_TTS_LOG_PREVIEW].replace("\n", " ")
    _tts_logger.info("source=%-20s | %s%s", source, preview, "..." if len(text) > _TTS_LOG_PREVIEW else "")
    engine      = DSP_PARAMS.get("tts_engine", "edge")
    local_voice = DSP_PARAMS.get("tts_local_voice", "")

    # Moteurs locaux (hors-ligne)
    local_resp = _tts_local_response(engine, text, local_voice)
    if local_resp is not None:
        _log.info(f"[TTS-PERF] /api/tts engine={engine} (local) total={time.monotonic() - _perf_t0:.2f}s chars={len(text)}")
        return local_resp

    # Moteur edge-tts (cloud) — avec retry + fallback
    try:
        _t_edge = time.monotonic()
        tmp_path = _tts_eng.edge_generate_mp3(text, VOICE)
        _perf_edge = time.monotonic() - _t_edge
        with open(tmp_path, "rb") as f:
            audio_data = f.read()
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # fichier temporaire déjà supprimé — non bloquant
        _t_dsp = time.monotonic()
        audio_data, mime = apply_dsp_to_mp3(audio_data)
        _perf_dsp = time.monotonic() - _t_dsp
        _log.info(f"[TTS-PERF] /api/tts engine=edge edge_gen={_perf_edge:.2f}s dsp={_perf_dsp:.2f}s total={time.monotonic() - _perf_t0:.2f}s chars={len(text)}")
        return _tts_wav_response(audio_data, mime)
    except Exception as edge_err:
        _log.warning(f"[JARVIS] edge-tts indisponible ({type(edge_err).__name__}: {edge_err}) — bascule TTS local")
        _tts_logger.warning(f"[FALLBACK] edge-tts échec ({type(edge_err).__name__}) — tentative moteur local")
        _fallback_resp = _tts_edge_fallback(text, local_voice)
        _log.info(f"[TTS-PERF] /api/tts engine=edge→fallback-local total={time.monotonic() - _perf_t0:.2f}s chars={len(text)}")
        return _fallback_resp

@limiter.limit("30 per minute")
@app.route("/api/tts/local/voices")
def api_tts_local_voices():
    """Liste les moteurs TTS locaux et voix disponibles."""
    _kok = _tts_eng.is_kokoro_available()
    _pip = _tts_eng.is_piper_available()
    _sap = _tts_eng.is_sapi_available()
    result = {
        "kokoro": {"available": _kok, "voices": [
            {"id": "ff_siwis", "name": "Siwis (FR féminine) — très haute qualité"},
        ] if _kok else []},
        "piper": {"available": _pip, "models": _tts_eng.list_piper_models() if _pip else []},
        "sapi":  {"available": _sap, "voices": _tts_eng.list_sapi_voices()},
        "current_engine": DSP_PARAMS.get("tts_engine", "kokoro"),
        "current_voice":  DSP_PARAMS.get("tts_local_voice", "ff_siwis"),
    }
    return Response(json.dumps(result, ensure_ascii=False), mimetype="application/json")

@limiter.limit("5 per minute")
@app.route("/api/tts/local/download", methods=["POST"])
def api_tts_local_download():
    """Télécharge un modèle Piper depuis HuggingFace (internet requis une seule fois)."""
    data = request.json or {}
    voice_name = data.get("voice", "fr_FR-upmc-medium")
    try:
        import shutil as _shutil

        from huggingface_hub import hf_hub_download
        # Mapping nom → chemin HF
        _HF_MAP = {
            "fr_FR-upmc-medium":   "fr/fr_FR/upmc/medium",
            "fr_FR-siwis-medium":  "fr/fr_FR/siwis/medium",
            "fr_FR-mls-medium":    "fr/fr_FR/mls/medium",
            "fr_FR-mls_1840-low":  "fr/fr_FR/mls_1840/low",
        }
        hf_subdir = _HF_MAP.get(voice_name)
        if not hf_subdir:
            return Response(json.dumps({"error": f"Voix inconnue: {voice_name}. Choisir parmi: {list(_HF_MAP.keys())}"}),
                            status=400, mimetype="application/json")
        downloaded = []
        for fname in [f"{voice_name}.onnx", f"{voice_name}.onnx.json"]:
            path = hf_hub_download(repo_id="rhasspy/piper-voices",
                                   filename=f"{hf_subdir}/{fname}")
            dest = _tts_eng.VOICES_DIR / fname
            if str(path) != str(dest):
                _shutil.copy2(path, dest)
            downloaded.append(str(dest))
        return Response(json.dumps({"ok": True, "model": voice_name, "files": downloaded}), mimetype="application/json")
    except Exception as e:
        _log.error(f"[JARVIS] Erreur interne: {e}"); return Response(json.dumps({"error": "Erreur interne serveur"}), status=500, mimetype="application/json")

@limiter.limit("60 per minute")
@app.route("/api/dsp-params", methods=["GET"])
def api_get_dsp_params():
    return Response(json.dumps(DSP_PARAMS), mimetype="application/json")

@limiter.limit("20 per minute")
@app.route("/api/dsp-params", methods=["POST"])
def api_set_dsp_params():
    data = request.json or {}
    _DSP_SAFE_STR = {
        "tts_engine":         {"edge", "kokoro", "piper", "sapi"},
        "tts_default_engine": {"edge", "kokoro", "piper", "sapi"},
        "fx_type":            {"reverb", "delay", "chorus", "flanger", "echo", "phaser", "exciter"},
        "fx_preset":          {"room", "studio", "concert", "cathedral", "plate", "cave", "spring"},
    }
    # Bornes physiques par clé — remplace le générique ±9999
    _DSP_BOUNDS = {
        "eq_low": (-24.0, 24.0), "eq_mid": (-24.0, 24.0), "eq_high": (-24.0, 24.0), "eq_air": (-24.0, 24.0),
        "comp_threshold": (-60.0, 0.0), "comp_ratio": (1.0, 20.0),
        "comp_attack": (0.001, 1.0), "comp_release": (0.01, 5.0),
        "gain": (-20.0, 20.0),
        "stereo_width": (0.0, 1.0), "haas_delay_ms": (0.0, 30.0),
        "df_atten_lim": (0.0, 100.0),
        "fx_wet": (0.0, 1.0), "fx_decay": (0.05, 10.0), "fx_predelay_ms": (0.0, 100.0),
        "fx_diffusion": (0.0, 1.0), "fx_delay_ms": (1.0, 2000.0), "fx_delay_feedback": (0.0, 0.98),
        "fx_delay_filter": (200.0, 20000.0), "fx_chorus_rate": (0.01, 10.0),
        "fx_chorus_depth": (0.001, 0.1), "fx_chorus_feedback": (0.0, 0.9),
        "fx_flanger_rate": (0.01, 5.0), "fx_flanger_depth": (0.0005, 0.02), "fx_flanger_feedback": (0.0, 0.95),
        "fx_echo_left_ms": (1.0, 2000.0), "fx_echo_right_ms": (1.0, 2000.0), "fx_echo_feedback": (0.0, 0.95),
        "fx_phaser_stages": (2, 12), "fx_phaser_rate": (0.01, 5.0), "fx_phaser_depth": (0.0, 1.0),
        "fx_exciter_drive": (0.0, 24.0), "fx_exciter_tone": (500.0, 16000.0), "fx_exciter_warmth": (0.0, 1.0),
        "enrich_drive": (0.0, 12.0), "enrich_tone": (200.0, 8000.0),
        "enrich_mix": (0.0, 0.5), "enrich_warmth": (0.0, 0.3),
        "tts_kokoro_speed": (0.5, 2.0),
    }
    sanitized = {}
    for k, v in data.items():
        if k not in DSP_PARAMS:
            continue
        orig = DSP_PARAMS[k]
        if k in _DSP_SAFE_STR:
            if isinstance(v, str) and v in _DSP_SAFE_STR[k]:
                sanitized[k] = v
        elif isinstance(orig, bool):
            sanitized[k] = bool(v)
        elif isinstance(orig, (int, float)) and isinstance(v, (int, float)):
            lo, hi = _DSP_BOUNDS.get(k, (-9999, 9999))
            clamped = max(lo, min(hi, v))
            sanitized[k] = int(round(clamped)) if isinstance(orig, int) else round(float(clamped), 6)
        elif isinstance(orig, str):
            sanitized[k] = str(v)[:128]
    DSP_PARAMS.update(sanitized)
    try:
        DSP_PARAMS_FILE.write_text(json.dumps(DSP_PARAMS, indent=2), encoding="utf-8")
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING save_dsp_params: {e}")
    return Response(json.dumps({"ok": True}), mimetype="application/json")

@limiter.limit("30 per minute")
@app.route("/api/models", methods=["GET"])
def api_models():
    global MODELS
    MODELS = _fetch_ollama_models()
    return Response(json.dumps({"models": MODELS, "current": MODEL}), mimetype="application/json")

@limiter.limit("5 per minute")
@app.route("/api/models/test", methods=["POST"])
def api_model_test():
    """Teste le modèle LLM actif avec une requête minimale et mesure la latence."""
    model = (request.json or {}).get("model", MODEL)
    if model not in MODELS:
        return Response(json.dumps({"ok": False, "error": "Modèle inconnu"}), status=400, mimetype="application/json")
    try:
        t0 = time.time()
        r = _ollama_circuit.call(req.post,
            f"{OLLAMA_URL}/api/chat",
            json={"model": model, "messages": [{"role": "user", "content": "Réponds uniquement: OK"}],
                  "stream": False, "options": {"num_predict": 5, "temperature": 0}},
            timeout=_OLLAMA_TOOL_DETECT_TIMEOUT_S
        )
        latency = round((time.time() - t0) * 1000)
        if r.status_code == 200:
            reply = r.json().get("message", {}).get("content", "").strip()
            return Response(json.dumps({"ok": True, "model": model, "latency_ms": latency, "reply": reply}),
                            mimetype="application/json")
        return Response(json.dumps({"ok": False, "model": model, "error": f"HTTP {r.status_code}"}),
                        mimetype="application/json")
    except Exception as e:
        return Response(json.dumps({"ok": False, "model": model, "error": str(e)}), mimetype="application/json")

@limiter.limit("20 per minute")
@app.route("/api/models", methods=["POST"])
def api_set_model():
    global MODEL, SYSTEM_PROMPT, _AUTO_PROFILE_MODEL
    model = (request.json or {}).get("model", "")
    if model in MODELS:
        with _MODEL_LOCK:
            MODEL = model
            _save_model()
        profile_name, profile_content = _get_model_profile(model)
        if profile_content is not None:
            # Nouveau modèle a un profil lié → l'appliquer
            SYSTEM_PROMPT = profile_content
            PROMPT_FILE.write_text(SYSTEM_PROMPT, encoding="utf-8")
            _AUTO_PROFILE_MODEL = model
        elif _AUTO_PROFILE_MODEL is not None:
            # On quitte un modèle avec auto-profil → restaurer le prompt par défaut
            SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT
            PROMPT_FILE.write_text(SYSTEM_PROMPT, encoding="utf-8")
            _AUTO_PROFILE_MODEL = None
            profile_name = None
        return Response(json.dumps({"ok": True, "model": MODEL, "auto_profile": profile_name}),
                        mimetype="application/json")
    return Response(json.dumps({"ok": False}), mimetype="application/json", status=400)

@limiter.limit("60 per minute")
@app.route("/api/voices", methods=["GET"])
def api_voices():
    return Response(json.dumps({"voices": VOICES, "current": VOICE}), mimetype="application/json")

@limiter.limit("20 per minute")
@app.route("/api/voices", methods=["POST"])
def api_set_voice():
    global VOICE
    voice_id = (request.json or {}).get("voice", "")
    if any(v["id"] == voice_id for v in VOICES):
        VOICE = voice_id
        return Response(json.dumps({"ok": True, "voice": VOICE}), mimetype="application/json")
    return Response(json.dumps({"ok": False}), mimetype="application/json", status=400)


# ── Voice Lab — logique métier dans `voice_lab.py` (Phase 3 module 2) ────────

def _voice_analyse_err(msg, code=400):
    return Response(json.dumps({"ok": False, "error": msg}, ensure_ascii=False),
                    mimetype="application/json", status=code)


@limiter.limit("10 per minute")
@app.route("/api/voice/analyse", methods=["POST"])
def api_voice_analyse():
    if not _voice_lab.is_librosa_available():
        return _voice_analyse_err("librosa non disponible — pip install librosa", 500)

    f = request.files.get("audio")
    if not f:
        return _voice_analyse_err("Aucun fichier audio reçu")

    fmin   = max(30.0,  min(500.0,  float(request.form.get("fmin",   50))))
    fmax   = max(200.0, min(2000.0, float(request.form.get("fmax",  800))))
    n_mels = max(16,    min(128,    int(request.form.get("n_mels",   32))))

    suffix   = Path(f.filename).suffix.lower() if f.filename else ".wav"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            f.save(tmp.name)
            tmp_path = tmp.name
        y, sr = _voice_lab.load_audio(tmp_path, duration=60.0)
    except Exception as e:
        return _voice_analyse_err(f"Lecture audio impossible: {e}")
    finally:
        if tmp_path:
            try: os.unlink(tmp_path)
            except OSError: pass  # tmp file may already be deleted — ignore

    try:
        feat = _voice_lab.analyse_features(y, sr, fmin, fmax, n_mels)
        return Response(json.dumps({
            "ok": True,
            "duration": round(feat["dur"], 2),
            "sr":       feat["sr"],
            "params":   {"fmin": fmin, "fmax": fmax, "n_mels": n_mels},
            "metrics": {
                "pitch_median":      round(feat["pitch_median"], 1),
                "pitch_min":         round(feat["pitch_min"], 1),
                "pitch_max":         round(feat["pitch_max"], 1),
                "spectral_centroid": round(feat["centroid_mean"], 0),
                "rolloff_hz":        round(feat["rolloff_mean"], 0),
                "flatness":          round(feat["flatness_mean"], 4),
                "zcr":               round(feat["zcr_mean"], 4),
                "dynamic_range_db":  feat["dynamic_range_db"],
                "voice_type":        feat["voice_type"],
                "brightness":        feat["brightness"],
                "breathiness":       feat["breathiness"],
                "voicing":           feat["voicing"],
                "mfcc_means":        feat["mfcc_means"],
            },
            "waveform":    feat["waveform"],
            "pitch_curve": feat["pitch_curve"],
            "spectrum":    feat["spectrum"],
            "eq_preset":   feat["eq_preset"],
        }, ensure_ascii=False), mimetype="application/json")
    except Exception as e:
        _log.error(f"[VOICE-PRINT] Analyse échouée: {e}", exc_info=True)
        return _voice_analyse_err(f"Analyse échouée: {e}", 500)


@app.route("/api/voice/prints", methods=["GET"])
def api_voice_prints():
    return Response(json.dumps(_voice_lab.list_prints(), ensure_ascii=False),
                    mimetype="application/json")


@limiter.limit("60 per minute")
@app.route("/api/voice/print/audio/<path:name>", methods=["GET"])
def api_voice_print_audio(name):
    """Sert un fichier WAV depuis voice_prints/ pour écoute/chargement dans le sélecteur."""
    wav_path = _voice_lab.get_print_path(name)
    if wav_path is None:
        return Response(status=404)
    from flask import send_file as _sf
    return _sf(wav_path, mimetype="audio/wav")


@limiter.limit("10 per minute")
@app.route("/api/voice/print/delete", methods=["POST"])
def api_voice_print_delete():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return Response(json.dumps({"ok": False, "error": "Nom requis"}, ensure_ascii=False),
                        mimetype="application/json", status=400)
    ok, result = _voice_lab.delete_print(name)
    if not ok:
        return Response(json.dumps({"ok": False, "error": result}, ensure_ascii=False),
                        mimetype="application/json", status=404)
    return Response(json.dumps({"ok": True, "name": result}, ensure_ascii=False),
                    mimetype="application/json")


@app.route("/api/voice/samples", methods=["GET"])
def api_voice_samples():
    return Response(json.dumps(_voice_lab.list_samples(), ensure_ascii=False),
                    mimetype="application/json")




# Préchargement Kokoro en background si engine actif = kokoro
def _kokoro_preload():
    if DSP_PARAMS.get("tts_engine") != "kokoro":
        return
    try:
        # Phrase représentative → chauffe CUDA kernels + pipeline complet
        _warm_wav = _tts_eng.kokoro_synth("JARVIS opérationnel.", "ff_siwis")
        # Chauffe aussi le pipeline DSP (EQ, Haas, enrich)
        apply_dsp_to_mp3(_warm_wav)
        _log.info("[TTS-Kokoro] Préchargement ff_siwis + DSP terminé.")
    except Exception as _e:
        _log.warning(f"[TTS-Kokoro] Préchargement échoué: {_e}")
_kokoro_preload_thread = threading.Thread(target=_kokoro_preload, daemon=True, name="kokoro-preload")
_kokoro_preload_thread.start()



# ---------------------------------------------------------------------------
# Thread de surveillance connectivité → basculement TTS automatique
# ---------------------------------------------------------------------------
_tts_internet_was_up = None  # None = inconnu au démarrage → premier cycle force le switch
_tts_stop_evt = threading.Event()  # set() pour arrêter proprement le thread

def _tts_connectivity_loop():
    """Vérifie toutes les 10 s si speech.platform.bing.com est joignable.
    Logique simple :
    - Internet OK  → edge-tts Antoine (si tts_default_engine == "edge")
    - Internet KO  → Kokoro → Piper → SAPI5 (premier moteur local disponible)
    Premier cycle forcé au démarrage (_tts_internet_was_up = None).
    Arrêt propre : _tts_stop_evt.set()
    """
    global _tts_internet_was_up
    import socket as _socket
    while not _tts_stop_evt.is_set():
        try:
            s = _socket.create_connection(("speech.platform.bing.com", 443), timeout=_OLLAMA_DIAG_TIMEOUT_S)
            s.close()
            up = True
        except OSError:
            up = False

        if up != _tts_internet_was_up:
            default_eng = DSP_PARAMS.get("tts_default_engine", "edge")
            cur_eng     = DSP_PARAMS.get("tts_engine", "edge")
            if up:
                # Internet revient : revenir sur edge uniquement si c'est le défaut configuré
                if default_eng == "edge" and cur_eng != "edge":
                    DSP_PARAMS["tts_engine"] = "edge"
                    _log.info("[TTS-AUTO] Internet OK → edge-tts Antoine (défaut EDGE)")
                else:
                    _log.info(f"[TTS-AUTO] Internet OK — défaut={default_eng}, engine={cur_eng}, pas de switch")
            else:
                # Internet KO : Kokoro en priorité (local, haute qualité)
                if _tts_eng.is_kokoro_available() is not False:
                    DSP_PARAMS["tts_engine"] = "kokoro"
                    _log.info("[TTS-AUTO] Internet KO → Kokoro (fallback local)")
                elif _tts_eng.is_piper_available():
                    DSP_PARAMS["tts_engine"] = "piper"
                    _log.info("[TTS-AUTO] Internet KO → Piper local")
                elif _tts_eng.is_sapi_available():
                    DSP_PARAMS["tts_engine"] = "sapi"
                    _log.info("[TTS-AUTO] Internet KO → SAPI5")
                else:
                    _log.info("[TTS-AUTO] Internet KO → aucun moteur local disponible")
            _tts_internet_was_up = up

        _tts_stop_evt.wait(10)  # interruptible — sort immédiatement si stop_evt.set()

_tts_conn_thread = threading.Thread(target=_tts_connectivity_loop, daemon=True)
_tts_conn_thread.start()

# ---------------------------------------------------------------------------
# Thread de surveillance température GPU
# ---------------------------------------------------------------------------
_GPU_TEMP_WARN    = 82   # °C — seuil d'alerte logiciel (avant throttle hardware à 90°C)
_gpu_stop_evt     = threading.Event()  # set() pour arrêt propre

def _gpu_temp_monitor_loop():
    """Thread background — surveille la température GPU toutes les 30s.
    Alerte vocale si temp >= _GPU_TEMP_WARN, cooldown 15 min."""
    from blueprints.soc import _soc_cooldown_ok
    time.sleep(_GPU_MON_START_S)  # délai one-shot démarrage, pas de loop ici
    while not _gpu_stop_evt.wait(_GPU_MON_POLL_S):
        try:
            if _nvml_handle is None:
                continue
            temp = pynvml.nvmlDeviceGetTemperature(_nvml_handle, pynvml.NVML_TEMPERATURE_GPU)
            if temp >= _GPU_TEMP_WARN and _soc_cooldown_ok("gpu_temp_warn", minutes=15):
                speak(f"Alerte thermique. Température GPU à {temp} degrés. Seuil d'alerte à {_GPU_TEMP_WARN} degrés. Vérifier la ventilation.")
        except Exception as _ge:
            _log.error(f"[GPU-TEMP-MON] {_ge}")

_gpu_temp_thread = threading.Thread(target=_gpu_temp_monitor_loop, daemon=True)
_gpu_temp_thread.start()

# ── RAG LIVE — Pré-chauffe du cache logs SOC au démarrage ──────────────────
threading.Thread(target=_rag_live_prewarm, daemon=True, name="rag-live-prewarm").start()

# ── RAG EMBED — Préchargement mxbai-embed-large en VRAM au démarrage ────────
def _rag_embed_prewarm():
    # RAG chargé tôt — avant le LLM (logique : la recherche RAG précède la
    # génération). 5s suffisent ; si Ollama pas encore prêt, le circuit breaker
    # gère et l'embed se chargera à la demande au 1er usage RAG. (2026-05-20)
    time.sleep(5)
    try:
        _ollama_circuit.call(req.post, f"{OLLAMA_URL}/api/embeddings",
                 json={"model": RAG_EMBED_MODEL, "prompt": "warm", "keep_alive": "10m"},
                 timeout=30)
        _log.info(f"[RAG] {RAG_EMBED_MODEL} préchauffé (keep_alive=10m — dé-épinglé 2026-05-20, anti-éviction VRAM)")
    except Exception as e:
        _log.warning(f"[RAG] Préchargement embed échoué : {e}")
threading.Thread(target=_rag_embed_prewarm, daemon=True, name="rag-embed-prewarm").start()

# ── BOOT VRAM CLEANUP — décharge les modèles résiduels du mode précédent ─────
def _boot_vram_cleanup():
    """Au boot, éjecte tout modèle Ollama chargé qui n'est pas phi4 ni le RAG embed."""
    time.sleep(25)  # après _rag_embed_prewarm (20s + marge)
    try:
        r = req.get(f"{OLLAMA_URL}/api/ps", timeout=8)
        if not r.ok:
            return
        loaded = [m.get("name", "") for m in (r.json().get("models") or [])]
        embed_base = RAG_EMBED_MODEL.split(":")[0]
        for m in loaded:
            if m == MODEL or m.split(":")[0] == embed_base:
                continue  # SOC model ou embed — garder
            import urllib.request as _ur3
            payload = json.dumps({"model": m, "prompt": "", "stream": False, "keep_alive": 0}).encode()
            _req = _ur3.Request(f"{OLLAMA_URL}/api/generate", data=payload, method="POST")
            _req.add_header("Content-Type", "application/json")
            with _ur3.urlopen(_req, timeout=10): pass
            _log.info(f"[BOOT-VRAM] {m} déchargé (résidu mode précédent)")
    except Exception as e:
        _log.warning(f"[BOOT-VRAM] cleanup: {e}")
threading.Thread(target=_boot_vram_cleanup, daemon=True, name="boot-vram-cleanup").start()

# ── BOOT SOC PRELOAD — préchauffe phi4:14b après le cleanup ──────────────────
def _soc_model_prewarm():
    """Précharge le modèle SOC (phi4:14b) en VRAM 30s après le boot, une fois le cleanup terminé."""
    time.sleep(30)
    _prewarm_t0 = time.monotonic()
    try:
        # num_ctx explicite = _SOC_NUM_CTX : phi4 se charge directement au contexte
        # SOC (8192) → pas de reload au 1er chat SOC (sinon prewarm charge en 4096
        # défaut Ollama puis reload en 8192 à la 1re requête SOC).
        _ollama_circuit.call(req.post, f"{OLLAMA_URL}/api/generate",
                 json={"model": MODEL, "prompt": "", "stream": False, "keep_alive": "30m",
                       "options": {"num_ctx": _SOC_NUM_CTX}},
                 timeout=180)
        _log.info(f"[TTS-PERF] [BOOT-VRAM] {MODEL} préchargé (SOC default, ctx={_SOC_NUM_CTX}) en {time.monotonic() - _prewarm_t0:.2f}s")
    except Exception as e:
        _log.warning(f"[BOOT-VRAM] preload SOC: {e}")
threading.Thread(target=_soc_model_prewarm, daemon=True, name="soc-model-prewarm").start()

# ── BOOT TTS KOKORO PREWARM — élimine cold start 42.8s mesuré (profile_tts) ─
def _kokoro_prewarm():
    """Précharge Kokoro CUDA en VRAM 60s après le boot.
    Profiling 2026-05-15 : 1er appel Kokoro = 42.8s (chargement modèle CUDA),
    appels suivants = 200ms TTFB. Préchauffage = TTS instantané dès la 1re alerte."""
    time.sleep(60)  # après _soc_model_prewarm (30s + marge GPU)
    _prewarm_t0 = time.monotonic()
    try:
        _tts_eng._get_kokoro("f")
        if _tts_eng.is_kokoro_available():
            _log.info(f"[TTS-PERF] [BOOT-TTS] Kokoro préchargé en VRAM en {time.monotonic() - _prewarm_t0:.2f}s (cold start évité)")
        else:
            _log.info("[TTS-PERF] [BOOT-TTS] Kokoro indisponible — pas de préchauffage")
    except Exception as e:
        _log.warning(f"[BOOT-TTS] Kokoro prewarm échoué : {e}")
threading.Thread(target=_kokoro_prewarm, daemon=True, name="kokoro-prewarm").start()

# ── RAG AUTO-REFRESH — Re-indexe les MEMORY.md toutes les 6h ────────────────
_rag_refresh_stop_evt = threading.Event()  # set() pour arrêt propre

def _rag_auto_refresh_loop():
    _PATHS = [
        str(_WORKSPACE_ROOT / "JARVIS"  / "MEMORY.md"),
        str(_WORKSPACE_ROOT / "SOC"     / "MEMORY.md"),
        str(_WORKSPACE_ROOT / "PROXMOX" / "MEMORY.md"),
        str(_WORKSPACE_ROOT / "NGINX"   / "MEMORY.md"),
    ]
    while not _rag_refresh_stop_evt.wait(_RAG_REFRESH_H * 3600):
        for path_str in _PATHS:
            p = Path(path_str)
            if p.exists():
                try:
                    _rag_index_text(p.read_text(encoding="utf-8", errors="ignore"), p.name)
                except Exception as e:
                    _log.warning(f"[RAG] Auto-refresh {p.name}: {e}")
        _log.info("[RAG] Auto-refresh 6h terminé.")

threading.Thread(target=_rag_auto_refresh_loop, daemon=True, name="rag-auto-refresh").start()

if __name__ == "__main__":
    # Filtre les TimeoutError Werkzeug (connexions keep-alive fermées par le navigateur — pas de vraies erreurs)
    from werkzeug.serving import WSGIRequestHandler
    class _QuietHandler(WSGIRequestHandler):
        def log_error(self, fmt, *args):
            msg = fmt % args if args else str(fmt)
            if "timed out" in msg.lower() or "timeouterror" in msg.lower():
                return  # bruit inutile — connexion keep-alive fermée proprement
            super().log_error(fmt, *args)
    # ── MCP Server — lancement autonome en sous-processus ────────────────────
    _mcp_script = Path(__file__).parent / "jarvis_mcp_server.py"
    _mcp_proc = None
    if _mcp_script.exists():
        # Libère le port 5010 si un orphelin occupe encore le port (redémarrage JARVIS)
        try:
            import socket as _sock
            with _sock.socket(_sock.AF_INET, _sock.SOCK_STREAM) as _s:
                _port_busy = _s.connect_ex(("127.0.0.1", _MCP_PORT)) == 0
            if _port_busy:
                import psutil as _psutil
                # psutil 7.x : "connections" renommé "net_connections" (warning sinon)
                _conn_attr = "net_connections" if hasattr(_psutil.Process, "net_connections") else "connections"
                for _proc in _psutil.process_iter(["pid", "name", _conn_attr]):
                    try:
                        for _c in (_proc.info.get(_conn_attr) or []):
                            if getattr(_c, "laddr", None) and _c.laddr.port == _MCP_PORT:
                                _log.info(f"[MCP] Port {_MCP_PORT} occupé par PID {_proc.pid} — kill orphelin")
                                _proc.kill()
                                time.sleep(0.5)
                    except Exception:
                        pass  # processus déjà mort ou accès refusé
        except Exception as _e:
            _log.warning(f"[MCP] Vérif port {_MCP_PORT} : {_e}")
        try:
            _mcp_proc = subprocess.Popen(
                [sys.executable, str(_mcp_script), "--port", str(_MCP_PORT)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            _log.info(f"[MCP] jarvis_mcp_server démarré (PID {_mcp_proc.pid}) → port {_MCP_PORT}")
        except Exception as _e:
            _log.warning(f"[MCP] Impossible de démarrer jarvis_mcp_server : {_e}")
    else:
        _log.warning("[MCP] jarvis_mcp_server.py introuvable — MCP non démarré")

    print("=" * 45)
    print(f"  JARVIS -> http://localhost:{JARVIS_PORT}")
    print(f"  MCP    -> 127.0.0.1:{_MCP_PORT}")
    print("  Ctrl+C pour arreter")
    print("=" * 45)
    try:
        app.run(host="127.0.0.1", port=JARVIS_PORT, debug=False, threaded=True, request_handler=_QuietHandler)
    finally:
        if _mcp_proc and _mcp_proc.poll() is None:
            _mcp_proc.terminate()
            _log.info("[MCP] jarvis_mcp_server arrêté proprement")
