"""Sleep-window calculator based on user preferences."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from while_i_slept_api.sleep_window.dto import SleepWindow


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


def calculate_last_sleep_window(
    sleep_time: str,
    wake_time: str,
    timezone: str,
    now: datetime | None = None,
) -> SleepWindow:
    """Return the user's most recent completed sleep window in local time."""

    user_tz = ZoneInfo(timezone)
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None or reference.tzinfo.utcoffset(reference) is None:
        # Treat naive datetimes as UTC to keep behavior deterministic.
        reference = reference.replace(tzinfo=UTC)
    local_now = reference.astimezone(user_tz)

    wake_hour, wake_minute = _parse_hhmm(wake_time)
    sleep_hour, sleep_minute = _parse_hhmm(sleep_time)

    today = local_now.date()
    today_wake = datetime.combine(today, time(wake_hour, wake_minute), tzinfo=user_tz)

    if local_now >= today_wake:
        start_day = today - timedelta(days=1)
        end_day = today
    else:
        start_day = today - timedelta(days=2)
        end_day = today - timedelta(days=1)

    start = datetime.combine(start_day, time(sleep_hour, sleep_minute), tzinfo=user_tz)
    end = datetime.combine(end_day, time(wake_hour, wake_minute), tzinfo=user_tz)
    return SleepWindow(start=start, end=end)
