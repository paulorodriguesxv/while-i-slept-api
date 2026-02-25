"""Unit tests for briefing retrieval and free/premium item limits."""

from __future__ import annotations

from while_i_slept_api.core.config import Settings
from while_i_slept_api.domain.models import EntitlementState, UserProfile
from while_i_slept_api.repositories.memory import InMemoryBriefingRepository
from while_i_slept_api.services.briefings import BriefingService, build_sample_briefing
from while_i_slept_api.services.entitlements import EntitlementService


def _make_service(*, free_max: int = 5, premium_max: int = 15) -> tuple[BriefingService, InMemoryBriefingRepository]:
    settings = Settings(
        free_briefing_max_items=free_max,
        premium_briefing_max_items=premium_max,
        timezone_default="America/Sao_Paulo",
    )
    repo = InMemoryBriefingRepository()
    entitlement_service = EntitlementService(settings)
    return BriefingService(repo, entitlement_service, settings), repo


def test_free_user_briefing_today_is_limited_to_five_items() -> None:
    service, repo = _make_service(free_max=5, premium_max=15)
    user = UserProfile(
        user_id="usr_test",
        provider="google",
        provider_user_id="sub1",
        entitlements=EntitlementState(premium=False),
        created_at="2026-02-25T00:00:00Z",
        updated_at="2026-02-25T00:00:00Z",
    )
    today = service.today_date_for_user(user)
    repo.save(build_sample_briefing(user.user_id, today))

    briefing, max_items, is_premium = service.get_today(user)

    assert len(briefing.items) == 5
    assert max_items == 5
    assert is_premium is False


def test_premium_history_returns_more_items() -> None:
    service, repo = _make_service(free_max=5, premium_max=10)
    user = UserProfile(
        user_id="usr_premium",
        provider="apple",
        provider_user_id="sub2",
        entitlements=EntitlementState(premium=True),
        created_at="2026-02-25T00:00:00Z",
        updated_at="2026-02-25T00:00:00Z",
    )
    repo.save(build_sample_briefing(user.user_id, "2026-02-20"))

    briefing, max_items, is_premium = service.get_for_date(user=user, date_str="2026-02-20", history=True)

    assert len(briefing.items) == 10
    assert max_items == 10
    assert is_premium is True
