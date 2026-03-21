"""AWS Lambda adapter for article-job processor SQS events."""

from __future__ import annotations

from functools import lru_cache
import logging
from typing import Any

from while_i_slept_api.article_pipeline.article_job_worker_processing import process_article_job_record
from while_i_slept_api.article_pipeline.runtime import build_ingestion_use_case
from while_i_slept_api.core.logging import StructuredLogger

_LOGGER = StructuredLogger("while_i_slept.article_processor.lambda")
_ARTICLE_LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_use_case():
    return build_ingestion_use_case()


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, list[dict[str, str]]]:
    """Handle Lambda SQS event with partial-batch failure semantics."""

    failures: list[dict[str, str]] = []
    records = event.get("Records", [])
    if not isinstance(records, list):
        _LOGGER.warning("article_job.invalid_event_records")
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

        should_ack = process_article_job_record(
            record_body=body,
            message_id=message_id,
            receive_count=receive_count,
            use_case=_get_use_case(),
            logger=_LOGGER,
            article_logger=_ARTICLE_LOGGER,
        )
        if not should_ack:
            failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": failures}
