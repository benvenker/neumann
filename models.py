from __future__ import annotations

from datetime import datetime

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator


class SummaryFrontMatter(BaseModel):
    doc_id: str = Field(..., description="Stable identifier derived from source_path")
    source_path: str = Field(..., description="Path to the original file")
    language: str = Field(..., description="Programming or natural language, e.g., 'python', 'markdown'")
    product_tags: list[str] = Field(default_factory=list, description="Product or domain tags")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of summary generation")
    key_topics: list[str] = Field(default_factory=list, description="High-level topics covered")
    api_symbols: list[str] = Field(default_factory=list, description="Referenced public API symbols")
    related_files: list[str] = Field(default_factory=list, description="Paths to related files")
    suggested_queries: list[str] = Field(default_factory=list, description="Suggested search queries")
    source_word_count: int | None = Field(
        default=None,
        ge=0,
        description="Word count of the original source text used for summarization.",
    )
    min_summary_words: int | None = Field(
        default=None,
        ge=0,
        description="Lower bound used when generating the summary.",
    )
    max_summary_words: int | None = Field(
        default=None,
        ge=0,
        description="Upper bound used when generating the summary.",
    )
    target_summary_words: int | None = Field(
        default=None,
        ge=0,
        description="Approximate target length for the generated summary.",
    )

    @model_validator(mode="after")
    def _validate_word_bounds(self) -> "SummaryFrontMatter":
        """Validate summary word count bounds are coherent when present."""
        # Only validate when all are present
        if self.min_summary_words is not None and self.max_summary_words is not None:
            if self.min_summary_words > self.max_summary_words:
                raise ValueError("min_summary_words must be <= max_summary_words")
        if (
            self.min_summary_words is not None
            and self.max_summary_words is not None
            and self.target_summary_words is not None
        ):
            if not (self.min_summary_words <= self.target_summary_words <= self.max_summary_words):
                raise ValueError("target_summary_words must be between min_summary_words and max_summary_words")
        return self


class FileSummary(BaseModel):
    front_matter: SummaryFrontMatter
    summary_md: str = Field(..., description="Markdown summary body.")

    @model_validator(mode="after")
    def validate_summary_word_count(self) -> FileSummary:
        words = [w for w in self.summary_md.split() if w]
        word_count = len(words)

        min_words = self.front_matter.min_summary_words or 200
        max_words = self.front_matter.max_summary_words or 400

        if word_count < min_words:
            raise ValueError(
                f"summary_md must be at least {min_words} words (got {word_count})"
            )
        if word_count > max_words:
            raise ValueError(
                f"summary_md must be at most {max_words} words (got {word_count})"
            )
        return self

    def to_yaml(self) -> str:
        """Serialize to YAML front-matter + markdown body suitable for .summary.md files."""
        # Represent front matter as plain dict with ISO datetime
        fm_dict = self.front_matter.model_dump()
        if isinstance(fm_dict.get("last_updated"), datetime):
            fm_dict["last_updated"] = fm_dict["last_updated"].isoformat() + "Z"

        front_matter_yaml = yaml.safe_dump(
            fm_dict,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ).strip()

        return f"---\n{front_matter_yaml}\n---\n\n{self.summary_md}\n"


__all__ = ["SummaryFrontMatter", "FileSummary", "ValidationError"]
