"""Create DynamoDB tables for local development (LocalStack/DynamoDB Local)."""

from __future__ import annotations

import time
from typing import Any

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from while_i_slept_api.core.config import Settings
from while_i_slept_api.core.logging import StructuredLogger

_LOGGER = StructuredLogger("while_i_slept.create_tables")


def _dynamodb_client(settings: Settings):
    endpoint_url = settings.aws_endpoint_url
    region = settings.aws_region
    return boto3.client("dynamodb", region_name=region, endpoint_url=endpoint_url)


def _wait_for_endpoint(client, retries: int = 30, delay_seconds: float = 1.0) -> None:
    for attempt in range(1, retries + 1):
        try:
            client.list_tables()
            return
        except EndpointConnectionError:
            if attempt == retries:
                raise
            time.sleep(delay_seconds)


def _table_exists(client, table_name: str) -> bool:
    try:
        client.describe_table(TableName=table_name)
        return True
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code == "ResourceNotFoundException":
            return False
        raise


def _create_table_if_missing(client, spec: dict[str, Any]) -> None:
    table_name = spec["TableName"]
    if _table_exists(client, table_name):
        _LOGGER.info(f"[skip] table exists: {table_name}")
        return

    client.create_table(**spec)
    waiter = client.get_waiter("table_exists")
    waiter.wait(TableName=table_name)
    _LOGGER.info(f"[ok] created table: {table_name}")


def main() -> None:
    settings = Settings()
    users_table = settings.users_table
    devices_table = settings.devices_table
    briefings_table = settings.briefings_table

    client = _dynamodb_client(settings)
    _wait_for_endpoint(client)

    users_spec = {
        "TableName": users_table,
        "BillingMode": "PAY_PER_REQUEST",
        "AttributeDefinitions": [
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        "KeySchema": [
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    }

    devices_spec = {
        "TableName": devices_table,
        "BillingMode": "PAY_PER_REQUEST",
        "AttributeDefinitions": [
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        "KeySchema": [
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
    }

    briefings_spec = {
        "TableName": briefings_table,
        "BillingMode": "PAY_PER_REQUEST",
        "AttributeDefinitions": [
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        "KeySchema": [
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
    }

    _create_table_if_missing(client, users_spec)
    _create_table_if_missing(client, devices_spec)
    _create_table_if_missing(client, briefings_spec)


if __name__ == "__main__":
    main()
