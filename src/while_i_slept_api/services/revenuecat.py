"""RevenueCat webhook handling and entitlement persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from while_i_slept_api.domain.models import EntitlementState
from while_i_slept_api.repositories.base import UserRepository
from while_i_slept_api.repositories.revenuecat_events import RevenueCatEventRepository
from while_i_slept_api.summarizer_worker.logging import StructuredLogger

ACTIVATION_EVENTS = {
    "INITIAL_PURCHASE",
    "RENEWAL",
    "NON_RENEWING_PURCHASE",
    "UNCANCELLATION",
    "SUBSCRIPTION_EXTENDED",
}
NON_STATE_EVENTS = {
    "CANCELLATION",
    "BILLING_ISSUE",
    "PRODUCT_CHANGE",
    "TRANSFER",
    "TEMPORARY_ENTITLEMENT_GRANT",
}
REVOCATION_EVENTS = {
    "EXPIRATION",
    "REFUND",
    "SUBSCRIPTION_PAUSED",
}


def _ms_to_iso(ms: int | None) -> str | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_ms(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _ms_to_datetime(ms: int | None) -> datetime | None:
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=UTC).replace(microsecond=0)


class RevenueCatService:
    """Processes RevenueCat webhook events into user entitlement snapshots."""

    def __init__(self, users: UserRepository, event_repo: RevenueCatEventRepository) -> None:
        self._users = users
        self._event_repo = event_repo
        self._logger = StructuredLogger("while_i_slept.revenuecat")

    def process_webhook(self, payload: dict[str, Any]) -> None:
        """Parse webhook payload and update user entitlements if possible."""

        if not isinstance(payload, dict):
            return
        raw_event = payload.get("event")
        event = raw_event if raw_event is not None else payload
        if not isinstance(event, dict):
            return

        event_id_raw = event.get("id")
        event_id = event_id_raw if isinstance(event_id_raw, str) and event_id_raw else None
        if event_id is not None:
            if not self._event_repo.record_event_once(event_id, event):
                self._logger.info("duplicate_event", event_id=event_id)
                return
            self._logger.info("event_recorded", event_id=event_id)
        else:
            self._logger.warning("missing_event_id")

        app_user_id = event.get("app_user_id") or event.get("original_app_user_id")
        if not isinstance(app_user_id, str) or not app_user_id:
            return

        user = self._users.get_by_id(app_user_id)
        if user is None:
            return

        event_type = str(event.get("type", "")).upper()
        store_raw = str(event.get("store", "")).lower()
        store: str | None
        if "app" in store_raw or store_raw == "apple":
            store = "apple"
        elif "play" in store_raw or store_raw == "google":
            store = "google"
        else:
            store = None

        expires_at = None
        expiration_at_ms = event.get("expiration_at_ms")
        if isinstance(expiration_at_ms, (int, float)):
            expires_at = _ms_to_iso(int(expiration_at_ms))
        elif isinstance(event.get("expires_date"), str):
            expires_at = event["expires_date"]

        event_timestamp_ms = _to_ms(event.get("event_timestamp_ms"))
        event_at = _ms_to_datetime(event_timestamp_ms)
        environment_raw = event.get("environment")
        environment = environment_raw if isinstance(environment_raw, str) and environment_raw else None
        event_type_value = event_type or None

        def _with_metadata(
            *,
            premium: bool,
            expires_at_value: str | None,
            product_id_value: str | None,
            store_value: str | None,
        ) -> EntitlementState:
            return EntitlementState(
                premium=premium,
                expires_at=expires_at_value,
                product_id=product_id_value,
                store=store_value,
                last_event_id=event_id,
                last_event_type=event_type_value,
                last_event_at=event_at,
                environment=environment,
            )

        if event_type in ACTIVATION_EVENTS:
            self._logger.info(
                "activation_event",
                event_type=event_type,
                app_user_id=user.user_id,
            )
            product_id = event.get("product_id")
            entitlements = _with_metadata(
                premium=True,
                expires_at_value=expires_at or user.entitlements.expires_at,
                product_id_value=product_id if isinstance(product_id, str) else user.entitlements.product_id,
                store_value=store or user.entitlements.store,
            )
            self._users.update_entitlements(user.user_id, entitlements)
            return

        if event_type in REVOCATION_EVENTS:
            self._logger.info(
                "revocation_event",
                event_type=event_type,
                app_user_id=user.user_id,
            )
            entitlements = _with_metadata(
                premium=False,
                expires_at_value=None,
                product_id_value=user.entitlements.product_id,
                store_value=user.entitlements.store,
            )
            self._users.update_entitlements(user.user_id, entitlements)
            return

        if event_type in NON_STATE_EVENTS:
            self._logger.info(
                "non_state_event",
                event_type=event_type,
                app_user_id=user.user_id,
            )
            entitlements = _with_metadata(
                premium=user.entitlements.premium,
                expires_at_value=user.entitlements.expires_at,
                product_id_value=user.entitlements.product_id,
                store_value=user.entitlements.store,
            )
            self._users.update_entitlements(user.user_id, entitlements)
            return

        self._logger.info(
            "unknown_event_type",
            event_type=event_type,
            app_user_id=user.user_id,
        )
        entitlements = _with_metadata(
            premium=user.entitlements.premium,
            expires_at_value=user.entitlements.expires_at,
            product_id_value=user.entitlements.product_id,
            store_value=user.entitlements.store,
        )
        self._users.update_entitlements(user.user_id, entitlements)
