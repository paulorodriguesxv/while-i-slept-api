"""AWS Lambda adapter for article summary worker SQS events."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from while_i_slept_api.article_pipeline.runtime import build_process_summary_use_case
from while_i_slept_api.article_pipeline.worker_processing import process_sqs_record
from while_i_slept_api.core.config import get_settings
from while_i_slept_api.core.logging import StructuredLogger

_LOGGER = StructuredLogger("while_i_slept.summary.lambda")
_SETTINGS = get_settings()


@lru_cache(maxsize=1)
def _get_use_case():
    return build_process_summary_use_case(_SETTINGS)


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
            max_attempts=_SETTINGS.summary_worker_retry_attempts,
            base_backoff_seconds=_SETTINGS.summary_worker_retry_backoff_seconds,
        )
        if not should_ack:
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
