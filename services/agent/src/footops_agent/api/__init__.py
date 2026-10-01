"""FastAPI transport and business event streaming.

Import the application from :mod:`footops_agent.api.main`. Keeping package
initialization side-effect free prevents CLI and Harness imports from creating
an API-to-Harness cycle.
"""

from typing import Any

__all__ = ["app", "create_app"]


def __getattr__(name: str) -> Any:
    """Preserve public imports without eagerly importing the application."""
    if name in __all__:
        from .main import app, create_app

        return {"app": app, "create_app": create_app}[name]
    raise AttributeError(name)
