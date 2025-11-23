# API Agent Guide

⚠️ **Protocol Override**: Follow the [Operational Protocols in root AGENTS.md](../AGENTS.md) (tmux, Beads MCP) for all tasks in this directory.

This directory contains the FastAPI backend for Neumann. It exposes search capabilities and document metadata to the frontend.

## 1. Directory Structure

| Path | Purpose |
| :--- | :--- |
| `app.py` | Application factory and entry point (`create_app`). |
| `models.py` | Pydantic models for requests and responses. |
| `deps.py` | Dependency injection (settings, Chroma client). |
| `routes/` | Route handlers grouped by functionality. |
| `routes/search.py` | Search endpoints (lexical, semantic, hybrid). |
| `routes/docs.py` | Document browsing endpoints (list, pages, chunks). |

## 2. Key Components

### Application Factory
We use a factory pattern in `app.py` (`create_app()`) to create the FastAPI instance. This allows for better testing and configuration management.

### Dependency Injection
Dependencies are defined in `deps.py`. Common dependencies include:
- `get_settings()`: Returns the `Config` object.
- `get_chroma_client()`: Returns the `chromadb.PersistentClient`.

### Pydantic Models
All API contracts are defined in `models.py`.
- **Search Requests**: `LexicalSearchRequest`, `SemanticSearchRequest`, `HybridSearchRequest`.
- **Search Results**: `LexicalSearchResult`, `SemanticSearchResult`, `HybridSearchResult`.
- **Document Info**: `DocumentInfo`, `PageRecord`, `ChunkInfo`.

## 3. Endpoints

All endpoints are prefixed with `/api/v1`.

### Search (`routes/search.py`)
- `POST /api/v1/lexical`: Lexical search (FTS + regex).
- `POST /api/v1/semantic`: Semantic search (vector similarity).
- `POST /api/v1/hybrid`: Hybrid search (weighted sum + RRF).

### Documents (`routes/docs.py`)
- `GET /api/v1/`: List all indexed documents.
- `GET /api/v1/{doc_id}/pages`: Get pages manifest for a document.
- `GET /api/v1/{doc_id}/chunks`: Get text/code chunks for a document.

## 4. Development

### Running the Server
Use `uvicorn` to run the server locally:
```bash
# From project root
uvicorn api.app:app --reload --port 8000
```
Or use the `tmux` session as recommended in the root `AGENTS.md`.

### Testing
- **Unit Tests**: Add tests in `tests/api/`.
- **Manual Testing**: Use the Swagger UI at `http://localhost:8000/docs`.

## 5. Conventions
- **Error Handling**: Use `HTTPException` with appropriate status codes. Map upstream errors using `_map_upstream_exception` in `routes/search.py`.
- **Logging**: Use `logging.getLogger(__name__)`.
- **Type Hints**: Strictly enforce type hints for all route handlers and dependencies.
