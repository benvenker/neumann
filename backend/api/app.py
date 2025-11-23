"""
FastAPI application factory and module-level app instance.

This module provides:
- create_app(): Factory function for creating FastAPI instances
- app: Module-level instance for uvicorn (uvicorn api.app:app)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .deps import get_settings
from .routes import api_router

logger = logging.getLogger(__name__)


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

    # Log ChromaDB path for debugging path mismatches
    logger.info(f"ChromaDB path: {cfg.CHROMA_PATH}")
    logger.info(f"OpenAI configured: {cfg.has_openai_key}")

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

    # Mount static assets (rendered WebP pages, etc.)
    # Served at /api/v1/assets to match the configured ASSET_BASE_URL logic
    if cfg.output_path.exists():
        app.mount("/api/v1/assets", StaticFiles(directory=str(cfg.output_path)), name="assets")
        logger.info(f"Mounted static assets from {cfg.output_path} at /api/v1/assets")
    else:
        logger.warning(f"Output path {cfg.output_path} does not exist; static assets not mounted")

    # Include versioned API router
    app.include_router(api_router, prefix="/api/v1")

    # Lightweight health endpoint for observability
    @app.get("/healthz", tags=["infra"])
    def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}

    @app.get("/api/v1/config", tags=["infra"])
    def get_config(cfg: Config = Depends(get_settings)) -> dict[str, object]:
        """
        Get public configuration for the frontend.
        """
        return {
            "asset_base_url": "/api/v1/assets",
            "has_openai_key": cfg.has_openai_key,
        }

    return app


# For `uvicorn api.app:app --reload`
app = create_app()
