"""Purge all messages from configured SQS queue."""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError
from while_i_slept_api.core.config import Settings
from while_i_slept_api.core.logging import StructuredLogger

_LOGGER = StructuredLogger("while_i_slept.purge_queue")


def main() -> None:
    settings = Settings()
    region = settings.aws_region
    endpoint_url = settings.aws_endpoint_url
    queue_name = settings.summary_jobs_queue_name

    sqs = boto3.client("sqs", region_name=region, endpoint_url=endpoint_url)
    try:
        queue_url = sqs.get_queue_url(QueueName=queue_name)["QueueUrl"]
        sqs.purge_queue(QueueUrl=queue_url)
    except ClientError as exc:
        raise RuntimeError(f"Unable to purge queue {queue_name}.") from exc

    _LOGGER.info(f"Queue purged: {queue_name}")


if __name__ == "__main__":
    main()
