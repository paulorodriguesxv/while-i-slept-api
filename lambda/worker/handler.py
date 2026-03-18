"""Lambda entrypoint for summary worker."""

from __future__ import annotations

from typing import Any

from while_i_slept_api.summarizer_worker.lambda_handler import lambda_handler


def handler(event: dict[str, Any], context: Any) -> dict[str, list[dict[str, str]]]:
    """Process SQS records using the existing worker adapter."""

    return lambda_handler(event, context)
