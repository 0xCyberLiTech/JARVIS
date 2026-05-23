"""Tuile **web** — recherche web (DDG + Wikipedia FR) + diagnostic connectivité.

16ème tuile autoportante (refactor jarvis.py étape 23, 2026-05-23).
"""
from flask import Blueprint

bp = Blueprint("web", __name__)

from . import routes, search  # noqa: E402,F401


def init(*, limiter, log, web_search_timeout_s=10, web_fetch_timeout_s=8,
         web_conn_timeout_s=5, web_fetch2_timeout_s=6) -> None:
    search.init(
        log=log,
        web_search_timeout_s=web_search_timeout_s,
        web_fetch_timeout_s=web_fetch_timeout_s,
        web_conn_timeout_s=web_conn_timeout_s,
        web_fetch2_timeout_s=web_fetch2_timeout_s,
    )
    routes.init_routes(log=log)
    limiter.limit("10 per minute")(routes.api_web_test)
