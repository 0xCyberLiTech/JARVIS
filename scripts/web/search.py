"""Recherche web — DuckDuckGo Instant Answer + Wikipedia FR fallback.

Tuile `web` — utilisé par le chat orchestrator (chat.system_prompt.build
quand web_enabled=True) et exposé via /api/web-test pour vérifier la
connectivité.
"""
import requests as req

_WEB_HEADERS = {
    "User-Agent": "JARVIS/3.0 (personal-assistant; fr)",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

_log = None
_web_search_timeout_s = 10
_web_fetch_timeout_s = 8
_web_conn_timeout_s = 5
_web_fetch2_timeout_s = 6


def init(*, log, web_search_timeout_s=10, web_fetch_timeout_s=8,
         web_conn_timeout_s=5, web_fetch2_timeout_s=6) -> None:
    global _log, _web_search_timeout_s, _web_fetch_timeout_s
    global _web_conn_timeout_s, _web_fetch2_timeout_s
    _log = log
    _web_search_timeout_s = web_search_timeout_s
    _web_fetch_timeout_s = web_fetch_timeout_s
    _web_conn_timeout_s = web_conn_timeout_s
    _web_fetch2_timeout_s = web_fetch2_timeout_s


def search_ddg(query: str, max_results: int) -> list:
    """DuckDuckGo Instant Answer API — pas de scraping HTML."""
    try:
        r = req.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_redirect": "1",
                    "no_html": "1", "skip_disambig": "1", "kl": "fr-fr"},
            headers=_WEB_HEADERS, timeout=_web_search_timeout_s
        )
        d = r.json()
        results = []
        abstract = (d.get("AbstractText") or d.get("Abstract") or "").strip()
        if abstract:
            results.append(f"[{d.get('AbstractSource','DDG')}] {abstract[:400]}")
        answer = d.get("Answer", "").strip()
        if answer and answer not in abstract:
            results.append(f"[Réponse directe] {answer}")
        definition = d.get("Definition", "").strip()
        if definition and definition not in abstract:
            results.append(f"[Définition] {definition}")
        for topic in d.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                txt = topic["Text"].strip()
                if txt and len(results) < max_results + 2:
                    results.append(f"• {txt[:200]}")
        return results
    except Exception:
        return []


def web_search(query: str, max_results: int = 5) -> str:
    """Recherche web combinée : DuckDuckGo + Wikipedia FR fallback."""
    results = search_ddg(query, max_results)

    try:
        r2 = req.get(
            "https://fr.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": query, "limit": max_results,
                    "namespace": "0", "format": "json"},
            headers=_WEB_HEADERS, timeout=_web_fetch_timeout_s
        )
        data = r2.json()
        titles   = data[1] if len(data) > 1 else []
        snippets = data[2] if len(data) > 2 else []
        for t, s in zip(titles, snippets, strict=False):
            if t and t not in str(results):
                entry = f"[Wikipedia] {t}"
                if s: entry += f": {s}"
                results.append(entry)
                if len(results) >= max_results + 3:
                    break
    except Exception as e:
        _log.warning(f"[JARVIS] WARNING web_search Wikipedia: {e}")

    if not results:
        return f"[Aucun résultat web trouvé pour: {query}]"
    return (
        f"=== RÉSULTATS WEB ({len(results)} sources) ===\n"
        + "\n".join(results[:max_results + 2])
        + "\n====================="
    )
