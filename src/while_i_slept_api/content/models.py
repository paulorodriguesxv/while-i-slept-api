"""Typed models for normalized feed ingestion payloads.

These models represent source feed definitions and normalized feed entries
before article_pipeline write-side persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FeedDefinition:
    """Configuration for one RSS/Atom source endpoint."""

    url: str
    source_name: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizedFeedEntry:
    """Normalized feed entry passed into article ingestion use cases."""

    language: str
    topic: str
    feed_url: str
    entry_id: str | None
    title: str
    link: str | None
    summary: str | None
    published_at: datetime
