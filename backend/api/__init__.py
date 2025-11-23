"""
Neumann FastAPI application scaffolding.

See api.app:create_app for the ASGI application factory.
"""

# Optionally expose create_app for convenience (safe import)
from .app import create_app  # noqa: F401

__all__ = ["create_app"]
