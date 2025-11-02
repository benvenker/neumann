"""Text embeddings using OpenAI's API.

Provides embed_texts() function for generating 1536-dimensional vectors from text.
Supports batch processing up to OpenAI's 2048-item limit with automatic rate limiting.
"""

from __future__ import annotations

import random
import time

from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from config import config

# Expected embedding dimensions for known models
EXPECTED_DIMS = {"text-embedding-3-small": 1536}


def embed_texts(
    texts: list[str],
    model: str = "text-embedding-3-small",
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> list[list[float]]:
    """Generate embeddings for a list of texts using OpenAI's API.

    Args:
        texts: List of texts to embed (max 2048 per API call)
        model: OpenAI embedding model (default: text-embedding-3-small)
        max_retries: Maximum number of retry attempts for rate limits and timeouts
        base_delay: Base delay in seconds for exponential backoff

    Returns:
        List of embedding vectors, one per input text. Returns empty list if texts is empty.

        Raises:
        APIError: For API errors after retries exhausted
        APITimeoutError: For timeout errors after retries
        ValueError: For dimension mismatches or count mismatches
        Exception: For unexpected errors

    Note:
        - Automatically handles batching for large inputs (max 2048 per batch)
        - Implements exponential backoff with jitter for rate limiting
        - Requires OPENAI_API_KEY to be set in config
        - Dimension validation is enforced for known models (e.g., text-embedding-3-small)
    """
    if not texts:
        return []

    config.require_openai()

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # OpenAI limit is 2048 texts per request
    batch_size = 2048

    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = _embed_batch_with_retry(client, batch, model, max_retries=max_retries, base_delay=base_delay)
        all_embeddings.extend(embeddings)

    return all_embeddings


def _embed_batch_with_retry(
    client: OpenAI, batch: list[str], model: str, max_retries: int = 3, base_delay: float = 1.0
) -> list[list[float]]:
    """Embed a batch of texts with exponential backoff on rate limit errors.

    Args:
        client: OpenAI client instance
        batch: List of texts to embed (max 2048)
        model: OpenAI embedding model
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff

    Returns:
        List of embedding vectors

    Raises:
        APIError: For API errors after retries exhausted
        APITimeoutError: For timeout errors after retries
    """
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(model=model, input=batch)

            # Verify response count matches input count
            if len(response.data) != len(batch):
                raise ValueError(f"OpenAI embeddings count mismatch: expected {len(batch)}, got {len(response.data)}")

            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]

            # Verify dimension if model is in EXPECTED_DIMS
            if model in EXPECTED_DIMS and embeddings:
                expected_dim = EXPECTED_DIMS[model]
                if any(len(vec) != expected_dim for vec in embeddings):
                    raise ValueError(f"Expected {expected_dim} dimensions for {model}, got mismatch")

            return embeddings

        except RateLimitError as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff with jitter: wait longer on each retry
                delay = base_delay * (2**attempt) * (1.0 + random.uniform(0.0, 0.1))
                time.sleep(delay)
            else:
                raise

        except APITimeoutError as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff with jitter: wait a bit and retry on timeout
                delay = base_delay * (2**attempt) * (1.0 + random.uniform(0.0, 0.1))
                time.sleep(delay)
            else:
                raise

        except APIError:
            # Don't retry on other API errors (e.g., invalid API key, malformed request)
            raise

        except Exception:
            # Unexpected errors: re-raise
            raise

    # Should never reach here, but mypy requires it
    assert last_error is not None
    raise last_error
