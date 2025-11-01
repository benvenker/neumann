from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path
from typing import Callable, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

from config import config
from ids import make_doc_id_from_str
from models import FileSummary, SummaryFrontMatter

_EXT_TO_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".js": "javascript",
    ".md": "markdown",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
}


def generate_doc_id_from_path(source_path: str) -> str:
    """Generate doc_id using canonical ids.make_doc_id_from_str.

    Args:
        source_path: File path as string

    Returns:
        doc_id string with spaces replaced by underscores
    """
    return make_doc_id_from_str(source_path)


def detect_language_from_extension(source_path: str) -> str:
    return _EXT_TO_LANGUAGE.get(Path(source_path).suffix.lower(), "text")


def _default_llm_generator(prompt: str) -> str:
    """Fallback summary generator for environments without OpenAI during tests.

    Produces a deterministic ~210-word body to satisfy validators.
    """
    words = [f"summary{i}" for i in range(210)]
    return " ".join(words)


class LLMStructuredSummary(BaseModel):
    """Internal model for OpenAI structured output (not exported).

    This model describes the JSON schema returned by OpenAI's structured output API.
    The fields are mapped to SummaryFrontMatter and FileSummary in summarize_file().
    """

    summary_md: str = Field(..., description="200-400 word markdown body")
    product_tags: List[str] = Field(default_factory=list)
    key_topics: List[str] = Field(default_factory=list)
    api_symbols: List[str] = Field(default_factory=list)
    related_files: List[str] = Field(default_factory=list)
    suggested_queries: List[str] = Field(default_factory=list)


def _build_system_prompt() -> str:
    """Build the system prompt for OpenAI structured summarization."""
    return (
        "You are a retrieval-oriented summarizer. Produce a concise 200-400 word markdown summary "
        "covering purpose, key functionality, patterns, API symbols, and related context. "
        "Also provide metadata: product_tags, key_topics, api_symbols, related_files, suggested_queries."
    )


def _build_user_prompt(source_path: str, language: str, text: str) -> str:
    """Build the user prompt for OpenAI structured summarization."""
    return f"""Source: {source_path}
Language: {language}

Please summarize this file. Your response must be 200-400 words.

Return your response as a JSON object with exactly these fields:
- summary_md: string (the 200-400 word markdown summary)
- product_tags: array of strings (optional)
- key_topics: array of strings (optional)
- api_symbols: array of strings (optional)
- related_files: array of strings (optional)
- suggested_queries: array of strings (optional)

```{language}
{text}
```
"""


def _openai_structured_summary(
    source_path: str,
    language: str,
    text: str,
    *,
    model: str = "gpt-4o-mini",
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> LLMStructuredSummary:
    """Call OpenAI with structured output and retry on rate limits/timeouts.

    Args:
        source_path: Path to the source file
        language: Detected language (e.g., 'python', 'markdown')
        text: File content to summarize
        model: OpenAI model to use (default: gpt-4o-mini)
        max_retries: Maximum number of retry attempts for rate limits and timeouts
        base_delay: Base delay in seconds for exponential backoff

    Returns:
        LLMStructuredSummary with summary_md and metadata fields

    Raises:
        ValidationError: If OPENAI_API_KEY is not configured
        APIError: For API errors after retries exhausted
        APITimeoutError: For timeout errors after retries
    """
    from openai import APIError, APITimeoutError, OpenAI, RateLimitError

    config.require_openai()
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "LLMStructuredSummary",
            "schema": LLMStructuredSummary.model_json_schema(),
            "strict": True,
        },
    }

    system_prompt = _build_system_prompt()
    user_prompt = _build_user_prompt(source_path, language, text)

    # Retry loop with exponential backoff
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            # Use Chat Completions API with structured outputs
            # Try json_schema first (preferred, strict validation)
            # Note: json_schema requires specific models (e.g., gpt-4o, gpt-4-turbo)
            # For gpt-4o-mini, fall back to json_object
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format=response_format,
                )
            except APIError as schema_error:
                # Log and fall back to json_object if json_schema not supported
                error_msg = str(schema_error)
                if hasattr(schema_error, "response"):
                    try:
                        error_body = schema_error.response.json() if hasattr(schema_error.response, "json") else {}
                        error_msg = error_body.get("error", {}).get("message", error_msg)
                    except Exception:
                        pass
                # Fallback to json_object format (less strict, but more compatible)
                logger.debug("Falling back from response_format=json_schema to json_object: %s", error_msg)
                resp = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
            content_text = resp.choices[0].message.content

            # Parse and validate
            if content_text is None:
                raise ValueError("OpenAI returned empty content")
            
            try:
                payload = json.loads(content_text)
            except json.JSONDecodeError as e:
                raise ValueError(
                    "OpenAI did not return valid JSON. This may indicate the model failed to follow "
                    "the structured output format. Try using a model that supports json_schema response_format "
                    "or ensure the model follows the JSON instructions strictly."
                ) from e
            
            # Handle case where OpenAI wraps fields in 'metadata' key (with json_object format)
            if "metadata" in payload and isinstance(payload["metadata"], dict):
                # Unwrap metadata fields and merge with summary_md if present at top level
                metadata = payload["metadata"]
                if "summary_md" in payload:
                    payload = {**metadata, "summary_md": payload["summary_md"]}
                else:
                    # If summary_md is in metadata, use it; otherwise try to extract
                    if "summary_md" in metadata:
                        payload = metadata
                    else:
                        # Fallback: create summary_md from available content
                        payload = {**metadata, "summary_md": payload.get("summary", "Summary not provided.")}
            
            return LLMStructuredSummary.model_validate(payload)

        except RateLimitError as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                delay = base_delay * (2**attempt) * (1.0 + random.uniform(0.0, 0.1))
                time.sleep(delay)
            else:
                raise

        except APITimeoutError as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff with jitter
                delay = base_delay * (2**attempt) * (1.0 + random.uniform(0.0, 0.1))
                time.sleep(delay)
            else:
                raise

        except APIError as e:
            # Don't retry on other API errors (e.g., invalid API key, malformed request)
            # Log the error details before re-raising
            error_msg = str(e)
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_body = e.response.json() if hasattr(e.response, "json") else {}
                    error_msg = error_body.get("error", {}).get("message", error_msg)
                except Exception:
                    pass
            raise APIError(f"OpenAI API error: {error_msg}") from e

        except Exception:
            # Unexpected errors: re-raise
            raise

    # Should never reach here, but mypy requires it
    assert last_error is not None
    raise last_error


def summarize_file(
    source_path: str,
    text: str,
    *,
    llm_generate_markdown: Optional[Callable[[str], str]] = None,
) -> FileSummary:
    """Summarize a file into the FileSummary schema.

    Args:
        source_path: Path to the source file
        text: File content to summarize
        llm_generate_markdown: Optional callable that returns a markdown body (200–400 words).
            If None, uses OpenAI structured output. Tests can inject custom generators.

    Returns:
        FileSummary with validated front_matter and summary_md

    Raises:
        ValidationError: If summary_md word count is out of range (200-400 words)
    """
    doc_id = generate_doc_id_from_path(source_path)
    language = detect_language_from_extension(source_path)

    if llm_generate_markdown is not None:
        # Test/mock path - use callback
        generator = llm_generate_markdown
        system_prompt = (
            "You are a retrieval-oriented summarizer. Produce a concise 200-400 word markdown summary "
            "covering purpose, key functionality, patterns, API symbols, and related context."
        )
        body_md = generator(system_prompt + "\n\n" + text)
        front_matter = SummaryFrontMatter(
            doc_id=doc_id,
            source_path=source_path,
            language=language,
        )
    else:
        # Production path - use OpenAI structured output
        llm_out = _openai_structured_summary(source_path, language, text)
        front_matter = SummaryFrontMatter(
            doc_id=doc_id,
            source_path=source_path,
            language=language,
            product_tags=llm_out.product_tags,
            key_topics=llm_out.key_topics,
            api_symbols=llm_out.api_symbols,
            related_files=llm_out.related_files,
            suggested_queries=llm_out.suggested_queries,
        )
        body_md = llm_out.summary_md

    return FileSummary(front_matter=front_matter, summary_md=body_md)


def save_summary_md(target_path: str | Path, summary: FileSummary) -> Path:
    target = Path(target_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = summary.to_yaml()
    target.write_text(content, encoding="utf-8")
    return target


__all__ = [
    "summarize_file",
    "save_summary_md",
    "generate_doc_id_from_path",
    "detect_language_from_extension",
]


