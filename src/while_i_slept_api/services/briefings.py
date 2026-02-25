"""Briefing retrieval, time-window computation, and free/premium limits."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.core.config import Settings
from while_i_slept_api.domain.models import (
    BriefingItem,
    BriefingRecord,
    BriefingSource,
    BriefingWindow,
    UserProfile,
)
from while_i_slept_api.repositories.base import BriefingRepository
from while_i_slept_api.services.entitlements import EntitlementService
from while_i_slept_api.services.utils import iso_now


class BriefingService:
    """Loads precomputed briefings and applies entitlement limits."""

    def __init__(
        self,
        briefings: BriefingRepository,
        entitlements: EntitlementService,
        settings: Settings,
    ) -> None:
        self._briefings = briefings
        self._entitlements = entitlements
        self._settings = settings

    def today_date_for_user(self, user: UserProfile) -> str:
        """Return today's date in the user's preferred timezone."""

        timezone = ZoneInfo(self._user_timezone(user))
        return datetime.now(timezone).date().isoformat()

    def get_today(self, user: UserProfile) -> tuple[BriefingRecord, int, bool]:
        """Return today's briefing limited by free/premium entitlements."""

        date_str = self.today_date_for_user(user)
        return self.get_for_date(user=user, date_str=date_str, history=False)

    def get_for_date(self, *, user: UserProfile, date_str: str, history: bool) -> tuple[BriefingRecord, int, bool]:
        """Return a briefing for a date; premium gate applies to history."""

        self._validate_date_string(date_str)
        if history:
            self._entitlements.require_premium_history(user.entitlements)
        max_items, is_premium = self._entitlements.briefing_limit(user.entitlements)
        briefing = self._briefings.get_for_user_date(user.user_id, date_str)
        if briefing is None:
            briefing = self._empty_briefing(user=user, date_str=date_str)
        limited = replace(briefing, items=briefing.items[:max_items])
        return limited, max_items, is_premium

    def _empty_briefing(self, *, user: UserProfile, date_str: str) -> BriefingRecord:
        """Synthesize an empty briefing when no precomputed record exists."""

        window = self._compute_window(user=user, date_str=date_str)
        lang = user.lang or "pt"
        now = iso_now()
        return BriefingRecord(
            user_id=user.user_id,
            date=date_str,
            lang=lang,
            window=window,
            items=[],
            created_at=now,
            updated_at=now,
        )

    def _compute_window(self, *, user: UserProfile, date_str: str) -> BriefingWindow:
        timezone = ZoneInfo(self._user_timezone(user))
        sleep_start = (user.sleep_window.start if user.sleep_window else "23:00")
        sleep_end = (user.sleep_window.end if user.sleep_window else "07:00")
        end_hour, end_minute = self._parse_hhmm(sleep_end)
        start_hour, start_minute = self._parse_hhmm(sleep_start)

        target_day = date.fromisoformat(date_str)
        end_local = datetime.combine(target_day, time(end_hour, end_minute), tzinfo=timezone)

        start_day = target_day
        if (start_hour, start_minute) >= (end_hour, end_minute):
            start_day = target_day - timedelta(days=1)
        start_local = datetime.combine(start_day, time(start_hour, start_minute), tzinfo=timezone)
        return BriefingWindow(
            start=start_local.isoformat(),
            end=end_local.isoformat(),
        )

    def _user_timezone(self, user: UserProfile) -> str:
        if user.sleep_window and user.sleep_window.timezone:
            return user.sleep_window.timezone
        return self._settings.timezone_default

    @staticmethod
    def _parse_hhmm(value: str) -> tuple[int, int]:
        hour_s, minute_s = value.split(":")
        return int(hour_s), int(minute_s)

    @staticmethod
    def _validate_date_string(value: str) -> None:
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ApiError(
                status_code=422,
                code="VALIDATION_ERROR",
                message="Request validation failed.",
                details={"date": "Invalid YYYY-MM-DD date."},
            ) from exc


def build_sample_briefing(user_id: str, date_str: str) -> BriefingRecord:
    """Helper for local demos/tests to seed a sample briefing record."""

    return BriefingRecord(
        user_id=user_id,
        date=date_str,
        lang="pt",
        window=BriefingWindow(
            start=f"{date_str}T00:00:00-03:00",
            end=f"{date_str}T08:00:00-03:00",
        ),
        items=[
            BriefingItem(
                story_id=f"sty_{i}",
                headline=f"Story {i}",
                summary_bullets=["Bullet 1", "Bullet 2"],
                score=0.9,
                sources=[BriefingSource(name="Example", url="https://example.com/story")],
            )
            for i in range(1, 13)
        ],
        created_at=iso_now(),
        updated_at=iso_now(),
    )
