"""Unit tests for RevenueCat webhook parsing and entitlement updates."""

from __future__ import annotations

from typing import Any, cast

from while_i_slept_api.domain.models import EntitlementState
from while_i_slept_api.repositories.memory import InMemoryUserRepository
from while_i_slept_api.repositories.revenuecat_events import InMemoryRevenueCatEventRepository
from while_i_slept_api.services.revenuecat import RevenueCatService, _ms_to_iso


def test_ms_to_iso_handles_none_and_timestamp() -> None:
    assert _ms_to_iso(None) is None
    assert _ms_to_iso(0) == "1970-01-01T00:00:00Z"


def test_revenuecat_positive_event_updates_entitlements_and_is_idempotent(
    revenuecat_service: RevenueCatService,
    make_user,
    user_repo,
) -> None:
    user = make_user(user_id="usr_rc_positive", premium=False)
    payload = {
        "event": {
            "id": "evt_positive_1",
            "app_user_id": user.user_id,
            "type": "INITIAL_PURCHASE",
            "store": "APP_STORE",
            "product_id": "monthly_premium",
            "expiration_at_ms": 1760000000000,
        }
    }

    revenuecat_service.process_webhook(payload)
    first = user_repo.get_by_id(user.user_id)
    revenuecat_service.process_webhook(payload)
    second = user_repo.get_by_id(user.user_id)

    assert first is not None and second is not None
    assert first.entitlements.premium is True
    assert first.entitlements.store == "apple"
    assert first.entitlements.product_id == "monthly_premium"
    assert first.entitlements.expires_at is not None
    assert second.entitlements == first.entitlements


def test_cancellation_does_not_remove_premium(
    revenuecat_service: RevenueCatService,
    make_user,
    user_repo,
) -> None:
    user = make_user(
        user_id="usr_rc_cancel",
        premium=True,
        expires_at="2099-01-01T00:00:00Z",
        product_id="old_product",
        store="apple",
    )
    payload = {
        "event": {
            "app_user_id": user.user_id,
            "type": "CANCELLATION",
            "store": "PLAY_STORE",
            "product_id": "monthly_premium",
            "expires_date": "2026-03-01T00:00:00Z",
        }
    }

    revenuecat_service.process_webhook(payload)
    updated = user_repo.get_by_id(user.user_id)

    assert updated is not None
    assert updated.entitlements == EntitlementState(
        premium=True,
        expires_at="2099-01-01T00:00:00Z",
        product_id="old_product",
        store="apple",
    )


def test_billing_issue_does_not_remove_premium(
    revenuecat_service: RevenueCatService,
    make_user,
    user_repo,
) -> None:
    user = make_user(
        user_id="usr_rc_billing_issue",
        premium=True,
        expires_at="2099-02-01T00:00:00Z",
        product_id="monthly_premium",
        store="google",
    )
    payload = {
        "event": {
            "app_user_id": user.user_id,
            "type": "BILLING_ISSUE",
            "store": "PLAY_STORE",
            "product_id": "monthly_premium",
        }
    }

    revenuecat_service.process_webhook(payload)
    updated = user_repo.get_by_id(user.user_id)

    assert updated is not None
    assert updated.entitlements == EntitlementState(
        premium=True,
        expires_at="2099-02-01T00:00:00Z",
        product_id="monthly_premium",
        store="google",
    )


def test_expiration_revokes_premium(
    revenuecat_service: RevenueCatService,
    make_user,
    user_repo,
) -> None:
    user = make_user(
        user_id="usr_rc_expiration",
        premium=True,
        expires_at="2099-03-01T00:00:00Z",
        product_id="monthly_premium",
        store="apple",
    )
    payload = {
        "event": {
            "app_user_id": user.user_id,
            "type": "EXPIRATION",
            "store": "PLAY_STORE",
            "product_id": "another_product",
            "expiration_at_ms": 1760000000000,
        }
    }

    revenuecat_service.process_webhook(payload)
    updated = user_repo.get_by_id(user.user_id)

    assert updated is not None
    assert updated.entitlements == EntitlementState(
        premium=False,
        expires_at=None,
        product_id="monthly_premium",
        store="apple",
    )


def test_renewal_extends_premium(
    revenuecat_service: RevenueCatService,
    make_user,
    user_repo,
) -> None:
    user = make_user(
        user_id="usr_rc_renewal",
        premium=True,
        expires_at="2026-01-01T00:00:00Z",
        product_id="old_product",
        store="apple",
    )
    payload = {
        "event": {
            "app_user_id": user.user_id,
            "type": "RENEWAL",
            "store": "PLAY_STORE",
            "product_id": "monthly_premium",
            "expiration_at_ms": 1770000000000,
        }
    }

    revenuecat_service.process_webhook(payload)
    updated = user_repo.get_by_id(user.user_id)

    assert updated is not None
    assert updated.entitlements.premium is True
    assert updated.entitlements.expires_at == _ms_to_iso(1770000000000)
    assert updated.entitlements.product_id == "monthly_premium"
    assert updated.entitlements.store == "google"


def test_revenuecat_unknown_event_preserves_existing_premium_and_store(
    revenuecat_service: RevenueCatService,
    make_user,
    user_repo,
) -> None:
    user = make_user(
        user_id="usr_rc_unknown",
        premium=True,
        expires_at="2026-04-01T00:00:00Z",
        product_id="prod_1",
        store="apple",
    )
    payload = {
        "app_user_id": user.user_id,
        "type": "SOMETHING_ELSE",
        "store": "WEB",
        "product_id": 1234,
    }

    revenuecat_service.process_webhook(payload)
    updated = user_repo.get_by_id(user.user_id)

    assert updated is not None
    assert updated.entitlements == EntitlementState(
        premium=True,
        expires_at="2026-04-01T00:00:00Z",
        product_id="prod_1",
        store="apple",
    )


def test_revenuecat_ignores_invalid_payload_shapes(
    revenuecat_service: RevenueCatService,
    make_user,
    user_repo,
) -> None:
    user = make_user(user_id="usr_rc_ignore")
    before = user_repo.get_by_id(user.user_id)

    revenuecat_service.process_webhook({"event": "not-a-dict"})
    revenuecat_service.process_webhook({"event": {}})
    revenuecat_service.process_webhook({"event": {"app_user_id": 123}})
    revenuecat_service.process_webhook({"event": {"app_user_id": "usr_missing"}})

    after = user_repo.get_by_id(user.user_id)
    assert before is not None and after is not None
    assert after.entitlements == before.entitlements


def test_revenuecat_ignores_non_dict_top_level_payload(revenuecat_service: RevenueCatService) -> None:
    revenuecat_service.process_webhook(cast(dict[str, Any], "not-a-dict"))


class _ToggleEventRepo:
    def __init__(self) -> None:
        self._calls = 0

    def record_event_once(self, event_id: str, payload: dict[str, Any]) -> bool:
        _ = event_id
        _ = payload
        self._calls += 1
        return self._calls == 1


class _CountingUserRepository(InMemoryUserRepository):
    def __init__(self) -> None:
        super().__init__()
        self.update_calls = 0

    def update_entitlements(self, user_id: str, entitlements: EntitlementState):
        self.update_calls += 1
        return super().update_entitlements(user_id, entitlements)


def test_duplicate_event_is_ignored(make_user) -> None:
    user_repo = _CountingUserRepository()
    event_repo = _ToggleEventRepo()
    service = RevenueCatService(user_repo, event_repo)
    user = make_user(user_id="usr_rc_dup", premium=False)
    user_repo.save(user)
    payload = {
        "event": {
            "id": "evt_123",
            "app_user_id": user.user_id,
            "type": "INITIAL_PURCHASE",
            "store": "APP_STORE",
            "product_id": "monthly_premium",
            "expiration_at_ms": 1760000000000,
        }
    }

    service.process_webhook(payload)
    first = user_repo.get_by_id(user.user_id)
    service.process_webhook(payload)
    second = user_repo.get_by_id(user.user_id)

    assert first is not None and second is not None
    assert first.entitlements.premium is True
    assert second.entitlements == first.entitlements
    assert user_repo.update_calls == 1


def test_duplicate_event_is_ignored_with_in_memory_event_repo(make_user) -> None:
    user_repo = _CountingUserRepository()
    event_repo = InMemoryRevenueCatEventRepository()
    service = RevenueCatService(user_repo, event_repo)
    user = make_user(user_id="usr_rc_dup_mem", premium=False)
    user_repo.save(user)
    payload = {
        "event": {
            "id": "evt_mem_1",
            "app_user_id": user.user_id,
            "type": "INITIAL_PURCHASE",
            "store": "APP_STORE",
            "product_id": "monthly_premium",
            "expiration_at_ms": 1760000000000,
        }
    }

    service.process_webhook(payload)
    service.process_webhook(payload)
    updated = user_repo.get_by_id(user.user_id)

    assert updated is not None
    assert updated.entitlements.premium is True
    assert user_repo.update_calls == 1
