"""Unit tests for summary worker state machine behavior."""

from __future__ import annotations

from dataclasses import dataclass

from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.models import RawArticle, SummaryOutput, SummaryState
from while_i_slept_api.article_pipeline.use_cases import ProcessSummaryJobUseCase
from while_i_slept_api.core.logging import StructuredLogger


@dataclass
class _FakeRepository:
    state: SummaryState | None = None
    raw_exists: bool = True
    mark_done_calls: int = 0
    mark_failed_calls: int = 0
    last_retry_count: int | None = None

    def put_raw_article_if_absent(self, article: RawArticle) -> bool:
        _ = article
        return True

    def put_feed_index_item(self, article: RawArticle, *, topic: str) -> None:
        _ = (article, topic)

    def put_summary_pending(self, *, content_hash: str, summary_version: int, created_at: str) -> None:
        _ = (content_hash, summary_version, created_at)

    def get_raw_article(self, content_hash: str) -> RawArticle | None:
        if not self.raw_exists:
            return None
        return RawArticle(
            content_hash=content_hash,
            article_id="a1",
            language="en",
            topic="technology",
            source="Example",
            source_url="https://example.com",
            title="Title",
            content="Body",
            published_at="2026-02-27T10:00:00Z",
            ingested_at="2026-02-27T10:01:00Z",
        )

    def get_summary_state(self, *, content_hash: str, summary_version: int) -> SummaryState | None:
        _ = (content_hash, summary_version)
        return self.state

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
        self.mark_done_calls += 1

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
        self.mark_failed_calls += 1
        self.last_retry_count = retry_count


class _FakeSummarizer:
    def summarize(self, article: RawArticle, job: SummaryJob) -> SummaryOutput:
        _ = (article, job)
        return SummaryOutput(summary="ok", model_used="test-model", tokens_used=10, cost_estimate_usd=0.01)


class _FailingSummarizer:
    def summarize(self, article: RawArticle, job: SummaryJob) -> SummaryOutput:
        _ = (article, job)
        raise RuntimeError("summarizer unavailable")


def _job(*, reprocess: bool = False) -> SummaryJob:
    return SummaryJob.from_payload(
        {
            "version": 1,
            "job_id": "job_1",
            "article_id": "article_1",
            "content_hash": "h1",
            "language": "en",
            "topic": "technology",
            "summary_version": 1,
            "priority": "normal",
            "reprocess": reprocess,
            "model_override": None,
            "created_at": "2026-02-27T10:00:00Z",
        }
    )


def test_worker_skips_when_done_and_not_reprocess() -> None:
    repository = _FakeRepository(state=SummaryState(content_hash="h1", summary_version=1, status="DONE", retry_count=0))
    use_case = ProcessSummaryJobUseCase(repository, _FakeSummarizer(), StructuredLogger("tests.article.worker"))

    result = use_case.process_summary_job(_job(reprocess=False))

    assert result.status == "SKIPPED"
    assert repository.mark_done_calls == 0
    assert repository.mark_failed_calls == 0


def test_worker_marks_done_on_success() -> None:
    repository = _FakeRepository(state=SummaryState(content_hash="h1", summary_version=1, status="PENDING", retry_count=2))
    use_case = ProcessSummaryJobUseCase(repository, _FakeSummarizer(), StructuredLogger("tests.article.worker.done"))

    result = use_case.process_summary_job(_job(reprocess=False))

    assert result.status == "DONE"
    assert repository.mark_done_calls == 1
    assert repository.mark_failed_calls == 0


def test_worker_marks_failed_when_raw_missing() -> None:
    repository = _FakeRepository(raw_exists=False)
    use_case = ProcessSummaryJobUseCase(repository, _FakeSummarizer(), StructuredLogger("tests.article.worker.raw_missing"))

    result = use_case.process_summary_job(_job())

    assert result.status == "FAILED"
    assert repository.mark_done_calls == 0
    assert repository.mark_failed_calls == 1
    assert repository.last_retry_count == 1


def test_worker_marks_failed_when_summarizer_raises() -> None:
    repository = _FakeRepository(state=SummaryState(content_hash="h1", summary_version=1, status="PENDING", retry_count=4))
    use_case = ProcessSummaryJobUseCase(repository, _FailingSummarizer(), StructuredLogger("tests.article.worker.fail"))

    result = use_case.process_summary_job(_job())

    assert result.status == "FAILED"
    assert repository.mark_done_calls == 0
    assert repository.mark_failed_calls == 1
    assert repository.last_retry_count == 5
