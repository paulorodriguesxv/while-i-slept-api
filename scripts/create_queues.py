"""Idempotently create the local/dev SQS queue."""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError
from while_i_slept_api.core.config import Settings
from while_i_slept_api.core.logging import StructuredLogger

_LOGGER = StructuredLogger("while_i_slept.create_queues")


def main() -> None:
    settings = Settings()
    region = settings.aws_region
    endpoint_url = settings.aws_endpoint_url
    queue_name = settings.summary_jobs_queue_name

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
