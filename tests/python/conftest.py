"""conftest pytest — ajoute scripts/ au sys.path pour importer les modules JARVIS sans installation.

Tests unitaires Python — chantier dette technique 2026-05-15.
"""
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
