"""API tests for sleep-window feed endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
import pytest

from while_i_slept_api.api.routers import feed as feed_router
from while_i_slept_api.article_pipeline.feed_query.dto import SleepWindowRequest, SleepWindowResponse
from while_i_slept_api.main import create_app


class _FakeSleepWindowUseCase:
    def __init__(self, response: SleepWindowResponse) -> None:
        self._response = response
        self.calls: list[SleepWindowRequest] = []

    def execute(self, request: SleepWindowRequest) -> SleepWindowResponse:
        self.calls.append(request)
        return self._response


@pytest.fixture
def client_factory(monkeypatch: pytest.MonkeyPatch):
    def _build(use_case: _FakeSleepWindowUseCase) -> tuple[TestClient, _FakeSleepWindowUseCase]:
        monkeypatch.setattr(feed_router, "build_sleep_window_use_case", lambda: use_case)
        return TestClient(create_app()), use_case

    return _build


def test_while_i_slept_returns_items_for_normal_window(client_factory) -> None:
    use_case = _FakeSleepWindowUseCase(
        SleepWindowResponse(
            items=[
                {
                    "content_hash": "h1",
                    "title": "First",
                    "source": "Source",
                    "source_url": "https://example.com/1",
                    "published_at": datetime(2026, 3, 10, 1, 30, tzinfo=UTC),
                    "summary": "Summary 1",
                }
            ]
        )
    )
    client, fake = client_factory(use_case)

    response = client.get(
        "/while-i-slept",
        params={
            "language": "en",
            "sleep_time": "2026-03-10T00:00:00Z",
            "wake_time": "2026-03-10T08:00:00Z",
        },
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["content_hash"] == "h1"
    assert len(fake.calls) == 1
    assert fake.calls[0].language == "en"
    assert fake.calls[0].start_time == datetime(2026, 3, 10, 0, 0, tzinfo=UTC)
    assert fake.calls[0].end_time == datetime(2026, 3, 10, 8, 0, tzinfo=UTC)
    assert fake.calls[0].limit == 50


def test_while_i_slept_returns_empty_result(client_factory) -> None:
    client, _ = client_factory(_FakeSleepWindowUseCase(SleepWindowResponse(items=[])))

    response = client.get(
        "/while-i-slept",
        params={
            "language": "pt",
            "sleep_time": "2026-03-10T00:00:00Z",
            "wake_time": "2026-03-10T08:00:00Z",
        },
    )

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_while_i_slept_returns_400_for_invalid_window(client_factory) -> None:
    client, fake = client_factory(_FakeSleepWindowUseCase(SleepWindowResponse(items=[])))

    response = client.get(
        "/while-i-slept",
        params={
            "language": "en",
            "sleep_time": "2026-03-10T08:00:00Z",
            "wake_time": "2026-03-10T08:00:00Z",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_SLEEP_WINDOW"
    assert fake.calls == []


def test_while_i_slept_respects_limit_parameter(client_factory) -> None:
    use_case = _FakeSleepWindowUseCase(SleepWindowResponse(items=[]))
    client, fake = client_factory(use_case)

    response = client.get(
        "/while-i-slept",
        params={
            "language": "en",
            "sleep_time": "2026-03-10T00:00:00Z",
            "wake_time": "2026-03-10T08:00:00Z",
            "limit": 3,
        },
    )

    assert response.status_code == 200
    assert len(fake.calls) == 1
    assert fake.calls[0].limit == 3


def test_while_i_slept_is_exposed_in_openapi(client_factory) -> None:
    client, _ = client_factory(_FakeSleepWindowUseCase(SleepWindowResponse(items=[])))

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/while-i-slept" in response.json()["paths"]
