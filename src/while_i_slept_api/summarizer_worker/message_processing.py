"""Shared message processing logic for lambda and local consumer."""

from __future__ import annotations

import json
from typing import Any

from while_i_slept_api.summarizer_worker.dto import SummaryJob
from while_i_slept_api.summarizer_worker.errors import (
    SummaryJobNonRetryableError,
    SummaryJobPayloadError,
    SummaryJobRetryableError,
)
from while_i_slept_api.summarizer_worker.logging import StructuredLogger
from while_i_slept_api.summarizer_worker.retry import RetryPolicy, execute_with_retries
from while_i_slept_api.summarizer_worker.use_case import SummaryJobUseCase


def process_sqs_record(
    *,
    record_body: str,
    message_id: str,
    receive_count: int | None,
    use_case: SummaryJobUseCase,
    logger: StructuredLogger,
    retry_policy: RetryPolicy,
) -> bool:
    """Process a single SQS record.

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
        job = SummaryJob.from_payload(cast_payload(payload))
    except SummaryJobPayloadError:
        logger.warning(
            "summary_job.invalid_payload_schema",
            message_id=message_id,
            receive_count=receive_count,
        )
        return True

    try:
        execute_with_retries(
            lambda: use_case.process_summary_job(job),
            policy=retry_policy,
        )
    except SummaryJobNonRetryableError:
        logger.warning(
            "summary_job.non_retryable_failure",
            message_id=message_id,
            receive_count=receive_count,
            job_id=job.job_id,
        )
        return True
    except SummaryJobRetryableError:
        logger.exception(
            "summary_job.retryable_failure",
            message_id=message_id,
            receive_count=receive_count,
            job_id=job.job_id,
        )
        return False

    logger.info(
        "summary_job.ack",
        message_id=message_id,
        receive_count=receive_count,
        job_id=job.job_id,
    )
    return True


def cast_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Type helper for payload narrowing."""

    return payload
