"""
Pydantic models for API contracts.

Contains request/response models for the Neumann API endpoints.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")


class ServiceInfo(BaseModel):
    """Service information model."""

    version: str = Field(..., description="API version")
    name: str = Field(default="neumann-api", description="Service name")


# TODO(nm-3573.2): Add SearchQuery, SearchResult, and pagination models.
# TODO(nm-3573.3): Add Page, Chunk, and Document models.
