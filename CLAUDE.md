# CLAUDE.md — JARVIS

> Briefing concentré pour Claude quand on travaille dans le workspace `JARVIS/` seul.
> Le fichier racine `0xCyberLiTech/CLAUDE.md` couvre tout le workspace (JARVIS + SOC + PROXMOX + sites) — ce fichier-ci ne duplique pas, il **complète** pour le focus JARVIS.

---

## Identité

**JARVIS** = assistant IA local type Iron Man · Flask `localhost:5000` · Windows 11 (RTX 5080, 16 GB VRAM) · 100% local, zéro cloud LLM.

- Version : **v3.3** (interface holographique)
- Score dette honnête : **92/100** (audit dette complet 2026-05-17 soir · cf. `BILAN-TECHNIQUE.md`)
- Tests : **933 pytest pass + 3 skip** · coverage 51% · 22 modules à 100% cov
- Refactor JS : **terminé** (`jarvis_main.js` 148L · −98,1% depuis 7828L)

## Sources de vérité (ordre de priorité)

1. **`MEMORY.md`** (2355L) — historique complet par session · décisions · commits SHA
2. **`BILAN-TECHNIQUE.md`** — état technique structuré · chiffres · décomposition score
3. **`RUNBOOK.md`** — reconstruction DR · secrets · vérifs
4. **`docs/`** — 7 fichiers de référence :
   - `AUDIO-DSP.md` — Web Audio graph (4 BiquadFilter + 2 Comp + Convolver) · TTS chain · DeepFilterNet CUDA · Voice Lab
   - `MCP-SERVER.md` — 12 outils · config Claude Desktop · watchdog · port 5010
   - `REFERENCE-TECHNIQUE.md` — architecture globale
   - `ROUTING-JARVIS.md` — 4 modes · 9 bypass Python · sécurité (RFC1918, `_BLOCKED_SSH`, whitelists)
   - `DEPLOIEMENT.md` — setup prod
   - `REINSTALLATION.md` — recovery
   - `SUPPORT-INFOGERANCE.md` — SLA support

## Stack

| Composant | Détail |
|---|---|
| OS | Windows 11 Pro · station Marc |
| GPU | RTX 5080 Blackwell · 16 GB GDDR7 · CUDA 12 · PyTorch sm_120 |
| Python | 3.11 · venv ou global · `requirements.txt` |
| LLM local | Ollama `:11434` · **5 modèles** (phi4:14b SOC · gemma4 GÉNÉRAL · qwen2.5-coder CODE · qwen3:8b CR · mxbai-embed-large RAG) |
| TTS | edge-tts → Kokoro CUDA → Piper → SAPI5 · pré-warm au boot · profiling `tools/profile_tts.py` |
| STT | faster-whisper large-v3-turbo · CUDA · initial_prompt vocabulaire SOC |
| RAG | 599 chunks · mxbai-embed-large · seuil 0.35 · TTL 300s · auto-refresh 6h |
| MCP | streamable-HTTP port 5010 · **12 outils** · Claude Desktop / Cursor |
| Frontend | SPA vanilla JS · zéro NPM (sauf tests E2E) · 21 modules JS · 8 CSS · 10 templates HTML |
| Tests | pytest (801) · ruff · eslint · pre-commit hooks · **pre-push pytest** (CI locale, pas de cloud) |

## Lancement

```powershell
# Démarrage
cd JARVIS\scripts && python jarvis.py
# → http://localhost:5000

# Arrêt
JARVIS\stop_jarvis.bat
# OU raccourci bureau `JARVIS - Arrêt.lnk`

# MCP server (optionnel pour Claude Desktop)
cd JARVIS\scripts && python jarvis_mcp_server.py
# → écoute 127.0.0.1:5010
```

## 4 modes (règle absolue)

Cf. mémoire `jarvis_modes` — règle ABSOLUE pour Claude :

| Mode | Modèle | Quand l'utiliser | Auto-engine SOC |
|---|---|---|---|
| **SOC** (défaut) | phi4:14b | Cybersécurité · analyse threat · injection live monitoring.json | ✅ ACTIF |
| **GENERAL** | gemma4:latest | Conversation libre · vision multimodale | ❌ |
| **CODE** | qwen2.5-coder:14b | Code · infogérance srv-dev-1 | ❌ |
| **CR** | qwen3:8b | Code Reasoning étendu | ❌ |

**Auto-engine SOC actif UNIQUEMENT en mode soc** — ne JAMAIS l'activer dans les autres modes.

## Conventions

- **Chemins Windows absolus** : `C:\Users\mmsab\Documents\0xCyberLiTech\JARVIS\...`
- **Chemins Unix (Git Bash pour ssh/scp)** : `/c/Users/mmsab/...`
- **Clients internes** : `http://127.0.0.1:PORT` (PAS `localhost` — résout IPv6 sur Windows, +97% latence) — source unique `OLLAMA_URL` dans `jarvis.py:544`
- **Pre-commit hooks** : ruff + eslint bloquants
- **Pre-push hook** : pytest 936 tests (alternative locale à CI cloud — impossible « rien sur le web »)
- **Édition gros fichiers** : ⚠ Write tool tronque >200 Ko → toujours `Edit`, jamais `Write` pour `jarvis.py` (4739L) ou `jarvis_main.js`

## Règles ABSOLUES (zéro régression infra)

Cf. mémoires `feedback_jarvis_no_regression` · `feedback_data_security` · `feedback_llm_cost_architecture` :

1. **RFC1918 immuable** — adresses 10./172.16-31./192.168./127. JAMAIS recommandées au ban · JAMAIS traitées comme menace · sanitize MCP `[IP]`
2. **`_BLOCKED_SSH` 29 patterns** — whitelist SSH read-only, ne JAMAIS l'élargir sans validation explicite Marc
3. **`_ALLOWED_SERVICES`** — liste blanche services restartables, immuable sans validation
4. **Injection SOC = 100% serveur** — JAMAIS dans l'historique chat (sinon hallucinations multi-tours)
5. **Architecture coût LLM** — JARVIS filtre/agrège/détecte EN LOCAL · jamais raw data vers Claude cloud · escalade uniquement
6. **Auto-engine SOC** — UNIQUEMENT en mode soc · jamais ailleurs
7. **SSH read-only** — la levée write-ops (apt/restart) est la seule tâche roadmap ouverte, à NE PAS implémenter sans validation Marc

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `scripts/jarvis.py` (4633L) | Serveur Flask · ~150 endpoints · routing 4 modes · pré-warm · circuit breaker |
| `scripts/blueprints/soc.py` (1007 stmts) | Endpoints SOC · cache 30s + fallback SSH · `_SOC_BAN_CONFIG` source unique |
| `scripts/jarvis_mcp_server.py` (269 stmts) | MCP 12 outils · sanitize IP → `[IP]` · port 5010 |
| `scripts/chat_soc_inject.py` | Injection bloc compact phi4 mode SOC (100% serveur) |
| `scripts/ollama_circuit.py` | Circuit breaker state machine 3 états · 100% cov · 23 tests |
| `scripts/security_whitelists.py` | `_BLOCKED_SSH` 29 patterns · `_ALLOWED_SERVICES` |
| `scripts/static/jarvis_main.js` (148L) | Point d'entrée JS (post-refactor) |
| `scripts/static/js/` (18 modules) | Modules JS extraits (audio_viz, chat_core, settings_llm, boot_init, ...) |
| `scripts/jarvis_llm_params.json` | Params LLM (temp/num_ctx/num_predict) — gitignored |
| `scripts/jarvis_model.json` | Modèle actif Ollama — gitignored |
| `scripts/jarvis_dsp_params.json` | DSP audio + moteur TTS — gitignored |
| `scripts/jarvis_prompt_profiles.json` | Profils prompt par mode (règles ABSOLUES SOC) |

## Fichiers gitignored (à recréer en DR)

| Fichier | Contenu |
|---|---|
| `scripts/jarvis_secret.key` | Clé secrète Flask |
| `scripts/jarvis_pve.json` | Ticket+token API Proxmox |
| `scripts/soc_config.json` | Config SOC (endpoints, clés) |
| `scripts/jarvis_dsp_params.json` | DSP audio + moteur TTS |
| `scripts/jarvis_system_prompt.txt` | System prompt personnalisé |
| `scripts/jarvis_llm_params.json` | Params LLM runtime |
| `scripts/jarvis_rag/` | Index RAG (régénérable) |
| `*.log`, `*.log.*` | Runtime |

⚠ Ne JAMAIS committer ces fichiers · ne JAMAIS les indexer dans le RAG.

## Roadmap

**Seule tâche ouverte** : SSH write ops (levée partielle `apt upgrade` / `restart` après stabilisation routing). Tout le reste `[x]` validé — cf. CLAUDE.md racine section JARVIS roadmap.

## Workflow

```
édition locale → pre-commit (ruff + eslint) → git commit
              → pre-push (pytest 801) → git push (local, pas de remote)
              → redémarrer JARVIS (stop_jarvis.bat → python jarvis.py)
```

**Le redémarrage est requis pour** : `jarvis.py`, modules Python, `jarvis_prompt_profiles.json`, system prompt. Les `.json` de config sont relus au démarrage.

## Conventions commit

Style préfixé `type(scope):` cohérent avec SOC :
- `feat(jarvis)` · `fix(jarvis)` · `docs(jarvis)` · `chore(jarvis)` · `test(jarvis)` · `refactor(jarvis)`

---

*CLAUDE.md JARVIS · 2026-05-17 · complémentaire au racine `0xCyberLiTech/CLAUDE.md` · briefing concentré pour focus JARVIS*
