"""Idempotently create the local/dev articles table."""

from __future__ import annotations

import os

import boto3
from botocore.exceptions import ClientError


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
    table_name = _required_env("DYNAMO_TABLE_NAME", "articles")

    dynamodb = boto3.client("dynamodb", region_name=region, endpoint_url=endpoint_url)
    try:
        dynamodb.describe_table(TableName=table_name)
        print(f"Table already exists: {table_name}")
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

    print(f"Table created: {table_name}")


if __name__ == "__main__":
    main()
