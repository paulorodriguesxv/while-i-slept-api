"""Resolve last completed sleep window from user preference window."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from while_i_slept_api.domain.models import SleepWindow


@dataclass(slots=True)
class ResolvedSleepWindow:
    """Concrete datetime interval for the latest completed sleep window."""

    start: datetime
    end: datetime


def _parse_hhmm(value: str) -> tuple[int, int]:
    parts = value.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {value!r}. Expected HH:MM.")
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError as exc:
        raise ValueError(f"Invalid time format: {value!r}. Expected HH:MM.") from exc
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Invalid time value: {value!r}.")
    return hour, minute


def resolve_last_sleep_window(
    sleep_window: SleepWindow,
    now: datetime | None = None,
) -> ResolvedSleepWindow:
    """Resolve the user's most recent completed sleep window in local timezone."""

    timezone = ZoneInfo(sleep_window.timezone)
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None or reference.tzinfo.utcoffset(reference) is None:
        # Keep behavior deterministic when callers pass a naive datetime.
        reference = reference.replace(tzinfo=UTC)
    local_now = reference.astimezone(timezone)

    sleep_hour, sleep_minute = _parse_hhmm(sleep_window.start)
    wake_hour, wake_minute = _parse_hhmm(sleep_window.end)

    today = local_now.date()
    today_wake = datetime.combine(today, time(wake_hour, wake_minute), tzinfo=timezone)

    if local_now >= today_wake:
        start_day = today - timedelta(days=1)
        end_day = today
    else:
        start_day = today - timedelta(days=2)
        end_day = today - timedelta(days=1)

    start = datetime.combine(start_day, time(sleep_hour, sleep_minute), tzinfo=timezone)
    end = datetime.combine(end_day, time(wake_hour, wake_minute), tzinfo=timezone)
    return ResolvedSleepWindow(start=start, end=end)
