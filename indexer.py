from __future__ import annotations

from typing import Callable, Iterable, List, Mapping, Optional, Sequence, Tuple

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


__all__ = [
    "get_client",
    "get_collections",
    "upsert_summaries",
    "upsert_code_chunks",
]


