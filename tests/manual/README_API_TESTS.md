# Manual API Tests

These scripts provide step-by-step manual verification of the FastAPI search endpoints (nm-3573.2).

## Prerequisites

1. **Ingest content first** - ChromaDB must contain indexed data:
   ```bash
   neumann ingest --input-dir ./docs --out-dir ./out
   ```

2. **Start the API server** in a separate terminal/tmux session:
   ```bash
   # Terminal 1: Start API server
   tmux new -s neumann-api
   uvicorn api.app:create_app --factory --reload --port 8001
   ```

3. **Configure `OPENAI_API_KEY`** (required for semantic/hybrid tests):
   - Preferred: add the key to your project `.env` (or use `direnv`) so pydantic-settings loads it automatically.
   - One-off: prefix a command instead of exporting globally, e.g.
     ```bash
     OPENAI_API_KEY="sk-..." python tests/manual/test_api_search_endpoints.py
     ```
   > Reminder: tmux sessions inherit the environment present when they are created. Create a new `neumann-*` session after updating `.env` so the key is available inside the pane.

## Test Scripts

### Quick Smoke Test (`test_api_quick.py`)

**Purpose:** Fast sanity check that all endpoints are working.

**Usage:**
```bash
python tests/manual/test_api_quick.py
```

**What it tests:**
- Health endpoint is reachable
- Each search endpoint returns 200 OK
- Error cases return appropriate status codes
- Basic response structure validation

**Output:**
```
API Quick Smoke Test
========================================
Testing /healthz... ✓
Testing /api/v1/search/lexical... ✓ (3 results)
Testing /api/v1/search/semantic... ✓ (5 results)
Testing /api/v1/search/hybrid... ✓ (4 results)
Testing error cases... ✓

✓ All quick tests passed!
```

### Comprehensive Test Suite (`test_api_search_endpoints.py`)

**Purpose:** Detailed validation of all endpoints with various scenarios and edge cases.

**Usage:**
```bash
# Full test suite (requires OPENAI_API_KEY)
python tests/manual/test_api_search_endpoints.py

# Skip semantic tests (no API key needed)
python tests/manual/test_api_search_endpoints.py --skip-semantic

# Use different port
python tests/manual/test_api_search_endpoints.py --port 8080
```

**What it tests:**
- **Test 1:** Lexical search with must_terms
- **Test 2:** Lexical search with regex patterns
- **Test 3:** Lexical search with path filtering
- **Test 4:** Error case - no filters provided (400)
- **Test 5:** Semantic search with natural language query
- **Test 6:** Error case - empty semantic query (422)
- **Test 7:** Hybrid search with both channels active
- **Test 8:** Hybrid search with lexical-only
- **Test 9:** Error case - no channels active (422)
- **Test 10:** Error case - invalid k value (422)

**Output:**
```
FastAPI Search Endpoints - Manual Test Suite
============================================================
Base URL: http://127.0.0.1:8001
Skip semantic: False

Checking server health at http://127.0.0.1:8001...
✓ Server is healthy

============================================================
TEST 1: Lexical Search - Basic term search
============================================================
POST http://127.0.0.1:8001/api/v1/search/lexical
Payload: {
  "must_terms": ["chroma", "collection"],
  "k": 5
}
Status: 200
✓ Received 3 results

Lexical Result:
  doc_id: indexer_py
  source_path: /Users/ben/code/neumann/indexer.py
  score: 0.8750
  line_range: 50-230
  page_uris: 2 pages
  why signals (3):
    - matched term: chroma (2 times, capped at 3)
    - matched term: collection (3 times, capped at 3)
    - lexical score computed via weighted categories

...

============================================================
TEST SUMMARY: 10/10 passed
============================================================
✓ All tests passed!
```

## Running Tests Step-by-Step

### Option 1: tmux Workflow (Recommended)

```bash
# Terminal 1: Start API server
tmux new -s neumann-api
uvicorn api.app:create_app --factory --reload --port 8001

# Detach: Ctrl+b, d

# Terminal 2: Run tests
python tests/manual/test_api_quick.py

# Or full suite:
python tests/manual/test_api_search_endpoints.py

# Reattach to API server to see logs:
tmux attach -t neumann-api
```

### Option 2: Separate Terminals

```bash
# Terminal 1:
uvicorn api.app:create_app --factory --reload --port 8001

# Terminal 2:
python tests/manual/test_api_search_endpoints.py
```

## Troubleshooting

### "Cannot connect to server"

**Problem:** API server is not running or on different port.

**Solution:**
```bash
# Check if server is running
curl http://127.0.0.1:8001/healthz

# Start server if needed
uvicorn api.app:create_app --factory --reload --port 8001
```

### "OPENAI_API_KEY is required"

**Problem:** Semantic/hybrid tests need OpenAI API key.

**Solution 1:** Set the key:
```bash
export OPENAI_API_KEY="sk-..."
```

**Solution 2:** Skip semantic tests:
```bash
python tests/manual/test_api_search_endpoints.py --skip-semantic
```

### "No results returned"

**Problem:** ChromaDB is empty or not populated.

**Solution:** Run ingestion first:
```bash
neumann ingest --input-dir ./docs --out-dir ./out
```

### Import errors

**Problem:** Python can't find modules.

**Solution:** Activate virtual environment:
```bash
source .venv/bin/activate
# Or with direnv:
direnv allow
```

## What Gets Tested

### Request Validation
✓ Empty queries rejected (semantic)  
✓ No filters rejected (lexical)  
✓ Invalid k values rejected (k <= 0)  
✓ No channels rejected (hybrid)  
✓ List normalization (comma-separated strings → lists)

### Response Structure
✓ Lexical results: `doc_id`, `score`, `page_uris`, `why`, `metadata`  
✓ Semantic results: Same as lexical  
✓ Hybrid results: Adds `sem_score`, `lex_score`, `rrf_score`  

### Error Handling
✓ 400 Bad Request for missing API key  
✓ 400 Bad Request for invalid client inputs  
✓ 422 Validation Error for Pydantic constraint violations  
✓ 502 Bad Gateway for upstream ChromaDB failures  

### Search Functionality
✓ FTS substring matching (must_terms)  
✓ Regex pattern matching  
✓ Path filtering (path_like)  
✓ Semantic vector similarity  
✓ Hybrid weighted fusion (semantic + lexical)  
✓ Lexical-only hybrid (w_semantic=0)  

## Next Steps

After manual verification passes:
1. Consider adding automated API integration tests under `tests/api/`
2. Add OpenAPI schema validation tests
3. Add performance/load testing for production readiness
4. Consider contract tests if UI clients are added
