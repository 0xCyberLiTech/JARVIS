"""TTS Cleaner — nettoyage texte avant synthèse vocale (markdown → texte parlable).

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 16.

Pure regex / dict — zéro dépendance externe, zéro IO.

Couvre :
- Suppression `<think>...</think>` (modèles raisonnement DeepSeek-R1, qwen3:8b)
- Blocs de code ``` ``` → silence
- Markdown : gras/italique/barré/titres/listes/liens/images/tableaux/citations
- Conversion IPs (192.168.1.50 → "un neuf deux point un six huit point un point cinq zéro")
- Normalisation espaces / lignes vides
"""
import re

# ── Helper IP → lecture chiffre par chiffre ───────────────────
_DIGITS_FR = {
    '0': 'zéro', '1': 'un',    '2': 'deux',  '3': 'trois', '4': 'quatre',
    '5': 'cinq', '6': 'six',   '7': 'sept',  '8': 'huit',  '9': 'neuf',
}


def _ip_octet(n: str) -> str:
    """Convertit '192' → 'un neuf deux' (chiffre par chiffre en français)."""
    return ' '.join(_DIGITS_FR[d] for d in n)


def replace_ips(s: str) -> str:
    """Convertit les adresses IP en lecture chiffre-par-chiffre.
    Gère le format point (192.168.1.50) et tiret (192-168-1-50)."""
    # Format avec points
    s = re.sub(
        r'\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b',
        lambda m: ' point '.join(_ip_octet(m.group(i)) for i in range(1, 5)),
        s,
    )
    # Format avec tirets (généré par certains profils LLM)
    s = re.sub(
        r'\b(\d{1,3})-(\d{1,3})-(\d{1,3})-(\d{1,3})\b',
        lambda m: ' point '.join(_ip_octet(m.group(i)) for i in range(1, 5)),
        s,
    )
    return s


# ── API publique ──────────────────────────────────────────────

def clean_for_tts(text: str) -> str:
    """Nettoie le markdown pour que le TTS prononce naturellement."""
    # Balises <think>...</think> (DeepSeek-R1 et modèles raisonnement) → silence
    text = re.sub(r'<think>[\s\S]*?</think>', '', text, flags=re.IGNORECASE)
    # Blocs de code ``` → silence
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Code inline `foo` → juste le contenu
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # **gras** ou __gras__
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    # *italique* ou _italique_
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    # ~~barré~~
    text = re.sub(r'~~(.+?)~~', r'\1', text)
    # Titres # ## ### → juste le texte
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Listes numérotées "1. " "2. " → supprime le numéro et le point
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    # Puces "- " "* " "+ " en début de ligne
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    # Liens [texte](url) → texte
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Images ![alt](url) → supprime
    text = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', text)
    # Tableaux markdown : lignes | col | col | → retire les pipes
    text = re.sub(r'\|', ' ', text)
    # Lignes de séparateur --- === *** ___
    text = re.sub(r'^\s*[-=*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # > citations
    text = re.sub(r'^\s*>\s*', '', text, flags=re.MULTILINE)
    # Astérisques/underscores isolés résiduels
    text = re.sub(r'[*_]{1,3}', '', text)
    # Adresses IP : "192.168.1.50" → "un neuf deux point un six huit point un point cinq zéro"
    text = replace_ips(text)
    # Espaces multiples / lignes vides en excès
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()
