"""Unit tests for sleep-window resolver."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from while_i_slept_api.domain.models import SleepWindow
from while_i_slept_api.sleep_window.resolver import resolve_last_sleep_window


def test_resolve_last_sleep_window_before_wake_time() -> None:
    timezone = ZoneInfo("America/Sao_Paulo")
    prefs = SleepWindow(start="23:30", end="07:00", timezone="America/Sao_Paulo")
    now = datetime(2026, 3, 11, 6, 59, tzinfo=timezone)

    resolved = resolve_last_sleep_window(prefs, now=now)

    assert resolved.start == datetime(2026, 3, 9, 23, 30, tzinfo=timezone)
    assert resolved.end == datetime(2026, 3, 10, 7, 0, tzinfo=timezone)


def test_resolve_last_sleep_window_after_wake_time() -> None:
    timezone = ZoneInfo("America/Sao_Paulo")
    prefs = SleepWindow(start="23:30", end="07:00", timezone="America/Sao_Paulo")
    now = datetime(2026, 3, 11, 8, 0, tzinfo=timezone)

    resolved = resolve_last_sleep_window(prefs, now=now)

    assert resolved.start == datetime(2026, 3, 10, 23, 30, tzinfo=timezone)
    assert resolved.end == datetime(2026, 3, 11, 7, 0, tzinfo=timezone)


def test_resolve_last_sleep_window_handles_timezone_conversion() -> None:
    timezone = ZoneInfo("America/Sao_Paulo")
    prefs = SleepWindow(start="23:30", end="07:00", timezone="America/Sao_Paulo")
    now_utc = datetime(2026, 3, 11, 10, 30, tzinfo=UTC)  # 07:30 in Sao Paulo

    resolved = resolve_last_sleep_window(prefs, now=now_utc)

    assert resolved.start == datetime(2026, 3, 10, 23, 30, tzinfo=timezone)
    assert resolved.end == datetime(2026, 3, 11, 7, 0, tzinfo=timezone)


def test_resolve_last_sleep_window_midnight_crossing() -> None:
    prefs = SleepWindow(start="23:50", end="00:10", timezone="UTC")
    now = datetime(2026, 3, 11, 0, 30, tzinfo=UTC)

    resolved = resolve_last_sleep_window(prefs, now=now)

    assert resolved.start == datetime(2026, 3, 10, 23, 50, tzinfo=UTC)
    assert resolved.end == datetime(2026, 3, 11, 0, 10, tzinfo=UTC)
