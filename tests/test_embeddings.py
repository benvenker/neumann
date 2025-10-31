"""Unit tests for embeddings module."""

import importlib
from unittest.mock import MagicMock, patch

import pytest
from openai import APIError, APITimeoutError, OpenAI, RateLimitError

import embeddings


def reload_embeddings_module():
    """Reload embeddings module to reset any cached state."""
    import sys

    sys.modules.pop("embeddings", None)
    return importlib.import_module("embeddings")


def test_embed_single_text():
    """Test embedding a single text."""
    # Mock OpenAI client
    mock_client = MagicMock(spec=OpenAI)
    mock_embeddings_create = MagicMock()

    mock_response = MagicMock()
    mock_embedding_obj = MagicMock()
    mock_embedding_obj.embedding = [0.1] * 1536  # 1536-dim vector
    mock_response.data = [mock_embedding_obj]
    mock_embeddings_create.return_value = mock_response

    mock_client.embeddings.create = mock_embeddings_create

    with patch("embeddings.OpenAI", return_value=mock_client), patch("embeddings.config") as mock_config:
        mock_config.require_openai = MagicMock()
        mock_config.OPENAI_API_KEY = "test-key"

        result = embeddings.embed_texts(["Hello, world!"])

        assert len(result) == 1
        assert len(result[0]) == 1536
        assert all(isinstance(x, float) for x in result[0])


def test_embed_batch():
    """Test embedding a batch of 10 texts."""
    # Mock OpenAI client
    mock_client = MagicMock(spec=OpenAI)
    mock_embeddings_create = MagicMock()

    # Create mock response with 10 embeddings
    mock_response = MagicMock()
    mock_response.data = []
    for _ in range(10):
        mock_embedding_obj = MagicMock()
        mock_embedding_obj.embedding = [0.1] * 1536
        mock_response.data.append(mock_embedding_obj)

    mock_embeddings_create.return_value = mock_response

    mock_client.embeddings.create = mock_embeddings_create

    with patch("embeddings.OpenAI", return_value=mock_client), patch("embeddings.config") as mock_config:
        mock_config.require_openai = MagicMock()
        mock_config.OPENAI_API_KEY = "test-key"

        texts = [f"Text {i}" for i in range(10)]
        result = embeddings.embed_texts(texts)

        assert len(result) == 10
        assert all(len(emb) == 1536 for emb in result)
        # Should only call API once (all in same batch)
        assert mock_embeddings_create.call_count == 1


def test_vector_dimension_is_1536():
    """Test that all embeddings have exactly 1536 dimensions."""
    mock_client = MagicMock(spec=OpenAI)
    mock_embeddings_create = MagicMock()

    # Return 1537 dimensions to test validation
    mock_response = MagicMock()
    mock_embedding_obj = MagicMock()
    mock_embedding_obj.embedding = [0.1] * 1537  # Wrong dimension!
    mock_response.data = [mock_embedding_obj]
    mock_embeddings_create.return_value = mock_response

    mock_client.embeddings.create = mock_embeddings_create

    with patch("embeddings.OpenAI", return_value=mock_client), patch("embeddings.config") as mock_config:
        mock_config.require_openai = MagicMock()
        mock_config.OPENAI_API_KEY = "test-key"

        with pytest.raises(ValueError, match="Expected 1536 dimensions"):
            embeddings.embed_texts(["test"])


def test_handles_rate_limit_errors():
    """Test that rate limit errors trigger retry with exponential backoff."""
    mock_client = MagicMock(spec=OpenAI)
    mock_embeddings_create = MagicMock()

    # First call: rate limit error
    # Second call: success
    mock_response = MagicMock()
    mock_embedding_obj = MagicMock()
    mock_embedding_obj.embedding = [0.1] * 1536
    mock_response.data = [mock_embedding_obj]

    # Need to provide response parameter (httpx.Response mock)
    mock_http_response = MagicMock()
    mock_embeddings_create.side_effect = [RateLimitError("Rate limit", response=mock_http_response, body=None), mock_response]

    mock_client.embeddings.create = mock_embeddings_create

    with patch("embeddings.OpenAI", return_value=mock_client), patch("embeddings.config") as mock_config:
        mock_config.require_openai = MagicMock()
        mock_config.OPENAI_API_KEY = "test-key"

        # Mock time.sleep to avoid waiting
        with patch("embeddings.time.sleep"):
            result = embeddings.embed_texts(["test"])

            assert len(result) == 1
            # Should have retried (2 calls total)
            assert mock_embeddings_create.call_count == 2


def test_handles_timeout_errors():
    """Test that timeout errors trigger retry."""
    mock_client = MagicMock(spec=OpenAI)
    mock_embeddings_create = MagicMock()

    # First call: timeout
    # Second call: success
    mock_response = MagicMock()
    mock_embedding_obj = MagicMock()
    mock_embedding_obj.embedding = [0.1] * 1536
    mock_response.data = [mock_embedding_obj]

    # APITimeoutError takes request parameter (httpx.Request mock)
    mock_http_request = MagicMock()
    mock_embeddings_create.side_effect = [APITimeoutError(mock_http_request), mock_response]

    mock_client.embeddings.create = mock_embeddings_create

    with patch("embeddings.OpenAI", return_value=mock_client), patch("embeddings.config") as mock_config:
        mock_config.require_openai = MagicMock()
        mock_config.OPENAI_API_KEY = "test-key"

        with patch("embeddings.time.sleep"):
            result = embeddings.embed_texts(["test"])

            assert len(result) == 1
            assert mock_embeddings_create.call_count == 2


def test_handles_api_errors():
    """Test that API errors (other than rate limit/timeout) are raised immediately."""
    mock_client = MagicMock(spec=OpenAI)
    mock_embeddings_create = MagicMock()

    # Raise API error (e.g., invalid API key)
    mock_http_request = MagicMock()
    mock_embeddings_create.side_effect = APIError(
        "Invalid API key", request=mock_http_request, body=None
    )

    mock_client.embeddings.create = mock_embeddings_create

    with patch("embeddings.OpenAI", return_value=mock_client), patch("embeddings.config") as mock_config:
        mock_config.require_openai = MagicMock()
        mock_config.OPENAI_API_KEY = "test-key"

        with pytest.raises(APIError):
            embeddings.embed_texts(["test"])

        # Should not retry on API errors
        assert mock_embeddings_create.call_count == 1


def test_empty_list_returns_empty():
    """Test that embedding an empty list returns empty list."""
    with patch("embeddings.config") as mock_config:
        mock_config.require_openai = MagicMock()

        result = embeddings.embed_texts([])

        assert result == []


def test_large_batch_splits_automatically():
    """Test that batches larger than 2048 are split automatically."""
    mock_client = MagicMock(spec=OpenAI)
    mock_embeddings_create = MagicMock()

    # Create mock responses for 2 batches
    mock_response_1 = MagicMock()
    mock_response_1.data = []
    for _ in range(2048):
        mock_embedding_obj = MagicMock()
        mock_embedding_obj.embedding = [0.1] * 1536
        mock_response_1.data.append(mock_embedding_obj)

    mock_response_2 = MagicMock()
    mock_response_2.data = []
    for _ in range(500):
        mock_embedding_obj = MagicMock()
        mock_embedding_obj.embedding = [0.1] * 1536
        mock_response_2.data.append(mock_embedding_obj)

    mock_embeddings_create.side_effect = [mock_response_1, mock_response_2]
    mock_client.embeddings.create = mock_embeddings_create

    with patch("embeddings.OpenAI", return_value=mock_client), patch("embeddings.config") as mock_config:
        mock_config.require_openai = MagicMock()
        mock_config.OPENAI_API_KEY = "test-key"

        # Create 2548 texts (should split into 2 batches)
        texts = [f"Text {i}" for i in range(2548)]
        result = embeddings.embed_texts(texts)

        assert len(result) == 2548
        # Should have called API twice
        assert mock_embeddings_create.call_count == 2

