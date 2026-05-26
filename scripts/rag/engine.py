"""Moteur RAG hybride — embeddings vectoriels + BM25 + index live SOC.

Tuile `rag` — brique métier. Indexation MD5-déduplicated, recherche hybride
(60% cosine vec + 40% BM25 normalisé), cache mémoire TTL 5 min sur l'index
chargé ET sur l'objet BM25.

Dépendances injectées par `init()` — depuis l'ossature jarvis.py.
"""
import hashlib
import json
import time

import requests as req

# ── Caches mémoire (mutables — partagés via alias par l'ossature) ────────
_rag_mem_cache:  dict = {"meta": None, "emb": None, "ts": 0.0}
_bm25_obj_cache: dict = {"bm25": None, "meta_len": 0, "ts": 0.0}
_RAG_CACHE_TTL = 300.0  # 5 min — invalidé automatiquement après indexation

# ── Dépendances injectées par init() ─────────────────────────────────────
_ollama_circuit:      object = None
_ollama_url:          str = ""
_embed_model:         str = ""
_embed_timeout_s:     int = 60
_chunk_size:          int = 1000
_chunk_over:          int = 100
_top_n:               int = 5
_threshold:           float = 0.35
_rag_dir:             object = None
_rag_meta_file:       object = None
_rag_emb_file:        object = None
_live_mod:            object = None
_ssh_nginx:            object = None
_ssh_log_timeout_s:   int = 5
_log:                 object = None


def init(*, ollama_circuit, ollama_url, embed_model, embed_timeout_s,
         chunk_size, chunk_over, top_n, threshold,
         rag_dir, rag_meta_file, rag_emb_file,
         live_mod, ssh_nginx, ssh_log_timeout_s, log) -> None:
    global _ollama_circuit, _ollama_url, _embed_model, _embed_timeout_s
    global _chunk_size, _chunk_over, _top_n, _threshold
    global _rag_dir, _rag_meta_file, _rag_emb_file
    global _live_mod, _ssh_nginx, _ssh_log_timeout_s, _log
    _ollama_circuit    = ollama_circuit
    _ollama_url        = ollama_url
    _embed_model       = embed_model
    _embed_timeout_s   = embed_timeout_s
    _chunk_size        = chunk_size
    _chunk_over        = chunk_over
    _top_n             = top_n
    _threshold         = threshold
    _rag_dir           = rag_dir
    _rag_meta_file     = rag_meta_file
    _rag_emb_file      = rag_emb_file
    _live_mod          = live_mod
    _ssh_nginx          = ssh_nginx
    _ssh_log_timeout_s = ssh_log_timeout_s
    _log               = log


def _rag_embed(text: str) -> list | None:
    """Embedding via Ollama (mxbai-embed-large). Retourne None si indisponible."""
    try:
        r = _ollama_circuit.call(req.post, f"{_ollama_url}/api/embeddings",
                     json={"model": _embed_model, "prompt": text[:2000], "keep_alive": "10m"},
                     timeout=_embed_timeout_s)
        if r.ok:
            return r.json().get("embedding")
    except Exception as e:
        _log.warning(f"[RAG] Erreur embedding: {e}")
    return None


def _rag_chunk(text: str, source: str) -> list:
    """Découpe un texte en chunks avec overlap."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + _chunk_size, len(text))
        if end < len(text):
            last_nl = text.rfind('\n', start, end)
            if last_nl > start + _chunk_size // 2:
                end = last_nl + 1
        content = text[start:end].strip()
        if len(content) > 50:
            chunks.append({"source": source, "content": content})
        start = end - _chunk_over if end < len(text) else end
    return chunks


def _get_bm25_cached(meta: list):
    """Retourne l'objet BM25Okapi mis en cache (TTL = _RAG_CACHE_TTL)."""
    now = time.monotonic()
    if (_bm25_obj_cache["bm25"] is not None
            and _bm25_obj_cache["meta_len"] == len(meta)
            and (now - _bm25_obj_cache["ts"]) < _RAG_CACHE_TTL):
        return _bm25_obj_cache["bm25"]
    from rank_bm25 import BM25Okapi
    corpus = [m.get("text", m.get("content", "")).lower().split() for m in meta]
    bm25 = BM25Okapi(corpus)
    _bm25_obj_cache.update({"bm25": bm25, "meta_len": len(meta), "ts": now})
    return bm25


def _rag_load():
    """Retourne (meta_list, embeddings_ndarray_or_None). Cache mémoire TTL 5 min."""
    try:
        import numpy as np
        now = time.monotonic()
        if _rag_mem_cache["meta"] is not None and (now - _rag_mem_cache["ts"]) < _RAG_CACHE_TTL:
            return _rag_mem_cache["meta"], _rag_mem_cache["emb"]
        meta = json.loads(_rag_meta_file.read_text(encoding="utf-8")) if _rag_meta_file.exists() else []
        emb  = np.load(str(_rag_emb_file)).astype(np.float32) if _rag_emb_file.exists() else None
        _rag_mem_cache["meta"] = meta
        _rag_mem_cache["emb"]  = emb
        _rag_mem_cache["ts"]   = now
        return meta, emb
    except Exception as e:
        _log.warning(f"[RAG] Erreur chargement index: {e}")
        return [], None


def _rag_save(meta: list, emb_list: list) -> bool:
    try:
        import numpy as np
        _rag_dir.mkdir(exist_ok=True)
        _rag_meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        np.save(str(_rag_emb_file), np.array(emb_list, dtype=np.float32))
        _rag_mem_cache["ts"] = 0.0  # invalide le cache → prochain _rag_load recharge depuis disque
        return True
    except Exception as e:
        _log.error(f"[RAG] Erreur sauvegarde index: {e}")
        return False


def _rag_index_text(text: str, source: str) -> int:
    """Indexe un texte : chunk → embed → ajout à l'index. Retourne le nb de chunks ajoutés."""
    chunks = _rag_chunk(text, source)
    if not chunks:
        return 0
    meta, embs = _rag_load()
    embs_list  = embs.tolist() if embs is not None else []
    existing   = {m.get("id") for m in meta}
    added = 0
    for chunk in chunks:
        cid = hashlib.md5(chunk["content"].encode()).hexdigest()[:12]
        if cid in existing:
            continue
        vec = _rag_embed(chunk["content"])
        if vec:
            meta.append({"id": cid, "source": source, "content": chunk["content"]})
            embs_list.append(vec)
            existing.add(cid)
            added += 1
    if added:
        _rag_save(meta, embs_list)
    _log.info(f"[RAG] Indexé '{source}' → {added} chunks ajoutés ({len(meta)} total)")
    return added


def _rag_live_refresh():
    """Wrapper — injecte _ssh_nginx puis délègue."""
    _live_mod.refresh(_ssh_nginx, timeout=_ssh_log_timeout_s)


def _rag_live_prewarm():
    """Wrapper — injecte _ssh_nginx puis délègue."""
    _live_mod.prewarm(_ssh_nginx, timeout=_ssh_log_timeout_s)


def _rag_query(query: str) -> list:
    """Recherche hybride BM25 + vecteur. Retourne les top-N chunks pertinents."""
    try:
        import numpy as np
        meta, embs = _rag_load()
        if embs is None or len(meta) == 0:
            return []

        # ── Score vectoriel (cosine) ───────────────────────────────────────
        q_vec = _rag_embed(query)
        if q_vec:
            q = np.array(q_vec, dtype=np.float32)
            q /= (np.linalg.norm(q) + 1e-9)
            E = embs / (np.linalg.norm(embs, axis=1, keepdims=True) + 1e-9)
            vec_scores = E @ q                 # shape (N,)
        else:
            vec_scores = np.zeros(len(meta), dtype=np.float32)

        # ── Score BM25 (term matching) — objet mis en cache ──────────────────
        try:
            bm25 = _get_bm25_cached(meta)
            raw_bm25  = bm25.get_scores(query.lower().split())
            bm25_max  = raw_bm25.max() + 1e-9
            bm25_scores = raw_bm25 / bm25_max
        except Exception:
            bm25_scores = np.zeros(len(meta), dtype=np.float32)

        # ── Score hybride 60% vector + 40% BM25 ───────────────────────────
        hybrid = 0.6 * vec_scores + 0.4 * bm25_scores
        top_idx = np.argsort(hybrid)[::-1][:_top_n]
        return [
            {**meta[i], "score": float(hybrid[i])}
            for i in top_idx if hybrid[i] >= _threshold
        ]
    except Exception as e:
        _log.warning(f"[RAG] Erreur requête: {e}")
        return []


def _rag_inject(system: str, query: str) -> str:
    """Injecte les chunks pertinents (statiques + live SOC) dans le system prompt."""
    if not query or len(query.strip()) < 10:
        return system
    # RAG statique (documents indexés)
    results = _rag_query(query)
    # RAG live SOC — injection directe du texte brut (sans embedding = sans latence)
    if _live_mod.should_inject(query):
        # Refresh async si TTL expiré — on sert toujours le cache existant sans attendre
        _live_mod.trigger_async_refresh(_ssh_nginx, timeout=_ssh_log_timeout_s)
        live_txt = _live_mod.get_text()
        if live_txt:
            system = system + f"\n\n[LOGS TEMPS RÉEL — srv-nginx]\n{live_txt}\n"
    if not results:
        return system
    block = "\n\n[CONTEXTE DOCUMENTAIRE — sources indexées localement]\n"
    for r in results:
        block += f"\n— {r['source']} (score {r['score']:.2f})\n{r['content']}\n"
    return system + block
