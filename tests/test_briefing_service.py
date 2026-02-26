"""Unit tests for briefing retrieval and free/premium item limits."""

from __future__ import annotations

import pytest

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.domain.models import EntitlementState, SleepWindow, UserProfile
from while_i_slept_api.services.briefings import BriefingService, build_sample_briefing


def test_free_user_briefing_today_is_limited_to_five_items(briefing_service: BriefingService, briefing_repo) -> None:
    user = UserProfile(
        user_id="usr_test",
        provider="google",
        provider_user_id="sub1",
        entitlements=EntitlementState(premium=False),
        created_at="2026-02-25T00:00:00Z",
        updated_at="2026-02-25T00:00:00Z",
    )
    today = briefing_service.today_date_for_user(user)
    briefing_repo.save(build_sample_briefing(user.user_id, today))

    briefing, max_items, is_premium = briefing_service.get_today(user)

    assert len(briefing.items) == 5
    assert max_items == 5
    assert is_premium is False


def test_premium_history_returns_more_items(briefing_service: BriefingService, briefing_repo) -> None:
    user = UserProfile(
        user_id="usr_premium",
        provider="apple",
        provider_user_id="sub2",
        entitlements=EntitlementState(premium=True),
        created_at="2026-02-25T00:00:00Z",
        updated_at="2026-02-25T00:00:00Z",
    )
    briefing_repo.save(build_sample_briefing(user.user_id, "2026-02-20"))

    briefing, max_items, is_premium = briefing_service.get_for_date(user=user, date_str="2026-02-20", history=True)

    assert len(briefing.items) == 10
    assert max_items == 10
    assert is_premium is True


def test_missing_briefing_returns_empty_with_default_window_and_lang(
    briefing_service: BriefingService,
    make_user,
) -> None:
    user = make_user(user_id="usr_empty")

    briefing, max_items, is_premium = briefing_service.get_for_date(
        user=user,
        date_str="2026-02-25",
        history=False,
    )

    assert briefing.date == "2026-02-25"
    assert briefing.lang == "pt"
    assert briefing.items == []
    assert briefing.window.start.endswith("-03:00")
    assert briefing.window.end.endswith("-03:00")
    assert "2026-02-24T23:00:00" in briefing.window.start
    assert "2026-02-25T07:00:00" in briefing.window.end
    assert max_items == 5
    assert is_premium is False


def test_compute_window_handles_non_overnight_sleep_window(briefing_service: BriefingService, make_user) -> None:
    user = make_user(
        user_id="usr_day_sleep",
        lang="en",
        sleep_window=SleepWindow(start="01:00", end="06:30", timezone="UTC"),
    )

    briefing, _, _ = briefing_service.get_for_date(user=user, date_str="2026-02-25", history=False)

    assert briefing.lang == "en"
    assert briefing.window.start == "2026-02-25T01:00:00+00:00"
    assert briefing.window.end == "2026-02-25T06:30:00+00:00"


def test_invalid_date_string_raises_validation_error(briefing_service: BriefingService, make_user) -> None:
    user = make_user(user_id="usr_bad_date")

    with pytest.raises(ApiError) as exc_info:
        briefing_service.get_for_date(user=user, date_str="2026-02-99", history=False)

    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "VALIDATION_ERROR"
