"""Unit tests for entitlement gating logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.core.config import Settings
from while_i_slept_api.domain.models import EntitlementState
from while_i_slept_api.services.entitlements import EntitlementService


def test_is_premium_active_false_when_expired() -> None:
    service = EntitlementService(Settings())
    expired = (datetime.now(UTC) - timedelta(days=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    result = service.is_premium_active(EntitlementState(premium=True, expires_at=expired))

    assert result is False


def test_history_requires_premium() -> None:
    service = EntitlementService(Settings())

    with pytest.raises(ApiError) as exc_info:
        service.require_premium_history(EntitlementState(premium=False))

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"


def test_briefing_limit_uses_premium_limit_when_active() -> None:
    service = EntitlementService(Settings(premium_briefing_max_items=12))
    future = (datetime.now(UTC) + timedelta(days=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    max_items, is_premium = service.briefing_limit(EntitlementState(premium=True, expires_at=future))

    assert max_items == 12
    assert is_premium is True
