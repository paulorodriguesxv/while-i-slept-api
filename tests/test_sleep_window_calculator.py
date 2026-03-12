"""Unit tests for sleep-window calculator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from while_i_slept_api.sleep_window.calculator import calculate_last_sleep_window


def test_calculate_last_sleep_window_after_wake_time() -> None:
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime(2026, 3, 11, 9, 0, tzinfo=tz)

    result = calculate_last_sleep_window(
        sleep_time="23:30",
        wake_time="07:00",
        timezone="America/Sao_Paulo",
        now=now,
    )

    assert result.start == datetime(2026, 3, 10, 23, 30, tzinfo=tz)
    assert result.end == datetime(2026, 3, 11, 7, 0, tzinfo=tz)


def test_calculate_last_sleep_window_before_wake_time() -> None:
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime(2026, 3, 11, 6, 59, tzinfo=tz)

    result = calculate_last_sleep_window(
        sleep_time="23:30",
        wake_time="07:00",
        timezone="America/Sao_Paulo",
        now=now,
    )

    assert result.start == datetime(2026, 3, 9, 23, 30, tzinfo=tz)
    assert result.end == datetime(2026, 3, 10, 7, 0, tzinfo=tz)


def test_calculate_last_sleep_window_applies_timezone_conversion() -> None:
    tz = ZoneInfo("America/Sao_Paulo")
    now_utc = datetime(2026, 3, 11, 10, 30, tzinfo=UTC)  # 07:30 in Sao Paulo

    result = calculate_last_sleep_window(
        sleep_time="23:30",
        wake_time="07:00",
        timezone="America/Sao_Paulo",
        now=now_utc,
    )

    assert result.start == datetime(2026, 3, 10, 23, 30, tzinfo=tz)
    assert result.end == datetime(2026, 3, 11, 7, 0, tzinfo=tz)


def test_calculate_last_sleep_window_handles_midnight_crossing() -> None:
    now = datetime(2026, 3, 11, 0, 30, tzinfo=UTC)

    result = calculate_last_sleep_window(
        sleep_time="23:50",
        wake_time="00:10",
        timezone="UTC",
        now=now,
    )

    assert result.start == datetime(2026, 3, 10, 23, 50, tzinfo=UTC)
    assert result.end == datetime(2026, 3, 11, 0, 10, tzinfo=UTC)
    assert result.end - result.start == timedelta(minutes=20)


def test_calculate_last_sleep_window_is_deterministic_with_explicit_now() -> None:
    now = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)

    first = calculate_last_sleep_window(
        sleep_time="22:45",
        wake_time="06:15",
        timezone="UTC",
        now=now,
    )
    second = calculate_last_sleep_window(
        sleep_time="22:45",
        wake_time="06:15",
        timezone="UTC",
        now=now,
    )

    assert first == second
