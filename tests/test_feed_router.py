"""API tests for authenticated sleep-window feed endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from while_i_slept_api.api.routers import feed as feed_router
from while_i_slept_api.article_pipeline.feed_query.dto import SleepWindowRequest, SleepWindowResponse
from while_i_slept_api.dependencies.container import get_current_user
from while_i_slept_api.domain.models import EntitlementState
from while_i_slept_api.domain.models import SleepWindow as UserSleepWindow
from while_i_slept_api.domain.models import UserProfile
from while_i_slept_api.main import create_app
from while_i_slept_api.sleep_window.resolver import ResolvedSleepWindow


class _FakeSleepWindowUseCase:
    def __init__(self, response: SleepWindowResponse) -> None:
        self._response = response
        self.calls: list[SleepWindowRequest] = []

    def execute(self, request: SleepWindowRequest) -> SleepWindowResponse:
        self.calls.append(request)
        return self._response


class _FakeUserService:
    def __init__(self, profile: UserProfile | None) -> None:
        self._profile = profile
        self.calls: list[str] = []

    def get_required(self, user_id: str, *, status_code: int = 404) -> UserProfile:
        self.calls.append(user_id)
        if self._profile is None:
            raise AssertionError("profile missing")
        return self._profile


def _user(*, user_id: str = "usr_1", lang: str | None = "en") -> UserProfile:
    return UserProfile(
        user_id=user_id,
        provider="google",
        provider_user_id="sub_1",
        lang=lang,  # type: ignore[arg-type]
        created_at="2026-03-11T00:00:00Z",
        updated_at="2026-03-11T00:00:00Z",
    )


@pytest.fixture
def client_factory(monkeypatch: pytest.MonkeyPatch):
    def _build(
        *,
        feed_use_case: _FakeSleepWindowUseCase,
        user_service: _FakeUserService,
        current_user: UserProfile | None = None,
        calculated_window: ResolvedSleepWindow | None = None,
    ) -> tuple[TestClient, _FakeSleepWindowUseCase, _FakeUserService]:
        window = calculated_window or ResolvedSleepWindow(
            start=datetime(2026, 3, 10, 23, 30, tzinfo=UTC),
            end=datetime(2026, 3, 11, 7, 0, tzinfo=UTC),
        )
        monkeypatch.setattr(feed_router, "resolve_last_sleep_window", lambda *_args, **_kwargs: window)

        app = create_app()
        app.dependency_overrides[feed_router.get_sleep_window_use_case] = lambda: feed_use_case
        app.dependency_overrides[feed_router.get_user_service] = lambda: user_service
        app.dependency_overrides[get_current_user] = lambda: current_user or _user()
        return TestClient(app), feed_use_case, user_service

    return _build


def test_authenticated_user_receives_sleep_window_feed(client_factory) -> None:
    feed_use_case = _FakeSleepWindowUseCase(
        SleepWindowResponse(
            items=[
                {
                    "content_hash": "h1",
                    "title": "First",
                    "source": "Source",
                    "source_url": "https://example.com/1",
                    "published_at": datetime(2026, 3, 11, 2, 0, tzinfo=UTC),
                    "summary": "Summary 1",
                }
            ]
        )
    )
    profile = _user(user_id="usr_auth_1", lang="en")
    profile.sleep_window = UserSleepWindow(start="23:30", end="07:00", timezone="UTC")
    user_service = _FakeUserService(profile)
    client, fake_feed, fake_user_service = client_factory(
        feed_use_case=feed_use_case,
        user_service=user_service,
        current_user=_user(user_id="usr_auth_1", lang="en"),
    )

    response = client.get("/while-i-slept", params={"limit": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["content_hash"] == "h1"
    assert payload["sleep_window"]["start"].startswith("2026-03-10T23:30:00")
    assert payload["sleep_window"]["end"].startswith("2026-03-11T07:00:00")
    assert len(fake_feed.calls) == 1
    assert fake_feed.calls[0].limit == 3
    assert fake_feed.calls[0].language == "en"
    assert fake_user_service.calls == ["usr_auth_1"]


def test_while_i_slept_returns_404_when_preferences_missing(client_factory) -> None:
    feed_use_case = _FakeSleepWindowUseCase(SleepWindowResponse(items=[]))
    profile = _user()
    profile.sleep_window = None
    user_service = _FakeUserService(profile)
    client, fake_feed, fake_user_service = client_factory(
        feed_use_case=feed_use_case,
        user_service=user_service,
    )

    response = client.get("/while-i-slept")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PREFERENCES_NOT_FOUND"
    assert fake_feed.calls == []
    assert fake_user_service.calls == ["usr_1"]


def test_while_i_slept_extracts_user_id_from_authenticated_user(client_factory) -> None:
    feed_use_case = _FakeSleepWindowUseCase(SleepWindowResponse(items=[]))
    profile = _user(user_id="usr_from_token", lang="pt")
    profile.sleep_window = UserSleepWindow(start="22:45", end="06:15", timezone="UTC")
    user_service = _FakeUserService(profile)
    client, _, fake_user_service = client_factory(
        feed_use_case=feed_use_case,
        user_service=user_service,
        current_user=_user(user_id="usr_from_token", lang="pt"),
    )

    response = client.get("/while-i-slept")

    assert response.status_code == 200
    assert fake_user_service.calls == ["usr_from_token"]


def test_free_user_limit_is_capped(client_factory) -> None:
    feed_use_case = _FakeSleepWindowUseCase(SleepWindowResponse(items=[]))
    profile = _user(user_id="usr_free_cap", lang="en")
    profile.sleep_window = UserSleepWindow(start="23:00", end="07:00", timezone="UTC")
    profile.entitlements = EntitlementState(premium=False)
    user_service = _FakeUserService(profile)
    client, fake_feed, _ = client_factory(
        feed_use_case=feed_use_case,
        user_service=user_service,
        current_user=profile,
    )

    response = client.get("/while-i-slept", params={"limit": 25})

    assert response.status_code == 200
    assert len(fake_feed.calls) == 1
    assert fake_feed.calls[0].limit == 3


def test_premium_user_can_access_full_limit(client_factory) -> None:
    feed_use_case = _FakeSleepWindowUseCase(SleepWindowResponse(items=[]))
    profile = _user(user_id="usr_premium_full", lang="en")
    profile.sleep_window = UserSleepWindow(start="23:00", end="07:00", timezone="UTC")
    profile.entitlements = EntitlementState(premium=True)
    user_service = _FakeUserService(profile)
    client, fake_feed, _ = client_factory(
        feed_use_case=feed_use_case,
        user_service=user_service,
        current_user=profile,
    )

    response = client.get("/while-i-slept", params={"limit": 25})

    assert response.status_code == 200
    assert len(fake_feed.calls) == 1
    assert fake_feed.calls[0].limit == 25


def test_premium_user_is_capped_by_max_limit(client_factory) -> None:
    feed_use_case = _FakeSleepWindowUseCase(SleepWindowResponse(items=[]))
    profile = _user(user_id="usr_premium_cap", lang="en")
    profile.sleep_window = UserSleepWindow(start="23:00", end="07:00", timezone="UTC")
    profile.entitlements = EntitlementState(premium=True)
    user_service = _FakeUserService(profile)
    client, fake_feed, _ = client_factory(
        feed_use_case=feed_use_case,
        user_service=user_service,
        current_user=profile,
    )

    response = client.get("/while-i-slept", params={"limit": 200})

    assert response.status_code == 200
    assert len(fake_feed.calls) == 1
    assert fake_feed.calls[0].limit == 25


def test_default_limit_still_respects_free_cap(client_factory) -> None:
    feed_use_case = _FakeSleepWindowUseCase(SleepWindowResponse(items=[]))
    profile = _user(user_id="usr_free_default", lang="en")
    profile.sleep_window = UserSleepWindow(start="23:00", end="07:00", timezone="UTC")
    profile.entitlements = EntitlementState(premium=False)
    user_service = _FakeUserService(profile)
    client, fake_feed, _ = client_factory(
        feed_use_case=feed_use_case,
        user_service=user_service,
        current_user=profile,
    )

    response = client.get("/while-i-slept")

    assert response.status_code == 200
    assert len(fake_feed.calls) == 1
    assert fake_feed.calls[0].limit == 3


def test_default_limit_still_respects_premium_cap(client_factory) -> None:
    feed_use_case = _FakeSleepWindowUseCase(SleepWindowResponse(items=[]))
    profile = _user(user_id="usr_premium_default", lang="en")
    profile.sleep_window = UserSleepWindow(start="23:00", end="07:00", timezone="UTC")
    profile.entitlements = EntitlementState(premium=True)
    user_service = _FakeUserService(profile)
    client, fake_feed, _ = client_factory(
        feed_use_case=feed_use_case,
        user_service=user_service,
        current_user=profile,
    )

    response = client.get("/while-i-slept")

    assert response.status_code == 200
    assert len(fake_feed.calls) == 1
    assert fake_feed.calls[0].limit == 25
