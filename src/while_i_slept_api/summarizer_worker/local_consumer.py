"""Local SQS consumer (single consolidated implementation)."""

from __future__ import annotations

from collections.abc import Callable
import json
import os
import signal
import time
from typing import Any

from while_i_slept_api.article_pipeline.dto import SummaryJob as ArticleSummaryJob
from while_i_slept_api.article_pipeline.errors import SummaryJobValidationError
from while_i_slept_api.article_pipeline.runtime import build_process_summary_use_case
from while_i_slept_api.core.config import Settings, get_settings
from while_i_slept_api.summarizer_worker.logging import StructuredLogger
from while_i_slept_api.summarizer_worker.message_processing import process_sqs_record
from while_i_slept_api.summarizer_worker.retry import RetryPolicy, execute_with_retries


def run_forever(settings: Settings | None = None) -> None:
    """Poll SQS forever and process one message at a time."""

    cfg = settings or get_settings()
    running = {"value": True}
    logger = StructuredLogger("while_i_slept.summarizer.local_consumer")
    use_case = build_process_summary_use_case()
    retry_policy = RetryPolicy(
        max_attempts=cfg.summary_worker_retry_attempts,
        base_backoff_seconds=cfg.summary_worker_retry_backoff_seconds,
    )
    sqs_client = _build_sqs_client(cfg)
    queue_url = _resolve_queue_url(cfg, sqs_client)

    def _shutdown_handler(_signum: int, _frame: Any) -> None:
        running["value"] = False
        logger.info("summary_consumer.stop_requested")

    signal.signal(signal.SIGINT, _shutdown_handler)
    logger.info("summary_consumer.started", queue_url=queue_url)
    while running["value"]:
        poll_once(
            sqs_client=sqs_client,
            queue_url=queue_url,
            logger=logger,
            use_case=use_case,
            retry_policy=retry_policy,
            wait_time_seconds=cfg.summary_worker_wait_time_seconds,
            visibility_timeout_seconds=cfg.summary_worker_visibility_timeout_seconds,
            max_number_of_messages=1,
        )
    logger.info("summary_consumer.stopped")


def poll_once(
    *,
    sqs_client: Any,
    queue_url: str,
    logger: StructuredLogger,
    use_case: Any,
    retry_policy: RetryPolicy,
    wait_time_seconds: int,
    visibility_timeout_seconds: int,
    max_number_of_messages: int = 1,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    """Poll SQS once and process received messages."""

    response = sqs_client.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=max_number_of_messages,
        WaitTimeSeconds=wait_time_seconds,
        VisibilityTimeout=visibility_timeout_seconds,
        AttributeNames=["ApproximateReceiveCount"],
    )
    messages = response.get("Messages", [])
    if not messages:
        sleep_fn(0.25)
        return

    for message in messages:
        message_id = str(message.get("MessageId", "unknown"))
        body = str(message.get("Body", ""))
        receipt_handle = message.get("ReceiptHandle")
        attributes = message.get("Attributes") or {}
        receive_count: int | None = None
        if isinstance(attributes, dict):
            raw = attributes.get("ApproximateReceiveCount")
            if raw is not None:
                try:
                    receive_count = int(str(raw))
                except ValueError:
                    receive_count = None

        should_ack = _process_record(
            record_body=body,
            message_id=message_id,
            receive_count=receive_count,
            use_case=use_case,
            logger=logger,
            retry_policy=retry_policy,
        )
        if should_ack and receipt_handle:
            sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


def _process_record(
    *,
    record_body: str,
    message_id: str,
    receive_count: int | None,
    use_case: Any,
    logger: StructuredLogger,
    retry_policy: RetryPolicy,
) -> bool:
    """Process one record and return whether it should be acknowledged."""

    try:
        payload = json.loads(record_body)
    except json.JSONDecodeError:
        logger.warning(
            "summary_consumer.invalid_json",
            message_id=message_id,
            receive_count=receive_count,
        )
        return True

    if isinstance(payload, dict) and payload.get("version") == 1:
        return _process_article_job(
            payload=payload,
            message_id=message_id,
            receive_count=receive_count,
            use_case=use_case,
            logger=logger,
            retry_policy=retry_policy,
        )

    # Backward-compatible path for legacy summarizer worker payloads.
    return process_sqs_record(
        record_body=record_body,
        message_id=message_id,
        receive_count=receive_count,
        use_case=use_case,
        logger=logger,
        retry_policy=retry_policy,
    )


def _process_article_job(
    *,
    payload: dict[str, Any],
    message_id: str,
    receive_count: int | None,
    use_case: Any,
    logger: StructuredLogger,
    retry_policy: RetryPolicy,
) -> bool:
    """Process v1 article summary job."""

    try:
        job = ArticleSummaryJob.from_payload(payload)
    except SummaryJobValidationError:
        logger.warning(
            "summary_consumer.invalid_job_payload",
            message_id=message_id,
            receive_count=receive_count,
        )
        return True

    try:
        result = execute_with_retries(
            lambda: use_case.process_summary_job(job),
            policy=retry_policy,
        )
    except Exception as exc:
        logger.exception(
            "summary_consumer.job_failed",
            message_id=message_id,
            receive_count=receive_count,
            content_hash=job.content_hash,
            summary_version=job.summary_version,
            error=exc.__class__.__name__,
        )
        return False

    logger.info(
        "summary_consumer.job_processed",
        message_id=message_id,
        receive_count=receive_count,
        content_hash=job.content_hash,
        summary_version=job.summary_version,
        status=getattr(result, "status", "UNKNOWN"),
    )
    return True


def _build_sqs_client(settings: Settings) -> Any:
    """Create SQS client for AWS or LocalStack."""

    import boto3

    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=settings.sqs_endpoint_url or settings.aws_endpoint_url or os.getenv("AWS_ENDPOINT_URL"),
    )


def _resolve_queue_url(settings: Settings, sqs_client: Any) -> str:
    """Resolve queue URL from settings or queue name."""

    if settings.summary_jobs_queue_url:
        return settings.summary_jobs_queue_url
    queue_name = os.getenv("SQS_QUEUE_NAME")
    if not queue_name:
        raise ValueError("Set APP_SUMMARY_JOBS_QUEUE_URL or SQS_QUEUE_NAME.")
    response = sqs_client.get_queue_url(QueueName=queue_name)
    return str(response["QueueUrl"])


if __name__ == "__main__":
    run_forever()
