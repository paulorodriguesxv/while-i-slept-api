"""DTOs for read-side feed queries over a resolved datetime window."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SleepWindowRequest(BaseModel):
    """Feed query request for a resolved datetime interval.

    ``start_time``/``end_time`` are concrete datetimes, not user preference
    values like ``HH:MM``.
    """

    language: str
    start_time: datetime
    end_time: datetime
    limit: int = Field(default=50, ge=1, le=200)


class SleepWindowItem(BaseModel):
    """One feed item returned by read-side feed lookup."""

    content_hash: str
    title: str
    source: str
    source_url: str
    published_at: datetime
    summary: str | None


class SleepWindowResponse(BaseModel):
    """Response envelope for feed window query results."""

    items: list[SleepWindowItem]
