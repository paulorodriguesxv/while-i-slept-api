"""Lambda entrypoint for article job processor."""

from __future__ import annotations

from typing import Any

from while_i_slept_api.article_pipeline.article_processor_handler import lambda_handler


def handler(event: dict[str, Any], context: Any) -> dict[str, list[dict[str, str]]]:
    """Process article-job SQS records using article pipeline adapter."""

    return lambda_handler(event, context)
