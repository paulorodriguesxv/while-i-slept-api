"""Repository ports for sleep window feed query."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class FeedQueryRepository(Protocol):
    """Repository contract for querying feed window and loading summaries."""

    def query_feed_window(
        self,
        language: str,
        start_time: datetime,
        end_time: datetime,
        limit: int,
    ) -> list[dict]:
        """Query FEED index rows in a sleep window."""

    def get_summary(
        self,
        content_hash: str,
        summary_version: int,
    ) -> str | None:
        """Load summary text when status is DONE."""
