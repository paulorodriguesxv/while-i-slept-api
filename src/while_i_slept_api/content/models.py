"""Typed models for internal content ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class FeedDefinition:
    """Describes a single RSS/Atom feed source."""

    url: str
    source_name: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizedFeedEntry:
    """Normalized RSS entry used by future editorial/generation layers."""

    language: str
    topic: str
    feed_url: str
    entry_id: str | None
    title: str
    link: str | None
    summary: str | None
    published_at: datetime
