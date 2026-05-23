"""Route /api/web-test — diagnostic connectivité web + DDG + Wikipedia."""
import json
import time

import requests as req
from flask import Response

from . import bp, search

_log = None


def init_routes(*, log) -> None:
    global _log
    _log = log


@bp.route("/api/web-test", methods=["GET"])
def api_web_test():
    """Teste la connectivité web et les moteurs de recherche."""
    result = {"connectivity": False, "ddg": False, "wikipedia": False,
              "latency_ms": None, "results_count": 0, "search_ok": False, "error": None}

    try:
        t0 = time.time()
        r = req.get("https://www.google.com", timeout=search._web_conn_timeout_s, allow_redirects=True)
        result["connectivity"] = r.status_code < 500
        result["latency_ms"] = round((time.time() - t0) * 1000)
    except Exception as e:
        result["error"] = str(e)

    try:
        r2 = req.get("https://api.duckduckgo.com/",
                     params={"q": "intelligence artificielle", "format": "json",
                             "no_redirect": "1", "no_html": "1"},
                     headers=search._WEB_HEADERS, timeout=search._web_fetch_timeout_s)
        d2 = r2.json()
        result["ddg"] = bool(d2.get("AbstractText") or d2.get("RelatedTopics") or d2.get("Answer"))
    except Exception as e:
        result["ddg_error"] = str(e)

    try:
        r3 = req.get("https://fr.wikipedia.org/w/api.php",
                     params={"action": "opensearch", "search": "intelligence artificielle",
                             "limit": 2, "format": "json"},
                     headers=search._WEB_HEADERS, timeout=search._web_fetch2_timeout_s)
        data = r3.json()
        result["wikipedia"] = len(data[1]) > 0 if len(data) > 1 else False
    except Exception as e:
        result["wikipedia_error"] = str(e)

    try:
        res = search.web_search("intelligence artificielle", max_results=3)
        result["search_ok"] = not res.startswith("[Aucun") and len(res) > 40
        result["results_count"] = res.count("\n") if result["search_ok"] else 0
        result["sample"] = res[:250]
    except Exception as e:
        result["search_error"] = str(e)

    return Response(json.dumps(result, ensure_ascii=False), mimetype="application/json")
