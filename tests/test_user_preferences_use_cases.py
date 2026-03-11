"""Unit tests for user sleep preferences use cases."""

from __future__ import annotations

from while_i_slept_api.user_preferences.dto import SleepPreferencesRequest
from while_i_slept_api.user_preferences.use_cases import GetSleepPreferencesUseCase, SetSleepPreferencesUseCase


class _FakePreferencesRepository:
    def __init__(self) -> None:
        self.saved_calls: list[dict[str, str]] = []
        self.saved: dict[str, dict[str, str]] = {}

    def save_preferences(
        self,
        user_id: str,
        sleep_time: str,
        wake_time: str,
        timezone: str,
    ) -> None:
        payload = {
            "sleep_time": sleep_time,
            "wake_time": wake_time,
            "timezone": timezone,
        }
        self.saved_calls.append({"user_id": user_id, **payload})
        self.saved[user_id] = payload

    def get_preferences(self, user_id: str) -> dict[str, str] | None:
        return self.saved.get(user_id)


def test_set_sleep_preferences_use_case_saves_preferences() -> None:
    repo = _FakePreferencesRepository()
    use_case = SetSleepPreferencesUseCase(repo)

    response = use_case.execute(
        user_id="usr_1",
        request=SleepPreferencesRequest(
            sleep_time="23:00",
            wake_time="07:00",
            timezone="America/Sao_Paulo",
        ),
    )

    assert response.sleep_time == "23:00"
    assert response.wake_time == "07:00"
    assert response.timezone == "America/Sao_Paulo"
    assert repo.saved_calls == [
        {
            "user_id": "usr_1",
            "sleep_time": "23:00",
            "wake_time": "07:00",
            "timezone": "America/Sao_Paulo",
        }
    ]


def test_get_sleep_preferences_use_case_loads_preferences() -> None:
    repo = _FakePreferencesRepository()
    repo.saved["usr_2"] = {
        "sleep_time": "22:30",
        "wake_time": "06:45",
        "timezone": "UTC",
    }
    use_case = GetSleepPreferencesUseCase(repo)

    response = use_case.execute(user_id="usr_2")

    assert response is not None
    assert response.sleep_time == "22:30"
    assert response.wake_time == "06:45"
    assert response.timezone == "UTC"
