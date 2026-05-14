"""Code Reasoning — pipeline qwen3:8b single-pass avec thinking masqué côté serveur.

Extrait de jarvis.py session 33 (2026-05-13) — Phase 3 sous-module 22 (Chat/LLM core).

Mode CODE REASONING (CR) : qwen3:8b génère un raisonnement <think>...</think>
puis la réponse finale. Le serveur masque le thinking au client (UI montre juste
"⏳ Raisonnement en cours…" pendant que le LLM réfléchit, puis affiche la réponse).

Architecture asynchrone :
1. `code_reasoning_gen()` lance un thread daemon + retourne immédiatement le task_id en SSE
2. `_run_task()` (thread) appelle Ollama en streaming, parse `<think>...</think>` à la volée,
   met à jour `tasks[task_id]['text']` au fur et à mesure
3. Le client poll `/api/cr-poll/<task_id>` (route Flask reste dans jarvis.py)

Dependency injection : `ensure_vram_fn`, `model`, `system_suffix`, `ollama_url`,
`llm_params` passés en arguments. State `tasks` exposé pour la route poll.
"""
import json
import logging
import re
import threading
import uuid

import requests

_log = logging.getLogger("jarvis.code_reasoning")

# ── Constantes ────────────────────────────────────────────────
TASKS_MAX = 15           # nettoyage auto des vieilles tâches terminées
NUM_CTX = 32768          # qwen3:8b supporte 32K — nécessaire pour les gros fichiers
DEFAULT_NUM_PREDICT = 4096
DEFAULT_TEMPERATURE = 0.1
OLLAMA_TIMEOUT_S = 600   # 10 min — gros fichiers + reasoning long

# Limite anti-explosion contexte pour les fichiers auto-injectés
FILE_CHAR_LIMIT = 80_000  # ~20K tokens

# Regex pour détecter les chemins de fichiers dans la requête utilisateur
# Format Windows (C:\path\file.ext) OU Unix (/path/file.ext)
_FILEPATH_RE = re.compile(
    r'[A-Za-z]:\\[^\s,;\'"]+\.[A-Za-z0-9]{1,10}|(?<!\w)/[^\s,;\'"]+\.[A-Za-z0-9]{1,10}'
)

# ── State (module-level) ──────────────────────────────────────
tasks: dict = {}  # task_id → {"status": "running"|"done"|"error", "text": str}


# ── Helpers ───────────────────────────────────────────────────

def _sse_tok(t: str, done: bool = False) -> str:
    """Helper SSE token (dupliqué pour autonomie du module)."""
    return f"data: {json.dumps({'type':'token','token':t,'done':done})}\n\n"


def _expand_user_files(user_content: str) -> str:
    """Auto-injecte le contenu des fichiers locaux mentionnés dans la requête.
    Tronque à FILE_CHAR_LIMIT chars pour rester sous la limite contexte 32K."""
    import os
    for fp in _FILEPATH_RE.findall(user_content):
        if os.path.isfile(fp):
            try:
                with open(fp, encoding="utf-8", errors="replace") as f:
                    raw = f.read()
                if len(raw) > FILE_CHAR_LIMIT:
                    raw = raw[:FILE_CHAR_LIMIT]
                    user_content += (
                        f"\n\n=== {fp} (tronqué à {FILE_CHAR_LIMIT//1000}K chars) ===\n{raw}\n\n"
                        f"⚠ Fichier tronqué — analysez par sections pour un audit complet."
                    )
                else:
                    user_content += f"\n\n=== {fp} ===\n{raw}"
            except Exception:
                pass  # fichier binaire ou accès refusé — on l'ignore silencieusement
    return user_content


def _cleanup_old_tasks():
    """Supprime les vieilles tâches terminées (garde les TASKS_MAX dernières)."""
    done_ids = [k for k, v in tasks.items() if v.get("status") in ("done", "error")]
    for old in done_ids[:-TASKS_MAX]:
        tasks.pop(old, None)


def _run_task(
    task_id: str,
    user_content: str,
    messages: list,
    np_override,
    *,
    ensure_vram_fn,
    model: str,
    system_suffix: str,
    ollama_url: str,
    llm_params: dict,
):
    """Pipeline C·R single-pass : qwen3:8b streaming (thinking masqué).
    Résultat sondable via /api/cr-poll/<task_id>."""
    task = tasks[task_id]
    num_predict = int(np_override) if np_override else llm_params.get("num_predict", DEFAULT_NUM_PREDICT)
    ensure_vram_fn(model)
    task["text"] = "*⏳ Chargement qwen3:8b…*\n\n"
    try:
        msgs = list(messages)
        msgs[-1] = dict(msgs[-1])
        msgs[-1]["content"] = user_content + system_suffix
        r = requests.post(
            f"{ollama_url}/api/chat",
            json={
                "model": model,
                "messages": msgs,
                "stream": True,
                "think": True,
                "options": {
                    "temperature": DEFAULT_TEMPERATURE,
                    "num_ctx": NUM_CTX,
                    "num_predict": num_predict,
                },
            },
            stream=True,
            timeout=OLLAMA_TIMEOUT_S,
        )
        full = ""
        for line in r.iter_lines():
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("done"):
                break
            tok = d.get("message", {}).get("content", "")
            if not tok:
                continue
            full += tok
            in_think = bool(re.search(r"<think>(?!.*</think>)", full, re.DOTALL))
            if in_think:
                task["text"] = "*🔄 Raisonnement en cours…*\n\n"
            else:
                task["text"] = re.sub(r"<think>.*?</think>", "", full, flags=re.DOTALL).strip()
        task["text"] = re.sub(r"<think>.*?</think>", "", full, flags=re.DOTALL).strip() or full
        task["status"] = "done"
        _log.info(f"[CR:{task_id}] Terminé — {len(task['text'])} chars")
    except Exception as e:
        _log.warning(f"[CR:{task_id}] {e}")
        task["status"] = "error"
        task["text"] += f"\n\n⚠ Erreur : {e}"


# ── API publique ──────────────────────────────────────────────

def code_reasoning_gen(
    messages,
    np_override,
    *,
    ensure_vram_fn,
    model: str,
    system_suffix: str,
    ollama_url: str,
    llm_params: dict,
):
    """Démarre le pipeline C·R en background et retourne immédiatement le task_id.

    Yields : 2 events SSE (cr_task avec task_id, puis token done=True).
    Le client poll ensuite `/api/cr-poll/<task_id>` pour récupérer le résultat.
    """
    _cleanup_old_tasks()
    user_content = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    user_content = _expand_user_files(user_content)
    task_id = uuid.uuid4().hex
    tasks[task_id] = {"status": "running", "text": "⚙ **[CODE REASONING]** Démarrage qwen3:8b…\n"}
    threading.Thread(
        target=_run_task,
        args=(task_id, user_content, messages, np_override),
        kwargs={
            "ensure_vram_fn": ensure_vram_fn,
            "model": model,
            "system_suffix": system_suffix,
            "ollama_url": ollama_url,
            "llm_params": llm_params,
        },
        daemon=True,
    ).start()
    yield f"data: {json.dumps({'type': 'cr_task', 'task_id': task_id})}\n\n"
    yield _sse_tok("", done=True)
