# Installation JARVIS

> Installation complète pas à pas sur Windows 11 + GPU NVIDIA (CUDA).

---

## Pré-requis

Voir [PRE-REQUIS.md](PRE-REQUIS.md) pour la liste complète.
Résumé : Windows 11 · Python 3.11 · NVIDIA GPU (CUDA 12) · Ollama installé.

---

## 1. Cloner / copier le dépôt

```bash
# Exemple Git (usage personnel)
git clone https://github.com/0xCyberLiTech/JARVIS.git
cd JARVIS
```

---

## 2. Environnement virtuel Python

```powershell
# Dans le dossier JARVIS/scripts/
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 3. Modèles Ollama

```bash
# Modèle SOC (défaut — toujours chaud)
ollama pull phi4:14b

# Modèle GÉNÉRAL + vision
ollama pull gemma4:latest

# Modèle CODE
ollama pull qwen2.5-coder:14b

# Modèle RAG (embeddings)
ollama pull mxbai-embed-large
```

> Les modèles occupent environ 29 GB de stockage au total.
> Le modèle RAG (`mxbai-embed-large`) doit être maintenu chaud (`keep_alive 10m`).

---

## 4. Configuration

### Fichiers de configuration

| Fichier | Rôle |
|---------|------|
| `scripts/jarvis_model.json` | Modèle Ollama actif |
| `scripts/jarvis_llm_params.json` | Paramètres LLM (temperature, num_ctx, num_predict) |
| `scripts/jarvis_dsp_params.json` | Paramètres DSP audio + moteur TTS |

### Valeurs par défaut importantes

```json
// jarvis_model.json
{"model": "phi4:14b"}

// jarvis_llm_params.json
{
  "temperature": 0.2,
  "num_ctx": 8192,
  "num_predict": -1
}
```

---

## 5. Lancement

```bat
start_dashboard.bat
```

Ce script :
1. Active l'environnement virtuel Python
2. Vérifie qu'Ollama tourne (le démarre si besoin)
3. Lance `jarvis.py` (Flask)
4. Ouvre `http://localhost:5000` dans le navigateur

**Arrêt propre** : `stop_jarvis.bat` (ou raccourci bureau `JARVIS - Arrêt`)

---

## 6. Vérification

Après lancement, vérifier dans l'interface :
- Synoptique Hermès : 6 briques en vert
- Modèle actif : `phi4:14b`
- RAG : status `ready`, chunks chargés
- STT : microphone disponible
- TTS : voix `fr-CA-AntoineNeural`

---

## 7. Tests (optionnel)

```powershell
cd scripts
python -m pytest ../tests/python/ -v
```

1 465 tests · 0 fail · 79 % coverage.

---

## 8. MCP Claude Desktop (optionnel)

Pour intégrer JARVIS dans Claude Code (VSCode), créer `.mcp.json` à la racine du workspace :

```json
{
  "mcpServers": {
    "jarvis": {
      "command": "pythonw",
      "args": ["chemin/absolu/vers/JARVIS/scripts/jarvis_mcp_server.py"],
      "env": {}
    }
  }
}
```

---

*INSTALLATION.md · 0xCyberLiTech · 2026-06-09*
