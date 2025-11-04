# API Testing Quickstart

## 1. One-Time Setup

```bash
# Make sure you've run ingestion at least once
neumann ingest --input-dir ./docs --out-dir ./out

# Add your OpenAI key to .env (preferred) or prefix commands when needed
# Example one-off invocation:
# OPENAI_API_KEY="sk-..." python tests/manual/test_api_search_endpoints.py
```

## 2. Start API Server

```bash
# Option A: In tmux (recommended)
tmux new -s neumann-api
uvicorn api.app:create_app --factory --reload --port 8001
# Press Ctrl+b, d to detach

# Option B: Regular terminal
uvicorn api.app:create_app --factory --reload --port 8001
```

## 3. Run Tests

In a separate terminal:

```bash
# Quick smoke test (30 seconds)
python tests/manual/test_api_quick.py

# Full test suite (2-3 minutes)
python tests/manual/test_api_search_endpoints.py

# Without semantic tests
python tests/manual/test_api_search_endpoints.py --skip-semantic
```

## 4. Manual curl Testing

```bash
# Test lexical search
curl -s http://127.0.0.1:8001/api/v1/search/lexical \
  -H 'Content-Type: application/json' \
  -d '{"must_terms": ["search", "chroma"], "k": 3}' | jq .

# Test semantic search (requires OPENAI_API_KEY)
curl -s http://127.0.0.1:8001/api/v1/search/semantic \
  -H 'Content-Type: application/json' \
  -d '{"query": "How does vector search work?", "k": 3}' | jq .

# Test hybrid search
curl -s http://127.0.0.1:8001/api/v1/search/hybrid \
  -H 'Content-Type: application/json' \
  -d '{"query": "indexing", "must_terms": ["chroma"], "k": 3}' | jq .
```

## 5. View API Docs

Open in browser: http://127.0.0.1:8001/docs

Interactive Swagger UI with all endpoints and schemas.
