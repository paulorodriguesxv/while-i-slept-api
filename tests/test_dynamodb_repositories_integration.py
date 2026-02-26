"""Integration tests for DynamoDB repositories against LocalStack."""

from __future__ import annotations

import os
from uuid import uuid4

import pytest

from while_i_slept_api.core.config import Settings
from while_i_slept_api.domain.models import (
    BriefingItem,
    BriefingRecord,
    BriefingSource,
    BriefingWindow,
    DeviceRegistration,
    EntitlementState,
    SleepWindow,
    UserProfile,
)
from while_i_slept_api.repositories.dynamodb import (
    DynamoBriefingRepository,
    DynamoDeviceRepository,
    DynamoTableFactory,
    DynamoUserRepository,
)

pytestmark = pytest.mark.integration


def _integration_settings() -> Settings:
    endpoint = (
        os.getenv("APP_DYNAMODB_ENDPOINT_URL")
        or os.getenv("DYNAMODB_ENDPOINT_URL")
        or os.getenv("AWS_ENDPOINT_URL")
    )
    if not endpoint:
        pytest.skip("DynamoDB endpoint env var not set for integration tests.")
    suffix = uuid4().hex[:8]
    return Settings(
        jwt_secret="integration-secret-0123456789abcdef",
        aws_region=os.getenv("APP_AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1",
        dynamodb_endpoint_url=endpoint,
        users_table=f"users_it_{suffix}",
        devices_table=f"devices_it_{suffix}",
        briefings_table=f"briefings_it_{suffix}",
    )


@pytest.fixture(scope="module")
def dynamo_factory() -> DynamoTableFactory:
    endpoint = os.getenv("APP_DYNAMODB_ENDPOINT_URL") or os.getenv("DYNAMODB_ENDPOINT_URL") or os.getenv("AWS_ENDPOINT_URL")
    if not endpoint:
        pytest.skip("DynamoDB endpoint env var not set for integration tests.")
    settings = _integration_settings()
    factory = DynamoTableFactory(settings)
    _ensure_test_tables(factory, settings)
    return factory


def _ensure_test_tables(factory: DynamoTableFactory, settings: Settings) -> None:
    resource = factory._get_resource()  # noqa: SLF001 - test-only setup helper
    client = resource.meta.client

    resource.create_table(
        TableName=settings.users_table,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
    )
    resource.create_table(
        TableName=settings.devices_table,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
    )
    resource.create_table(
        TableName=settings.briefings_table,
        BillingMode="PAY_PER_REQUEST",
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
    )
    waiter = client.get_waiter("table_exists")
    waiter.wait(TableName=settings.users_table)
    waiter.wait(TableName=settings.devices_table)
    waiter.wait(TableName=settings.briefings_table)


@pytest.fixture
def user_repo_dynamo(dynamo_factory: DynamoTableFactory) -> DynamoUserRepository:
    return DynamoUserRepository(dynamo_factory)


@pytest.fixture
def device_repo_dynamo(dynamo_factory: DynamoTableFactory) -> DynamoDeviceRepository:
    return DynamoDeviceRepository(dynamo_factory)


@pytest.fixture
def briefing_repo_dynamo(dynamo_factory: DynamoTableFactory) -> DynamoBriefingRepository:
    return DynamoBriefingRepository(dynamo_factory)


def test_dynamo_user_repository_save_lookup_gsi_and_entitlements(user_repo_dynamo: DynamoUserRepository) -> None:
    suffix = uuid4().hex[:8]
    user = UserProfile(
        user_id=f"usr_it_{suffix}",
        provider="google",
        provider_user_id=f"sub_{suffix}",
        email=f"user_{suffix}@example.com",
        name="Integration User",
        lang="pt",
        sleep_window=SleepWindow(start="23:00", end="07:00", timezone="America/Sao_Paulo"),
        topics=["tech"],
        onboarding_completed=True,
        entitlements=EntitlementState(premium=False),
        created_at="2026-02-25T00:00:00Z",
        updated_at="2026-02-25T00:00:00Z",
    )

    saved = user_repo_dynamo.save(user)
    by_id = user_repo_dynamo.get_by_id(user.user_id)
    by_gsi = user_repo_dynamo.get_by_provider_identity(user.provider, user.provider_user_id)

    assert saved.user_id == user.user_id
    assert by_id is not None and by_id.email == user.email
    assert by_gsi is not None and by_gsi.user_id == user.user_id

    updated = user_repo_dynamo.update_entitlements(
        user.user_id,
        EntitlementState(
            premium=True,
            expires_at="2026-03-03T12:00:00Z",
            product_id="monthly_premium",
            store="google",
        ),
    )
    assert updated is not None
    assert updated.entitlements.premium is True
    assert updated.entitlements.product_id == "monthly_premium"


def test_dynamo_device_repository_upsert_and_list(device_repo_dynamo: DynamoDeviceRepository) -> None:
    suffix = uuid4().hex[:8]
    user_id = f"usr_it_devices_{suffix}"
    first = DeviceRegistration(
        user_id=user_id,
        device_id="device-1",
        platform="ios",
        push_token="token-1",
        app_version="1.0.0",
        created_at="2026-02-25T00:00:00Z",
        updated_at="2026-02-25T00:00:00Z",
    )
    second = DeviceRegistration(
        user_id=user_id,
        device_id="device-2",
        platform="android",
        push_token="token-2",
        app_version=None,
        created_at="2026-02-25T00:00:00Z",
        updated_at="2026-02-25T00:00:00Z",
    )
    device_repo_dynamo.upsert(first)
    device_repo_dynamo.upsert(second)
    # Upsert same device to validate overwrite semantics.
    device_repo_dynamo.upsert(
        DeviceRegistration(
            user_id=user_id,
            device_id="device-1",
            platform="ios",
            push_token="token-1b",
            app_version="1.0.1",
            created_at="2026-02-25T00:00:00Z",
            updated_at="2026-02-26T00:00:00Z",
        )
    )

    devices = device_repo_dynamo.list_by_user(user_id)

    assert len(devices) == 2
    assert {device.device_id for device in devices} == {"device-1", "device-2"}
    assert next(device for device in devices if device.device_id == "device-1").push_token == "token-1b"


def test_dynamo_briefing_repository_save_and_get(briefing_repo_dynamo: DynamoBriefingRepository) -> None:
    suffix = uuid4().hex[:8]
    briefing = BriefingRecord(
        user_id=f"usr_it_brief_{suffix}",
        date="2026-02-25",
        lang="en",
        window=BriefingWindow(
            start="2026-02-24T23:00:00-03:00",
            end="2026-02-25T07:00:00-03:00",
        ),
        items=[
            BriefingItem(
                story_id="sty_it_1",
                headline="Integration story",
                summary_bullets=["b1", "b2"],
                score=0.8,
                sources=[BriefingSource(name="Example", url="https://example.com/1")],
            )
        ],
        created_at="2026-02-25T12:00:00Z",
        updated_at="2026-02-25T12:00:00Z",
    )

    saved = briefing_repo_dynamo.save(briefing)
    fetched = briefing_repo_dynamo.get_for_user_date(briefing.user_id, briefing.date)

    assert saved.user_id == briefing.user_id
    assert fetched is not None
    assert fetched.date == "2026-02-25"
    assert fetched.window.start == briefing.window.start
    assert len(fetched.items) == 1
    assert fetched.items[0].score == 0.8
