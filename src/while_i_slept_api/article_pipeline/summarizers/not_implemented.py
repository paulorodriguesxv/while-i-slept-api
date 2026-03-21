"""Placeholder summarizer implementation."""

from __future__ import annotations

from while_i_slept_api.core.logging import StructuredLogger
from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.models import RawArticle, SummaryOutput


class NotImplementedSummarizer:
    """Placeholder summarizer for local/dev until LLM integration exists."""
    def __init__(self, logger: StructuredLogger) -> None:
        self._logger = logger

    def summarize(self, article: RawArticle, job: SummaryJob) -> SummaryOutput:
        raise NotImplementedError(
            "Summarizer integration is not implemented yet. "
            f"Cannot summarize content_hash={article.content_hash} "
            f"for summary_version={job.summary_version}."
        )

