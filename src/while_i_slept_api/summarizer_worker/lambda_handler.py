"""AWS Lambda adapter for summary worker SQS events."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from while_i_slept_api.core.config import get_settings
from while_i_slept_api.summarizer_worker.logging import StructuredLogger
from while_i_slept_api.summarizer_worker.message_processing import process_sqs_record
from while_i_slept_api.summarizer_worker.retry import RetryPolicy
from while_i_slept_api.summarizer_worker.runtime import build_use_case

_LOGGER = StructuredLogger("while_i_slept.summarizer.lambda")
_SETTINGS = get_settings()
_RETRY_POLICY = RetryPolicy(
    max_attempts=_SETTINGS.summary_worker_retry_attempts,
    base_backoff_seconds=_SETTINGS.summary_worker_retry_backoff_seconds,
)


@lru_cache(maxsize=1)
def _get_use_case():
    return build_use_case(_SETTINGS)


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, list[dict[str, str]]]:
    """Handle Lambda SQS event with partial-batch failure semantics."""

    failures: list[dict[str, str]] = []
    records = event.get("Records", [])
    if not isinstance(records, list):
        _LOGGER.warning("summary_job.invalid_event_records")
        return {"batchItemFailures": failures}

    for record in records:
        if not isinstance(record, dict):
            continue
        message_id = str(record.get("messageId", "unknown"))
        body = str(record.get("body", ""))
        attributes = record.get("attributes") or {}
        receive_count: int | None = None
        if isinstance(attributes, dict):
            raw = attributes.get("ApproximateReceiveCount")
            if raw is not None:
                try:
                    receive_count = int(str(raw))
                except ValueError:
                    receive_count = None

        should_ack = process_sqs_record(
            record_body=body,
            message_id=message_id,
            receive_count=receive_count,
            use_case=_get_use_case(),
            logger=_LOGGER,
            retry_policy=_RETRY_POLICY,
        )
        if not should_ack:
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
