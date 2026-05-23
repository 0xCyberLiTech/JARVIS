"""Tuile **tasks** — tâches planifiées + polling Code Reasoning.

12ème tuile autoportante (refactor jarvis.py étape 18, 2026-05-23).
"""
from flask import Blueprint

bp = Blueprint("tasks", __name__)

from . import routes  # noqa: E402,F401

_ROUTE_LIMITS = {
    "cr_poll":          "120 per minute",
    "api_tasks_get":    "60 per minute",
    "api_tasks_post":   "30 per minute",
    "api_tasks_delete": "20 per minute",
    "api_tasks_run":    "10 per minute",
}


def init(*, limiter, log, get_tasks_file, terminal_cwd, terminal_timeout_s, cr_tasks) -> None:
    routes.init_routes(
        log=log, get_tasks_file=get_tasks_file, terminal_cwd=terminal_cwd,
        terminal_timeout_s=terminal_timeout_s, cr_tasks=cr_tasks,
    )
    for fn_name, limit_str in _ROUTE_LIMITS.items():
        fn = getattr(routes, fn_name, None)
        if fn is not None:
            limiter.limit(limit_str)(fn)
