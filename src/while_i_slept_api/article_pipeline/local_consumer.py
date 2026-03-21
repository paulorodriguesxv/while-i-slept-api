"""Local SQS consumer for article summary jobs."""

from __future__ import annotations

import argparse
from collections.abc import Callable
import os
import signal
import time
from typing import Any

from while_i_slept_api.article_pipeline.runtime import build_process_summary_use_case
from while_i_slept_api.article_pipeline.worker_processing import process_sqs_record
from while_i_slept_api.core.config import Settings, get_settings
from while_i_slept_api.core.logging import StructuredLogger

_DEFAULT_ONCE_MAX_EMPTY_POLLS = 2


def run_forever(settings: Settings | None = None) -> None:
    """Poll SQS forever and process messages."""

    _run_consumer(
        settings=settings,
        once=False,
        max_empty_polls=_DEFAULT_ONCE_MAX_EMPTY_POLLS,
    )


def run_once(
    settings: Settings | None = None,
    *,
    max_empty_polls: int = _DEFAULT_ONCE_MAX_EMPTY_POLLS,
) -> None:
    """Poll SQS until consecutive empty polls are reached."""

    if max_empty_polls < 1:
        raise ValueError("max_empty_polls must be >= 1.")

    _run_consumer(
        settings=settings,
        once=True,
        max_empty_polls=max_empty_polls,
    )


def _run_consumer(
    *,
    settings: Settings | None,
    once: bool,
    max_empty_polls: int,
) -> None:
    cfg = settings or get_settings()
    running = {"value": True}
    consecutive_empty_polls = 0
    logger = StructuredLogger("while_i_slept.summary.local_consumer")
    use_case = build_process_summary_use_case(cfg)
    sqs_client = _build_sqs_client(cfg)
    queue_url = _resolve_queue_url(cfg, sqs_client)

    def _shutdown_handler(_signum: int, _frame: Any) -> None:
        running["value"] = False
        logger.info("summary_consumer.stop_requested")

    signal.signal(signal.SIGINT, _shutdown_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _shutdown_handler)

    logger.info(
        "summary_consumer.started",
        queue_url=queue_url,
        mode="once" if once else "forever",
        max_empty_polls=max_empty_polls if once else None,
    )

    while running["value"]:
        has_messages = poll_once(
            sqs_client=sqs_client,
            queue_url=queue_url,
            logger=logger,
            use_case=use_case,
            max_attempts=cfg.summary_worker_retry_attempts,
            base_backoff_seconds=cfg.summary_worker_retry_backoff_seconds,
            wait_time_seconds=cfg.summary_worker_wait_time_seconds,
            visibility_timeout_seconds=cfg.summary_worker_visibility_timeout_seconds,
            max_number_of_messages=1,
        )

        if not once:
            continue

        if has_messages:
            consecutive_empty_polls = 0
            continue

        consecutive_empty_polls += 1
        logger.info(
            "summary_consumer.empty_poll",
            consecutive_empty_polls=consecutive_empty_polls,
            max_empty_polls=max_empty_polls,
        )
        if consecutive_empty_polls >= max_empty_polls:
            logger.info("summary_consumer.once_complete", max_empty_polls=max_empty_polls)
            break

    logger.info("summary_consumer.stopped")


def poll_once(
    *,
    sqs_client: Any,
    queue_url: str,
    logger: StructuredLogger,
    use_case: Any,
    max_attempts: int,
    base_backoff_seconds: float,
    wait_time_seconds: int,
    visibility_timeout_seconds: int,
    max_number_of_messages: int = 1,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> bool:
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
        return False

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
            max_attempts=max_attempts,
            base_backoff_seconds=base_backoff_seconds,
            sleep_fn=sleep_fn,
        )

        if should_ack and receipt_handle:
            sqs_client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)

    return True


def _build_sqs_client(settings: Settings) -> Any:
    import boto3

    return boto3.client("sqs", region_name=settings.aws_region)


def _resolve_queue_url(settings: Settings, sqs_client: Any) -> str:
    if settings.summary_jobs_queue_url:
        return settings.summary_jobs_queue_url

    summary_queue_url = os.getenv("SUMMARY_QUEUE_URL")
    if summary_queue_url:
        return summary_queue_url

    queue_name = os.getenv("SQS_QUEUE_NAME")
    if not queue_name:
        raise ValueError("Set APP_SUMMARY_JOBS_QUEUE_URL, SUMMARY_QUEUE_URL, or SQS_QUEUE_NAME.")

    response = sqs_client.get_queue_url(QueueName=queue_name)
    return str(response["QueueUrl"])


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local SQS consumer for article summary jobs.")
    parser.add_argument("--once", action="store_true", help="Exit after consecutive empty polls.")
    parser.add_argument(
        "--max-empty-polls",
        type=int,
        default=_DEFAULT_ONCE_MAX_EMPTY_POLLS,
        help="Consecutive empty polls before exit in --once mode (default: 2).",
    )
    args = parser.parse_args(argv)
    if args.max_empty_polls < 1:
        parser.error("--max-empty-polls must be >= 1.")
    return args


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.once:
        run_once(max_empty_polls=args.max_empty_polls)
        return
    run_forever()


if __name__ == "__main__":
    main()
