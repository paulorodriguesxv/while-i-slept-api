"""Shared SQS record processing for article job worker adapters."""

from __future__ import annotations

import json
import logging

from while_i_slept_api.article_pipeline.article_fetcher import enrich_article_content
from while_i_slept_api.article_pipeline.article_job_dto import ArticleJob
from while_i_slept_api.article_pipeline.errors import ArticleJobValidationError
from while_i_slept_api.article_pipeline.hashing import compute_content_hash
from while_i_slept_api.article_pipeline.models import RawArticle
from while_i_slept_api.article_pipeline.use_cases import IngestArticleUseCase
from while_i_slept_api.core.logging import StructuredLogger
from while_i_slept_api.services.utils import iso_now


def process_article_job_record(
    *,
    record_body: str,
    message_id: str,
    receive_count: int | None,
    use_case: IngestArticleUseCase,
    logger: StructuredLogger,
    article_logger: logging.Logger,
) -> bool:
    """Process one article-job SQS record.

    Returns True when the record should be acknowledged/deleted.
    Returns False when the record should be retried by SQS/Lambda.
    """

    try:
        payload = json.loads(record_body)
    except json.JSONDecodeError:
        logger.warning(
            "article_job.invalid_json",
            message_id=message_id,
            receive_count=receive_count,
        )
        return True

    if not isinstance(payload, dict):
        logger.warning(
            "article_job.invalid_payload_type",
            message_id=message_id,
            receive_count=receive_count,
        )
        return True

    try:
        job = ArticleJob.from_payload(payload)
    except ArticleJobValidationError:
        logger.warning(
            "article_job.invalid_payload_schema",
            message_id=message_id,
            receive_count=receive_count,
        )
        return True

    try:
        enriched = enrich_article_content(
            url=job.article_url,
            fallback_text=job.summary or "",
            logger=article_logger,
        )
        content_hash = compute_content_hash(title=job.title, content=enriched.content)
        article = RawArticle(
            content_hash=content_hash,
            article_id=job.entry_id,
            language=job.language,
            topic=job.topic,
            source=job.source,
            source_url=job.article_url,
            title=job.title,
            content=enriched.content,
            image_url=enriched.image_url,
            description=enriched.description,
            author=enriched.author,
            article_published_time=enriched.article_published_time,
            reading_time_minutes=enriched.reading_time_minutes,
            published_at=job.published_at.isoformat(),
            ingested_at=iso_now(),
        )
        result = use_case.ingest(article)
    except Exception as exc:
        logger.exception(
            "article_job.retryable_failure",
            message_id=message_id,
            receive_count=receive_count,
            error=exc.__class__.__name__,
        )
        return False

    logger.info(
        "article_job.ack",
        message_id=message_id,
        receive_count=receive_count,
        content_hash=result.content_hash,
        status=result.status,
    )
    return True
