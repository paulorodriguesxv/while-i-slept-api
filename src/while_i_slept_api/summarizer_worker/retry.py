"""Retry policy utility shared by worker adapters."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import time
from typing import TypeVar

from while_i_slept_api.summarizer_worker.errors import SummaryJobNonRetryableError, SummaryJobRetryableError

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Retry policy for transient failures."""

    max_attempts: int = 3
    base_backoff_seconds: float = 0.2


def execute_with_retries(
    fn: Callable[[], T],
    *,
    policy: RetryPolicy,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    """Execute callable with bounded retries for retryable errors."""

    if policy.max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn()
        except SummaryJobNonRetryableError:
            raise
        except SummaryJobRetryableError:
            if attempt >= policy.max_attempts:
                raise
            sleep_fn(policy.base_backoff_seconds * attempt)

    raise RuntimeError("unreachable")
