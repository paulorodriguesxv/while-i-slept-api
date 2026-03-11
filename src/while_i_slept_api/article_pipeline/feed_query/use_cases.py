"""Use cases for sleep window feed query."""

from __future__ import annotations

from while_i_slept_api.article_pipeline.feed_query.dto import (
    SleepWindowItem,
    SleepWindowRequest,
    SleepWindowResponse,
)
from while_i_slept_api.article_pipeline.feed_query.ports import FeedQueryRepository
from while_i_slept_api.article_pipeline.story_dedup.cluster import deduplicate_articles


class GetSleepWindowFeedUseCase:
    """Return feed items for a language inside a sleep window."""

    def __init__(self, repository: FeedQueryRepository):
        self._repository = repository

    def execute(self, request: SleepWindowRequest) -> SleepWindowResponse:
        """Execute sleep window query and hydrate summaries."""

        rows = self._repository.query_feed_window(
            language=request.language,
            start_time=request.start_time,
            end_time=request.end_time,
            limit=request.limit,
        )

        items: list[SleepWindowItem] = []
        for row in rows:
            summary_version = int(row.get("summary_version_default", 1))
            summary = self._repository.get_summary(
                row["content_hash"],
                summary_version,
            )
            items.append(
                SleepWindowItem(
                    content_hash=row["content_hash"],
                    title=row["title"],
                    source=row["source"],
                    source_url=row["source_url"],
                    published_at=row["published_at"],
                    summary=summary,
                )
            )

        return SleepWindowResponse(items=deduplicate_articles(items))
