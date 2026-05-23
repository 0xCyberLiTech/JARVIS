"""conftest pytest — ajoute scripts/ au sys.path pour importer les modules JARVIS sans installation.

Tests unitaires Python — chantier dette technique 2026-05-15.

⚠ IMPORTANT — JARVIS_SKIP_BOOT_THREADS=1 setté AVANT tout import (2026-05-23) :
les 5 fichiers test_jarvis_* importent `jarvis` au chargement → sans ce garde-fou,
pytest démarrerait les 10 threads boot dans son propre process Python (synthèse
Kokoro audio, déchargement modèles Ollama, prewarm phi4/Kokoro), interférant
avec une instance JARVIS en service sur la même machine. Le flag est lu dans
bootstrap/threads.start_all() qui retourne immédiatement sans rien lancer.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("JARVIS_SKIP_BOOT_THREADS", "1")

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
