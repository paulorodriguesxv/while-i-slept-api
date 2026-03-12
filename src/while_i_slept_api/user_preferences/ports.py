"""Repository ports for user sleep preferences."""

from __future__ import annotations

from typing import Protocol


class SleepPreferencesRepository(Protocol):
    """Persistence operations for sleep preferences."""

    def save_preferences(
        self,
        user_id: str,
        sleep_time: str,
        wake_time: str,
        timezone: str,
    ) -> None:
        """Persist sleep preferences for a user."""

    def get_preferences(self, user_id: str) -> dict[str, str] | None:
        """Return stored sleep preferences for a user."""
