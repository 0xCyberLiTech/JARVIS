"""Tuile **dev** — exécution code/dev sur srv-dev-1 (sans WebSocket).

15ème tuile autoportante (refactor jarvis.py étape 22, 2026-05-23).
"""
from flask import Blueprint

bp = Blueprint("dev", __name__)

from . import routes  # noqa: E402,F401

_ROUTE_LIMITS = {
    "api_code_exec": "10 per minute",
    "api_dev_exec":  "60 per minute",
    "dev_stats":     "30 per minute",
    "api_save_code": "10 per minute",
}


def init(*, limiter, **kwargs) -> None:
    routes.init_routes(**kwargs)
    for fn_name, limit_str in _ROUTE_LIMITS.items():
        fn = getattr(routes, fn_name, None)
        if fn is not None:
            limiter.limit(limit_str)(fn)
