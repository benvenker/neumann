from collections.abc import Sequence
from pathlib import Path

from backend.indexer import get_client, get_collections, upsert_code_chunks, upsert_summaries


def test_client_initialization(tmp_path: Path) -> None:
    client = get_client(str(tmp_path / "chroma"))
    # Creating a collection implicitly verifies client works
    summaries, code = get_collections(client)
    assert summaries is not None and code is not None


def test_collections_created(tmp_path: Path) -> None:
    client = get_client(str(tmp_path / "chroma"))
    summaries, code = get_collections(client)
    names = {summaries.name, code.name}
    assert {"search_summaries", "search_code"} <= names


def test_upsert_summaries_with_mock_embeddings(tmp_path: Path) -> None:
    client = get_client(str(tmp_path / "chroma"))

    def fake_embed(texts: Sequence[str]) -> list[list[float]]:
        return [[float(i % 3) for i in range(8)] for _ in texts]

    count = upsert_summaries(
        [
            {"id": "a", "document": "alpha", "metadata": {"doc_id": "d1"}},
            {"id": "b", "document": "beta", "metadata": {"doc_id": "d2"}},
        ],
        client=client,
        embedding_function=fake_embed,
    )
    assert count == 2


def test_upsert_code_chunks(tmp_path: Path) -> None:
    client = get_client(str(tmp_path / "chroma"))
    count = upsert_code_chunks(
        [
            {"id": "1", "document": "print('x')", "metadata": {"lang": "python"}},
            {"id": "2", "document": "console.log('y')", "metadata": {"lang": "js"}},
        ],
        client=client,
    )
    assert count == 2


def test_persistence_across_restarts(tmp_path: Path) -> None:
    store = tmp_path / "chroma"
    c1 = get_client(str(store))
    upsert_code_chunks(
        [{"id": "p", "document": "persist", "metadata": {"ok": True}}],
        client=c1,
    )
    # Re-open client and ensure existing collections are accessible
    c2 = get_client(str(store))
    summaries, code = get_collections(c2)
    assert summaries.name == "search_summaries"
    assert code.name == "search_code"
