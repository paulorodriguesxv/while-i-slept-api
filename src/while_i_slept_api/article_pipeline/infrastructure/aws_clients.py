"""AWS client factory with endpoint override support."""

from __future__ import annotations

from typing import Any

import boto3

from while_i_slept_api.core.config import Settings


class AwsClientFactory:
    """Factory for boto3 clients/resources with optional endpoint override."""

    def __init__(
        self,
        *,
        region: str | None = None,
        endpoint_url: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._region = region or self._settings.aws_region
        self._endpoint_url = endpoint_url if endpoint_url is not None else self._settings.aws_endpoint_url

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
