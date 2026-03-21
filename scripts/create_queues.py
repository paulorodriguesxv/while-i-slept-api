"""Idempotently create the local/dev SQS queue."""

from __future__ import annotations

import os

import boto3
from botocore.exceptions import ClientError
from while_i_slept_api.core.logging import StructuredLogger

_LOGGER = StructuredLogger("while_i_slept.create_queues")


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
    queue_url: str | None = None
    try:
        queue_url = sqs.get_queue_url(QueueName=queue_name)["QueueUrl"]
        _LOGGER.info(f"Queue already exists: {queue_name} ({queue_url})")
    except sqs.exceptions.QueueDoesNotExist:
        queue_url = sqs.create_queue(QueueName=queue_name)["QueueUrl"]
        _LOGGER.info(f"Queue created: {queue_name} ({queue_url})")
    except ClientError as exc:
        raise RuntimeError(f"Unable to create or fetch queue {queue_name}.") from exc

    if not queue_url:
        raise RuntimeError(f"Queue URL missing for queue {queue_name}.")


if __name__ == "__main__":
    main()
