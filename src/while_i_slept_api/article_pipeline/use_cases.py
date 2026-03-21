"""Runtime-agnostic use cases for ingestion and summary processing."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from while_i_slept_api.article_pipeline.constants import DEFAULT_SUMMARY_VERSION
from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.models import RawArticle
from while_i_slept_api.article_pipeline.ports import ArticleSummaryRepository, Summarizer, SummaryJobQueue
from while_i_slept_api.services.utils import iso_now
from while_i_slept_api.core.logging import StructuredLogger


@dataclass(slots=True, frozen=True)
class IngestionResult:
    """Result of ingestion attempt."""

    status: str
    content_hash: str
    enqueued: bool


@dataclass(slots=True, frozen=True)
class ProcessSummaryResult:
    """Result of summary processing."""

    status: str
    content_hash: str
    summary_version: int
    retry_count: int


class IngestArticleUseCase:
    """Create RAW + FEED + SUMMARY(PENDING) and enqueue summary job."""

    def __init__(
        self,
        repository: ArticleSummaryRepository,
        queue: SummaryJobQueue,
        logger: StructuredLogger,
    ) -> None:
        self._repository = repository
        self._queue = queue
        self._logger = logger

    def ingest(self, article: RawArticle) -> IngestionResult:
        """Ingest article into single-table model with idempotency."""

        created = self._repository.put_raw_article_if_absent(article)
        if not created:
            self._logger.info(
                "ingestion.duplicate_article",
                content_hash=article.content_hash,
                language=article.language,
                topic=article.topic,
            )
            return IngestionResult(status="DUPLICATE", content_hash=article.content_hash, enqueued=False)

        self._repository.put_feed_index_item(article, topic=article.topic)
        self._repository.put_feed_index_item(article, topic="all")
        self._repository.put_summary_pending(
            content_hash=article.content_hash,
            summary_version=DEFAULT_SUMMARY_VERSION,
            created_at=article.ingested_at,
        )
        job = SummaryJob(
            version=1,
            job_id=str(uuid4()),
            article_id=article.article_id or article.content_hash,
            content_hash=article.content_hash,
            language=article.language,  # type: ignore[arg-type]
            topic=article.topic,  # type: ignore[arg-type]
            summary_version=DEFAULT_SUMMARY_VERSION,
            priority="normal",
            reprocess=False,
            model_override=None,
            created_at=article.ingested_at,
        )
        self._queue.enqueue(job)
        self._logger.info(
            "ingestion.article_enqueued",
            content_hash=article.content_hash,
            summary_version=DEFAULT_SUMMARY_VERSION,
            job_id=job.job_id,
        )
        return IngestionResult(status="CREATED", content_hash=article.content_hash, enqueued=True)


class ProcessSummaryJobUseCase:
    """Process summary job state machine with status transitions."""

    def __init__(
        self,
        repository: ArticleSummaryRepository,
        summarizer: Summarizer,
        logger: StructuredLogger,
    ) -> None:
        self._repository = repository
        self._summarizer = summarizer
        self._logger = logger

    def process_summary_job(self, job: SummaryJob) -> ProcessSummaryResult:
        """Process one summary job."""

        state = self._repository.get_summary_state(
            content_hash=job.content_hash,
            summary_version=job.summary_version,
        )
        retry_count = state.retry_count if state else 0
        if state and state.status == "DONE" and not job.reprocess:
            self._logger.info(
                "summary_job.skipped_done",
                content_hash=job.content_hash,
                summary_version=job.summary_version,
            )
            return ProcessSummaryResult(
                status="SKIPPED",
                content_hash=job.content_hash,
                summary_version=job.summary_version,
                retry_count=retry_count,
            )

        raw_article = self._repository.get_raw_article(job.content_hash)
        if raw_article is None:
            retry_count += 1
            self._repository.mark_summary_failed(
                content_hash=job.content_hash,
                summary_version=job.summary_version,
                error_code="RAW_NOT_FOUND",
                error_message=f"Raw article not found for content_hash={job.content_hash}",
                retry_count=retry_count,
                updated_at=iso_now(),
            )
            return ProcessSummaryResult(
                status="FAILED",
                content_hash=job.content_hash,
                summary_version=job.summary_version,
                retry_count=retry_count,
            )

        try:
            output = self._summarizer.summarize(raw_article, job)
        except Exception as exc:
            retry_count += 1
            self._repository.mark_summary_failed(
                content_hash=job.content_hash,
                summary_version=job.summary_version,
                error_code=exc.__class__.__name__,
                error_message=str(exc),
                retry_count=retry_count,
                updated_at=iso_now(),
            )
            self._logger.warning(
                "summary_job.failed",
                content_hash=job.content_hash,
                summary_version=job.summary_version,
                error_code=exc.__class__.__name__,
                retry_count=retry_count,
            )
            return ProcessSummaryResult(
                status="FAILED",
                content_hash=job.content_hash,
                summary_version=job.summary_version,
                retry_count=retry_count,
            )

        self._repository.mark_summary_done(
            content_hash=job.content_hash,
            summary_version=job.summary_version,
            summary=output.summary,
            model_used=output.model_used,
            tokens_used=output.tokens_used,
            cost_estimate_usd=output.cost_estimate_usd,
            summarized_at=iso_now(),
        )
        self._logger.info(
            "summary_job.done",
            content_hash=job.content_hash,
            summary_version=job.summary_version,
        )
        return ProcessSummaryResult(
            status="DONE",
            content_hash=job.content_hash,
            summary_version=job.summary_version,
            retry_count=retry_count,
        )

