"""
FastAPI application factory and module-level app instance.

This module provides:
- create_app(): Factory function for creating FastAPI instances
- app: Module-level instance for uvicorn (uvicorn api.app:app)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .deps import get_settings
from .routes import api_router


def create_app() -> FastAPI:
    """
    Create and configure a FastAPI application instance.

    Returns:
        FastAPI: Configured application with CORS, routers, and health endpoint.
    """
    app = FastAPI(
        title="Neumann API",
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    cfg = get_settings()

    # Add CORS middleware only if origins are configured
    origins = cfg.API_CORS_ORIGINS or []
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        )

    # Include versioned API router
    app.include_router(api_router, prefix="/api/v1")

    # Lightweight health endpoint for observability
    @app.get("/healthz", tags=["infra"])
    def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    return app


# For `uvicorn api.app:app --reload`
app = create_app()
