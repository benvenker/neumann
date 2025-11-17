from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Centralized, type-safe configuration loaded from environment variables.

    Uses pydantic-settings to support .env files and runtime validation.
    """

    # Asset serving
    ASSET_BASE_URL: str = Field(  # e.g., http://127.0.0.1:8000
        default="http://127.0.0.1:8000",
        description="Base URL used to build public URIs for rendered page images.",
    )

    # Storage/DB paths
    CHROMA_PATH: str = Field(
        default="./chroma_data",
        description="Filesystem path for ChromaDB persistent storage.",
    )

    OUTPUT_DIR: str = Field(
        default="./out",
        description="Filesystem path for rendered output (pages/tiles).",
    )

    # API configuration
    API_CORS_ORIGINS: list[str] = Field(
        default_factory=list,
        description="Allowed CORS origins for FastAPI (comma-separated env or JSON list).",
    )

    # OpenAI
    OPENAI_API_KEY: str | None = Field(
        default=None,
        description="API key for OpenAI (required for summaries/embeddings).",
    )

    SUMMARY_MODEL: str = Field(
        default="gpt-4.1-mini",
        description="OpenAI model used for summary generation. If the model does not support response_format=json_schema, the summarizer falls back to response_format=json_object automatically.",
    )

    # Chunking
    LINES_PER_CHUNK: int = Field(default=180, ge=1, le=10000)
    OVERLAP: int = Field(default=30, ge=0, le=1000)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("ASSET_BASE_URL")
    @classmethod
    def normalize_asset_base_url(cls, value: str) -> str:
        value = value.strip()
        if value.endswith("/"):
            value = value[:-1]
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("ASSET_BASE_URL must be a valid http(s) URL")
        return value

    @field_validator("OVERLAP")
    @classmethod
    def validate_overlap(cls, v: int, info):  # type: ignore[no-redef]
        # Ensure overlap is strictly less than LINES_PER_CHUNK when both available
        # (pydantic v2 provides access to field values via info.data)
        lines_per_chunk = info.data.get("LINES_PER_CHUNK") if hasattr(info, "data") else None
        if isinstance(lines_per_chunk, int) and v >= lines_per_chunk:
            raise ValueError("OVERLAP must be less than LINES_PER_CHUNK")
        return v

    @field_validator("CHROMA_PATH")
    @classmethod
    def normalize_chroma_path(cls, v: str) -> str:
        """
        Normalize CHROMA_PATH to an absolute path.

        Relative paths are resolved from the project root (where config.py lives),
        not from the current working directory. This ensures CLI and API processes
        use the same ChromaDB location regardless of where they're started from.

        Examples:
            - "./chroma_data" → "/Users/ben/code/neumann/chroma_data"
            - "~/data/chroma" → "/Users/ben/data/chroma"
            - "/abs/path" → "/abs/path"
        """
        path = Path(v).expanduser()  # Handle ~ expansion

        if not path.is_absolute():
            # Resolve relative paths from project root (where this file lives)
            project_root = Path(__file__).parent
            path = (project_root / path).resolve()
        else:
            path = path.resolve()

        return str(path)

    @field_validator("API_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):  # type: ignore[no-redef]
        """
        Accept list[str], JSON array string, or comma-separated string.

        Examples:
            - None or "" → []
            - ["http://localhost:3000"] → ["http://localhost:3000"]
            - '["http://localhost:3000"]' → ["http://localhost:3000"]
            - "http://localhost:3000,http://127.0.0.1:5173" → ["http://localhost:3000", "http://127.0.0.1:5173"]
        """
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return [str(s).strip() for s in v if str(s).strip()]
        if isinstance(v, str):
            s = v.strip()
            # Try JSON parsing first if it looks like a JSON array
            if s.startswith("["):
                import json

                try:
                    arr = json.loads(s)
                    return [str(x).strip() for x in arr if str(x).strip()]
                except Exception:
                    # Fall back to comma-separated parsing
                    pass
            # Comma-separated parsing
            return [p.strip() for p in s.split(",") if p.strip()]
        # Fallback: coerce single value to list
        return [str(v).strip()]

    # Convenience helpers
    @property
    def chroma_path(self) -> Path:
        return Path(self.CHROMA_PATH)

    @property
    def output_path(self) -> Path:
        return Path(self.OUTPUT_DIR)

    @property
    def has_openai_key(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    def require_openai(self) -> None:
        """Raise a helpful error if OpenAI is not configured."""
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for summaries/embeddings")


# Eagerly load configuration at import time for convenience across modules
config = Config()
