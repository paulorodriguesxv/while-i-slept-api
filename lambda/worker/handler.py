"""Lambda entrypoint for summary worker."""

from __future__ import annotations

from typing import Any

from while_i_slept_api.article_pipeline.worker_handler import lambda_handler


def handler(event: dict[str, Any], context: Any) -> dict[str, list[dict[str, str]]]:
    """Process SQS records using the article pipeline worker adapter."""

    return lambda_handler(event, context)
