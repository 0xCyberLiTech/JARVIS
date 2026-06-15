<div align="center">

  <br></br>

  <a href="https://github.com/0xCyberLiTech">
    <img src="https://readme-typing-svg.herokuapp.com?font=JetBrains+Mono&size=50&duration=6000&pause=1000000000&color=8B5CF6&center=true&vCenter=true&width=1100&lines=%3EJARVIS_" alt="Titre dynamique JARVIS" />
  </a>

  <br></br>

  <h2>Assistant IA local · voix · interface holographique · automatisation SOC 24/7</h2>

  <p align="center">
    <a href="https://0xcyberlitech.github.io/">
      <img src="https://img.shields.io/badge/Portfolio-0xCyberLiTech-181717?logo=github&style=flat-square" alt="Portfolio" />
    </a>
    <a href="https://github.com/0xCyberLiTech">
      <img src="https://img.shields.io/badge/Profil-GitHub-181717?logo=github&style=flat-square" alt="Profil GitHub" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/releases/latest">
      <img src="https://img.shields.io/github/v/release/0xCyberLiTech/JARVIS?label=version&style=flat-square&color=blue" alt="Dernière version" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/blob/main/CHANGELOG.md">
      <img src="https://img.shields.io/badge/%F0%9F%93%84%20Changelog-JARVIS-blue?style=flat-square" alt="Changelog" />
    </a>
    <a href="https://github.com/0xCyberLiTech?tab=repositories">
      <img src="https://img.shields.io/badge/D%C3%A9p%C3%B4ts-publics-blue?style=flat-square" alt="Dépôts publics" />
    </a>
    <a href="https://github.com/0xCyberLiTech/JARVIS/graphs/contributors">
      <img src="https://img.shields.io/badge/%F0%9F%91%A5%20Contributeurs-cliquez%20ici-007ec6?style=flat-square" alt="Contributeurs" />
    </a>
  </p>

</div>

<div align="center">
  <img src="https://img.icons8.com/fluency/96/000000/cyber-security.png" alt="CyberSec" width="80"/>
</div>

<div align="center">
  <p>
    <strong>IA 100% locale</strong> <img src="https://img.icons8.com/color/24/000000/lock--v1.png"/> &nbsp;•&nbsp; <strong>Voix naturelle · STT · TTS</strong> <img src="https://img.icons8.com/color/24/000000/linux.png"/> &nbsp;•&nbsp; <strong>Automatisation SOC</strong> <img src="https://img.icons8.com/color/24/000000/shield-security.png"/>
  </p>
</div>

---
# Installation

## Pré-requis matériel

| Composant | Minimum | Recommandé |
|-----------|---------|-----------|
| **GPU** | NVIDIA 8 GB VRAM | NVIDIA 16 GB VRAM (RTX série) |
| **RAM** | 16 GB | 32 GB DDR5 |
| **Stockage** | 50 GB SSD | NVMe — modèles Ollama ~29 GB |
| **OS** | Windows 11 | Windows 11 Pro |

> Avec 8 GB VRAM, le modèle par défaut qwen3:8b (~5.6 GB) + mxbai-embed (0.7 GB) tient sans swap.
> Pour les modèles 14B (qwen3:14b THINK · qwen2.5-coder CODE · gemma4 VISION, ~9 GB chacun), prévoir **12 GB+ de VRAM**.

---

## Logiciels requis

| Logiciel | Version | Notes |
|----------|---------|-------|
| **Python** | 3.11.x | Strictement — certains paquets CUDA incompatibles 3.12 |
| **Ollama** | Dernière stable | https://ollama.com |
| **Pilotes NVIDIA** | 570+ | CUDA 12 requis |
| **PyTorch** | 2.7.1+cu128 | Inclus dans requirements.txt |

---

## Étape 1 — Environnement Python

```powershell
# Dans le dossier scripts/
python -m venv .venv
.venv\Scriptsctivate
pip install -r requirements.txt
```

---

## Étape 2 — Modèles Ollama

```bash
# Modèle SOC + GÉNÉRAL + Code-Reasoning (défaut — toujours chaud)
ollama pull qwen3:8b

# Modèle THINK (raisonnement profond)
ollama pull qwen3:14b

# Modèle CODE
ollama pull qwen2.5-coder:14b

# Modèle VISION (multimodal)
ollama pull gemma4:latest

# Modèle RAG (embeddings)
ollama pull mxbai-embed-large
```

> Les modèles occupent environ **29 GB** au total.

---

## Étape 3 — Vérification CUDA

```python
import torch
print("CUDA :", torch.cuda.is_available())
print("GPU  :", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")
```

---

## Étape 4 — Lancement

```bat
start_dashboard.bat
```

Ce script : active le venv · vérifie Ollama · lance Flask · ouvre localhost:5000.

**Arrêt propre** : `stop_jarvis.bat`

---

## Étape 5 — Vérification post-démarrage

Dans l'interface, vérifier :
- Synoptique Hermès : 6 briques vertes
- Modèle actif : `qwen3:8b`
- RAG : `ready` · chunks chargés
- TTS : `edge-tts` · voix `fr-CA-AntoineNeural`
- STT : microphone disponible

---

## Étape 6 — Tests (optionnel)

```powershell
cd scripts
python -m pytest ../tests/python/ -v
# → 1 465 tests · 0 fail · 79 % coverage
```

---

## MCP Claude Desktop (optionnel)

Pour intégrer JARVIS dans Claude Code (VSCode), créer `.mcp.json` à la racine du workspace :

```json
{
  "mcpServers": {
    "jarvis": {
      "command": "pythonw",
      "args": ["chemin/absolu/vers/scripts/jarvis_mcp_server.py"],
      "env": {}
    }
  }
}
```

`pythonw` supprime la fenêtre console Windows — requis pour les pipes stdio MCP.

---

## Dépannage rapide

| Symptôme | Vérification | Solution |
|----------|-------------|---------|
| TTS silencieux | `/api/status` → `tts_engine` | Forcer edge-tts dans les réglages |
| Ollama indisponible | HUD `● OLLAMA` rouge | `ollama serve` dans un terminal |
| RAG `stale` | `/api/rag/status` | `POST /api/rag/refresh` |
| STT inactif | Permissions micro Windows | Paramètres → Confidentialité → Microphone |

---

**Précédent ←** [04 — Audio DSP](04-AUDIO-DSP.md) &nbsp;&nbsp; **Suivant →** [06 — MCP Server](06-MCP-SERVER.md)

---

<div align="center">

<table>
<tr>
<td align="center"><b>🖥️ Infrastructure &amp; Sécurité</b></td>
<td align="center"><b>💻 Développement &amp; Web</b></td>
<td align="center"><b>🤖 Intelligence Artificielle</b></td>
</tr>
<tr>
<td align="center">
  <a href="https://www.kernel.org/"><img src="https://skillicons.dev/icons?i=linux" width="48" title="Linux" /></a>
  <a href="https://www.debian.org"><img src="https://skillicons.dev/icons?i=debian" width="48" title="Debian" /></a>
  <a href="https://www.gnu.org/software/bash/"><img src="https://skillicons.dev/icons?i=bash" width="48" title="Bash" /></a>
  <br/>
  <a href="https://nginx.org"><img src="https://skillicons.dev/icons?i=nginx" width="48" title="Nginx" /></a>
  <a href="https://git-scm.com"><img src="https://skillicons.dev/icons?i=git" width="48" title="Git" /></a>
</td>
<td align="center">
  <a href="https://www.python.org"><img src="https://skillicons.dev/icons?i=python" width="48" title="Python" /></a>
  <a href="https://flask.palletsprojects.com"><img src="https://skillicons.dev/icons?i=flask" width="48" title="Flask" /></a>
  <a href="https://developer.mozilla.org/docs/Web/HTML"><img src="https://skillicons.dev/icons?i=html" width="48" title="HTML5" /></a>
  <br/>
  <a href="https://developer.mozilla.org/docs/Web/CSS"><img src="https://skillicons.dev/icons?i=css" width="48" title="CSS3" /></a>
  <a href="https://developer.mozilla.org/docs/Web/JavaScript"><img src="https://skillicons.dev/icons?i=js" width="48" title="JavaScript" /></a>
  <a href="https://code.visualstudio.com"><img src="https://skillicons.dev/icons?i=vscode" width="48" title="VS Code" /></a>
</td>
<td align="center">
  <a href="https://ollama.com"><img src="https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white" alt="Ollama" /></a>
  <br/><br/>
  <a href="https://anthropic.com"><img src="https://img.shields.io/badge/Anthropic-D97757?style=for-the-badge&logo=anthropic&logoColor=white" alt="Anthropic" /></a>
</td>
</tr>
</table>

<br/>

<sub>🔒 Projets proposés par <a href="https://github.com/0xCyberLiTech">0xCyberLiTech</a> · Développés en collaboration avec <a href="https://claude.ai">Claude AI</a> (Anthropic) 🔒</sub>

</div>
