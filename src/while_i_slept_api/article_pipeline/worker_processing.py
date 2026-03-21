"""Shared SQS record processing for article summary worker adapters."""

from __future__ import annotations

import json
import time
from typing import Any, Callable

from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.errors import SummaryJobValidationError
from while_i_slept_api.article_pipeline.use_cases import ProcessSummaryJobUseCase
from while_i_slept_api.core.logging import StructuredLogger


def _execute_with_retries(
    fn: Callable[[], Any],
    *,
    max_attempts: int,
    base_backoff_seconds: float,
    sleep_fn: Callable[[float], None],
) -> Any:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception:
            if attempt >= max_attempts:
                raise
            sleep_fn(base_backoff_seconds * attempt)

    raise RuntimeError("unreachable")


def process_sqs_record(
    *,
    record_body: str,
    message_id: str,
    receive_count: int | None,
    use_case: ProcessSummaryJobUseCase,
    logger: StructuredLogger,
    max_attempts: int,
    base_backoff_seconds: float,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> bool:
    """Process one SQS record.

    Returns True when the record should be acknowledged/deleted.
    Returns False when the record should be retried by SQS/Lambda.
    """

    try:
        payload = json.loads(record_body)
    except json.JSONDecodeError:
        logger.warning(
            "summary_job.invalid_json",
            message_id=message_id,
            receive_count=receive_count,
        )
        return True

    if not isinstance(payload, dict):
        logger.warning(
            "summary_job.invalid_payload_type",
            message_id=message_id,
            receive_count=receive_count,
        )
        return True

    try:
        job = SummaryJob.from_payload(payload)
    except SummaryJobValidationError:
        logger.warning(
            "summary_job.invalid_payload_schema",
            message_id=message_id,
            receive_count=receive_count,
        )
        return True

    try:
        result = _execute_with_retries(
            lambda: use_case.process_summary_job(job),
            max_attempts=max_attempts,
            base_backoff_seconds=base_backoff_seconds,
            sleep_fn=sleep_fn,
        )
    except Exception as exc:
        logger.exception(
            "summary_job.retryable_failure",
            message_id=message_id,
            receive_count=receive_count,
            content_hash=job.content_hash,
            summary_version=job.summary_version,
            error=exc.__class__.__name__,
        )
        return False

    if result.status == "FAILED":
        logger.warning(
            "summary_job.failed",
            message_id=message_id,
            receive_count=receive_count,
            content_hash=result.content_hash,
            summary_version=result.summary_version,
            retry_count=result.retry_count,
        )
        return False

    logger.info(
        "summary_job.ack",
        message_id=message_id,
        receive_count=receive_count,
        content_hash=result.content_hash,
        summary_version=result.summary_version,
        status=result.status,
    )
    return True
