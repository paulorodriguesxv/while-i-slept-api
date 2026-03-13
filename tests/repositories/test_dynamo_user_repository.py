"""Unit tests for DynamoUserRepository partial entitlement updates."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from while_i_slept_api.domain.models import EntitlementState, SleepWindow, UserProfile
from while_i_slept_api.repositories.dynamodb import DynamoUserRepository


class _ConditionalCheckFailedException(Exception):
    pass


class _FakeTable:
    def __init__(self) -> None:
        self._items: dict[tuple[str, str], dict[str, Any]] = {}
        self.put_calls = 0
        self.update_calls = 0
        self.meta = type(
            "_Meta",
            (),
            {
                "client": type(
                    "_Client",
                    (),
                    {
                        "exceptions": type(
                            "_Exceptions",
                            (),
                            {"ConditionalCheckFailedException": _ConditionalCheckFailedException},
                        )()
                    },
                )()
            },
        )()

    @staticmethod
    def _key_from(data: dict[str, Any]) -> tuple[str, str]:
        return data["pk"], data["sk"]

    def get_item(self, Key: dict[str, Any]) -> dict[str, Any]:
        item = self._items.get(self._key_from(Key))
        return {"Item": deepcopy(item)} if item else {}

    def put_item(self, Item: dict[str, Any], ConditionExpression: str | None = None) -> dict[str, Any]:
        self.put_calls += 1
        key = self._key_from(Item)
        if ConditionExpression and key in self._items:
            raise _ConditionalCheckFailedException()
        self._items[key] = deepcopy(Item)
        return {}

    def drop_attributes(self, key: tuple[str, str], *attrs: str) -> None:
        item = self._items[key]
        for attr in attrs:
            item.pop(attr, None)

    def update_item(
        self,
        *,
        Key: dict[str, Any],
        UpdateExpression: str,
        ExpressionAttributeValues: dict[str, Any],
        ConditionExpression: str | None = None,
        ReturnValues: str | None = None,
    ) -> dict[str, Any]:
        self.update_calls += 1
        _ = UpdateExpression
        _ = ReturnValues
        key = self._key_from(Key)
        if ConditionExpression and key not in self._items:
            raise _ConditionalCheckFailedException()
        item = deepcopy(self._items[key])
        item["premium_active"] = ExpressionAttributeValues[":premium_active"]
        item["premium_expires_at"] = ExpressionAttributeValues[":premium_expires_at"]
        item["premium_product_id"] = ExpressionAttributeValues[":premium_product_id"]
        item["premium_store"] = ExpressionAttributeValues[":premium_store"]
        item["premium_last_event_id"] = ExpressionAttributeValues[":premium_last_event_id"]
        item["premium_last_event_type"] = ExpressionAttributeValues[":premium_last_event_type"]
        item["premium_last_event_at"] = ExpressionAttributeValues[":premium_last_event_at"]
        item["premium_environment"] = ExpressionAttributeValues[":premium_environment"]
        item["updated_at"] = ExpressionAttributeValues[":updated_at"]
        self._items[key] = deepcopy(item)
        return {"Attributes": deepcopy(item)}


class _FakeFactory:
    def __init__(self, table: _FakeTable) -> None:
        self._table = table

    def users(self) -> _FakeTable:
        return self._table


def test_update_entitlements_updates_only_entitlement_fields() -> None:
    table = _FakeTable()
    repository = DynamoUserRepository(_FakeFactory(table))
    user = UserProfile(
        user_id="usr_dynamo_1",
        provider="google",
        provider_user_id="sub_1",
        email="user@example.com",
        name="Alice",
        lang="en",
        sleep_window=SleepWindow(start="22:30", end="06:30", timezone="UTC"),
        topics=["tech"],
        accepted_terms_version="v1",
        accepted_terms_at="2026-03-10T00:00:00Z",
        accepted_privacy_version="v1",
        accepted_privacy_at="2026-03-10T00:00:00Z",
        onboarding_completed=True,
        entitlements=EntitlementState(premium=False),
        created_at="2026-03-10T00:00:00Z",
        updated_at="2026-03-10T00:00:00Z",
    )
    repository.save(user)
    before = repository.get_by_id(user.user_id)
    assert before is not None

    updated = repository.update_entitlements(
        user.user_id,
        EntitlementState(
            premium=True,
            expires_at="2026-04-01T00:00:00Z",
            product_id="premium_monthly",
            store="apple",
            last_event_id="evt_123",
            last_event_type="RENEWAL",
            last_event_at=datetime(2026, 3, 12, 12, 0, tzinfo=UTC),
            environment="PRODUCTION",
        ),
    )
    after = repository.get_by_id(user.user_id)

    assert updated is not None
    assert after is not None
    assert table.update_calls == 1
    assert table.put_calls == 1
    assert after.email == before.email
    assert after.name == before.name
    assert after.lang == before.lang
    assert after.sleep_window == before.sleep_window
    assert after.topics == before.topics
    assert after.accepted_terms_version == before.accepted_terms_version
    assert after.accepted_privacy_version == before.accepted_privacy_version
    assert after.created_at == before.created_at
    assert after.entitlements.premium is True
    assert after.entitlements.expires_at == "2026-04-01T00:00:00Z"
    assert after.entitlements.product_id == "premium_monthly"
    assert after.entitlements.store == "apple"
    assert after.entitlements.last_event_id == "evt_123"
    assert after.entitlements.last_event_type == "RENEWAL"
    assert after.entitlements.last_event_at == datetime(2026, 3, 12, 12, 0, tzinfo=UTC)
    assert after.entitlements.environment == "PRODUCTION"
    assert after.updated_at != before.updated_at


def test_update_entitlements_creates_fields_if_missing() -> None:
    table = _FakeTable()
    repository = DynamoUserRepository(_FakeFactory(table))
    user = UserProfile(
        user_id="usr_dynamo_missing",
        provider="google",
        provider_user_id="sub_missing",
        created_at="2026-03-10T00:00:00Z",
        updated_at="2026-03-10T00:00:00Z",
    )
    repository.save(user)
    key = ("USER#usr_dynamo_missing", "PROFILE")
    table.drop_attributes(
        key,
        "premium_active",
        "premium_expires_at",
        "premium_product_id",
        "premium_store",
        "premium_last_event_id",
        "premium_last_event_type",
        "premium_last_event_at",
        "premium_environment",
    )

    updated = repository.update_entitlements(
        user.user_id,
        EntitlementState(
            premium=True,
            expires_at="2026-05-01T00:00:00Z",
            product_id="premium_yearly",
            store="google",
            last_event_id="evt_456",
            last_event_type="INITIAL_PURCHASE",
            last_event_at=datetime(2026, 3, 11, 8, 30, tzinfo=UTC),
            environment="SANDBOX",
        ),
    )

    assert updated is not None
    assert updated.entitlements.premium is True
    assert updated.entitlements.expires_at == "2026-05-01T00:00:00Z"
    assert updated.entitlements.product_id == "premium_yearly"
    assert updated.entitlements.store == "google"
    assert updated.entitlements.last_event_id == "evt_456"
    assert updated.entitlements.last_event_type == "INITIAL_PURCHASE"
    assert updated.entitlements.last_event_at == datetime(2026, 3, 11, 8, 30, tzinfo=UTC)
    assert updated.entitlements.environment == "SANDBOX"
