"""Integration-style API tests for RevenueCat webhook endpoint behavior."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from while_i_slept_api.core.config import Settings, get_settings
from while_i_slept_api.dependencies.container import get_revenuecat_service
from while_i_slept_api.domain.models import UserProfile
from while_i_slept_api.main import create_app
from while_i_slept_api.repositories.memory import InMemoryUserRepository
from while_i_slept_api.repositories.revenuecat_events import InMemoryRevenueCatEventRepository
from while_i_slept_api.services.revenuecat import RevenueCatService

WEBHOOK_SECRET = "webhook-secret-test"


class _RecordingRevenueCatService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def process_webhook(self, payload: dict[str, Any]) -> None:
        self.calls.append(payload)


@pytest.fixture
def client_factory():
    def _build(service: Any) -> TestClient:
        app = create_app()
        app.dependency_overrides[get_settings] = lambda: Settings(revenuecat_webhook_secret=WEBHOOK_SECRET)
        app.dependency_overrides[get_revenuecat_service] = lambda: service
        return TestClient(app)

    return _build


def _payload(*, event_id: str = "evt_test_1", event_type: str = "INITIAL_PURCHASE") -> dict[str, Any]:
    return {
        "event": {
            "id": event_id,
            "type": event_type,
            "app_user_id": "user_123",
            "product_id": "premium_monthly",
            "store": "app_store",
            "environment": "SANDBOX",
            "event_timestamp_ms": 1700000000000,
        }
    }


def test_webhook_requires_secret_header(client_factory) -> None:
    service = _RecordingRevenueCatService()
    client = client_factory(service)

    response = client.post("/webhooks/revenuecat", json=_payload())

    assert response.status_code in {401, 422}


def test_webhook_rejects_invalid_secret(client_factory) -> None:
    service = _RecordingRevenueCatService()
    client = client_factory(service)

    response = client.post(
        "/webhooks/revenuecat",
        headers={"X-Webhook-Secret": "wrong-secret"},
        json=_payload(),
    )

    assert response.status_code == 401


def test_webhook_accepts_valid_secret(client_factory) -> None:
    service = _RecordingRevenueCatService()
    client = client_factory(service)

    response = client.post(
        "/webhooks/revenuecat",
        headers={"X-Webhook-Secret": WEBHOOK_SECRET},
        json=_payload(),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert len(service.calls) == 1


def test_webhook_returns_200_even_for_duplicate_event(client_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    user_repo = InMemoryUserRepository()
    user_repo.save(
        UserProfile(
            user_id="user_123",
            provider="google",
            provider_user_id="sub_123",
            created_at="2026-03-12T00:00:00Z",
            updated_at="2026-03-12T00:00:00Z",
        )
    )
    service = RevenueCatService(user_repo, InMemoryRevenueCatEventRepository())
    client = client_factory(service)
    payload = _payload(event_id="evt_duplicate_1")
    payload["event"]["environment"] = "PRODUCTION"

    first = client.post(
        "/webhooks/revenuecat",
        headers={"X-Webhook-Secret": WEBHOOK_SECRET},
        json=payload,
    )
    second = client.post(
        "/webhooks/revenuecat",
        headers={"X-Webhook-Secret": WEBHOOK_SECRET},
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200


def test_webhook_handles_unknown_event_type(client_factory) -> None:
    service = _RecordingRevenueCatService()
    client = client_factory(service)

    response = client.post(
        "/webhooks/revenuecat",
        headers={"X-Webhook-Secret": WEBHOOK_SECRET},
        json=_payload(event_id="evt_unknown_1", event_type="UNKNOWN_EVENT_TYPE"),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
