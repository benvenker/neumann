from __future__ import annotations

import re
from typing import (Any, Callable, Dict, Iterable, List, Mapping, Optional,
                    Pattern, Sequence, Tuple)

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from config import config


def get_client(path: Optional[str] = None) -> ClientAPI:
    storage_path = path or config.CHROMA_PATH
    return chromadb.PersistentClient(path=storage_path)


def get_collections(
    client: Optional[ClientAPI] = None,
) -> Tuple[Collection, Collection]:
    """Return (search_summaries, search_code) collections.

    - search_summaries: for summary markdown with embeddings
    - search_code: for raw code/text chunks (no embeddings attached here)
    """
    cl = client or get_client()
    summaries = cl.get_or_create_collection(
        name="search_summaries",
        metadata={"description": "Summaries with embeddings"},
    )
    code = cl.get_or_create_collection(
        name="search_code",
        metadata={"description": "Raw code/text chunks (FTS/regex)"},
    )
    return summaries, code


def upsert_summaries(
    items: Iterable[Mapping[str, object]],
    *,
    client: Optional[ClientAPI] = None,
    embedding_function: Optional[Callable[[Sequence[str]], List[List[float]]]] = None,
) -> int:
    """Upsert summaries into search_summaries.

    Each item must include: id (str), document (markdown body), metadata (dict).
    If embedding_function is provided, embeddings are computed client-side; otherwise
    rely on collection's embedding function.
    """
    summaries, _ = get_collections(client)

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Mapping[str, object]] = []
    for item in items:
        ids.append(str(item["id"]))
        documents.append(str(item["document"]))
        metadatas.append(item.get("metadata", {}))

    kwargs = {"ids": ids, "documents": documents, "metadatas": metadatas}
    if embedding_function is not None:
        kwargs["embeddings"] = embedding_function(documents)
    summaries.upsert(**kwargs)  # type: ignore[arg-type]
    return len(ids)


def upsert_code_chunks(
    items: Iterable[Mapping[str, object]],
    *,
    client: Optional[ClientAPI] = None,
) -> int:
    """Upsert code/text chunks into search_code without embeddings."""
    _, code = get_collections(client)

    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Mapping[str, object]] = []
    for item in items:
        ids.append(str(item["id"]))
        documents.append(str(item["document"]))
        metadatas.append(item.get("metadata", {}))

    code.upsert(ids=ids, documents=documents, metadatas=metadatas)  # type: ignore[arg-type]
    return len(ids)


def _sanitize_list(xs: Optional[Sequence[str]]) -> List[str]:
    """Clean and deduplicate input list: strip whitespace, remove empty strings, preserve order."""
    if not xs:
        return []
    seen: set[str] = set()
    out: List[str] = []
    for s in xs:
        if not s:
            continue
        t = s.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _build_where_document(
    must_terms: Optional[List[str]], regexes: Optional[List[str]]
) -> Optional[Dict[str, Any]]:
    """Build ChromaDB where_document filter combining must_terms (AND $contains) and regexes (OR $regex)."""
    terms = _sanitize_list(must_terms)
    regs = _sanitize_list(regexes)

    terms_group: Optional[Dict[str, Any]] = None
    if terms:
        if len(terms) == 1:
            # Single term: no need for $and wrapper
            terms_group = {"$contains": terms[0]}
        else:
            # Multiple terms: wrap in $and
            terms_group = {"$and": [{"$contains": t} for t in terms]}

    regex_group: Optional[Dict[str, Any]] = None
    if regs:
        if len(regs) == 1:
            # Single regex: no need for $or wrapper
            regex_group = {"$regex": regs[0]}
        else:
            # Multiple regexes: wrap in $or
            regex_group = {"$or": [{"$regex": r} for r in regs]}

    if terms_group and regex_group:
        return {"$and": [terms_group, regex_group]}
    return terms_group or regex_group


def _build_where_metadata(path_like: Optional[str]) -> Optional[Dict[str, Any]]:
    """Build ChromaDB where filter for source_path metadata.
    
    Note: ChromaDB's metadata filters don't support $contains, so path filtering
    is handled client-side after retrieval. This function is kept for future use
    if ChromaDB adds substring matching support.
    """
    # ChromaDB metadata doesn't support $contains, so we filter client-side
    return None


def _compile_regexes(regexes: List[str]) -> List[Tuple[Pattern[str], str]]:
    """Safely compile regex patterns, skipping invalid ones. Returns list of (pattern, original) tuples."""
    patterns: List[Tuple[Pattern[str], str]] = []
    for raw in regexes:
        try:
            compiled = re.compile(raw, flags=re.IGNORECASE | re.MULTILINE)
            patterns.append((compiled, raw))
        except re.error:
            # Skip invalid patterns silently (POC tolerance)
            continue
    return patterns


def lexical_search(
    must_terms: Optional[List[str]] = None,
    regexes: Optional[List[str]] = None,
    path_like: Optional[str] = None,
    k: int = 12,
    *,
    client: Optional[ClientAPI] = None,
) -> List[Dict[str, Any]]:
    """Query search_code collection using FTS ($contains), regex ($regex), and path filtering.

    Args:
        must_terms: Terms that must all be present (AND logic via $contains)
        regexes: Regex patterns, any of which can match (OR logic via $regex)
        path_like: Filter by substring match in source_path metadata
        k: Maximum number of results to return
        client: Optional ChromaDB client (uses default if not provided)

    Returns:
        List of result dicts with doc_id, source_path, score, page_uris, line_start, line_end, why
    """
    if k <= 0:
        return []

    terms = _sanitize_list(must_terms)
    raw_regs = _sanitize_list(regexes)
    pl = path_like.strip() if path_like else None

    # Compile and validate regexes early to filter out invalid patterns
    compiled_patterns = _compile_regexes(raw_regs)
    # Extract valid regex strings for Chroma query
    valid_regs = [raw for _, raw in compiled_patterns]

    # Return empty if all filters are empty
    if not terms and not valid_regs and not pl:
        return []

    where_doc = _build_where_document(terms, valid_regs)
    # Note: ChromaDB metadata filters don't support $contains for path filtering,
    # so we filter client-side after retrieval
    where_meta = _build_where_metadata(pl)

    _, code = get_collections(client)

    # Perform FTS query
    # For path filtering, we may need to fetch more results than k to account for
    # client-side filtering, but for simplicity we'll fetch k and filter
    fetch_limit = k * 3 if pl else k  # Fetch more if path filtering is needed

    # IDs are always returned, so we only need documents and metadatas in include
    res = code.get(
        where=where_meta,
        where_document=where_doc,
        limit=fetch_limit,
        include=["documents", "metadatas"],
    )

    # Assemble results
    results: List[Dict[str, Any]] = []
    ids = res.get("ids", [])
    documents = res.get("documents", [])
    metadatas = res.get("metadatas", [])

    # Iterate by index with defensive access to handle None/short lists
    for i in range(len(ids)):
        id_ = ids[i]
        doc = documents[i] if i < len(documents) else None
        meta = metadatas[i] if metadatas and i < len(metadatas) else {}
        meta_dict = meta or {}
        doc_id = meta_dict.get("doc_id") or id_
        source_path = meta_dict.get("source_path")
        page_uris = meta_dict.get("page_uris") or []
        # Handle page_uris if stored as string (comma-separated)
        if isinstance(page_uris, str):
            page_uris = [uri.strip() for uri in page_uris.split(",") if uri.strip()]
        elif not isinstance(page_uris, list):
            page_uris = []
        line_start = meta_dict.get("line_start")
        line_end = meta_dict.get("line_end")

        # Client-side path filtering (since ChromaDB metadata doesn't support $contains)
        if pl and isinstance(source_path, str):
            if pl.lower() not in source_path.lower():
                continue  # Skip this result if path doesn't match

        # Build why signals
        why: List[str] = []
        doc_str = str(doc) if doc else ""
        doc_lower = doc_str.lower()

        # Check for term matches (case-insensitive)
        for t in terms:
            if t.lower() in doc_lower:
                why.append(f"matched term: '{t}'")

        # Check for regex matches
        for pattern, raw in compiled_patterns:
            if pattern.search(doc_str):
                why.append(f"matched regex: r'{raw}'")

        # Check for path match (add to why if path was filtered)
        if pl and isinstance(source_path, str):
            if pl.lower() in source_path.lower():
                why.append(f"path matched: '{pl}' in '{source_path}'")

        results.append(
            {
                "doc_id": doc_id,
                "source_path": source_path,
                "score": 1.0,
                "page_uris": page_uris,
                "line_start": line_start,
                "line_end": line_end,
                "why": why,
            }
        )

        # Stop once we have k results after filtering
        if len(results) >= k:
            break

    return results


__all__ = [
    "get_client",
    "get_collections",
    "upsert_summaries",
    "upsert_code_chunks",
    "lexical_search",
]


