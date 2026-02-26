"""Unit tests for entitlement gating logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.domain.models import EntitlementState
from while_i_slept_api.services.entitlements import EntitlementService


def test_is_premium_active_false_when_expired(entitlement_service: EntitlementService) -> None:
    expired = (datetime.now(UTC) - timedelta(days=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    result = entitlement_service.is_premium_active(EntitlementState(premium=True, expires_at=expired))

    assert result is False


def test_history_requires_premium(entitlement_service: EntitlementService) -> None:
    with pytest.raises(ApiError) as exc_info:
        entitlement_service.require_premium_history(EntitlementState(premium=False))

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_briefing_limit_uses_premium_limit_when_active() -> None:
    from while_i_slept_api.core.config import Settings

    service = EntitlementService(Settings(jwt_secret="f" * 32, premium_briefing_max_items=12))
    future = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    max_items, is_premium = service.briefing_limit(EntitlementState(premium=True, expires_at=future))

    assert max_items == 12
    assert is_premium is True


def test_invalid_expiry_string_keeps_premium_active(entitlement_service: EntitlementService) -> None:
    result = entitlement_service.is_premium_active(EntitlementState(premium=True, expires_at="not-a-date"))

    assert result is True


def test_naive_expiry_timestamp_is_assumed_utc(entitlement_service: EntitlementService) -> None:
    future_naive = (datetime.now(UTC) + timedelta(hours=1)).replace(tzinfo=None).isoformat(timespec="seconds")

    assert entitlement_service.is_premium_active(EntitlementState(premium=True, expires_at=future_naive)) is True


def test_history_allows_premium_user(entitlement_service: EntitlementService) -> None:
    entitlement_service.require_premium_history(EntitlementState(premium=True))
