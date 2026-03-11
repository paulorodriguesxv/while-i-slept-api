"""Use cases for user sleep preferences."""

from __future__ import annotations

from while_i_slept_api.user_preferences.dto import SleepPreferencesRequest, SleepPreferencesResponse
from while_i_slept_api.user_preferences.ports import SleepPreferencesRepository


class SetSleepPreferencesUseCase:
    """Store sleep preferences for a user."""

    def __init__(self, repository: SleepPreferencesRepository):
        self._repository = repository

    def execute(self, *, user_id: str, request: SleepPreferencesRequest) -> SleepPreferencesResponse:
        """Persist preferences and return stored payload."""

        self._repository.save_preferences(
            user_id=user_id,
            sleep_time=request.sleep_time,
            wake_time=request.wake_time,
            timezone=request.timezone,
        )
        return SleepPreferencesResponse(
            sleep_time=request.sleep_time,
            wake_time=request.wake_time,
            timezone=request.timezone,
        )


class GetSleepPreferencesUseCase:
    """Load sleep preferences for a user."""

    def __init__(self, repository: SleepPreferencesRepository):
        self._repository = repository

    def execute(self, *, user_id: str) -> SleepPreferencesResponse | None:
        """Return stored sleep preferences if present."""

        payload = self._repository.get_preferences(user_id)
        if payload is None:
            return None
        return SleepPreferencesResponse(
            sleep_time=payload["sleep_time"],
            wake_time=payload["wake_time"],
            timezone=payload["timezone"],
        )
