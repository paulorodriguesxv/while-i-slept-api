"""Idempotently create the local/dev articles table."""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError
from while_i_slept_api.core.config import Settings
from while_i_slept_api.core.logging import StructuredLogger

_LOGGER = StructuredLogger("while_i_slept.create_table")


def main() -> None:
    settings = Settings()
    region = settings.aws_region
    endpoint_url = settings.aws_endpoint_url
    table_name = settings.articles_table

    dynamodb = boto3.client("dynamodb", region_name=region, endpoint_url=endpoint_url)
    try:
        dynamodb.describe_table(TableName=table_name)
        _LOGGER.info(f"Table already exists: {table_name}")
        return
    except dynamodb.exceptions.ResourceNotFoundException:
        pass
    except ClientError as exc:
        raise RuntimeError(f"Unable to describe table {table_name}.") from exc

    try:
        dynamodb.create_table(
            TableName=table_name,
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
        )
        dynamodb.get_waiter("table_exists").wait(TableName=table_name)
    except ClientError as exc:
        raise RuntimeError(f"Unable to create table {table_name}.") from exc

    _LOGGER.info(f"Table created: {table_name}")


if __name__ == "__main__":
    main()
