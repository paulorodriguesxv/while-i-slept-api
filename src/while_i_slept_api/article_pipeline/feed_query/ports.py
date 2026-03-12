"""Read-side repository ports for feed query use cases."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class FeedQueryRepository(Protocol):
    """Port for FEED-index range queries and summary hydration."""

    def query_feed_window(
        self,
        language: str,
        start_time: datetime,
        end_time: datetime,
        limit: int,
    ) -> list[dict]:
        """Query FEED index rows in a resolved datetime window."""

    def get_summary(
        self,
        content_hash: str,
        summary_version: int,
    ) -> str | None:
        """Load summary text for an article/version when status is DONE."""
