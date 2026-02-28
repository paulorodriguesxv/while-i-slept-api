"""Structured logging helpers for worker modules."""

from __future__ import annotations

import json
import logging
from typing import Any


class StructuredLogger:
    """Small structured logger wrapper emitting JSON records."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def info(self, event: str, **fields: Any) -> None:
        """Log an info-level event."""

        self._emit(logging.INFO, event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        """Log a warning-level event."""

        self._emit(logging.WARNING, event, **fields)

    def exception(self, event: str, **fields: Any) -> None:
        """Log an exception event with traceback."""

        self._emit(logging.ERROR, event, exc_info=True, **fields)

    def _emit(self, level: int, event: str, *, exc_info: bool = False, **fields: Any) -> None:
        payload: dict[str, Any] = {"event": event, **fields}
        self._logger.log(level, json.dumps(payload, default=str, sort_keys=True), exc_info=exc_info)
