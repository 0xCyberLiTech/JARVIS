"""Persistance de l'historique conversationnel + résumés long terme.

Extrait de jarvis.py le 2026-05-23 (refactor incrémental jarvis.py étape 2).

Cluster cohérent « mémoire conversationnelle » :
- `load_memory` / `save_memory` : persistance jarvis_memory.json + déclenchement
  du résumé background quand l'historique dépasse `MEMORY_LIMIT`.
- `_summarize_messages` : appel Ollama (modèle courant) pour résumer un lot.
- `_background_summarize` : thread wrapper qui synthétise puis persiste.
- `_append_memory_summary` / `_load_memory_summary` : rotation à 5 résumés,
  lecture des 3 plus récents pour injection dans le prompt système.

Dépendances injectées par `init()` :
- 4 accesseurs (lambdas) pour les valeurs réassignées au runtime OU
  monkeypatchées par les tests : `memory_file`, `summary_file`, `model`,
  `mode`.
- Constantes : `memory_limit`, `summary_keep`, `summary_min_msgs`,
  `general_model`, `code_model`, `ollama_url`, `ollama_circuit`, `log`.
"""
import datetime
import json
import threading

import requests as req

# Accesseurs injectés (lambdas) — résolus à l'appel pour suivre les
# réaffectations runtime (MODEL, _jarvis_mode) et les monkeypatch de test
# (MEMORY_FILE, SUMMARY_FILE).
_get_memory_file:  object = None
_get_summary_file: object = None
_get_model:        object = None
_get_mode:         object = None

# Constantes et services injectés (valeurs stables).
_memory_limit:     int = 60
_summary_keep:     int = 5
_summary_min_msgs: int = 5
_general_model:    str = ""
_code_model:       str = ""
_ollama_url:       str = ""
_ollama_circuit:   object = None
_log:              object = None


def init(*, get_memory_file, get_summary_file, get_model, get_mode,
         memory_limit, summary_keep, summary_min_msgs,
         general_model, code_model, ollama_url, ollama_circuit, log) -> None:
    """Injecte accesseurs + constantes + services depuis jarvis.py."""
    global _get_memory_file, _get_summary_file, _get_model, _get_mode
    global _memory_limit, _summary_keep, _summary_min_msgs
    global _general_model, _code_model, _ollama_url, _ollama_circuit, _log
    _get_memory_file  = get_memory_file
    _get_summary_file = get_summary_file
    _get_model        = get_model
    _get_mode         = get_mode
    _memory_limit     = memory_limit
    _summary_keep     = summary_keep
    _summary_min_msgs = summary_min_msgs
    _general_model    = general_model
    _code_model       = code_model
    _ollama_url       = ollama_url
    _ollama_circuit   = ollama_circuit
    _log              = log


def load_memory():
    try:
        f = _get_memory_file()
        if f.exists():
            return json.loads(f.read_text(encoding="utf-8"))
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING load_memory: {e}")
    return []


def save_memory(history):
    try:
        clean = [m for m in history if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
        to_summarize = []
        if len(clean) > _memory_limit:
            to_summarize = clean[:-_memory_limit]
            clean = clean[-_memory_limit:]
        _get_memory_file().write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
        if len(to_summarize) >= _summary_min_msgs:
            threading.Thread(target=_background_summarize, args=(to_summarize,), daemon=True).start()
    except Exception as e:
        _log.error(f"[MEMORY] Erreur sauvegarde: {e}")


def _summarize_messages(messages: list) -> str:
    """Appelle Ollama pour résumer un lot de messages en points clés."""
    lines = []
    for m in messages:
        role = "Marc" if m["role"] == "user" else "JARVIS"
        lines.append(f"{role}: {m['content'][:400]}")
    prompt = (
        "Résume en 5 à 8 points clés (format: • fait) les informations importantes "
        "de cet historique. Sois concis, factuel, pas de markdown superflu.\n\n"
        + "\n".join(lines)
    )
    try:
        model_active = _get_model()
        _mode_model = {"soc": model_active, "general": _general_model, "code": _code_model}.get(_get_mode(), model_active)
        r = _ollama_circuit.call(req.post, f"{_ollama_url}/api/generate", json={
            "model": _mode_model,
            "prompt": prompt,
            "keep_alive": 0,
            "options": {"num_predict": 350, "num_ctx": 2048, "temperature": 0.3},
            "stream": False
        }, timeout=80)
        if r.ok:
            return r.json().get("response", "").strip()
    except Exception as e:
        _log.warning(f"[SUMMARY] Erreur résumé mémoire: {e}")
    return ""


def _append_memory_summary(new_summary: str):
    try:
        f = _get_summary_file()
        data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
        summaries = data.get("summaries", [])
        summaries.append({"date": datetime.date.today().isoformat(), "content": new_summary})
        if len(summaries) > _summary_keep:
            summaries = summaries[-_summary_keep:]
        f.write_text(json.dumps({"summaries": summaries}, ensure_ascii=False, indent=2), encoding="utf-8")
        _log.info(f"[SUMMARY] Résumé sauvegardé ({len(new_summary)} chars)")
    except Exception as e:
        _log.error(f"[SUMMARY] Erreur sauvegarde: {e}")


def _load_memory_summary() -> str:
    try:
        f = _get_summary_file()
        if f.exists():
            data = json.loads(f.read_text(encoding="utf-8"))
            summaries = data.get("summaries", [])
            if summaries:
                parts = [f"[{s.get('date','?')}]\n{s['content']}" for s in summaries[-3:]]
                return "\n\n---\n".join(parts)
    except Exception:
        pass  # fichier absent ou malformé — retourne chaîne vide
    return ""


def _background_summarize(messages: list):
    summary = _summarize_messages(messages)
    if summary:
        _append_memory_summary(summary)
