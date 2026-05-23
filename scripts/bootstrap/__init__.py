"""Tuile **bootstrap** — threads de démarrage et préchauffage.

Architecture par tuiles (refactor jarvis.py étape 29, 2026-05-23) — 17ème tuile.
**Pas de routes HTTP** — uniquement des threads daemon lancés au démarrage de
JARVIS pour préchauffer les modèles (LLM SOC, Kokoro CUDA, embed RAG), nettoyer
la VRAM, et surveiller en continu (température GPU, connectivité Internet pour
le switch TTS auto, synchronisation `_vram_model` avec l'état réel d'Ollama).

Sous-modules :
- `threads` : 9 fonctions thread + `init(...)` (DI) + `start_all()` (lance tout)

Pourquoi tout dans un seul module ? Toutes les fonctions partagent les mêmes
~20 dépendances (logger, DSP_PARAMS, Ollama circuit, modules TTS, …) — les
éclater par catégorie multiplierait les init() sans réel gain.
"""
from . import threads  # noqa: F401
