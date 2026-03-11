"""DTOs for sleep window feed query."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SleepWindowRequest(BaseModel):
    """Sleep window query request."""

    language: str
    start_time: datetime
    end_time: datetime
    limit: int = Field(default=50, ge=1, le=200)


class SleepWindowItem(BaseModel):
    """Feed item returned for a sleep window."""

    content_hash: str
    title: str
    source: str
    source_url: str
    published_at: datetime
    summary: str | None


class SleepWindowResponse(BaseModel):
    """Sleep window query response."""

    items: list[SleepWindowItem]
