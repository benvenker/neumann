"""
API route composition.

Provides a shared APIRouter instance for organizing route modules.
"""

from fastapi import APIRouter

# Shared router for all API routes
api_router = APIRouter()

# TODO(nm-3573.2): include_router(search_router, prefix="/search", tags=["search"])
# TODO(nm-3573.3): include_router(doc_router, prefix="/docs", tags=["documents"])
