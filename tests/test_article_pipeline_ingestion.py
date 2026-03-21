"""Unit tests for ingestion idempotency and enqueue behavior."""

from __future__ import annotations

from dataclasses import dataclass, field

from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.models import RawArticle, SummaryOutput, SummaryState
from while_i_slept_api.article_pipeline.use_cases import IngestArticleUseCase
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

