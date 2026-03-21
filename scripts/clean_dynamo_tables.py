"""Delete all DynamoDB tables for local development environments."""

from __future__ import annotations

import boto3

from while_i_slept_api.core.config import Settings
from while_i_slept_api.core.logging import StructuredLogger

_LOGGER = StructuredLogger("while_i_slept.clean_dynamo_tables")


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
    settings = Settings()
    dynamodb = boto3.client(
        "dynamodb",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
    )

    tables = _list_all_tables(dynamodb)
    if not tables:
        _LOGGER.info("No DynamoDB tables found.")
        return

    for table_name in tables:
        _LOGGER.info(f"Deleting table: {table_name}")
        dynamodb.delete_table(TableName=table_name)

    waiter = dynamodb.get_waiter("table_not_exists")
    for table_name in tables:
        waiter.wait(TableName=table_name)
        _LOGGER.info(f"Deleted table: {table_name}")


if __name__ == "__main__":
    main()
