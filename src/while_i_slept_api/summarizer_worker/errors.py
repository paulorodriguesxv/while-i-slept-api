"""Error types for summarizer worker."""

from __future__ import annotations


class SummaryWorkerError(Exception):
    """Base error for summarizer worker."""


class SummaryJobPayloadError(SummaryWorkerError):
    """Raised when summary job payload is malformed or unsupported."""


class SummaryJobNonRetryableError(SummaryWorkerError):
    """Raised for processing errors that should not be retried."""


class SummaryJobRetryableError(SummaryWorkerError):
    """Raised for transient processing errors that can be retried."""
