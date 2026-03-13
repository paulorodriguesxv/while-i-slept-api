"""RevenueCat webhook idempotency repositories."""

from __future__ import annotations

from typing import Any, Protocol

from while_i_slept_api.services.utils import iso_now


class RevenueCatEventRepository(Protocol):
    """Persistence contract for RevenueCat webhook event idempotency."""

    def record_event_once(self, event_id: str, payload: dict[str, Any]) -> bool:
        """Record event id once; return False when event was already seen."""


class DynamoRevenueCatEventRepository:
    """DynamoDB implementation for RevenueCat webhook idempotency."""

    def __init__(self, table: Any) -> None:
        self._table = table

    def record_event_once(self, event_id: str, payload: dict[str, Any]) -> bool:
        event_type = payload.get("type")
        app_user_id = payload.get("app_user_id") or payload.get("original_app_user_id")
        environment = payload.get("environment")

        item: dict[str, Any] = {
            "pk": f"RC_EVENT#{event_id}",
            "sk": f"RC_EVENT#{event_id}",
            "event_id": event_id,
            "event_type": event_type if isinstance(event_type, str) else "",
            "app_user_id": app_user_id if isinstance(app_user_id, str) else "",
            "processed_at": iso_now(),
        }
        if isinstance(environment, str) and environment:
            item["environment"] = environment

        conditional_check_failed = self._table.meta.client.exceptions.ConditionalCheckFailedException
        try:
            self._table.put_item(Item=item, ConditionExpression="attribute_not_exists(pk)")
            return True
        except conditional_check_failed:
            return False


class InMemoryRevenueCatEventRepository:
    """In-memory implementation for tests and non-persistent environments."""

    def __init__(self) -> None:
        self._event_ids: set[str] = set()

    def record_event_once(self, event_id: str, payload: dict[str, Any]) -> bool:
        _ = payload
        if event_id in self._event_ids:
            return False
        self._event_ids.add(event_id)
        return True
