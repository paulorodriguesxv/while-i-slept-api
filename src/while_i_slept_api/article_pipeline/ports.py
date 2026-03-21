"""Ports for runtime-agnostic use cases."""

from __future__ import annotations

from typing import Protocol

from while_i_slept_api.article_pipeline.article_job_dto import ArticleJob
from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.models import RawArticle, SummaryOutput, SummaryState


class ArticleSummaryRepository(Protocol):
    """Persistence port for raw/feed/summary items."""

    def put_raw_article_if_absent(self, article: RawArticle) -> bool:
        """Insert raw article conditionally. Return True if created."""

    def put_feed_index_item(self, article: RawArticle, *, topic: str) -> None:
        """Insert feed index item."""

    def put_summary_pending(self, *, content_hash: str, summary_version: int, created_at: str) -> None:
        """Insert pending summary item if absent."""

    def get_raw_article(self, content_hash: str) -> RawArticle | None:
        """Load raw article by hash."""

    def get_summary_state(self, *, content_hash: str, summary_version: int) -> SummaryState | None:
        """Load summary state by identity."""

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
        """Mark summary as done."""

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
        """Mark summary as failed."""


class SummaryJobQueue(Protocol):
    """Queue port for summary jobs."""

    def enqueue(self, job: SummaryJob) -> None:
        """Enqueue summary job."""


class ArticleJobQueue(Protocol):
    """Queue port for intermediate article jobs."""

    def enqueue(self, job: ArticleJob) -> None:
        """Enqueue intermediate article job."""


class Summarizer(Protocol):
    """Summarizer abstraction."""

    def summarize(self, article: RawArticle, job: SummaryJob) -> SummaryOutput:
        """Generate summary output."""
