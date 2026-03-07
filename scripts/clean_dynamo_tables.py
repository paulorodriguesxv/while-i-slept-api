"""Delete all DynamoDB tables for local development environments."""

from __future__ import annotations

import os

import boto3


def _resolve_region() -> str:
    return (
        os.getenv("APP_AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or os.getenv("AWS_REGION")
        or "us-east-1"
    )


def _resolve_endpoint_url() -> str | None:
    return (
        os.getenv("APP_DYNAMODB_ENDPOINT_URL")
        or os.getenv("DYNAMODB_ENDPOINT_URL")
        or os.getenv("AWS_ENDPOINT_URL")
    )


def _list_all_tables(client: object) -> list[str]:
    tables: list[str] = []
    start_table_name: str | None = None

    while True:
        kwargs = {}
        if start_table_name:
            kwargs["ExclusiveStartTableName"] = start_table_name

        response = client.list_tables(**kwargs)
        tables.extend(response.get("TableNames", []))

        start_table_name = response.get("LastEvaluatedTableName")
        if not start_table_name:
            break

    return tables


def main() -> None:
    dynamodb = boto3.client(
        "dynamodb",
        region_name=_resolve_region(),
        endpoint_url=_resolve_endpoint_url(),
    )

    tables = _list_all_tables(dynamodb)
    if not tables:
        print("No DynamoDB tables found.")
        return

    for table_name in tables:
        print(f"Deleting table: {table_name}")
        dynamodb.delete_table(TableName=table_name)

    waiter = dynamodb.get_waiter("table_not_exists")
    for table_name in tables:
        waiter.wait(TableName=table_name)
        print(f"Deleted table: {table_name}")


if __name__ == "__main__":
    main()
