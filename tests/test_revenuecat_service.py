"""Unit tests for RevenueCat webhook parsing and entitlement updates."""

from __future__ import annotations

from typing import Any, cast

from while_i_slept_api.domain.models import EntitlementState
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


def test_revenuecat_negative_event_updates_google_store_and_expires_date(
    revenuecat_service: RevenueCatService,
    make_user,
    user_repo,
) -> None:
    user = make_user(
        user_id="usr_rc_negative",
        premium=True,
        expires_at="2099-01-01T00:00:00Z",
        product_id="old_product",
        store="apple",
    )
    payload = {
        "app_user_id": user.user_id,
        "type": "EXPIRATION",
        "store": "PLAY_STORE",
        "product_id": "monthly_premium",
        "expires_date": "2026-03-01T00:00:00Z",
    }

    revenuecat_service.process_webhook(payload)
    updated = user_repo.get_by_id(user.user_id)

    assert updated is not None
    assert updated.entitlements.premium is False
    assert updated.entitlements.store == "google"
    assert updated.entitlements.expires_at == "2026-03-01T00:00:00Z"
    assert updated.entitlements.product_id == "monthly_premium"


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
