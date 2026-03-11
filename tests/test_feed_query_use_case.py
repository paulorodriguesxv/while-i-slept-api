"""Unit tests for sleep-window feed query use case."""

from __future__ import annotations

from datetime import UTC, datetime

from while_i_slept_api.article_pipeline.feed_query.dto import SleepWindowRequest
from while_i_slept_api.article_pipeline.feed_query.use_cases import GetSleepWindowFeedUseCase


class _FakeFeedQueryRepository:
    def __init__(self, rows: list[dict], summaries: dict[tuple[str, int], str | None]) -> None:
        self._rows = rows
        self._summaries = summaries
        self.query_calls: list[dict] = []
        self.summary_calls: list[tuple[str, int]] = []

    def query_feed_window(
        self,
        language: str,
        start_time: datetime,
        end_time: datetime,
        limit: int,
    ) -> list[dict]:
        self.query_calls.append(
            {
                "language": language,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
            }
        )
        return self._rows[:limit]

    def get_summary(
        self,
        content_hash: str,
        summary_version: int,
    ) -> str | None:
        self.summary_calls.append((content_hash, summary_version))
        return self._summaries.get((content_hash, summary_version))


def test_sleep_window_use_case_returns_items_and_summaries_in_order() -> None:
    rows = [
        {
            "content_hash": "h1",
            "title": "First",
            "source": "A",
            "source_url": "https://a",
            "published_at": "2026-03-10T01:00:00Z",
            "summary_version_default": 1,
        },
        {
            "content_hash": "h2",
            "title": "Second",
            "source": "B",
            "source_url": "https://b",
            "published_at": "2026-03-10T02:00:00Z",
            "summary_version_default": 2,
        },
    ]
    repo = _FakeFeedQueryRepository(
        rows=rows,
        summaries={
            ("h1", 1): "summary-1",
            ("h2", 2): "summary-2",
        },
    )
    use_case = GetSleepWindowFeedUseCase(repo)

    response = use_case.execute(
        SleepWindowRequest(
            language="en",
            start_time=datetime(2026, 3, 10, 0, 30, tzinfo=UTC),
            end_time=datetime(2026, 3, 10, 3, 0, tzinfo=UTC),
            limit=50,
        )
    )

    assert [item.content_hash for item in response.items] == ["h1", "h2"]
    assert [item.summary for item in response.items] == ["summary-1", "summary-2"]
    assert repo.summary_calls == [("h1", 1), ("h2", 2)]


def test_sleep_window_use_case_returns_empty_when_no_rows() -> None:
    repo = _FakeFeedQueryRepository(rows=[], summaries={})
    use_case = GetSleepWindowFeedUseCase(repo)

    response = use_case.execute(
        SleepWindowRequest(
            language="pt",
            start_time=datetime(2026, 3, 10, 0, 0, tzinfo=UTC),
            end_time=datetime(2026, 3, 10, 6, 0, tzinfo=UTC),
            limit=50,
        )
    )

    assert response.items == []
    assert repo.summary_calls == []


def test_sleep_window_use_case_deduplicates_similar_story_titles() -> None:
    rows = [
        {
            "content_hash": "h1",
            "title": "US senate approves major climate bill",
            "source": "A",
            "source_url": "https://a",
            "published_at": "2026-03-10T01:00:00Z",
            "summary_version_default": 1,
        },
        {
            "content_hash": "h2",
            "title": "Senate approves major climate bill in US",
            "source": "B",
            "source_url": "https://b",
            "published_at": "2026-03-10T01:10:00Z",
            "summary_version_default": 1,
        },
    ]
    repo = _FakeFeedQueryRepository(
        rows=rows,
        summaries={
            ("h1", 1): "short",
            ("h2", 1): "a much longer summary for the same story",
        },
    )
    use_case = GetSleepWindowFeedUseCase(repo)

    response = use_case.execute(
        SleepWindowRequest(
            language="en",
            start_time=datetime(2026, 3, 10, 0, 30, tzinfo=UTC),
            end_time=datetime(2026, 3, 10, 3, 0, tzinfo=UTC),
            limit=50,
        )
    )

    assert [item.content_hash for item in response.items] == ["h2"]
