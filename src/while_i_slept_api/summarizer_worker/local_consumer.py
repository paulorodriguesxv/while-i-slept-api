"""Local development SQS consumer for summary jobs."""

from __future__ import annotations

from collections.abc import Callable
import time
from typing import Any

from while_i_slept_api.core.config import Settings, get_settings
from while_i_slept_api.summarizer_worker.logging import StructuredLogger
from while_i_slept_api.summarizer_worker.message_processing import process_sqs_record
from while_i_slept_api.summarizer_worker.retry import RetryPolicy
from while_i_slept_api.summarizer_worker.runtime import build_use_case


def run_forever(settings: Settings | None = None) -> None:
    """Poll SQS forever and process one message at a time."""

    cfg = settings or get_settings()
    queue_url = cfg.summary_jobs_queue_url
    if not queue_url:
        raise ValueError("APP_SUMMARY_JOBS_QUEUE_URL is required for local consumer.")

    logger = StructuredLogger("while_i_slept.summarizer.local_consumer")
    use_case = build_use_case(cfg)
    retry_policy = RetryPolicy(
        max_attempts=cfg.summary_worker_retry_attempts,
        base_backoff_seconds=cfg.summary_worker_retry_backoff_seconds,
    )
    sqs_client = _build_sqs_client(cfg)

    logger.info("summary_consumer.started", queue_url=queue_url)
    try:
        while True:
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
    except KeyboardInterrupt:
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

        should_ack = process_sqs_record(
            record_body=body,
            message_id=message_id,
            receive_count=receive_count,
            use_case=use_case,
            logger=logger,
            retry_policy=retry_policy,
        )
        if should_ack and receipt_handle:
            sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)


def _build_sqs_client(settings: Settings) -> Any:
    """Create SQS client for AWS or LocalStack."""

    import boto3

    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=settings.sqs_endpoint_url or settings.aws_endpoint_url,
    )


if __name__ == "__main__":
    run_forever()
