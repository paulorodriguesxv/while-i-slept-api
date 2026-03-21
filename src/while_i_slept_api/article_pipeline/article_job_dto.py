"""Intermediate article-job DTO contract (v1) for ingestion decoupling."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from while_i_slept_api.article_pipeline.errors import ArticleJobValidationError


class ArticleJob(BaseModel):
    """Lightweight article payload enqueued by ingestion lambda."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    entry_id: str | None
    language: Literal["en", "pt"]
    topic: Literal["world", "technology", "finance", "science", "sports", "business"]
    source: str
    source_feed_url: str
    article_url: str
    title: str
    summary: str | None
    published_at: datetime

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ArticleJob":
        """Parse payload and raise typed error on failure."""

        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            raise ArticleJobValidationError("Invalid article job payload.") from exc
