"""Runtime-agnostic models for article summary pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SummaryStatus = Literal["PENDING", "DONE", "FAILED", "SKIPPED"]


@dataclass(slots=True, frozen=True)
class RawArticle:
    """Raw article stored in single table."""

    content_hash: str
    article_id: str | None
    language: str
    topic: str
    source: str
    source_url: str
    title: str
    content: str
    published_at: str
    ingested_at: str


@dataclass(slots=True, frozen=True)
class SummaryState:
    """Summary item state snapshot."""

    content_hash: str
    summary_version: int
    status: SummaryStatus
    retry_count: int
    summary: str | None = None


@dataclass(slots=True, frozen=True)
class SummaryOutput:
    """Summarizer output."""

    summary: str
    model_used: str
    tokens_used: int | None = None
    cost_estimate_usd: float | None = None

