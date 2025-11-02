from __future__ import annotations

from datetime import datetime

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


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


class FileSummary(BaseModel):
    front_matter: SummaryFrontMatter
    summary_md: str = Field(..., description="200-400 word markdown summary body")

    @field_validator("summary_md")
    @classmethod
    def validate_summary_word_count(cls, value: str) -> str:
        words = [w for w in value.split() if w]
        word_count = len(words)
        if word_count < 200 or word_count > 400:
            raise ValueError(f"summary_md must be 200-400 words (got {word_count})")
        return value

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
