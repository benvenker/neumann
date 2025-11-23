"""
Document browsing endpoints.

Provides read-only APIs to list documents, view rendered pages manifests, and
retrieve code/text chunks associated with a document.
"""

import json
import logging
from pathlib import Path
from typing import Any

from chromadb.api import ClientAPI
from fastapi import APIRouter, Depends, HTTPException

from config import Config
from indexer import get_collections

from ..deps import get_chroma_client, get_settings
from ..models import ChunkInfo, DocumentInfo, PageRecord

router = APIRouter()
logger = logging.getLogger(__name__)


def _safe_get(results: dict[str, Any], key: str) -> list[Any]:
    """Helper to pull list values from Chroma get() results safely."""

    value = results.get(key)
    return value if isinstance(value, list) else []


@router.get("/", response_model=list[DocumentInfo])
def list_documents(client: ClientAPI = Depends(get_chroma_client)) -> list[DocumentInfo]:
    """Return lightweight metadata for all indexed documents."""

    try:
        summaries, _ = get_collections(client)
        # Reduced limit for POC; production would need pagination
        results = summaries.get(include=["metadatas"], limit=100)
    except Exception as exc:  # Chroma or client failures
        logger.exception("Failed to list documents")
        raise HTTPException(status_code=502, detail=f"Failed to list documents: {exc}") from exc

    docs: list[DocumentInfo] = []
    ids = _safe_get(results, "ids")
    metas = _safe_get(results, "metadatas")

    for i, doc_id in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        meta_map = meta if isinstance(meta, dict) else {}
        docs.append(
            DocumentInfo(
                doc_id=str(doc_id),
                source_path=str(meta_map.get("source_path", "")) or None,
                language=str(meta_map.get("language") or meta_map.get("lang") or "") or None,
                last_updated=str(meta_map.get("last_updated", "")) or None,
            )
        )
    return docs


def _resolve_manifest_path(doc_id: str, source_path: str | None, cfg: Config) -> Path | None:
    """Try multiple candidate locations for pages.jsonl and return the first match."""

    candidates: list[Path] = []
    if source_path:
        src = Path(source_path)
        candidates.append(cfg.output_path / source_path / "pages" / "pages.jsonl")
        candidates.append(cfg.output_path / src.name / "pages" / "pages.jsonl")

    candidates.append(cfg.output_path / doc_id / "pages" / "pages.jsonl")

    for path in candidates:
        if path.exists():
            return path
    return None


@router.get("/{doc_id}/pages", response_model=list[PageRecord])
def get_document_pages(
    doc_id: str,
    cfg: Config = Depends(get_settings),
    client: ClientAPI = Depends(get_chroma_client),
) -> list[PageRecord]:
    """Read pages.jsonl for a document and return page records."""

    source_path: str | None = None
    try:
        summaries, _ = get_collections(client)
        result = summaries.get(ids=[doc_id], include=["metadatas"])
        if _safe_get(result, "ids"):
            meta = _safe_get(result, "metadatas")[0] if _safe_get(result, "metadatas") else {}
            if isinstance(meta, dict):
                source_path = meta.get("source_path")
    except Exception as exc:
        logger.exception("Failed to resolve document metadata for pages", extra={"doc_id": doc_id})
        raise HTTPException(status_code=502, detail=f"Failed to resolve document: {exc}") from exc

    manifest_path = _resolve_manifest_path(doc_id, source_path, cfg)
    if manifest_path is None:
        raise HTTPException(status_code=404, detail=f"Pages manifest not found for document: {doc_id}")

    pages: list[PageRecord] = []
    try:
        with open(manifest_path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if "doc_id" not in data:
                        data["doc_id"] = doc_id
                    pages.append(PageRecord(**data))
                except json.JSONDecodeError:
                    logger.warning("Skipping malformed JSON line", extra={"path": str(manifest_path)})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Pages manifest not found for document: {doc_id}") from exc
    except Exception as exc:
        logger.exception("Error reading pages manifest", extra={"path": str(manifest_path)})
        raise HTTPException(status_code=500, detail="Failed to read pages manifest") from exc

    return pages


@router.get("/{doc_id}/chunks", response_model=list[ChunkInfo])
def get_document_chunks(
    doc_id: str,
    client: ClientAPI = Depends(get_chroma_client),
) -> list[ChunkInfo]:
    """Return text/code chunks for a document from the search_code collection."""

    try:
        _, code_coll = get_collections(client)
        # Reduced limit: 500 chunks covers ~90k lines, which is plenty for a single file
        results = code_coll.get(where={"doc_id": doc_id}, include=["documents", "metadatas"], limit=500)
    except Exception as exc:
        logger.exception("Failed to load chunks", extra={"doc_id": doc_id})
        raise HTTPException(status_code=502, detail=f"Failed to load chunks: {exc}") from exc

    chunks: list[ChunkInfo] = []
    ids = _safe_get(results, "ids")
    docs = _safe_get(results, "documents")
    metas = _safe_get(results, "metadatas")

    for i, chunk_id in enumerate(ids):
        text = docs[i] if i < len(docs) else ""
        meta = metas[i] if i < len(metas) else {}
        meta_map = meta if isinstance(meta, dict) else {}

        chunks.append(
            ChunkInfo(
                chunk_id=str(chunk_id),
                doc_id=doc_id,
                text=str(text),
                source_path=str(meta_map.get("source_path", "")) or None,
                line_start=meta_map.get("line_start"),
                line_end=meta_map.get("line_end"),
            )
        )

    return chunks
