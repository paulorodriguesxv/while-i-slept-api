"""Entitlement evaluation and premium gating rules."""

from __future__ import annotations

from datetime import UTC, datetime

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.core.config import Settings
from while_i_slept_api.domain.models import EntitlementState


def _parse_utc_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class EntitlementService:
    """Applies subscription business rules."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def is_premium_active(self, entitlements: EntitlementState) -> bool:
        """Return whether premium is currently active."""

        if not entitlements.premium:
            return False
        expires_at = _parse_utc_timestamp(entitlements.expires_at)
        if expires_at is None:
            return True
        return expires_at > datetime.now(UTC)

    def briefing_limit(self, entitlements: EntitlementState) -> tuple[int, bool]:
        """Return `(max_items, is_premium)` for briefing responses."""

        premium = self.is_premium_active(entitlements)
        if premium:
            return self._settings.premium_briefing_max_items, True
        return self._settings.free_briefing_max_items, False

    def require_premium_history(self, entitlements: EntitlementState) -> None:
        """Raise if history access should be blocked for non-premium users."""

        if not self.is_premium_active(entitlements):
            raise ApiError(status_code=403, code="FORBIDDEN", message="Premium subscription required.")
