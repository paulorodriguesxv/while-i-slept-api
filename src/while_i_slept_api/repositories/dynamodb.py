"""DynamoDB-backed repositories.

This module keeps all boto3 access out of routers/services.
"""

from __future__ import annotations

from datetime import UTC, datetime
from dataclasses import asdict
from decimal import Decimal
from typing import Any, cast

from while_i_slept_api.core.config import Settings
from while_i_slept_api.domain.models import (
    BriefingItem,
    BriefingRecord,
    BriefingSource,
    BriefingWindow,
    DeviceRegistration,
    EntitlementState,
    Provider,
    SleepWindow,
    UserProfile,
)
from while_i_slept_api.repositories.base import BriefingRepository, DeviceRepository, UserRepository


def _normalize_number(value: Any) -> Any:
    """Convert DynamoDB Decimal values into JSON-compatible Python numbers."""

    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, list):
        return [_normalize_number(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_number(item) for key, item in value.items()}
    return value


def _to_iso_utc(value: datetime | None) -> str | None:
    """Serialize datetime into UTC ISO8601 with Z suffix."""

    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _from_iso_utc(value: Any) -> datetime | None:
    """Parse UTC ISO8601 datetime strings from persistence storage."""

    if not isinstance(value, str) or not value:
        return None
    parsed = value
    if parsed.endswith("Z"):
        parsed = parsed[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(parsed)
    except ValueError:
        return None


class DynamoTableFactory:
    """Constructs DynamoDB table resources lazily."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._resource = None

    def _get_resource(self):
        if self._resource is None:
            import boto3  # Imported lazily so tests can run without boto3 installed.

            endpoint_url = self._settings.aws_endpoint_url
            self._resource = boto3.resource(
                "dynamodb",
                region_name=self._settings.aws_region,
                endpoint_url=endpoint_url,
            )
        return self._resource

    def users(self):
        return self._get_resource().Table(self._settings.users_table)

    def devices(self):
        return self._get_resource().Table(self._settings.devices_table)

    def briefings(self):
        return self._get_resource().Table(self._settings.briefings_table)


class DynamoUserRepository(UserRepository):
    """User repository backed by the DynamoDB users table."""

    def __init__(self, factory: DynamoTableFactory) -> None:
        self._table = factory.users()

    def get_by_id(self, user_id: str) -> UserProfile | None:
        response = self._table.get_item(Key={"pk": f"USER#{user_id}", "sk": "PROFILE"})
        item = response.get("Item")
        if not item:
            return None
        return self._from_item(cast(dict[str, Any], item))

    def get_by_provider_identity(self, provider: Provider, provider_user_id: str) -> UserProfile | None:
        from boto3.dynamodb.conditions import Key

        response = self._table.query(
            IndexName="GSI1",
            KeyConditionExpression=Key("GSI1PK").eq(f"IDP#{provider}#{provider_user_id}"),
            Limit=1,
        )
        items = response.get("Items") or []
        if not items:
            return None
        return self._from_item(cast(dict[str, Any], items[0]))

    def save(self, user: UserProfile) -> UserProfile:
        item = self._to_item(user)
        conditional_check_failed = self._table.meta.client.exceptions.ConditionalCheckFailedException
        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(pk)",
            )
        except conditional_check_failed:
            self._table.put_item(Item=item)
        return user

    def update_entitlements(self, user_id: str, entitlements: EntitlementState) -> UserProfile | None:
        updated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        conditional_check_failed = self._table.meta.client.exceptions.ConditionalCheckFailedException
        try:
            response = self._table.update_item(
                Key={"pk": f"USER#{user_id}", "sk": "PROFILE"},
                UpdateExpression=(
                    "SET premium_active = :premium_active, "
                    "premium_expires_at = :premium_expires_at, "
                    "premium_product_id = :premium_product_id, "
                    "premium_store = :premium_store, "
                    "premium_last_event_id = :premium_last_event_id, "
                    "premium_last_event_type = :premium_last_event_type, "
                    "premium_last_event_at = :premium_last_event_at, "
                    "premium_environment = :premium_environment, "
                    "updated_at = :updated_at"
                ),
                ExpressionAttributeValues={
                    ":premium_active": entitlements.premium,
                    ":premium_expires_at": entitlements.expires_at,
                    ":premium_product_id": entitlements.product_id,
                    ":premium_store": entitlements.store,
                    ":premium_last_event_id": entitlements.last_event_id,
                    ":premium_last_event_type": entitlements.last_event_type,
                    ":premium_last_event_at": _to_iso_utc(entitlements.last_event_at),
                    ":premium_environment": entitlements.environment,
                    ":updated_at": updated_at,
                },
                ConditionExpression="attribute_exists(pk) AND attribute_exists(sk)",
                ReturnValues="ALL_NEW",
            )
        except conditional_check_failed:
            return None

        item = response.get("Attributes")
        if not item:
            return self.get_by_id(user_id)
        return self._from_item(cast(dict[str, Any], item))

    def _to_item(self, user: UserProfile) -> dict[str, Any]:
        return {
            "pk": f"USER#{user.user_id}",
            "user_id": user.user_id,
            "sk": "PROFILE",
            "provider": user.provider,
            "provider_user_id": user.provider_user_id,
            "email": user.email,
            "name": user.name,
            "lang": user.lang,
            "sleep_start": user.sleep_window.start if user.sleep_window else None,
            "sleep_end": user.sleep_window.end if user.sleep_window else None,
            "timezone": user.sleep_window.timezone if user.sleep_window else None,
            "topics": user.topics,
            "accepted_terms_version": user.accepted_terms_version,
            "accepted_terms_at": user.accepted_terms_at,
            "accepted_privacy_version": user.accepted_privacy_version,
            "accepted_privacy_at": user.accepted_privacy_at,
            "onboarding_completed": user.onboarding_completed,
            "premium_active": user.entitlements.premium,
            "premium_expires_at": user.entitlements.expires_at,
            "premium_product_id": user.entitlements.product_id,
            "premium_store": user.entitlements.store,
            "premium_last_event_id": user.entitlements.last_event_id,
            "premium_last_event_type": user.entitlements.last_event_type,
            "premium_last_event_at": _to_iso_utc(user.entitlements.last_event_at),
            "premium_environment": user.entitlements.environment,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "GSI1PK": f"IDP#{user.provider}#{user.provider_user_id}",
            "GSI1SK": f"USER#{user.user_id}",
        }

    def _from_item(self, item: dict[str, Any]) -> UserProfile:
        normalized = _normalize_number(item)
        user_id = normalized.get("user_id")
        if not user_id and isinstance(normalized.get("pk"), str):
            pk_value = normalized["pk"]
            if pk_value.startswith("USER#"):
                user_id = pk_value.removeprefix("USER#")
        timezone = normalized.get("timezone")
        sleep_window = None
        if normalized.get("sleep_start") and normalized.get("sleep_end"):
            sleep_window = SleepWindow(
                start=normalized["sleep_start"],
                end=normalized["sleep_end"],
                timezone=timezone or "America/Sao_Paulo",
            )
        return UserProfile(
            user_id=user_id or "",
            provider=normalized["provider"],
            provider_user_id=normalized["provider_user_id"],
            email=normalized.get("email"),
            name=normalized.get("name"),
            lang=normalized.get("lang"),
            sleep_window=sleep_window,
            topics=normalized.get("topics"),
            accepted_terms_version=normalized.get("accepted_terms_version"),
            accepted_terms_at=normalized.get("accepted_terms_at"),
            accepted_privacy_version=normalized.get("accepted_privacy_version"),
            accepted_privacy_at=normalized.get("accepted_privacy_at"),
            onboarding_completed=bool(normalized.get("onboarding_completed", False)),
            entitlements=EntitlementState(
                premium=bool(normalized.get("premium_active", False)),
                expires_at=normalized.get("premium_expires_at"),
                product_id=normalized.get("premium_product_id"),
                store=normalized.get("premium_store"),
                last_event_id=normalized.get("premium_last_event_id"),
                last_event_type=normalized.get("premium_last_event_type"),
                last_event_at=_from_iso_utc(normalized.get("premium_last_event_at")),
                environment=normalized.get("premium_environment"),
            ),
            created_at=normalized.get("created_at", ""),
            updated_at=normalized.get("updated_at", ""),
        )


class DynamoDeviceRepository(DeviceRepository):
    """Device repository backed by the DynamoDB devices table."""

    def __init__(self, factory: DynamoTableFactory) -> None:
        self._table = factory.devices()

    def upsert(self, device: DeviceRegistration) -> DeviceRegistration:
        self._table.put_item(
            Item={
                "pk": f"USER#{device.user_id}",
                "user_id": device.user_id,
                "sk": f"DEVICE#{device.device_id}",
                "device_id": device.device_id,
                "platform": device.platform,
                "push_token": device.push_token,
                "app_version": device.app_version,
                "created_at": device.created_at,
                "updated_at": device.updated_at,
            }
        )
        return device

    def list_by_user(self, user_id: str) -> list[DeviceRegistration]:
        from boto3.dynamodb.conditions import Key

        response = self._table.query(
            KeyConditionExpression=Key("pk").eq(f"USER#{user_id}") & Key("sk").begins_with("DEVICE#"),
        )
        items = response.get("Items") or []
        devices: list[DeviceRegistration] = []
        for raw in items:
            item = _normalize_number(cast(dict[str, Any], raw))
            devices.append(
                DeviceRegistration(
                    user_id=item["user_id"],
                    device_id=item["device_id"],
                    platform=item["platform"],
                    push_token=item["push_token"],
                    app_version=item.get("app_version"),
                    created_at=item.get("created_at", ""),
                    updated_at=item.get("updated_at", ""),
                )
            )
        return devices


class DynamoBriefingRepository(BriefingRepository):
    """Briefing repository backed by the DynamoDB briefings table."""

    def __init__(self, factory: DynamoTableFactory) -> None:
        self._table = factory.briefings()

    def get_for_user_date(self, user_id: str, date: str) -> BriefingRecord | None:
        response = self._table.get_item(Key={"pk": f"USER#{user_id}", "sk": f"BRIEFING#{date}"})
        item = response.get("Item")
        if not item:
            return None
        normalized = _normalize_number(cast(dict[str, Any], item))
        items = [
            BriefingItem(
                story_id=story["story_id"],
                headline=story["headline"],
                summary_bullets=list(story["summary_bullets"]),
                score=float(story["score"]),
                sources=[BriefingSource(name=src["name"], url=src["url"]) for src in story["sources"]],
            )
            for story in normalized.get("items", [])
        ]
        return BriefingRecord(
            user_id=user_id,
            date=normalized["date"],
            lang=normalized["lang"],
            window=BriefingWindow(
                start=normalized["window_start"],
                end=normalized["window_end"],
            ),
            items=items,
            created_at=normalized.get("created_at", ""),
            updated_at=normalized.get("updated_at", ""),
        )

    def save(self, briefing: BriefingRecord) -> BriefingRecord:
        self._table.put_item(
            Item={
                "pk": f"USER#{briefing.user_id}",
                "sk": f"BRIEFING#{briefing.date}",
                "date": briefing.date,
                "lang": briefing.lang,
                "window_start": briefing.window.start,
                "window_end": briefing.window.end,
                "items": [
                    {
                        "story_id": item.story_id,
                        "headline": item.headline,
                        "summary_bullets": item.summary_bullets,
                        "score": Decimal(str(item.score)),
                        "sources": [asdict(source) for source in item.sources],
                    }
                    for item in briefing.items
                ],
                "created_at": briefing.created_at,
                "updated_at": briefing.updated_at,
            }
        )
        return briefing
