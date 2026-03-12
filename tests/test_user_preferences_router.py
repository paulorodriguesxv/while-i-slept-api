"""API tests for user sleep preferences endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from while_i_slept_api.api.routers import user_preferences as user_preferences_router
from while_i_slept_api.dependencies.container import get_current_user
from while_i_slept_api.domain.models import UserProfile
from while_i_slept_api.main import create_app
from while_i_slept_api.user_preferences.dto import SleepPreferencesRequest, SleepPreferencesResponse


def _current_user() -> UserProfile:
    return UserProfile(
        user_id="usr_1",
        provider="google",
        provider_user_id="sub_1",
        created_at="2026-03-11T00:00:00Z",
        updated_at="2026-03-11T00:00:00Z",
    )


class _FakeSetUseCase:
    def __init__(self) -> None:
        self.calls: list[tuple[str, SleepPreferencesRequest]] = []

    def execute(self, *, user_id: str, request: SleepPreferencesRequest) -> SleepPreferencesResponse:
        self.calls.append((user_id, request))
        return SleepPreferencesResponse(
            sleep_time=request.sleep_time,
            wake_time=request.wake_time,
            timezone=request.timezone,
        )


class _FakeGetUseCase:
    def __init__(self, response: SleepPreferencesResponse | None) -> None:
        self.response = response
        self.calls: list[str] = []

    def execute(self, *, user_id: str) -> SleepPreferencesResponse | None:
        self.calls.append(user_id)
        return self.response


@pytest.fixture
def client_factory(monkeypatch: pytest.MonkeyPatch):
    def _build(
        set_use_case: _FakeSetUseCase | None = None,
        get_use_case: _FakeGetUseCase | None = None,
    ) -> tuple[TestClient, _FakeSetUseCase, _FakeGetUseCase]:
        resolved_set = set_use_case or _FakeSetUseCase()
        resolved_get = get_use_case or _FakeGetUseCase(
            SleepPreferencesResponse(
                sleep_time="23:00",
                wake_time="07:00",
                timezone="America/Sao_Paulo",
            )
        )
        monkeypatch.setattr(
            user_preferences_router,
            "build_set_sleep_preferences_use_case",
            lambda: resolved_set,
        )
        monkeypatch.setattr(
            user_preferences_router,
            "build_get_sleep_preferences_use_case",
            lambda: resolved_get,
        )
        app = create_app()
        app.dependency_overrides[get_current_user] = _current_user
        return TestClient(app), resolved_set, resolved_get

    return _build


def test_set_sleep_preferences_saves_preferences(client_factory) -> None:
    client, set_use_case, _ = client_factory()

    response = client.post(
        "/users/me/sleep-preferences",
        json={
            "sleep_time": "23:00",
            "wake_time": "07:00",
            "timezone": "America/Sao_Paulo",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "sleep_time": "23:00",
        "wake_time": "07:00",
        "timezone": "America/Sao_Paulo",
    }
    assert len(set_use_case.calls) == 1
    assert set_use_case.calls[0][0] == "usr_1"


def test_get_sleep_preferences_loads_preferences(client_factory) -> None:
    client, _, get_use_case = client_factory(
        get_use_case=_FakeGetUseCase(
            SleepPreferencesResponse(
                sleep_time="22:30",
                wake_time="06:45",
                timezone="UTC",
            )
        )
    )

    response = client.get("/users/me/sleep-preferences")

    assert response.status_code == 200
    assert response.json() == {
        "sleep_time": "22:30",
        "wake_time": "06:45",
        "timezone": "UTC",
    }
    assert get_use_case.calls == ["usr_1"]


def test_set_sleep_preferences_returns_400_when_times_match(client_factory) -> None:
    client, set_use_case, _ = client_factory()

    response = client.post(
        "/users/me/sleep-preferences",
        json={
            "sleep_time": "07:00",
            "wake_time": "07:00",
            "timezone": "UTC",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_SLEEP_PREFERENCES"
    assert set_use_case.calls == []
