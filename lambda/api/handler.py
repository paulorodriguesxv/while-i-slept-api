"""Lambda entrypoint for FastAPI API runtime."""

from __future__ import annotations

from mangum import Mangum

from while_i_slept_api.main import app

_handler = Mangum(app)


def handler(event: dict, context: object) -> dict:
    """Proxy API Gateway/Lambda Function URL events to ASGI app."""

    return _handler(event, context)
