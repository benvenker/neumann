"""
API route composition.

Provides a shared APIRouter instance for organizing route modules.
"""

from fastapi import APIRouter

from .search import router as search_router

# Shared router for all API routes
api_router = APIRouter()

# Search endpoints (nm-3573.2)
api_router.include_router(search_router, prefix="/search", tags=["search"])

# TODO(nm-3573.3): include_router(doc_router, prefix="/docs", tags=["documents"])
