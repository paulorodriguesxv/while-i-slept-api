"""Unit tests for ingestion idempotency and enqueue behavior."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from while_i_slept_api.article_pipeline.dto import SummaryJob
import while_i_slept_api.article_pipeline.ingestion_handler as ingestion_handler_module
from while_i_slept_api.article_pipeline.models import RawArticle, SummaryOutput, SummaryState
from while_i_slept_api.article_pipeline.use_cases import IngestArticleUseCase
from while_i_slept_api.content.models import FeedDefinition, NormalizedFeedEntry
from while_i_slept_api.core.logging import StructuredLogger


@dataclass
class _FakeRepository:
    should_create: bool = True
    feed_topics: list[str] = field(default_factory=list)
    pending_created: int = 0

    def put_raw_article_if_absent(self, _article: RawArticle) -> bool:
        return self.should_create

    def put_feed_index_item(self, _article: RawArticle, *, topic: str) -> None:
        self.feed_topics.append(topic)

    def put_summary_pending(self, *, content_hash: str, summary_version: int, created_at: str) -> None:
        _ = (content_hash, summary_version, created_at)
        self.pending_created += 1

    def get_raw_article(self, content_hash: str) -> RawArticle | None:
        _ = content_hash
        return None

    def get_summary_state(self, *, content_hash: str, summary_version: int) -> SummaryState | None:
        _ = (content_hash, summary_version)
        return None

    def mark_summary_done(
        self,
        *,
        content_hash: str,
        summary_version: int,
        summary: str,
        model_used: str,
        tokens_used: int | None,
        cost_estimate_usd: float | None,
        summarized_at: str,
    ) -> None:
        _ = (content_hash, summary_version, summary, model_used, tokens_used, cost_estimate_usd, summarized_at)

    def mark_summary_failed(
        self,
        *,
        content_hash: str,
        summary_version: int,
        error_code: str,
        error_message: str,
        retry_count: int,
        updated_at: str,
    ) -> None:
        _ = (content_hash, summary_version, error_code, error_message, retry_count, updated_at)


@dataclass
class _FakeQueue:
    jobs: list[SummaryJob] = field(default_factory=list)

    def enqueue(self, job: SummaryJob) -> None:
        self.jobs.append(job)


def _article() -> RawArticle:
    return RawArticle(
        content_hash="h1",
        article_id="a1",
        language="en",
        topic="world",
        source="Example",
        source_url="https://example.com/story",
        title="Story",
        content="Content",
        published_at="2026-02-27T12:00:00Z",
        ingested_at="2026-02-27T12:05:00Z",
    )


def test_ingestion_creates_feed_indexes_pending_and_enqueue() -> None:
    repository = _FakeRepository(should_create=True)
    queue = _FakeQueue()
    use_case = IngestArticleUseCase(repository, queue, StructuredLogger("tests.article.ingestion"))

    result = use_case.ingest(_article())

    assert result.status == "CREATED"
    assert result.enqueued is True
    assert repository.feed_topics == ["world", "all"]
    assert repository.pending_created == 1
    assert len(queue.jobs) == 1
    assert queue.jobs[0].summary_version == 1


def test_ingestion_duplicate_does_not_enqueue() -> None:
    repository = _FakeRepository(should_create=False)
    queue = _FakeQueue()
    use_case = IngestArticleUseCase(repository, queue, StructuredLogger("tests.article.ingestion.duplicate"))

    result = use_case.ingest(_article())

    assert result.status == "DUPLICATE"
    assert result.enqueued is False
    assert repository.feed_topics == []
    assert repository.pending_created == 0
    assert queue.jobs == []


@dataclass
class _FakeArticleJobQueue:
    jobs: list[Any] = field(default_factory=list)

    def enqueue(self, job: Any) -> None:
        self.jobs.append(job)


def test_ingestion_lambda_enqueues_lightweight_article_jobs(monkeypatch) -> None:
    queue = _FakeArticleJobQueue()
    feeds = [FeedDefinition(url="https://example.com/feed", source_name="Example Source")]
    entries = [
        NormalizedFeedEntry(
            language="en",
            topic="world",
            feed_url="https://example.com/feed",
            entry_id="entry-1",
            title="Title 1",
            link="https://example.com/story-1",
            summary="Summary 1",
            published_at=datetime(2026, 2, 27, 10, 0, tzinfo=UTC),
        ),
        NormalizedFeedEntry(
            language="en",
            topic="world",
            feed_url="https://example.com/feed",
            entry_id="entry-2",
            title="Title 2",
            link=None,
            summary="Summary 2",
            published_at=datetime(2026, 2, 27, 10, 5, tzinfo=UTC),
        ),
    ]

    class _FakeRegistry:
        def resolve(self, *, language: str, topic: str) -> list[FeedDefinition]:
            assert language == "en"
            assert topic == "world"
            return feeds

    class _FakeFetcher:
        def fetch_feed(self, *, language: str, topic: str, feed: FeedDefinition) -> list[NormalizedFeedEntry]:
            assert language == "en"
            assert topic == "world"
            assert feed.url == "https://example.com/feed"
            return entries

    monkeypatch.setattr(ingestion_handler_module, "FeedRegistry", _FakeRegistry)
    monkeypatch.setattr(ingestion_handler_module, "RSSFetcher", _FakeFetcher)
    monkeypatch.setattr(ingestion_handler_module, "build_article_job_queue", lambda *_: queue)

    result = ingestion_handler_module.lambda_handler({"language": "en", "topic": "world"}, None)

    assert result == {"language": "en", "topic": "world", "total": 2, "enqueued": 2}
    assert len(queue.jobs) == 2
    assert queue.jobs[0].article_url == "https://example.com/story-1"
    assert queue.jobs[1].article_url == "https://example.com/feed"
    assert queue.jobs[0].source == "Example Source"


def test_ingestion_lambda_returns_zero_when_no_feeds(monkeypatch) -> None:
    class _FakeRegistry:
        def resolve(self, *, language: str, topic: str) -> list[FeedDefinition]:
            _ = (language, topic)
            return []

    monkeypatch.setattr(ingestion_handler_module, "FeedRegistry", _FakeRegistry)

    result = ingestion_handler_module.lambda_handler({"language": "pt", "topic": "science"}, None)

    assert result == {"language": "pt", "topic": "science", "total": 0, "enqueued": 0}
