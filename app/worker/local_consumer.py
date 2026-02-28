"""Local SQS consumer that reuses the existing summary job use case."""

from __future__ import annotations

import os
import signal
from typing import Any

import boto3

from while_i_slept_api.summarizer_worker.logging import StructuredLogger
from while_i_slept_api.summarizer_worker.message_processing import process_sqs_record
from while_i_slept_api.summarizer_worker.retry import RetryPolicy
from while_i_slept_api.summarizer_worker.runtime import build_use_case


def _required_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or not value.strip():
        raise ValueError(f"{name} is required.")
    return value


def main() -> None:
    logger = StructuredLogger("while_i_slept.worker.local_consumer")
    region = _required_env("AWS_REGION", "us-east-1")
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    queue_name = _required_env("SQS_QUEUE_NAME", "summary-jobs")
    wait_time = int(_required_env("SQS_WAIT_TIME_SECONDS", "20"))
    batch_size = int(_required_env("SQS_BATCH_SIZE", "1"))
    visibility_timeout = int(_required_env("SQS_VISIBILITY_TIMEOUT", "60"))
    retry_attempts = int(_required_env("SUMMARY_RETRY_ATTEMPTS", "3"))
    retry_backoff = float(_required_env("SUMMARY_RETRY_BACKOFF_SECONDS", "0.2"))

    running = {"value": True}

    def _shutdown_handler(_signum: int, _frame: Any) -> None:
        running["value"] = False
        logger.info("worker.stop_requested")

    signal.signal(signal.SIGINT, _shutdown_handler)

    sqs = boto3.client("sqs", region_name=region, endpoint_url=endpoint_url)
    queue_url = sqs.get_queue_url(QueueName=queue_name)["QueueUrl"]
    use_case = build_use_case()
    retry_policy = RetryPolicy(max_attempts=retry_attempts, base_backoff_seconds=retry_backoff)

    logger.info(
        "worker.started",
        queue_name=queue_name,
        queue_url=queue_url,
        batch_size=batch_size,
        wait_time_seconds=wait_time,
        visibility_timeout=visibility_timeout,
    )

    while running["value"]:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=batch_size,
            WaitTimeSeconds=wait_time,
            VisibilityTimeout=visibility_timeout,
            AttributeNames=["ApproximateReceiveCount"],
        )
        messages = response.get("Messages", [])
        for message in messages:
            message_id = str(message.get("MessageId", "unknown"))
            body = str(message.get("Body", ""))
            receipt_handle = message.get("ReceiptHandle")

            attributes = message.get("Attributes") or {}
            raw_receive_count = attributes.get("ApproximateReceiveCount") if isinstance(attributes, dict) else None
            receive_count: int | None = None
            if raw_receive_count is not None:
                try:
                    receive_count = int(str(raw_receive_count))
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
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)

    logger.info("worker.stopped")


if __name__ == "__main__":
    main()
