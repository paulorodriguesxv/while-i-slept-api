"""Purge all messages from configured SQS queue."""

from __future__ import annotations

import os

import boto3
from botocore.exceptions import ClientError
from while_i_slept_api.summarizer_worker.logging import StructuredLogger

_LOGGER = StructuredLogger("while_i_slept.purge_queue")


def _required_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or not value.strip():
        raise ValueError(f"{name} is required.")
    return value


def main() -> None:
    region = (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or os.getenv("APP_AWS_REGION")
        or "us-east-1"
    )
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    queue_name = _required_env("SQS_QUEUE_NAME", "summary-jobs")

    sqs = boto3.client("sqs", region_name=region, endpoint_url=endpoint_url)
    try:
        queue_url = sqs.get_queue_url(QueueName=queue_name)["QueueUrl"]
        sqs.purge_queue(QueueUrl=queue_url)
    except ClientError as exc:
        raise RuntimeError(f"Unable to purge queue {queue_name}.") from exc

    _LOGGER.info(f"Queue purged: {queue_name}")


if __name__ == "__main__":
    main()
