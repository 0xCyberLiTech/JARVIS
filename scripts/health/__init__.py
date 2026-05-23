"""Tuile **health** — santé runtime + stats + ping + security."""
from flask import Blueprint

bp = Blueprint("health", __name__)

from . import routes  # noqa: E402,F401

_ROUTE_LIMITS = {
    "api_boot_id":         "60 per minute",
    "api_health":          "120 per minute",
    "api_stats":           "60 per minute",
    "api_status":          "60 per minute",
    "api_ollama_status":   "60 per minute",
    "api_vram":            "30 per minute",
    "api_security":        "60 per minute",
    "api_security_clear":  "10 per minute",
    "api_ping":            "20 per minute",
}


def init(*, limiter, **kwargs) -> None:
    routes.init_routes(**kwargs)
    for fn_name, limit_str in _ROUTE_LIMITS.items():
        fn = getattr(routes, fn_name, None)
        if fn is not None:
            limiter.limit(limit_str)(fn)
