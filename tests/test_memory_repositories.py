"""Unit tests for in-memory repositories used by service-layer tests."""

from __future__ import annotations

from while_i_slept_api.domain.models import DeviceRegistration, EntitlementState, UserProfile
from while_i_slept_api.repositories.memory import (
    InMemoryBriefingRepository,
    InMemoryDeviceRepository,
    InMemoryUserRepository,
)
from while_i_slept_api.services.briefings import build_sample_briefing


def test_in_memory_user_repository_handles_missing_and_updates_entitlements() -> None:
    repo = InMemoryUserRepository()

    assert repo.get_by_id("missing") is None
    assert repo.get_by_provider_identity("google", "missing-sub") is None
    assert repo.update_entitlements("missing", EntitlementState(premium=True)) is None

    user = UserProfile(
        user_id="usr_repo_user",
        provider="google",
        provider_user_id="sub-repo",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    repo.save(user)

    updated = repo.update_entitlements(
        user.user_id,
        EntitlementState(premium=True, product_id="monthly_premium", store="google"),
    )

    assert updated is not None
    assert updated.entitlements.premium is True
    assert repo.get_by_provider_identity("google", "sub-repo") is not None


def test_in_memory_device_and_briefing_repositories_round_trip() -> None:
    device_repo = InMemoryDeviceRepository()
    stored_device = device_repo.upsert(
        DeviceRegistration(
            user_id="usr_repo_roundtrip",
            device_id="dev-rt",
            platform="android",
            push_token="token",
            app_version=None,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
    )
    assert stored_device.device_id == "dev-rt"
    assert len(device_repo.list_by_user("usr_repo_roundtrip")) == 1
    assert device_repo.list_by_user("usr_missing") == []

    briefing_repo = InMemoryBriefingRepository()
    assert briefing_repo.get_for_user_date("usr_repo_roundtrip", "2026-01-01") is None
    sample = build_sample_briefing("usr_repo_roundtrip", "2026-01-01")
    saved = briefing_repo.save(sample)
    fetched = briefing_repo.get_for_user_date("usr_repo_roundtrip", "2026-01-01")
    assert saved.date == "2026-01-01"
    assert fetched is not None
    assert fetched.items[0].story_id == "sty_1"
