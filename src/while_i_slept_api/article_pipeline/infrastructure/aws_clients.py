"""AWS client factory with endpoint override support."""

from __future__ import annotations

import os
from typing import Any

import boto3


def _resolve_region() -> str:
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or os.getenv("APP_AWS_REGION") or "us-east-1"


def _resolve_endpoint() -> str | None:
    return os.getenv("AWS_ENDPOINT_URL")


class AwsClientFactory:
    """Factory for boto3 clients/resources with optional endpoint override."""

    def __init__(self, *, region: str | None = None, endpoint_url: str | None = None) -> None:
        self._region = region or _resolve_region()
        self._endpoint_url = endpoint_url if endpoint_url is not None else _resolve_endpoint()

    def dynamodb_resource(self) -> Any:
        return boto3.resource(
            "dynamodb",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
        )

    def sqs_client(self) -> Any:
        return boto3.client(
            "sqs",
            region_name=self._region,
            endpoint_url=self._endpoint_url,
        )

