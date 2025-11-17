"""
Search API routes.

Provides POST endpoints for lexical, semantic, and hybrid search.
"""

import logging

from chromadb.api import ClientAPI
from fastapi import APIRouter, Depends, HTTPException

from config import Config
from indexer import hybrid_search as idx_hyb
from indexer import lexical_search as idx_lex
from indexer import semantic_search as idx_sem

from ..deps import get_chroma_client, get_settings
from ..models import (
    HybridSearchRequest,
    HybridSearchResult,
    LexicalSearchRequest,
    LexicalSearchResult,
    SemanticSearchRequest,
    SemanticSearchResult,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _map_upstream_exception(e: Exception) -> HTTPException:
    """Map upstream exceptions to appropriate HTTP status codes.

    Args:
        e: Exception from indexer or ChromaDB

    Returns:
        HTTPException with appropriate status code and message
    """
    msg = str(e)
    # Check for client-correctable issues (400)
    if "OPENAI_API_KEY" in msg or "embed query" in msg.lower():
        return HTTPException(status_code=400, detail=msg)
    # All other upstream failures (502)
    return HTTPException(status_code=502, detail=f"Upstream search error: {msg}")


@router.post("/lexical", response_model=list[LexicalSearchResult], summary="Lexical search")
def lexical_endpoint(
    req: LexicalSearchRequest,
    client: ClientAPI = Depends(get_chroma_client),
) -> list[LexicalSearchResult]:
    """
    Perform lexical search using FTS (must_terms) and regex patterns.

    Requires at least one of: must_terms, regexes, or path_like.

    Args:
        req: Lexical search request
        client: ChromaDB client (injected)

    Returns:
        List of search results with lexical scores

    Raises:
        HTTPException: 400 for invalid request, 502 for upstream errors
    """
    # Validate at least one filter is provided
    if not req.must_terms and not req.regexes and not req.path_like:
        raise HTTPException(status_code=400, detail="Provide at least one of must_terms, regexes, or path_like")

    try:
        results = idx_lex(
            must_terms=req.must_terms,
            regexes=req.regexes,
            path_like=req.path_like,
            k=req.k,
            client=client,
        )
        return results  # type: ignore[return-value]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Lexical search failed")
        raise _map_upstream_exception(e) from e


@router.post("/semantic", response_model=list[SemanticSearchResult], summary="Semantic search")
def semantic_endpoint(
    req: SemanticSearchRequest,
    cfg: Config = Depends(get_settings),
    client: ClientAPI = Depends(get_chroma_client),
) -> list[SemanticSearchResult]:
    """
    Perform semantic search using vector similarity.

    Requires OPENAI_API_KEY to be configured.

    Args:
        req: Semantic search request
        cfg: Configuration (injected)
        client: ChromaDB client (injected)

    Returns:
        List of search results with semantic similarity scores

    Raises:
        HTTPException: 400 for missing API key, 502 for upstream errors
    """
    if not cfg.has_openai_key:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY is required for semantic search")

    try:
        results = idx_sem(query=req.query, k=req.k, client=client)
        return results  # type: ignore[return-value]
    except Exception as e:
        logger.exception("Semantic search failed")
        raise _map_upstream_exception(e) from e


@router.post("/hybrid", response_model=list[HybridSearchResult], summary="Hybrid search")
def hybrid_endpoint(
    req: HybridSearchRequest,
    cfg: Config = Depends(get_settings),
    client: ClientAPI = Depends(get_chroma_client),
) -> list[HybridSearchResult]:
    """
    Perform hybrid search combining semantic and lexical channels.

    Uses weighted-sum fusion with RRF tie-breaking. Requires OPENAI_API_KEY
    if a semantic query is provided.

    Args:
        req: Hybrid search request
        cfg: Configuration (injected)
        client: ChromaDB client (injected)

    Returns:
        List of search results with combined scores

    Raises:
        HTTPException: 400 for missing API key when semantic query provided, 502 for upstream errors
    """
    # Check if semantic channel is requested and validate API key
    if req.query and not cfg.has_openai_key:
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY is required when hybrid search includes a semantic query",
        )

    try:
        results = idx_hyb(
            query=req.query or "",
            k=req.k,
            must_terms=req.must_terms,
            regexes=req.regexes,
            path_like=req.path_like,
            client=client,
            embedding_function=None,
            w_semantic=req.w_semantic,
            w_lexical=req.w_lexical,
        )
        return results  # type: ignore[return-value]
    except Exception as e:
        logger.exception("Hybrid search failed")
        raise _map_upstream_exception(e) from e
