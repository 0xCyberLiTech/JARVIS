# RUNBOOK — JARVIS (Assistant IA local)

> Procédure de reconstruction / disaster recovery du projet JARVIS.
> Dernière mise à jour : 2026-05-14.
> Dépôt git local : `JARVIS/` (100 % local, aucun remote). `MEMORY.md` = source de vérité de l'état.

---

## 1. Identité

Assistant IA personnel (type Iron Man) — serveur Flask **localhost:5000**, tourne sur la **station Windows 11** (RTX 5080).

| Élément | Emplacement |
|---|---|
| Serveur Flask | `JARVIS/scripts/jarvis.py` (~4633 L + 31 modules Python) |
| Blueprint SOC | `JARVIS/scripts/blueprints/soc.py` |
| Serveur MCP | `JARVIS/scripts/jarvis_mcp_server.py` (port 5010, streamable-HTTP) |
| UI | `JARVIS/scripts/templates/` + `JARVIS/scripts/static/` (`jarvis_main.js` 148 L + 21 modules JS dont 18 dans `static/js/` + 8 CSS) |
| Lancement | `cd JARVIS\scripts && python jarvis.py` → http://localhost:5000 |
| Arrêt | `JARVIS\stop_jarvis.bat` ou raccourci bureau `JARVIS - Arrêt.lnk` |

---

## 2. Dépendances

- **Python 3.11** + `requirements.txt` (Flask, faster-whisper, edge-tts, torch+cu128, etc.).
- **Ollama** (`:11434`) avec les modèles : `phi4:14b` (SOC), `gemma4:latest` (GÉNÉRAL/VOCAL/vision), `qwen2.5-coder:14b` (CODE), `qwen3:8b` (CODE REASONING), `mxbai-embed-large` (RAG).
- **GPU** RTX 5080 / CUDA 12 — PyTorch sm_120 (STT faster-whisper, Kokoro/XTTS TTS, DeepFilterNet).
- **Clés SSH** (`~/.ssh/`) : `id_nginx`, `id_clt`, `id_pa85`, `id_proxmox`, `id_dev` — pour les bypass infra/SSH.
- **node_modules** (`npm install`) — uniquement pour les tests E2E Playwright.
- Réseau : accès à srv-ngix `:8080` (monitoring.json) ; le SOC fonctionne sans JARVIS, l'inverse n'est pas vrai.

---

## 3. Secrets / fichiers NON versionnés (à recréer en DR)

`JARVIS/.gitignore` exclut — **à recréer manuellement, jamais commités** :

| Fichier | Contenu |
|---|---|
| `scripts/jarvis_secret.key` | clé secrète Flask |
| `scripts/jarvis_pve.json` | ticket/token API Proxmox |
| `scripts/soc_config.json` | config SOC (endpoints, clés) |
| `scripts/jarvis_dsp_params.json` | params DSP audio + moteur TTS |
| `scripts/jarvis_system_prompt.txt` | system prompt personnalisé |
| `scripts/jarvis_llm_params.json` | params LLM (muté au runtime — `num_ctx` adaptatif) |
| `scripts/jarvis_rag/` | index RAG (régénérable) |
| logs (`*.log`, `*.log.*`) | runtime |

> ⚠ Ne JAMAIS committer ces fichiers. Ne JAMAIS les indexer dans le RAG.

---

## 4. Reconstruction from scratch

1. **Cloner le dépôt** → `C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\`.
2. **Python** : `python -m venv` (ou global 3.11) + `pip install -r requirements.txt`.
3. **Ollama** : installer Ollama + `ollama pull phi4:14b gemma4:latest qwen2.5-coder:14b qwen3:8b mxbai-embed-large`.
4. **Recréer les secrets** du §3 (coffre / régénération).
5. **Clés SSH** : restaurer `~/.ssh/id_*` (backup `C:\Users\mmsab\Documents\CLES_SSH_0xcyberlitech\`).
6. **node_modules** (tests seulement) : `cd JARVIS && npm install`.
7. **Lancer** : `cd JARVIS\scripts && python jarvis.py` → http://localhost:5000.
8. (Optionnel) MCP : `python jarvis_mcp_server.py` — config Claude Desktop pointant `:5010`.
9. Raccourcis bureau : recréer `JARVIS - Arrêt.lnk` et `JARVIS Dashboard.lnk` si besoin.

---

## 5. Déploiement (mise à jour courante)

Projet **local** — pas de déploiement distant.
```
git pull (n/a — repo local)  →  éditer  →  pre-commit (ruff+eslint)  →  git commit
→ redémarrer JARVIS (stop_jarvis.bat puis python jarvis.py)
```
Le redémarrage est requis pour : `jarvis.py`, les modules Python, `jarvis_prompt_profiles.json`, le system prompt. Les `.json` de config sont relus au démarrage.

---

## 6. Vérification

- http://localhost:5000 charge l'UI ; les 4 modes (SOC/GENERAL/CODE/CR) basculent.
- `GET /api/mode` répond ; tuile SOC affiche les données monitoring.
- Ollama : `ollama ps` montre le modèle chargé en VRAM.
- Tests : `cd JARVIS && npm test` (JARVIS doit être up) → 25 E2E.
- Hooks : `pre-commit run --all-files` → ruff + eslint Passed.

---

## 7. Points de vigilance

- ⚠ **Write tool tronque les gros fichiers (>200 Ko)** — toujours éditer `jarvis.py` / `jarvis_main.js` par Edit, jamais Write.
- ⚠ **Zéro régression infra** : `RFC1918` immuable, `_BLOCKED_SSH` et `_ALLOWED_*` whitelists immuables sans validation explicite (cf. `feedback_jarvis_no_regression`).
- ⚠ **Architecture coût LLM** : JARVIS filtre/agrège/détecte en local ; jamais de raw data vers un LLM cloud.
- ⚠ Les 4 modes : SOC = cybersécurité (défaut), GENERAL = conversation, CODE = code+infogérance (srv-dev-1 uniquement), CR = code+reasoning. Auto-engine SOC actif **uniquement en mode SOC**.
- ⚠ Injection contexte SOC = **100 % serveur** (system prompt, jamais l'historique) — ne pas réintroduire d'incrustation client-side.
- ⚠ **Clients internes = 127.0.0.1, pas localhost** : `OLLAMA_URL`, `JARVIS_BASE` (MCP) et tout client interne JARVIS doivent utiliser `http://127.0.0.1:PORT` explicite. `localhost` résout `::1` (IPv6) en premier sur Windows et Flask n'écoute pas IPv6 → timeout ~2s par requête. Source unique : `OLLAMA_URL` dans `jarvis.py:544`. Outil de profiling : `tools/profile_perf.py`.
- ⚠ **Tests Python** : `python -m pytest` (682 tests sur 32/34 modules · coverage 39% lignes via `pytest --cov=scripts` · pyproject.toml `[tool.pytest.ini_options]` · `tests/python/conftest.py` ajoute `scripts/` au sys.path). Doit être vert avant tout commit Python ET avant tout push (hook pre-push installé).
- ⚠ **Hook pre-push pytest** : `pre-commit install --hook-type pre-push` lance les 682 tests avant chaque `git push`. Bloque sur tests rouges. Alternative locale à CI cloud (impossible « rien sur le web »). Bypass : `git push --no-verify` (à éviter — c'est précisément contre ça).
- `JARVIS/MEMORY.md` est tracké (≠ SOC où il est gitignored).
