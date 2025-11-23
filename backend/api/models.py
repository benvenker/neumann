"""
Pydantic models for API contracts.

Contains request/response models for the Neumann API endpoints.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field(..., description="Service status")


class ServiceInfo(BaseModel):
    """Service information model."""

    version: str = Field(..., description="API version")
    name: str = Field(default="neumann-api", description="Service name")


# --- Search API Models (nm-3573.2) ---


def _sanitize_list_like(value: object) -> list[str]:
    """Normalize list-like inputs from comma-separated strings or lists.

    Args:
        value: Input that can be None, str (comma-separated), or list

    Returns:
        Deduplicated list of non-empty strings, preserving order
    """
    if value is None:
        return []
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",")]
    elif isinstance(value, list):
        parts = [str(x).strip() for x in value]
    else:
        return []

    seen = set()
    out: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out


class LexicalSearchRequest(BaseModel):
    """Request model for lexical (FTS + regex) search."""

    must_terms: list[str] = Field(default_factory=list, description="ANDed substring terms")
    regexes: list[str] = Field(default_factory=list, description="ORed regex patterns")
    path_like: str | None = Field(default=None, description="Substring to match in source_path")
    k: int = Field(default=12, ge=1, description="Max results to return (must be > 0)")

    model_config = {"extra": "forbid"}

    @field_validator("must_terms", "regexes", mode="before")
    @classmethod
    def _validate_lists(cls, v: object) -> list[str]:
        return _sanitize_list_like(v)

    @field_validator("path_like", mode="before")
    @classmethod
    def _validate_path_like(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None


class SemanticSearchRequest(BaseModel):
    """Request model for semantic (vector similarity) search."""

    query: str = Field(..., description="Semantic query string (non-empty)")
    k: int = Field(default=12, ge=1, description="Max results to return")

    model_config = {"extra": "forbid"}

    @field_validator("query", mode="before")
    @classmethod
    def _validate_query(cls, v: object) -> str:
        s = str(v or "").strip()
        if not s:
            raise ValueError("query must be non-empty")
        return s


class HybridSearchRequest(BaseModel):
    """Request model for hybrid (semantic + lexical) search."""

    query: str | None = Field(default=None, description="Semantic query if semantic channel is desired")
    must_terms: list[str] = Field(default_factory=list, description="ANDed substring terms")
    regexes: list[str] = Field(default_factory=list, description="ORed regex patterns")
    path_like: str | None = Field(default=None, description="Substring to match in source_path")
    k: int = Field(default=12, ge=1, description="Max results to return")
    w_semantic: float = Field(default=0.6, ge=0.0, le=1.0, description="Weight for semantic score")
    w_lexical: float = Field(default=0.4, ge=0.0, le=1.0, description="Weight for lexical score")

    model_config = {"extra": "forbid"}

    @field_validator("must_terms", "regexes", mode="before")
    @classmethod
    def _validate_lists(cls, v: object) -> list[str]:
        return _sanitize_list_like(v)

    @field_validator("path_like", mode="before")
    @classmethod
    def _validate_path_like(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @field_validator("query", mode="before")
    @classmethod
    def _validate_query(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @model_validator(mode="after")
    def _validate_channels(self) -> "HybridSearchRequest":
        """Ensure at least one search channel is active."""
        has_sem = bool(self.query)
        has_lex = bool(self.must_terms or self.regexes or self.path_like)
        if not has_sem and not has_lex:
            raise ValueError("At least one of query or lexical filters must be provided")
        if (self.w_semantic + self.w_lexical) <= 0:
            raise ValueError("w_semantic + w_lexical must be > 0")
        return self


class BaseSearchResult(BaseModel):
    """Base search result model with common fields."""

    doc_id: str
    source_path: str | None = None
    score: float
    page_uris: list[str] = Field(default_factory=list)
    line_start: int | None = None
    line_end: int | None = None
    why: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    lex_term_hits: int = Field(default=0, description="Count of exact term matches")
    lex_regex_hits: int = Field(default=0, description="Count of regex matches")


class LexicalSearchResult(BaseSearchResult):
    """Result model for lexical search."""

    pass


class SemanticSearchResult(BaseSearchResult):
    """Result model for semantic search."""

    pass


class HybridSearchResult(BaseSearchResult):
    """Result model for hybrid search with additional score breakdowns."""

    sem_score: float = 0.0
    lex_score: float = 0.0
    rrf_score: float = 0.0


class DocumentInfo(BaseModel):
    """Summary information for a document."""

    doc_id: str = Field(..., description="Unique document identifier (usually filename)")
    source_path: str | None = Field(None, description="Relative path to source file")
    language: str | None = None
    last_updated: str | None = None

    model_config = {"extra": "ignore"}


class PageRecord(BaseModel):
    """Represents a single page from pages.jsonl."""

    doc_id: str
    page: int
    uri: str = Field(..., description="Full URI to the page asset")
    width: int
    height: int
    bytes: int | None = None
    sha256: str | None = None
    source_file: str | None = None

    model_config = {"extra": "ignore"}


class ChunkInfo(BaseModel):
    """Represents a text/code chunk from the index."""

    chunk_id: str
    doc_id: str
    text: str
    source_path: str | None = None
    line_start: int | None = None
    line_end: int | None = None

    model_config = {"extra": "ignore"}
