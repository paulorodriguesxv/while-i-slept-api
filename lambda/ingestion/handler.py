"""Lambda entrypoint for periodic RSS ingestion."""

from __future__ import annotations

from typing import Any

from while_i_slept_api.article_pipeline.ingestion_handler import lambda_handler


def handler(event: dict[str, Any] | None, context: Any) -> dict[str, Any]:
    """Process scheduled ingestion event using article pipeline adapter."""

    return lambda_handler(event, context)
