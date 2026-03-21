"""Structured logging helpers."""

from __future__ import annotations

import json
import logging
from typing import Any


class StructuredLogger:
    """Small structured logger wrapper emitting JSON records."""

    def __init__(self, name: str) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
        )        
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)        
        if not self._logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(message)s")
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

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
