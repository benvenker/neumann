from __future__ import annotations

import logging
import math
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from re import Pattern
from typing import Any, TypedDict

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from config import config
from embeddings import embed_texts

logger = logging.getLogger(__name__)

# Lexical scoring defaults (tunable)
LEX_W_TERM: float = 1.0  # weight for substring term matches
LEX_W_REGEX: float = 1.5  # weight for regex matches (identifiers)
LEX_TERM_CAP: int = 3  # cap per term (prevent repeat domination)
LEX_REGEX_CAP: int = 3  # cap per regex
LEX_LENGTH_ALPHA: float = 0.2  # strength of mild length penalty
LEX_PATH_ONLY_BASELINE: float = 0.25  # baseline when only path_like matches
LEX_PATH_FETCH_MULTIPLIER: int = 10  # multiplier for fetch limit when path filtering

# Metadata keys that are normalized from comma-separated strings to lists on read
NORMALIZED_META_LIST_KEYS: list[str] = [
    "product_tags",
    "key_topics",
    "api_symbols",
    "related_files",
    "suggested_queries",
    "page_uris",
]


def get_client(path: str | None = None) -> ClientAPI:
    """Get ChromaDB persistent client with resolved absolute path.

    Args:
        path: Optional ChromaDB storage path. If None, uses config.CHROMA_PATH.
            Both relative and absolute paths are resolved to absolute.

    Returns:
        ClientAPI: ChromaDB persistent client.

    Note:
        Paths are always resolved to absolute to ensure CLI and API processes
        use the same database regardless of their current working directory.
    """
    storage_path = path or config.CHROMA_PATH
    # Resolve to absolute path to avoid CWD-dependent path mismatches
    resolved_path = str(Path(storage_path).expanduser().resolve())
    return chromadb.PersistentClient(path=resolved_path)


def get_collections(
    client: ClientAPI | None = None,
) -> tuple[Collection, Collection]:
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
    client: ClientAPI | None = None,
    embedding_function: Callable[[Sequence[str]], list[list[float]]] | None = None,
) -> int:
    """Upsert summaries into search_summaries.

    Each item must include: id (str), document (markdown body), metadata (dict).
    If embedding_function is provided, embeddings are computed client-side; otherwise
    rely on collection's embedding function.
    """
    summaries, _ = get_collections(client)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[Mapping[str, object]] = []
    for item in items:
        ids.append(str(item["id"]))
        documents.append(str(item["document"]))
        raw_meta = item.get("metadata", {})
        meta_map = raw_meta if isinstance(raw_meta, Mapping) else {}
        metadatas.append(_normalize_metadata_for_chroma(meta_map))

    kwargs = {"ids": ids, "documents": documents, "metadatas": metadatas}
    if embedding_function is not None:
        kwargs["embeddings"] = embedding_function(documents)
    summaries.upsert(**kwargs)  # type: ignore[arg-type]
    return len(ids)


def upsert_code_chunks(
    items: Iterable[Mapping[str, object]],
    *,
    client: ClientAPI | None = None,
) -> int:
    """Upsert code/text chunks into search_code without embeddings."""
    _, code = get_collections(client)

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[Mapping[str, object]] = []
    for item in items:
        ids.append(str(item["id"]))
        documents.append(str(item["document"]))
        raw_meta = item.get("metadata", {})
        meta_map = raw_meta if isinstance(raw_meta, Mapping) else {}
        metadatas.append(_normalize_metadata_for_chroma(meta_map))

    code.upsert(ids=ids, documents=documents, metadatas=metadatas)  # type: ignore[arg-type]
    return len(ids)


def _sanitize_list(xs: Sequence[str] | None) -> list[str]:
    """Clean and deduplicate input list: strip whitespace, remove empty strings, preserve order."""
    if not xs:
        return []
    seen: set[str] = set()
    out: list[str] = []
    for s in xs:
        if not s:
            continue
        t = s.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _build_where_document(must_terms: list[str] | None, regexes: list[str] | None) -> dict[str, Any] | None:
    """Build ChromaDB where_document filter combining must_terms and regexes.

    Filter semantics:
    - must_terms: Combined via AND of {"$contains": term} (case-sensitive in Chroma)
    - regexes: Combined via OR of {"$regex": pattern} (honors pattern flags; embed (?i) for case-insensitive)
    - Both present: The two groups are ANDed together: {"$and": [terms_group, regex_group]}

    Notes:
    - Chroma's $contains is case-sensitive
    - Chroma's $regex follows the pattern's semantics (flags embedded in pattern are honored)
    - Local scoring uses case-insensitive regex matching (re.IGNORECASE) for robustness;
      this may differ from Chroma's matching if the user doesn't embed flags. This is
      acceptable for PoC and documented.
    """
    terms = _sanitize_list(must_terms)
    regs = _sanitize_list(regexes)

    terms_group: dict[str, Any] | None = (
        {"$contains": terms[0]}
        if terms and len(terms) == 1
        else {"$and": [{"$contains": t} for t in terms]}
        if terms
        else None
    )

    regex_group: dict[str, Any] | None = (
        {"$regex": regs[0]} if regs and len(regs) == 1 else {"$or": [{"$regex": r} for r in regs]} if regs else None
    )

    if terms_group and regex_group:
        return {"$and": [terms_group, regex_group]}
    return terms_group or regex_group


def _build_where_metadata(path_like: str | None) -> dict[str, Any] | None:
    """Build ChromaDB where filter for source_path metadata.

    Note: ChromaDB's metadata filters don't support $contains, so path filtering
    is handled client-side after retrieval. This function is kept for future use
    if ChromaDB adds substring matching support.
    """
    _ = path_like  # placeholder for future metadata filtering support
    # ChromaDB metadata doesn't support $contains, so we filter client-side
    return None


def _compile_regexes(regexes: list[str]) -> list[tuple[Pattern[str], str]]:
    """Safely compile regex patterns, skipping invalid ones. Returns list of (pattern, original) tuples."""
    patterns: list[tuple[Pattern[str], str]] = []
    for raw in regexes:
        try:
            compiled = re.compile(raw, flags=re.IGNORECASE | re.MULTILINE)
            patterns.append((compiled, raw))
        except re.error:
            # Skip invalid patterns silently (POC tolerance)
            continue
    return patterns


class LexicalMetrics(TypedDict, total=False):
    """Metrics returned by _compute_lexical_score for scoring and explainability."""

    term_hits: int  # uncapped total across terms
    regex_hits: int  # uncapped total across regexes
    doc_len: int
    per_term: dict[str, int]  # exact input term -> count
    per_regex: dict[str, int]  # raw regex pattern string -> count
    raw: float  # weighted sum with caps, pre-normalization
    max_raw: float  # theoretical max given caps and query shape
    length_pen: float  # multiplicative penalty applied


def _compute_lexical_score(
    doc_str: str,
    terms: list[str],
    compiled_patterns: list[tuple[Pattern[str], str]],
) -> tuple[float, LexicalMetrics]:
    """Compute a 0–1 lexical score with capped match counts and mild length penalty.

    - Counts occurrences per term (case-insensitive, non-overlapping)
    - Counts regex matches (finditer; ignores zero-length)
    - Caps per-term and per-regex contributions to reduce domination by repeats
    - Applies mild length penalty so concise chunks rate slightly higher
    - Normalizes by the maximum possible raw score given caps and query shape

    Returns:
        (score, metrics_dict) where score is in [0,1] and metrics contains hit counts
    """
    doc_lower = doc_str.lower()

    # Count per-term occurrences (non-overlapping, case-insensitive)
    term_hits_list: list[int] = [doc_lower.count(t.lower()) for t in terms] if terms else []
    per_term: dict[str, int] = {t: term_hits_list[i] for i, t in enumerate(terms)} if terms else {}

    # Count regex matches (ignore zero-length matches)
    regex_hits_list: list[int] = []
    per_regex: dict[str, int] = {}
    for pat, raw in compiled_patterns:
        cnt = 0
        for m in pat.finditer(doc_str):
            if m.end() > m.start():
                cnt += 1
        regex_hits_list.append(cnt)
        per_regex[raw] = cnt

    # Cap contributions to prevent repeat domination
    term_hits_capped = [min(h, LEX_TERM_CAP) for h in term_hits_list]
    regex_hits_capped = [min(h, LEX_REGEX_CAP) for h in regex_hits_list]

    # Raw score and max possible (for normalization)
    raw = LEX_W_TERM * sum(term_hits_capped) + LEX_W_REGEX * sum(regex_hits_capped)
    max_raw = LEX_W_TERM * (len(terms) * LEX_TERM_CAP) + LEX_W_REGEX * (len(compiled_patterns) * LEX_REGEX_CAP)

    if max_raw <= 0:
        return 0.0, LexicalMetrics(
            term_hits=0,
            regex_hits=0,
            doc_len=len(doc_str),
            per_term={},
            per_regex={},
            raw=0.0,
            max_raw=0.0,
            length_pen=1.0,
        )

    # Mild length penalty (saturating via log)
    length_pen = 1.0 + LEX_LENGTH_ALPHA * math.log1p(len(doc_str) / 1000.0)
    score = (raw / max_raw) / length_pen
    score = max(0.0, min(score, 1.0))

    return score, LexicalMetrics(
        term_hits=sum(term_hits_list),
        regex_hits=sum(regex_hits_list),
        doc_len=len(doc_str),
        per_term=per_term,
        per_regex=per_regex,
        raw=raw,
        max_raw=max_raw,
        length_pen=length_pen,
    )


def _filters_satisfied(metrics: LexicalMetrics, terms: list[str], compiled: list[tuple[Pattern[str], str]]) -> bool:
    """Check if lexical filter semantics are satisfied based on metrics.

    Returns True if:
        - terms is empty OR every term has count > 0 in metrics.per_term
        - compiled is empty OR at least one pattern has count > 0 in metrics.per_regex

    This enforces AND semantics for terms (all must match) and OR semantics for regexes
    (at least one must match).

    Args:
        metrics: LexicalMetrics dict with per_term and per_regex counts
        terms: List of search terms that must all be present (AND logic)
        compiled: List of (pattern, raw_string) tuples for regex matching (OR logic)

    Returns:
        True if filters are satisfied, False otherwise
    """
    per_term = metrics.get("per_term") or {}
    per_regex = metrics.get("per_regex") or {}

    # AND semantics: all terms must have count > 0
    terms_ok = True if not terms else all(per_term.get(t, 0) > 0 for t in terms)

    # OR semantics: at least one regex must have count > 0
    regex_ok = True if not compiled else any(per_regex.get(raw, 0) > 0 for _, raw in compiled)

    return terms_ok and regex_ok


def _parse_meta_list(value: object) -> list[str]:
    """Normalize list-like metadata fields from comma-separated strings or lists to deduplicated lists.

    Args:
        value: Either a list (convert items to str, strip), a string (split on commas), or other (return [])

    Returns:
        Deduplicated list of strings, preserving order
    """
    if isinstance(value, list):
        seen: set[str] = set()
        out: list[str] = []
        for v in value:
            s = str(v).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",")]
        seen: set[str] = set()
        out: list[str] = []
        for s in parts:
            if s and s not in seen:
                seen.add(s)
                out.append(s)
        return out
    return []


def _normalize_metadata_for_chroma(meta: Mapping[str, object] | None) -> dict[str, object]:
    """Convert metadata values to Chroma-acceptable primitives.

    - list -> comma-joined string (empty list -> "")
    - primitives (str, int, float, bool, None) -> unchanged
    - others (dict, Path, datetime, etc.) -> str(value)
    """
    if not meta:
        return {}
    out: dict[str, object] = {}
    for k, v in meta.items():
        if isinstance(v, list):
            out[k] = ",".join(str(x) for x in v) if v else ""
        elif v is None or isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


def _distance_to_score(d: float | None) -> float:
    """Convert Chroma distance to a bounded [0,1] relevance score (higher is better).

    Args:
        d: Distance value (None or float). Lower distances indicate higher relevance.

    Returns:
        Score in [0,1] range, where 1.0 is highest relevance. Returns 0.0 if d is None.
    """
    if d is None:
        return 0.0
    return 1.0 / (1.0 + max(d, 0.0))


def _rrf_component(rank: int | None, k: int = 60) -> float:
    """Compute RRF contribution for a rank. Returns 0.0 if rank is None."""
    if rank is None:
        return 0.0
    return 1.0 / (k + max(rank, 0) + 1)


def _merge_unique_ordered(a: list[str] | None, b: list[str] | None) -> list[str]:
    """Merge two URI lists, preserving order and removing duplicates."""
    out: list[str] = []
    seen: set[str] = set()
    for src in ((a or []), (b or [])):
        for u in src:
            if not u:
                continue
            if u not in seen:
                seen.add(u)
                out.append(u)
    return out


def lexical_search(
    must_terms: list[str] | None = None,
    regexes: list[str] | None = None,
    path_like: str | None = None,
    k: int = 12,
    *,
    client: ClientAPI | None = None,
) -> list[dict[str, Any]]:
    """Query search_code collection using FTS ($contains), regex ($regex), and path filtering.

    Args:
        must_terms: Terms that must all be present (AND logic via $contains)
        regexes: Regex patterns, any of which can match (OR logic via $regex)
        path_like: Filter by substring match in source_path metadata
        k: Maximum number of results to return
        client: Optional ChromaDB client (uses default if not provided)

    Returns:
        List of result dicts with doc_id, source_path, score, page_uris, line_start,
        line_end, why, and normalized metadata dict (for symmetry with semantic_search).

    Filter semantics:
    - must_terms: ANDed via $contains (case-sensitive in Chroma)
    - regexes: ORed via $regex (honors pattern flags; embed (?i) for case-insensitive)
    - Both groups are ANDed together when both are present
    - path_like: Client-side substring filtering on metadata source_path. When used
      without terms/regex, we apply a small baseline (LEX_PATH_ONLY_BASELINE) so it
      contributes to hybrid fusion.
    - Local explainability uses case-insensitive counts for robustness (may differ
      from Chroma matching if user doesn't embed flags in regex patterns).
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
    # For path filtering, we need to fetch more results than k to account for
    # client-side filtering
    fetch_limit = (k * LEX_PATH_FETCH_MULTIPLIER) if pl else k

    # IDs are always returned, so we only need documents and metadatas in include
    res = code.get(
        where=where_meta,
        where_document=where_doc,
        limit=fetch_limit,
        include=["documents", "metadatas"],
    )

    # Client-side fallback if where_document filters returned empty
    # Some ChromaDB backends don't fully support $contains/$regex
    if not res.get("ids") and where_doc:
        # Fetch capped docs without document filters and filter client-side
        fallback_limit = min(5000, fetch_limit * 10)
        logger.debug(
            "Chroma where_document returned no results; falling back to broad fetch. "
            "fetch_limit=%d, fallback_limit=%d, terms=%s, regexes=%s, path_like=%s",
            fetch_limit,
            fallback_limit,
            terms,
            valid_regs,
            pl,
        )
        res = code.get(
            where=where_meta,  # Keep metadata filters if any
            limit=fallback_limit,
            include=["documents", "metadatas"],
        )
        # Note: Client-side filtering happens below in the iteration loop

    # Assemble results
    results: list[dict[str, Any]] = []
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
        line_start = meta_dict.get("line_start")
        line_end = meta_dict.get("line_end")

        # Track path match status for scoring/why
        path_matched = False
        # Client-side path filtering (since ChromaDB metadata doesn't support $contains)
        if pl and isinstance(source_path, str):
            path_matched = pl.lower() in source_path.lower()
            if not path_matched:
                continue  # Skip this result if path doesn't match

        # Build why signals and compute lexical score
        doc_str = str(doc) if doc else ""

        # Compute lexical score (0–1) and get metrics for why signals
        lex_score, metrics = _compute_lexical_score(doc_str, terms, compiled_patterns)

        # Enforce filter semantics: if terms or regexes were provided, ensure they're satisfied
        # This applies to both normal queries and fallback paths to ensure consistent behavior
        if (terms or compiled_patterns) and not _filters_satisfied(metrics, terms, compiled_patterns):
            continue  # Skip this candidate if filters aren't satisfied

        # Build why signals using metrics (avoid re-counting)
        why: list[str] = []
        for term, cnt in (metrics.get("per_term") or {}).items():
            if cnt > 0:
                why.append(f"matched term: '{term}' x{cnt}")

        for raw, cnt in (metrics.get("per_regex") or {}).items():
            if cnt > 0:
                why.append(f"matched regex: r'{raw}' x{cnt}")

        # Check for path match (add to why if path was filtered)
        if path_matched:
            why.append(f"path matched: '{pl}' in '{source_path}'")

        # If this is a path-only lexical query (no terms/regex provided) and it matched,
        # apply a small baseline so path contributes to hybrid fusion.
        if path_matched and not terms and not compiled_patterns:
            if lex_score < LEX_PATH_ONLY_BASELINE:
                lex_score = LEX_PATH_ONLY_BASELINE
            why.append(f"path-only match baseline applied: {LEX_PATH_ONLY_BASELINE:.2f}")

        # Compute tie-breaker keys for deterministic sorting
        any_term = any(c > 0 for c in (metrics.get("per_term") or {}).values())
        any_regex = any(c > 0 for c in (metrics.get("per_regex") or {}).values())
        cats = int(path_matched) + int(any_term) + int(any_regex)
        raw_hits = int(metrics.get("term_hits", 0)) + int(metrics.get("regex_hits", 0))
        doc_len = int(metrics.get("doc_len", 0))

        # Normalize metadata (same shape as semantic_search)
        metadata_norm = {
            "language": meta_dict.get("language") or meta_dict.get("lang"),
            "last_updated": meta_dict.get("last_updated"),
        }
        for key in NORMALIZED_META_LIST_KEYS:
            metadata_norm[key] = _parse_meta_list(meta_dict.get(key))

        page_uris = metadata_norm.get("page_uris", [])

        results.append(
            {
                "doc_id": str(doc_id),
                "source_path": source_path,
                "score": lex_score,
                "page_uris": page_uris,
                "line_start": line_start,
                "line_end": line_end,
                "why": why,
                "metadata": metadata_norm,
                # Ephemeral tie-breaker keys (will be stripped after sorting)
                "_cats": cats,
                "_raw_hits": raw_hits,
                "_doc_len": doc_len,
            }
        )

    # Rank by lexical score desc, then apply hierarchical tie-breakers
    results.sort(
        key=lambda r: (
            r.get("score", 0.0),
            r.get("_cats", 0),
            r.get("_raw_hits", 0),
            -r.get("_doc_len", 0),
        ),
        reverse=True,
    )
    results = results[:k]

    # Strip ephemeral tie-breaker keys
    for r in results:
        r.pop("_cats", None)
        r.pop("_raw_hits", None)
        r.pop("_doc_len", None)

    return results


def semantic_search(
    query: str,
    k: int = 12,
    *,
    client: ClientAPI | None = None,
    embedding_function: Callable[[Sequence[str]], list[list[float]]] | None = None,
) -> list[dict[str, Any]]:
    """Query search_summaries collection using semantic similarity via embeddings.

    Args:
        query: Natural-language query string. Empty or whitespace-only returns [].
        k: Number of results to return. k <= 0 returns [].
        client: Optional ChromaDB client (uses default if not provided)
        embedding_function: Optional callable to embed the query. If None, uses embed_texts.
            Useful for testing with deterministic embeddings.

    Returns:
        List of result dicts with doc_id, source_path, score, page_uris, line_start,
        line_end, why, and normalized metadata dict for downstream consumers.

        Note: page_uris appears both top-level (for convenience) and in metadata
        (for completeness). This is intentional duplication for UX.
    """
    q = (query or "").strip()
    if not q or k <= 0:
        return []

    summaries, _ = get_collections(client)

    # Embed query using provided function or default embed_texts
    try:
        vecs = embed_texts([q]) if embedding_function is None else embedding_function([q])
    except Exception as e:
        error_msg = str(e)
        if "OPENAI_API_KEY" in error_msg or "api key" in error_msg.lower():
            raise ValueError(
                "Failed to embed query: OPENAI_API_KEY not configured or invalid. "
                "Set OPENAI_API_KEY in environment or .env file."
            ) from e
        raise ValueError(f"Failed to embed query: {error_msg}") from e

    if not vecs:
        return []

    try:
        res = summaries.query(
            query_embeddings=[vecs[0]],
            n_results=k,
            include=["metadatas", "documents", "distances"],
        )
    except Exception as e:
        raise ValueError(
            f"Failed to query ChromaDB collection 'search_summaries': {str(e)}. "
            "Ensure summaries are indexed and the collection exists."
        ) from e

    ids0 = (res.get("ids") or [[]])[0]
    metas0 = (res.get("metadatas") or [[]])[0]
    dists0 = (res.get("distances") or [[]])[0]

    out: list[dict[str, Any]] = []
    for i in range(len(ids0)):
        meta = metas0[i] or {}
        doc_id = meta.get("doc_id") or ids0[i]
        source_path = meta.get("source_path")
        page_uris = _parse_meta_list(meta.get("page_uris"))

        dist = dists0[i] if i < len(dists0) else None
        score = _distance_to_score(dist)
        why = [f"semantic match to query: '{q}'"]
        if dist is not None:
            why.append(f"distance={dist:.3f}")

        # Normalize selected known list-like fields in metadata for consumers
        metadata_norm = {
            "language": meta.get("language") or meta.get("lang"),
            "last_updated": meta.get("last_updated"),
        }
        for key in NORMALIZED_META_LIST_KEYS:
            metadata_norm[key] = _parse_meta_list(meta.get(key))

        # Note: page_uris appears both top-level (for convenience) and in metadata (for completeness)
        out.append(
            {
                "doc_id": str(doc_id),
                "source_path": source_path,
                "score": score,
                "page_uris": page_uris,
                "line_start": None,
                "line_end": None,
                "why": why,
                "metadata": metadata_norm,
            }
        )

    return out


def hybrid_search(
    query: str,
    k: int = 12,
    *,
    must_terms: list[str] | None = None,
    regexes: list[str] | None = None,
    path_like: str | None = None,
    client: ClientAPI | None = None,
    embedding_function: Callable[[Sequence[str]], list[list[float]]] | None = None,
    w_semantic: float = 0.6,
    w_lexical: float = 0.4,
) -> list[dict[str, Any]]:
    """Hybrid search combining semantic and lexical channels using weighted-sum fusion.

    Supports three modes:
    - Semantic-only: query provided, no lexical filters
    - Lexical-only: lexical filters provided, no query
    - True hybrid: both query and filters provided (results fused via weighted sum)

    Args:
        query: Natural-language query for semantic search
        k: Maximum results to return
        must_terms: Terms that must all be present (AND logic)
        regexes: Regex patterns (OR logic)
        path_like: Filter by substring in source_path
        client: Optional ChromaDB client
        embedding_function: Optional embedding function for testing
        w_semantic: Weight for semantic channel (default 0.6)
        w_lexical: Weight for lexical channel (default 0.4)

    Returns:
        List of result dicts with doc_id, source_path, score (weighted sum),
        sem_score, lex_score, rrf_score (tie-breaker), page_uris, line_start,
        line_end, and why signals.

    Notes:
        - score = w_semantic * sem_score + w_lexical * lex_score (default 0.6/0.4)
        - rrf_score provided for tie-breaking and debugging
        - All scores in [0,1] range for consistency
        - Returns [] if k <= 0 or neither channel would run
        - Deduplication by doc_id (first occurrence per channel)
        - page_uris merged (union), line ranges prefer lexical, why signals concatenated
    """
    RRF_K = 60

    q = (query or "").strip()
    if k <= 0:
        return []

    # Determine which channels to run
    run_semantic = bool(q)
    run_lexical = bool(must_terms or regexes or path_like)

    if not run_semantic and not run_lexical:
        return []

    # Execute channels conditionally
    sem_results = semantic_search(q, k, client=client, embedding_function=embedding_function) if run_semantic else []
    lex_results = (
        lexical_search(must_terms=must_terms, regexes=regexes, path_like=path_like, k=k, client=client)
        if run_lexical
        else []
    )

    # Build rank maps (first occurrence per doc_id)
    sem_rank_by_doc: dict[str, int] = {}
    lex_rank_by_doc: dict[str, int] = {}
    sem_by_doc: dict[str, dict[str, Any]] = {}
    lex_by_doc: dict[str, dict[str, Any]] = {}

    for i, r in enumerate(sem_results):
        did = str(r.get("doc_id"))
        if did not in sem_rank_by_doc:
            sem_rank_by_doc[did] = i
            sem_by_doc[did] = r

    for i, r in enumerate(lex_results):
        did = str(r.get("doc_id"))
        if did not in lex_rank_by_doc:
            lex_rank_by_doc[did] = i
            lex_by_doc[did] = r

    # Fuse results with weighted sum + RRF tie-breaker
    fused: list[dict[str, Any]] = []
    for did in set(sem_by_doc) | set(lex_by_doc):
        sem_match = sem_by_doc.get(did)
        lex_match = lex_by_doc.get(did)

        # Compute RRF score (for tie-breaking)
        fused_rrf = _rrf_component(sem_rank_by_doc.get(did), RRF_K) + _rrf_component(lex_rank_by_doc.get(did), RRF_K)

        # Channel scores for weighted sum
        sem_score = float((sem_match or {}).get("score") or 0.0)
        lex_score = float((lex_match or {}).get("score") or 0.0)

        # Combined score: weighted sum if both present, else single-channel
        combined = w_semantic * sem_score + w_lexical * lex_score if sem_match and lex_match else sem_score or lex_score

        # Merge fields (prefer lexical for granular details)
        source_path = (lex_match or {}).get("source_path") or (sem_match or {}).get("source_path")
        page_uris = _merge_unique_ordered((lex_match or {}).get("page_uris"), (sem_match or {}).get("page_uris"))
        line_start = (lex_match or {}).get("line_start") or (sem_match or {}).get("line_start")
        line_end = (lex_match or {}).get("line_end") or (sem_match or {}).get("line_end")

        # Concatenate why signals
        why: list[str] = []
        if lex_match and isinstance(lex_match.get("why"), list):
            why.extend(lex_match["why"])
        if sem_match and isinstance(sem_match.get("why"), list):
            why.extend(sem_match["why"])

        fused.append(
            {
                "doc_id": did,
                "source_path": source_path,
                "score": combined,  # final weighted score (0–1)
                "sem_score": sem_score,  # for debugging/UX
                "lex_score": lex_score,  # for debugging/UX
                "rrf_score": fused_rrf,  # tie-break/info
                "page_uris": page_uris,
                "line_start": line_start,
                "line_end": line_end,
                "why": why,
            }
        )

    # Sort by combined score, break ties by RRF
    fused.sort(key=lambda r: (r.get("score", 0.0), r.get("rrf_score", 0.0)), reverse=True)
    return fused[:k]


__all__ = [
    "get_client",
    "get_collections",
    "upsert_summaries",
    "upsert_code_chunks",
    "lexical_search",
    "semantic_search",
    "hybrid_search",
]
