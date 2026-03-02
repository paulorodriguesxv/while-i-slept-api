"""Error types for article summary pipeline."""

from __future__ import annotations


class SummaryJobValidationError(ValueError):
    """Raised when summary job payload is invalid."""

