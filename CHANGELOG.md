# Changelog

Toutes les évolutions notables de la vitrine **JARVIS** sont consignées dans ce fichier.

Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le projet suit le [versionnage sémantique](https://semver.org/lang/fr/).

## [1.0.0] — 2026-06-15

Première version publique de la vitrine.

### Ajouté
- **Galerie de l'interface** — tour visuel des modules : écran d'accueil, réglages LLM & profils GPU, poste de pilotage, studio audio DSP, Voice Lab, accès web gouverné, monitoring GPU/VRAM, SOC.
- **Hermès — l'agent persistant** : cœur de l'agent, architecture (entrée → Hermès → LLM → réponse), croissance du cerveau (mémoire qui s'accumule).
- **Console de maintenance & reprise après sinistre** (menu terminal : statut, modèles, DSP, sauvegarde & restauration, API).
- **Documentation** — 6 pages : Hermès, intégration SOC, architecture globale, audio DSP, installation, MCP server.

### Caractéristiques présentées
- LLM 100 % local via Ollama : `qwen3:8b` (défaut) · `qwen3:14b` (think) · `qwen2.5-coder` (code) · `gemma4` (vision).
- Voix Edge Antoine → repli Kokoro neural local · STT faster-whisper `large-v3-turbo`.
- RAG hybride (~1150 chunks) · MCP 12 outils · auto-engine SOC.
- Accélération CUDA (RTX 5080) avec garde-fou anti-débordement VRAM.

### Sécurité
- Doctrine vitrine : aucune donnée actionnable publiée (IP, clés, configurations). La vitrine **décrit**, elle ne branche rien de live.

[1.0.0]: https://github.com/0xCyberLiTech/JARVIS/releases/tag/v1.0.0
