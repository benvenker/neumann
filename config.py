from __future__ import annotations

from pathlib import Path

from pydantic import AnyHttpUrl, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Centralized, type-safe configuration loaded from environment variables.

    Uses pydantic-settings to support .env files and runtime validation.
    """

    # Asset serving
    ASSET_BASE_URL: AnyHttpUrl = Field(  # e.g., http://127.0.0.1:8000
        default="http://127.0.0.1:8000",
        description="Base URL used to build public URIs for rendered page images.",
    )

    # Storage/DB paths
    CHROMA_PATH: str = Field(
        default="./chroma_data",
        description="Filesystem path for ChromaDB persistent storage.",
    )

    # OpenAI
    OPENAI_API_KEY: str | None = Field(
        default=None,
        description="API key for OpenAI (required for summaries/embeddings).",
    )

    # Chunking
    LINES_PER_CHUNK: int = Field(default=180, ge=1, le=10000)
    OVERLAP: int = Field(default=30, ge=0, le=1000)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("OVERLAP")
    @classmethod
    def validate_overlap(cls, v: int, info):  # type: ignore[no-redef]
        # Ensure overlap is strictly less than LINES_PER_CHUNK when both available
        # (pydantic v2 provides access to field values via info.data)
        lines_per_chunk = info.data.get("LINES_PER_CHUNK") if hasattr(info, "data") else None
        if isinstance(lines_per_chunk, int) and v >= lines_per_chunk:
            raise ValueError("OVERLAP must be less than LINES_PER_CHUNK")
        return v

    # Convenience helpers
    @property
    def chroma_path(self) -> Path:
        return Path(self.CHROMA_PATH)

    @property
    def has_openai_key(self) -> bool:
        return bool(self.OPENAI_API_KEY)

    def require_openai(self) -> None:
        """Raise a helpful error if OpenAI is not configured."""
        if not self.OPENAI_API_KEY:
            raise ValidationError(
                [
                    {
                        "loc": ("OPENAI_API_KEY",),
                        "msg": "OPENAI_API_KEY is required for summaries/embeddings",
                        "type": "value_error.missing",
                    }
                ],
                Config,
            )


# Eagerly load configuration at import time for convenience across modules
config = Config()
