"""
JARVIS — Core
Relie Ollama (LLM) + edge-tts (voix) + Flask (interface web)
"""

import json
import logging
import logging.handlers
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

# LlmCtx + _LAST_EXCHANGES déplacés dans chat/orchestrator.py — aliases définis
# après l'import `from chat import ...` (étape 12 refactor jarvis.py).

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(message)s",
    datefmt="%H:%M:%S",
)
_log = logging.getLogger("JARVIS")

# ── JARVIS log rotatif persistant — capture les WARNING/ERROR/INFO + tracebacks ──
# Le bug intermittent « UI reload sur switch voix Edge » (2026-05-23) montre que
# basicConfig stdout seul n'est pas suffisant : si la console PowerShell est fermée
# ou que le scrollback est dépassé, le traceback est perdu. Ce FileHandler garantit
# la persistance sur disque avec rotation 5 MB × 7 backups.
#
# ⚠ IDEMPOTENCE OBLIGATOIRE : blueprints/soc.py contient des `from jarvis import X`
# dans des fonctions thread (`_soc_llm_call`, etc.) qui ré-importent jarvis.py comme
# module `jarvis` (Python ne le voit pas dans sys.modules car c'est `__main__`).
# Sans la garde, le handler serait ajouté à chaque ré-import → logs écrits 2x, 3x…
# Le nom de logger est unique (« JARVIS »), on filtre sur ce nom dans les handlers
# déjà attachés. (Fix 2026-05-23 — bug reproduit par Marc à 14:30 lecture audio + EQ).
_JARVIS_LOG_PATH = Path(__file__).parent / "jarvis.log"
if not any(
    isinstance(h, logging.handlers.RotatingFileHandler)
    and getattr(h, "baseFilename", None) == str(_JARVIS_LOG_PATH)
    for h in _log.handlers
):
    _jarvis_log_handler = logging.handlers.RotatingFileHandler(
        _JARVIS_LOG_PATH, maxBytes=5_000_000, backupCount=7, encoding="utf-8"
    )
    _jarvis_log_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)-8s] %(name)s | %(message)s",
                          datefmt="%Y-%m-%d %H:%M:%S")
    )
    _jarvis_log_handler.setLevel(logging.INFO)
    _log.addHandler(_jarvis_log_handler)

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
# TOOLS schemas deplaces dans chat/tool_schemas.py (etape 24, 2026-05-23)

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    from flask import Flask, Response, render_template, request
except ImportError:
    install("flask"); from flask import Flask, Response, request, render_template

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
    import psutil  # noqa: F401 — utilisé indirectement par runtime/gpu_stats + import local _psutil
except ImportError:
    install("psutil"); import psutil  # noqa: F401

try:
    import requests as req
except ImportError:
    install("requests"); import requests as req

# ── Modules dédiés (Phase 3 split monolithe · session 33) ────────────────────
from bypass import backup as _bypass_bk
from bypass import code as _bypass_code
from bypass import filesystem as _bypass_fs
from bypass import proxmox as _bypass_pve
from bypass import simple as _bypass_simple
from chat import messages as _chat_msg
from chat import orchestrator as _chat_orch
from chat import soc_inject as _chat_soc

# LlmCtx + _LAST_EXCHANGES vivent dans chat/orchestrator.py (étape 12) —
# aliases ici pour que jarvis.py garde la même surface (LlmCtx construit
# l'instance ligne 3457, _LAST_EXCHANGES consommé par api_history_last).
LlmCtx          = _chat_orch.LlmCtx
_LAST_EXCHANGES = _chat_orch._LAST_EXCHANGES

# TOOLS schemas (étape 24, 2026-05-23) — alias depuis chat/tool_schemas.py
from chat.tool_schemas import TOOLS  # noqa: E402,F401

import code_reasoning as _cr_mod
import commands as _commands
from voice import deferred_speak as _deferred_speak
import dev as _dev
import files as _files
import health as _health
import llm_opts as _llm_opts_mod
import memory as _memory
from proxmox import api as _pve_api
import rag as _rag
import rag_live as _rag_live_mod
import security_whitelists as _sec
import settings as _settings
import ssh as _ssh
import sse_helpers as _sse
import ssh_terminal as _ssh_term
import stream_tokens as _stream_tokens_mod
import system as _system
import tasks as _tasks
import vision as _vision
import web as _web
import voice as _voice
from voice import tts_cleaner as _tts_cleaner
from voice import tts_dedup as _tts_dedup
from voice import tts_engines as _tts_eng
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
_GPU_TEMP_WARN      = 82     # °C — seuil d'alerte logiciel (avant throttle HW à 90°C)
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
from voice import deepfilter as _df          # NDT: aussi consommé hors DSP (/api/sysdiag)
from voice import audio_dsp as _audio_dsp
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

# _load_facts + _now_fr + _facts_inject déménagés dans facts/inject.py
# (étape 34b, 2026-05-23). DI : FACTS_FILE + _load_memory_summary + _log.
from facts import inject as _facts_inject_mod  # noqa: E402
# Getter lambda pour FACTS_FILE : permet aux tests de monkeypatch jm.FACTS_FILE
# et de voir l'effet (sinon copie figée au moment de init()).
_facts_inject_mod.init(
    get_facts_file=lambda: FACTS_FILE,
    load_memory_summary=_load_memory_summary,
    log=_log,
)
# Aliases backward-compat pour les consommateurs (chat orchestrator, tests) :
_load_facts   = _facts_inject_mod.load_facts
_now_fr       = _facts_inject_mod.now_fr
_facts_inject = _facts_inject_mod.inject
_MOIS_FR      = _facts_inject_mod._MOIS_FR
_JOURS_FR     = _facts_inject_mod._JOURS_FR

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
# _JARVIS_BOOT_ID : identifiant unique de la session JARVIS (timestamp boot).
# Consommé par /api/boot-id côté frontend (_pollBootId boot_init.js:870) qui
# fait location.reload() si l'ID stocké en sessionStorage diffère du courant
# — mécanisme normal pour rafraîchir l'UI après un redémarrage serveur.
#
# ⚠ IDEMPOTENCE via env var (2026-05-23) : blueprints/soc.py contient des
# `from jarvis import X` dans des fonctions thread qui ré-importent jarvis.py
# comme module `jarvis` (Python ne le voit pas dans sys.modules car il tourne
# en `__main__`) → top-level RÉ-EXÉCUTÉ → `_JARVIS_BOOT_ID` régénéré avec un
# nouveau timestamp → côté JS, sessionStorage devient désynchrone → reload
# UI déclenché à tort. Le cache via os.environ est partagé entre tous les
# imports du même process Python, garantit que tous les modules voient
# exactement le même boot_id. C'est la VRAIE racine du bug UI reboot reporté
# par Marc à 14:30, 14:33, 14:51, 14:55 — fix précédent (idempotence handler
# + threads boot) résolvait les symptômes secondaires mais pas celui-ci.
_JARVIS_BOOT_ID = os.environ.get("_JARVIS_BOOT_ID_CACHE")
if not _JARVIS_BOOT_ID:
    _JARVIS_BOOT_ID = str(int(time.time()))
    os.environ["_JARVIS_BOOT_ID_CACHE"] = _JARVIS_BOOT_ID

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
# _net_prev + _disk_prev + _STATS_LOCK + 3 fonctions GPU déménagés dans
# runtime/gpu_stats.py (étape 31, 2026-05-23). Init en fin de fichier.
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

# 3 fonctions GPU stats déménagées dans runtime/gpu_stats.py (étape 31).
# init() inline ici : pynvml, _nvml_handle, _GPU_TEMP_WARN tous déjà définis ;
# MODEL est lu via getter lambda pour rester en phase avec _set_model_global.
from runtime import gpu_stats as _runtime_stats  # noqa: E402
_runtime_stats.init(
    pynvml=pynvml,
    nvml_handle=_nvml_handle,
    get_model=lambda: MODEL,
    gpu_temp_warn=_GPU_TEMP_WARN,
)
_gpu_cuda_procs      = _runtime_stats._gpu_cuda_procs
_gpu_extended_stats  = _runtime_stats._gpu_extended_stats
get_stats            = _runtime_stats.get_stats
_STATS_LOCK          = _runtime_stats._STATS_LOCK  # re-export pour code legacy

# ── TTS — speak() + état Queues déménagés dans runtime/speak.py (étape 31) ──
# _clean_for_tts garde son alias jarvis.py (consommateurs internes : chat orch).
_clean_for_tts = _tts_cleaner.clean_for_tts

from runtime import speak as _runtime_speak  # noqa: E402
_runtime_speak.init(
    log=_log,
    tts_logger=_tts_logger,
    clean_for_tts=_clean_for_tts,
    tts_dedup=_tts_dedup,
    tts_dedup_s=_TTS_DEDUP_S,
    tts_log_preview=_TTS_LOG_PREVIEW,
)
speak               = _runtime_speak.speak
_speak_queue        = _runtime_speak._speak_queue
_chat_stream_active = _runtime_speak._chat_stream_active
_speak_deferred     = _runtime_speak._speak_deferred

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
_VRAM_LOCK = threading.Lock()       # protège _vram_model + _ollama_swap (anti-race multi-requête)
_last_toks_per_sec: float = 0.0     # vitesse dernière génération (tok/s)
# _dev_cwd déplacé dans dev/routes.py (étape 22).


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

# _build_monitoring_context + _kc_ban_signal + _pve_context_lines + _INFRA_IPS
# déménagés dans chat/soc_context.py (étape 26, 2026-05-23). Aliases :
from chat import soc_context as _soc_context  # noqa: E402
_KC_BAN_SIGNAL_MIN_HITS  = _soc_context._KC_BAN_SIGNAL_MIN_HITS
_INFRA_IPS               = _soc_context._INFRA_IPS
_kc_ban_signal           = _soc_context.kc_ban_signal
_pve_context_lines       = _soc_context.pve_context_lines
_build_monitoring_context = _soc_context.build_monitoring_context
_soc_context.init(net_spike_window_s=_NET_SPIKE_WINDOW_S)

# Tuile files (refactor jarvis.py étape 6, 2026-05-23) : outils fichier
# vivent dans scripts/files/. Init immédiat (deps simples) + alias légers
# pour les consommateurs internes (execute_tool dispatcher, tests).
_WORKSPACE_ROOTS = [
    _WORKSPACE_ROOT,
    Path.home() / "AppData" / "Local" / "Temp",
]
_files.init(workspace_roots=_WORKSPACE_ROOTS)
_tool_lire_fichier             = _files._tool_lire_fichier
_check_local_write_path        = _files._check_local_write_path
_tool_ecrire_fichier           = _files._tool_ecrire_fichier
_tool_modifier_fichier         = _files._tool_modifier_fichier
_tool_lister_dossier           = _files._tool_lister_dossier
_tool_arborescence_projet      = _files._tool_arborescence_projet
_tool_lire_plusieurs_fichiers  = _files._tool_lire_plusieurs_fichiers

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

# 3 tools LLM déménagés dans tools/local.py (étape 33, 2026-05-23).
# Init déféré juste après _ALLOWED_SCRIPTS défini ; aliases backward-compat ci-dessous.
from tools import local as _tools_local  # noqa: E402
_tools_local.init(
    blocked_hard              = _BLOCKED_HARD,
    blocked_args              = _BLOCKED_ARGS,
    sec_log                   = _sec_log,
    fetch_monitoring          = _fetch_monitoring,
    build_monitoring_context  = _build_monitoring_context,
    allowed_scripts           = {},  # placeholder : init() re-appelé après _ALLOWED_SCRIPTS défini
    proc_timeout_s            = _BACKUP_PROC_TIMEOUT_S,
)
_tool_executer_code = _tools_local.executer_code
_tool_soc_status    = _tools_local.soc_status

# _tool_rechercher_dans_fichiers + constantes _RGLOB_* déménagées dans
# scripts/files/tools.py (étape 6).
_tool_rechercher_dans_fichiers = _files._tool_rechercher_dans_fichiers

# _BLOCKED_SSH, _ALLOWED_RESTART_SVCS, _ALLOWED_APT_PKGS, _check_write_op,
# _parse_upgradable_packages : déplacés dans security_whitelists.py (Phase 3 module 6b)
_SVC_BOUNCER = "crowdsec-firewall-bouncer"  # constante encore utilisée localement (ban TTL, etc.)


# Tuile ssh (refactor jarvis.py étape 7, 2026-05-23) : 4 wrappers
# _tool_commande_ssh_* + _ssh_timeout + cœur _tool_commande_ssh_run vivent
# dans scripts/ssh/. DI : 4 fonctions SSH (importées de blueprints.soc) +
# module security_whitelists.
_ssh.init(
    ssh_ngix    = _ssh_ngix,
    ssh_proxmox = _ssh_proxmox,
    ssh_clt     = _ssh_clt,
    ssh_pa85    = _ssh_pa85,
    security    = _sec,
)
_ssh_timeout               = _ssh._ssh_timeout
_tool_commande_ssh_run     = _ssh._tool_commande_ssh_run
_tool_commande_ssh_ngix    = _ssh._tool_commande_ssh_ngix
_tool_commande_ssh_proxmox = _ssh._tool_commande_ssh_proxmox
_tool_commande_ssh_clt     = _ssh._tool_commande_ssh_clt
_tool_commande_ssh_pa85    = _ssh._tool_commande_ssh_pa85

_ALLOWED_SCRIPTS = {
    "backup-auto":   str(_WORKSPACE_ROOT / "PROXMOX" / "proxmox-backup-auto.ps1"),
    "disk-report":   str(_WORKSPACE_ROOT / "PROXMOX" / "windows-disk-report.ps1"),
    "backup-jarvis": str(_WORKSPACE_ROOT / "JARVIS" / "scripts" / "backup-jarvis.ps1"),
}

# _tool_executer_script_windows déménagé dans tools/local.py (étape 33).
# Mutation in-place du dict _ALLOWED_SCRIPTS passé en DI (cohérent avec
# le placeholder de tools_local.init() ci-dessus — meme objet partagé).
_tools_local._allowed_scripts = _ALLOWED_SCRIPTS
_tool_executer_script_windows  = _tools_local.executer_script_windows

# _TOOL_DISPATCH construit dans tools/dispatch.py (étape 34a, 2026-05-23).
# Tous les handlers (14 outils, 4 tuiles) sont injectes en DI explicite.
from tools import dispatch as _tools_dispatch  # noqa: E402
_TOOL_DISPATCH = _tools_dispatch.build(
    lire_fichier             = _tool_lire_fichier,
    ecrire_fichier           = _tool_ecrire_fichier,
    modifier_fichier         = _tool_modifier_fichier,
    lister_dossier           = _tool_lister_dossier,
    arborescence_projet      = _tool_arborescence_projet,
    lire_plusieurs_fichiers  = _tool_lire_plusieurs_fichiers,
    executer_code            = _tool_executer_code,
    rechercher_dans_fichiers = _tool_rechercher_dans_fichiers,
    soc_status               = _tool_soc_status,
    commande_ssh_ngix        = _tool_commande_ssh_ngix,
    commande_ssh_proxmox     = _tool_commande_ssh_proxmox,
    commande_ssh_clt         = _tool_commande_ssh_clt,
    commande_ssh_pa85        = _tool_commande_ssh_pa85,
    executer_script_windows  = _tool_executer_script_windows,
)

# execute_tool + call_llm_with_tools déménagés dans chat/orchestrator.py (étape 25).
# Aliases pour les consommateurs externes (MCP server qui passe par /api/chat) :
execute_tool         = _chat_orch.execute_tool
call_llm_with_tools  = _chat_orch.call_llm_with_tools

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

# api_boot_id déménagée dans health/routes.py (étape 19).

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

# api_health, api_stats déménagées dans health/routes.py (étape 19).
# api_status déménagée dans health/routes.py (étape 32, 2026-05-23).
# api_soc_context déménagée dans blueprints/soc.py (étape 32, 2026-05-23).
# api_facts_get + api_facts_save déménagées dans facts/routes.py (étape 32).
# Init facts/ tardif (nécessite limiter défini) :
import facts as _facts  # noqa: E402
_facts.routes.init(limiter=limiter, facts_file=FACTS_FILE)
app.register_blueprint(_facts.bp)


# ── Diagnostic JS — instrumentation passive (2026-05-23) ──────────────────────
# Endpoint qui ingère les events JS critiques (window.onerror,
# unhandledrejection, location.reload pre-call) postés par boot_init.js.
# Tout est loggé dans scripts/jarvis.log sous le tag [JS-DIAG] avec source.
# Objectif : capturer la prochaine occurrence du bug « UI qui se relance »
# (Marc 2026-05-23) — révèle la cause exacte si reload JS ou exception non
# gérée frontend, sinon on saura que ça vient d'ailleurs.
@limiter.limit("60 per minute")
@app.route("/api/_diag/jslog", methods=["POST"])
def api_diag_jslog():
    try:
        data = request.json or {}
        kind = str(data.get("kind", "?"))[:32]
        msg = str(data.get("msg", ""))[:1000].replace("\n", " ⏎ ")
        src = str(data.get("src", ""))[:300]
        url = str(data.get("url", ""))[:300]
        _log.warning(f"[JS-DIAG] kind={kind} | url={url} | src={src} | msg={msg}")
    except Exception as e:
        _log.warning(f"[JS-DIAG] parse failed: {e}")
    return Response('{"ok":true}', mimetype="application/json")


# Routes /api/memory* + /api/memory-summary* + /api/memory/summarize-session
# déménagées dans la tuile scripts/memory/routes.py (étape 4).

# Routes /api/rag/* déménagées dans la tuile scripts/rag/routes.py (étape 5).

# api_code_exec déménagée dans dev/routes.py (étape 22)

# Routes /api/llm-params + /api/llm-params/reset-prompt déménagées dans
# settings/routes.py (étape 17, 2026-05-23).

def _ensure_vram(next_model: str):
    """Décharge le modèle actuellement en VRAM si différent du prochain.
    Évite les collisions VRAM lors du routing automatique inter-modes.

    Protégé par `_VRAM_LOCK` (Improvement #1, 2026-05-23) : sérialise le
    check + swap + mutation pour éliminer la race condition multi-requête
    (ex: /api/chat user A + /api/sysdiag _diag_ollama en parallèle)."""
    global _vram_model
    effective = next_model or MODEL
    with _VRAM_LOCK:
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
            _model_next = {"soc": MODEL, "general": _GENERAL_MODEL, "code": _CODE_MODEL, "code_reasoning": _CODE_REASONING_ANALYSIS_MODEL}.get(new_mode, MODEL)
            # _ensure_vram() est protégé par _VRAM_LOCK (Improvement #1) :
            # sérialise check + swap + mutation. Plus de chemin direct vers
            # _ollama_swap qui contournerait le lock.
            _ensure_vram(_model_next)
    _model_map = {"soc": MODEL, "general": _GENERAL_MODEL, "code": _CODE_MODEL, "code_reasoning": _CODE_REASONING_ANALYSIS_MODEL}
    return Response(json.dumps({"mode": _jarvis_mode, "model": _model_map.get(_jarvis_mode, MODEL)}),
                    mimetype="application/json")

# api_dev_exec + dev_stats déménagées dans dev/routes.py (étape 22)


# WS PTY SSH (ws_ssh_host + ws_dev + 3 helpers) déménagés dans
# terminal/ssh_ws.py (étape 30, 2026-05-23). init() différé en fin de fichier
# (nécessite _SSH_TERMINAL_MAP défini plus bas via _ssh_term.TERMINAL_MAP).
from terminal import ssh_ws as _term_ws  # noqa: E402
# Aliases backward-compat pour tests éventuels :
_ws_ssh_reader  = _term_ws._ssh_reader
_ws_ssh_connect = _term_ws._ssh_connect
_ws_ssh_handler = _term_ws._ssh_handler

# api_save_code déménagée dans dev/routes.py (étape 22)

# api_ollama_status + api_vram déménagées dans health/routes.py (étape 19).

# Routes /api/prompt-profiles* + /api/welcome* déménagées dans settings/routes.py (étape 17).

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

# ── Routes voice (STT/TTS/speak) déménagées dans scripts/voice/routes.py ──
# (refactor jarvis.py étapes 13-14 — Phases B1+B2 voice tuile, 2026-05-23).
# Init différé plus bas : nécessite _tts_internet_was_up défini tard.

# Route /api/vision déménagée dans vision/routes.py (étape 16, 2026-05-23).
_vision.init(
    limiter          = limiter,
    ollama_url       = OLLAMA_URL,
    vision_timeout_s = _OLLAMA_VISION_TIMEOUT_S,
    sse_headers      = _SSE_HEADERS,
    rag_inject_fn    = _rag_inject,
)
app.register_blueprint(_vision.bp)

# Routes /api/cr-poll + /api/tasks* déménagées dans tasks/routes.py (étape 18, 2026-05-23).
_tasks.init(
    limiter            = limiter,
    log                = _log,
    get_tasks_file     = lambda: TASKS_FILE,   # lambda pour suivre les monkeypatch de test
    terminal_cwd       = TERMINAL_CWD,
    terminal_timeout_s = _TERMINAL_TIMEOUT_S,
    cr_tasks           = _cr_mod.tasks,
)
app.register_blueprint(_tasks.bp)
# Aliases backward-compat pour les tests (jm._load_tasks, jm._save_tasks)
_load_tasks = _tasks.routes._load_tasks
_save_tasks = _tasks.routes._save_tasks

# ── Init tuile health (étape 19, 2026-05-23) ──
_health.init(
    limiter                    = limiter,
    log                        = _log,
    ollama_circuit             = _ollama_circuit,
    ollama_status_timeout_s    = _OLLAMA_STATUS_TIMEOUT_S,
    ssh_proxmox_cmd_timeout_s  = _SSH_PROXMOX_CMD_TIMEOUT_S,
    stats_cache                = _stats_cache,
    stats_ttl                  = _STATS_TTL,
    sec_events                 = _SEC_EVENTS,
    sec_lock                   = _SEC_LOCK,
    get_boot_id                = lambda: _JARVIS_BOOT_ID,
    get_stats_fn               = get_stats,
    get_model                  = lambda: MODEL,
    get_last_toks_per_sec      = lambda: _last_toks_per_sec,
    get_llm_params             = lambda: LLM_PARAMS,
    get_soc_status             = get_soc_status,
    code_reasoning_model       = _CODE_REASONING_ANALYSIS_MODEL,
    code_model                 = _CODE_MODEL,
    general_model              = _GENERAL_MODEL,
)
app.register_blueprint(_health.bp)

# ── Web Search (DuckDuckGo HTML) ──────────────────────────────
# Web search + /api/web-test déménagés dans web/ tuile (étape 23, 2026-05-23).
# web_search() exposée en alias pour _chat_build_system_prompt (chat orchestrator).
_web.init(
    limiter                = limiter,
    log                    = _log,
    web_search_timeout_s   = _WEB_SEARCH_TIMEOUT_S,
    web_fetch_timeout_s    = _WEB_FETCH_TIMEOUT_S,
    web_conn_timeout_s     = _WEB_CONN_TIMEOUT_S,
    web_fetch2_timeout_s   = _WEB_FETCH2_TIMEOUT_S,
)
app.register_blueprint(_web.bp)
web_search = _web.search.web_search  # alias pour chat orchestrator

# Listes SOC keywords déplacées dans chat_soc_inject.py — alias backward-compat
_CHAT_SOC_KW       = _chat_soc.SOC_KW
_CHAT_SOC_VOCAL_KW = _chat_soc.SOC_VOCAL_KW

_CHAT_PVE_KW = _pve_api.CHAT_PVE_KW  # alias backward-compat

# Fonctions Proxmox API déplacées dans proxmox_api.py — alias backward-compat
_pve_fetch_state     = _pve_api.fetch_state
_pve_context_summary = _pve_api.context_summary
_chat_inject_pve     = _pve_api.chat_inject


# Wrappers chat déplacés dans chat/orchestrator.py (étape 12 refactor jarvis.py,
# 2026-05-23). Aliases conservés ici pour les consommateurs internes
# (_chat_try_bypass, api_chat avant son déménagement étape 13).
_chat_build_messages = _chat_msg.build_messages
_APT_HOST_MAP = {
    "commande_ssh_clt":     ("clt",      _ssh_clt),
    "commande_ssh_pa85":    ("pa85",     _ssh_pa85),
    "commande_ssh_ngix":    ("srv-ngix", _ssh_ngix),
    "commande_ssh_proxmox": ("proxmox",  _ssh_proxmox),
}
_cr_tasks            = _cr_mod.tasks  # state partagé (utilisé par /api/cr-poll/<task_id>)
_chat_inject_soc     = _chat_orch._chat_inject_soc
_run_tool_calls      = _chat_orch._run_tool_calls
_build_llm_opts      = _chat_orch._build_llm_opts
_stream_tokens_tts   = _chat_orch._stream_tokens_tts
_flush_deferred_speak= _chat_orch._flush_deferred_speak
_code_reasoning_gen  = _chat_orch._code_reasoning_gen
_chat_stream_inner   = _chat_orch._chat_stream_inner

# ── Détection commandes VM Proxmox (bypass LLM) ───────────────
# Wrappers DI + tables/regex couplées _ssh_* déménagés dans bypass/wrappers.py
# (étape 27, 2026-05-23). Init en fin de fichier (nécessite _pve_fetch_state +
# _sse_tok définis tard). Aliases backward-compat conservés ici.
_pending_reboot: dict = {}  # {host, ssh_fn, is_proxmox, ts} — reboot différé après upgrade

# Aliases backward-compat — pointeurs vers bypass/wrappers (rempli par init() tardif)
from bypass import wrappers as _bypass_wrap  # noqa: E402
_detect_service_restart = _bypass_wrap.detect_service_restart
_detect_vm_command      = _bypass_wrap.detect_vm_command
_detect_reboot_command  = _bypass_wrap.detect_reboot_command
_detect_update_command  = _bypass_wrap.detect_update_command


# 6 générateurs SSE commandes infra déplacés dans commands/sse.py (étape 20).
# Init en fin de fichier (nécessite _sse_tok défini ligne ~2500 + _pve_fetch_state).
# Aliases conservés ici pour les consommateurs (_chat_try_bypass, _vm_command_sse).
_vm_command_sse             = _commands.vm_command_sse
_post_start_verify_sse      = _commands.post_start_verify_sse
_update_machine_sse         = _commands.update_machine_sse
_pve_stop_vms_before_reboot = _commands.pve_stop_vms_before_reboot
_reboot_machine_sse         = _commands.reboot_machine_sse
_service_restart_sse        = _commands.service_restart_sse


# _sse_tok et _sse_response déplacés dans sse_helpers.py — alias backward-compat
_sse_tok = _sse.sse_tok
_sse_response = _sse.sse_response


# _LAST_EXCHANGES + _capture_gen vivent dans chat/orchestrator.py (étape 12).
# Alias _LAST_EXCHANGES défini en haut (consommé par api_history_last).
_capture_gen = _chat_orch._capture_gen


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

# File correction (validate_protect_directives + PROTECTED_DIRECTIVES + 3 SSE gens)
# déplacée dans chat/file_correct.py (étape 21, 2026-05-23). Aliases backward-compat
# pour les tests existants (jm._validate_protect_directives) :
from chat import file_correct as _file_correct_mod  # noqa: E402
_PROTECTED_DIRECTIVES        = _file_correct_mod.PROTECTED_DIRECTIVES
_validate_protect_directives = _file_correct_mod.validate_protect_directives

# _detect_file_command, _detect_multi_file_command, _file_command_sse :
# déplacés dans bypass_filesystem.py (Phase 3 module 7) — appelés via _bypass_fs.*
# Regex FEDIT_RE, FADD_RE, SUR_VM_RE sont maintenant dans bypass_filesystem.py


# _file_correct_gen, _file_correct_multi_gen, _file_correct_multi_inject
# déménagés dans chat/file_correct.py (étape 21, 2026-05-23). Aliases :
_file_correct_gen           = _file_correct_mod.file_correct_gen
_file_correct_multi_gen     = _file_correct_mod.file_correct_multi_gen
_file_correct_multi_inject  = _file_correct_mod._file_correct_multi_inject


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

# Init tuile terminal (étape 30, 2026-05-23) — enregistre /ws/ssh/<host> + /ws/dev
_term_ws.init(sock=sock, ssh_terminal_map=_SSH_TERMINAL_MAP)
# _dev_stats_cache + _STATS_CMD déplacés dans dev/routes.py (étape 22).

# Regex/helpers code déplacés dans bypass_code.py (Phase 3 module 10)


# ── Bypass SSH terminal — regexes par hôte ────────────────────────────────────
# Regex + générateur SSH terminal déplacés dans ssh_terminal.py
_SSH_TERMINAL_RE = _ssh_term.TERMINAL_RE
_ssh_terminal_sse = _ssh_term.terminal_sse


# Wrappers code/backup + apt_upgrade SSE déménagés dans bypass/wrappers.py
# (étape 27, 2026-05-23). Aliases backward-compat ci-dessous (pointeurs vers
# fonctions du module wrappers — valides dès l'import, init() tardif).
_detect_code_command     = _bypass_wrap.detect_code_command
_code_scp_exec_sse       = _bypass_wrap.code_scp_exec_sse
_detect_backup_command   = _bypass_wrap.detect_backup_command
_backup_sse              = _bypass_wrap.backup_sse
_jarvis_backup_log_sse   = _bypass_wrap.jarvis_backup_log_sse
_jarvis_backup_sse       = _bypass_wrap.jarvis_backup_sse
_apt_upgrade_bypass_sse  = _bypass_wrap.apt_upgrade_bypass_sse

# _datetime_bypass_sse déplacé dans bypass_simple.py → utiliser _bypass_simple.datetime_sse()


# _dev_exec_sse + _dev_cwd + _STATS_CMD + _dev_stats_cache déménagés
# dans dev/routes.py (étape 22).


# _chat_resolve_pending_bypass vit dans chat/orchestrator.py (étape 12).
_chat_resolve_pending_bypass = _chat_orch._chat_resolve_pending_bypass


# _chat_try_bypass + _detect_file_corrections + api_chat déménagés dans
# chat/dispatcher.py (étape 28, 2026-05-23). Aliases backward-compat ci-dessous
# et register_blueprint + init() tardif en fin de fichier.
from chat import dispatcher as _chat_dispatch  # noqa: E402
_chat_try_bypass         = _chat_dispatch.chat_try_bypass
_detect_file_corrections = _chat_dispatch.detect_file_corrections

# 3 derniers wrappers chat déplacés dans chat/orchestrator.py (étape 12).
_chat_generate            = _chat_orch._chat_generate
_chat_build_system_prompt = _chat_orch._chat_build_system_prompt
_chat_resolve_model       = _chat_orch._chat_resolve_model

# api_history_last déménagée dans chat/dispatcher.py (étape 32, 2026-05-23).
# api_security + api_security_clear déménagées dans health/routes.py (étape 19).

# api_dsp_process_audio déménagée dans settings/routes.py (étape 17).
# api_speak déménagée dans voice/routes.py (étape 14).
# api_ping déménagée dans health/routes.py (étape 19).

# Routes speak/tts/tts_log/tts_status/tts_local_* déménagées dans
# voice/routes.py (étape 14, 2026-05-23). _tts_wav_response,
# _tts_local_response, _tts_edge_fallback sont des helpers internes au tuile.

# Routes /api/dsp-params + /api/models* déménagées dans settings/routes.py (étape 17).

# Routes /api/voices + /api/voice/* déménagées dans voice/routes.py (étape 15).


def _set_voice_global(voice_id: str) -> bool:
    """Setter VOICE injecté à la tuile voice. Valide l'id dans VOICES."""
    global VOICE
    if any(v["id"] == voice_id for v in VOICES):
        VOICE = voice_id
        return True
    return False




# 9 threads boot (kokoro/tts-conn/gpu-temp/rag-embed/boot-vram/soc-prewarm/
# kokoro-prewarm/rag-auto-refresh/vram-sync) + rag-live-prewarm démenagés
# dans bootstrap/threads.py (étape 29, 2026-05-23). Init + start_all() en
# fin de fichier (nécessite speak, _vram_lock, get/set _vram_model définis).
from bootstrap import threads as _boot_th  # noqa: E402

# Aliases backward-compat — _tts_internet_was_up est lu par voice/routes (get_internet_up)
# Compatibilité maintenue via getter lambda passé à _voice.init() plus bas.
_tts_stop_evt         = _boot_th._tts_stop_evt
_gpu_stop_evt         = _boot_th._gpu_stop_evt
_rag_refresh_stop_evt = _boot_th._rag_refresh_stop_evt

# _rag_auto_refresh_loop : déménagée dans bootstrap/threads.py (étape 29).

# ── Init chat/file_correct (étape 21) — placé tard pour _sse_tok ──
_file_correct_mod.init(log=_log, sse_tok=_sse_tok)

# ── Init tuile dev (étape 22) — code/exec + dev/exec + dev/stats + save-code ──
_dev.init(
    limiter               = limiter,
    log                   = _log,
    ssh_dev1              = _ssh_dev1,
    code_scp_exec_sse_fn  = _code_scp_exec_sse,
    sse_tok               = _sse_tok,
    code_dev_ip           = _CODE_DEV_IP,
    code_dev_port         = _CODE_DEV_PORT,
    code_dev_key          = _CODE_DEV_KEY,
    generated_code_dir    = Path(__file__).parent / "generated_code",
)
app.register_blueprint(_dev.bp)

# ── Init tuile bypass/wrappers (étape 27, 2026-05-23) — placé ici avant ──
# _commands.init (qui consomme VM_START_SSH_MAP) et avant _chat_orch.init
# (qui consomme _apt_upgrade_bypass_sse). DI : 5 SSH fns + 3 modules bypass +
# _pve_fetch_state + _sse_tok + _log + dicts mutables.
_bypass_wrap.init(
    ssh_ngix          = _ssh_ngix,
    ssh_proxmox       = _ssh_proxmox,
    ssh_clt           = _ssh_clt,
    ssh_pa85          = _ssh_pa85,
    ssh_dev1          = _ssh_dev1,
    bypass_pve        = _bypass_pve,
    bypass_code       = _bypass_code,
    bypass_bk         = _bypass_bk,
    pve_fetch_state   = _pve_fetch_state,
    sse_tok           = _sse_tok,
    log               = _log,
    pending_infra_cmd = _pending_infra_cmd,
    allowed_scripts   = _ALLOWED_SCRIPTS,
    ssh_apt_timeout_s = _SSH_APT_TIMEOUT_S,
    svc_bouncer       = _SVC_BOUNCER,
)

# ── Init tuile commands (étape 20, 2026-05-23) — placé tard car nécessite ──
# _pve_fetch_state (alias chat orchestrator) + _sse_tok (sse helpers alias).
_commands.init(
    ssh_proxmox                  = _SSH_PROXMOX,
    ssh_proxmox_cmd_timeout_s    = _SSH_PROXMOX_CMD_TIMEOUT_S,
    ssh_proxmox_state_timeout_s  = _SSH_PROXMOX_STATE_TIMEOUT_S,
    ssh_apt_timeout_s            = _SSH_APT_TIMEOUT_S,
    systemctl_restart_timeout_s  = _SYSTEMCTL_RESTART_TIMEOUT_S,
    systemctl_status_timeout_s   = _SYSTEMCTL_STATUS_TIMEOUT_S,
    pve_fetch_state              = _pve_fetch_state,
    bypass_pve                   = _bypass_pve,
    vm_start_ssh_map             = _bypass_wrap.VM_START_SSH_MAP,
    pending_reboot               = _pending_reboot,
    sse_tok                      = _sse_tok,
    log                          = _log,
)

# ── Init différé de la tuile voice (refactor étapes 13-14, 2026-05-23) ──
# Placé ici car _tts_internet_was_up est défini tard (ligne ~3896).
# ── Init tuile settings (étape 17) — setters pour les mutables jarvis.py ──
def _set_system_prompt_global(v: str) -> None:
    global SYSTEM_PROMPT
    SYSTEM_PROMPT = v

def _set_model_global(v: str) -> None:
    global MODEL
    MODEL = v

def _reset_welcome_global() -> None:
    global _welcome_data
    _welcome_data = dict(DEFAULT_WELCOME)

def _set_auto_profile_model_global(v) -> None:
    global _AUTO_PROFILE_MODEL
    _AUTO_PROFILE_MODEL = v

_SETTINGS_DSP_SAFE_STR = {
    "tts_engine":         {"edge", "kokoro", "piper", "sapi"},
    "tts_default_engine": {"edge", "kokoro", "piper", "sapi"},
    "fx_type":             {"reverb", "delay", "chorus", "flanger", "echo", "phaser", "exciter"},
    "fx_preset":           {"room", "studio", "concert", "cathedral", "plate", "cave", "spring"},
}
_SETTINGS_DSP_BOUNDS = {
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

_settings.init(
    limiter = limiter,
    log = _log,
    ollama_circuit = _ollama_circuit,
    ollama_url = OLLAMA_URL,
    ollama_tool_detect_timeout_s = _OLLAMA_TOOL_DETECT_TIMEOUT_S,
    dsp_max_bytes = _DSP_MAX_BYTES,
    get_llm_params = lambda: LLM_PARAMS,
    get_system_prompt = lambda: SYSTEM_PROMPT,
    get_model = lambda: MODEL,
    get_models = lambda: MODELS,
    get_dsp_params = lambda: DSP_PARAMS,
    get_welcome_data = lambda: _welcome_data,
    get_auto_profile_model = lambda: _AUTO_PROFILE_MODEL,
    set_system_prompt = _set_system_prompt_global,
    set_model = _set_model_global,
    set_dsp_params = lambda d: DSP_PARAMS.update(d),  # mutation in-place
    set_welcome_data = lambda d: _welcome_data.update(d),  # mutation in-place
    reset_welcome = _reset_welcome_global,
    save_model_fn = _save_model,
    set_auto_profile_model = _set_auto_profile_model_global,
    llm_defaults = _LLM_DEFAULTS,
    default_system_prompt = DEFAULT_SYSTEM_PROMPT,
    llm_params_file = LLM_PARAMS_FILE,
    prompt_file = PROMPT_FILE,
    prompt_profiles_file = PROMPT_PROFILES_FILE,
    welcome_file = WELCOME_FILE,
    default_welcome = DEFAULT_WELCOME,
    dsp_params_file = DSP_PARAMS_FILE,
    dsp_safe_str = _SETTINGS_DSP_SAFE_STR,
    dsp_bounds = _SETTINGS_DSP_BOUNDS,
    model_lock = _MODEL_LOCK,
    get_model_profile_fn = _get_model_profile,
    fetch_ollama_models_fn = _fetch_ollama_models,
    apply_dsp_to_mp3_fn = apply_dsp_to_mp3,
)
app.register_blueprint(_settings.bp)

_voice.init(
    limiter            = limiter,
    log                = _log,
    tts_logger         = _tts_logger,
    speak_fn           = speak,
    speak_queue        = _speak_queue,
    speak_deferred     = _speak_deferred,
    chat_stream_active = _chat_stream_active,
    tts_log_path       = _TTS_LOG_PATH,
    get_dsp_params     = lambda: DSP_PARAMS,
    get_voice          = lambda: VOICE,
    get_voices         = lambda: VOICES,
    set_voice          = _set_voice_global,
    get_internet_up    = lambda: _boot_th._tts_internet_was_up,
    clean_for_tts      = _clean_for_tts,
    tts_log_preview    = _TTS_LOG_PREVIEW,
    tts_dedup_s        = _TTS_DEDUP_S,
)
app.register_blueprint(_voice.bp)


# _vram_sync_loop : déménagée dans bootstrap/threads.py (étape 29).

# Setter pour _vram_model — injecté à bootstrap/threads (vram_sync_loop)
def _set_vram_model_global(v) -> None:
    global _vram_model
    _vram_model = v

# ── Init bootstrap/threads (étape 29, 2026-05-23) — placé tard car nécessite ──
# speak (défini après voice.init), _vram_lock + _vram_model (globals jarvis),
# _rag_live_prewarm (alias rag.engine). start_all() lance les 10 threads daemon.
import blueprints.soc as _soc_bp  # noqa: E402
_boot_th.init(
    log                  = _log,
    dsp_params           = DSP_PARAMS,
    tts_eng              = _tts_eng,
    apply_dsp_to_mp3     = apply_dsp_to_mp3,
    pynvml               = pynvml,
    nvml_handle          = _nvml_handle,
    speak                = speak,
    ollama_circuit       = _ollama_circuit,
    req                  = req,
    ollama_url           = OLLAMA_URL,
    rag_embed_model      = RAG_EMBED_MODEL,
    soc_num_ctx          = _SOC_NUM_CTX,
    workspace_root       = _WORKSPACE_ROOT,
    rag_index_text       = _rag_index_text,
    rag_live_prewarm     = _rag_live_prewarm,
    vram_lock            = _VRAM_LOCK,
    get_model            = lambda: MODEL,
    get_vram_model       = lambda: _vram_model,
    set_vram_model       = _set_vram_model_global,
    soc_cooldown_ok      = _soc_bp._soc_cooldown_ok,
    ollama_diag_timeout_s = _OLLAMA_DIAG_TIMEOUT_S,
    gpu_temp_warn        = _GPU_TEMP_WARN,
    gpu_mon_start_s      = _GPU_MON_START_S,
    gpu_mon_poll_s       = _GPU_MON_POLL_S,
    rag_refresh_h        = _RAG_REFRESH_H,
)
_boot_th.start_all()

# ── Init différé de la tuile chat (refactor jarvis.py étape 12, 2026-05-23) ──
# Placé ici car les SSE generators (_apt_upgrade_bypass_sse, _reboot_machine_sse)
# sont définis tard. À ce point, TOUTES les deps du chat orchestrator existent.
_chat_orch.init(
    log                            = _log,
    security                       = _sec,
    ollama_circuit                 = _ollama_circuit,
    llm_opts_mod                   = _llm_opts_mod,
    stream_tokens_mod              = _stream_tokens_mod,
    voice_deferred_speak           = _deferred_speak,
    code_reasoning_mod             = _cr_mod,
    bypass_pve                     = _bypass_pve,
    fetch_monitoring               = _fetch_monitoring,
    build_monitoring_context       = _build_monitoring_context,
    fetch_defense                  = _fetch_defense,
    ensure_vram                    = _ensure_vram,
    stream_llm                     = stream_llm,
    clean_for_tts                  = _clean_for_tts,
    facts_inject                   = _facts_inject,
    rag_inject                     = _rag_inject,
    web_search                     = web_search,
    chat_inject_pve                = _chat_inject_pve,
    apt_upgrade_sse                = _apt_upgrade_bypass_sse,
    reboot_machine_sse             = _reboot_machine_sse,
    sse_response                   = _sse_response,
    sse_tok                        = _sse_tok,
    tool_dispatch                  = _TOOL_DISPATCH,
    apt_host_map                   = _APT_HOST_MAP,
    pending_infra_cmd              = _pending_infra_cmd,
    pending_reboot                 = _pending_reboot,
    speak_deferred                 = _speak_deferred,
    chat_stream_active             = _chat_stream_active,
    get_system_prompt              = lambda: SYSTEM_PROMPT,
    get_model                      = lambda: MODEL,
    get_mode                       = lambda: _jarvis_mode,
    general_model                  = _GENERAL_MODEL,
    code_model                     = _CODE_MODEL,
    code_reasoning_analysis_model  = _CODE_REASONING_ANALYSIS_MODEL,
    code_system_suffix             = _CODE_SYSTEM_SUFFIX,
    ollama_url                     = OLLAMA_URL,
    llm_params                     = LLM_PARAMS,
    llm_defaults                   = _LLM_DEFAULTS,
    soc_temperature                = _SOC_TEMPERATURE,
    soc_num_ctx                    = _SOC_NUM_CTX,
    num_ctx_short                  = _NUM_CTX_SHORT,
    reasoning_np_min               = _REASONING_NP_MIN,
    tts_phrase_min                 = _TTS_PHRASE_MIN,
    tool_call_max                  = _TOOL_CALL_MAX,
    tool_result_trunc              = _TOOL_RESULT_TRUNC,
    ollama_tool_detect_timeout_s   = _OLLAMA_TOOL_DETECT_TIMEOUT_S,
    pending_apt_ttl_s              = _PENDING_APT_TTL_S,
    confirm_re                     = _CONFIRM_RE,
    cancel_re                      = _CANCEL_RE,
    rag_relevant_kw                = _RAG_RELEVANT_KW,
)

# ── Init tuile chat/dispatcher (étape 28, 2026-05-23) — placé tard car ──
# consomme les helpers chat_orch (_chat_generate / _chat_build_system_prompt /
# _chat_resolve_model / _code_reasoning_gen) qui n'existent qu'après l'init
# de _chat_orch ci-dessus. La route /api/chat est portée par bp dispatcher.
_chat_dispatch.init(
    log                          = _log,
    limiter                      = limiter,
    bypass_simple                = _bypass_simple,
    bypass_fs                    = _bypass_fs,
    bypass_wrap                  = _bypass_wrap,
    chat_orch                    = _chat_orch,
    sse_response                 = _sse_response,
    capture_gen                  = _capture_gen,
    vm_command_sse               = _vm_command_sse,
    reboot_machine_sse           = _reboot_machine_sse,
    update_machine_sse           = _update_machine_sse,
    service_restart_sse          = _service_restart_sse,
    ssh_terminal_sse             = _ssh_terminal_sse,
    chat_resolve_pending_bypass  = _chat_resolve_pending_bypass,
    chat_build_system_prompt     = _chat_build_system_prompt,
    chat_resolve_model           = _chat_resolve_model,
    chat_generate                = _chat_generate,
    code_reasoning_gen           = _code_reasoning_gen,
    chat_build_messages          = _chat_build_messages,
    facts_inject                 = _facts_inject,
    file_correct_gen             = _file_correct_gen,
    file_correct_multi_gen       = _file_correct_multi_gen,
    file_vm_ssh                  = _FILE_VM_SSH,
    fcorr_re                     = _FCORR_RE,
    ssh_terminal_re              = _SSH_TERMINAL_RE,
    ssh_terminal_map             = _SSH_TERMINAL_MAP,
    code_dev_vm                  = _CODE_DEV_VM,
    sse_headers                  = _SSE_HEADERS,
    code_reasoning_mode          = _CODE_REASONING_MODE,
    code_model                   = _CODE_MODEL,
    code_system_suffix           = _CODE_SYSTEM_SUFFIX,
    llm_ctx_cls                  = LlmCtx,
    get_system_prompt            = lambda: SYSTEM_PROMPT,
    get_model                    = lambda: MODEL,
    get_mode                     = lambda: _jarvis_mode,
)
app.register_blueprint(_chat_dispatch.bp)

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
