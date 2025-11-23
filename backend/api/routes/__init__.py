"""
API route composition.

Provides a shared APIRouter instance for organizing route modules.
"""

from fastapi import APIRouter

from .docs import router as docs_router
from .search import router as search_router

# Shared router for all API routes
api_router = APIRouter()

# Search endpoints (nm-3573.2)
api_router.include_router(search_router, prefix="/search", tags=["search"])

# Document browsing endpoints (nm-3573.3)
api_router.include_router(docs_router, prefix="/docs", tags=["documents"])
