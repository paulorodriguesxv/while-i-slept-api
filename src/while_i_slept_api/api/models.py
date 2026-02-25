"""Pydantic request/response models matching openapi.yaml."""

from __future__ import annotations

from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from while_i_slept_api.domain.models import BriefingRecord, EntitlementState, UserProfile


Provider = Literal["apple", "google"]
Platform = Literal["ios", "android"]
Language = Literal["pt", "en"]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class SleepWindowModel(BaseModel):
    start: str = Field(description="HH:MM")
    end: str = Field(description="HH:MM")
    timezone: str = Field(description="IANA timezone")

    @field_validator("start", "end")
    @classmethod
    def validate_time(cls, value: str) -> str:
        parts = value.split(":")
        if len(parts) != 2 or any(not p.isdigit() for p in parts):
            raise ValueError("Expected HH:MM")
        hour, minute = (int(part) for part in parts)
        if hour not in range(24) or minute not in range(60):
            raise ValueError("Invalid HH:MM time")
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("Invalid IANA timezone") from exc
        return value


class EntitlementsModel(BaseModel):
    premium: bool
    expires_at: str | None = None
    product_id: str | None = None
    store: Literal["apple", "google"] | None = None


class MeModel(BaseModel):
    id: str
    email: str | None = None
    name: str | None = None
    lang: Language | None = None
    sleep_window: SleepWindowModel | None = None
    topics: list[str] | None = None
    onboarding_completed: bool
    accepted_terms: bool
    accepted_privacy: bool
    entitlements: EntitlementsModel


class ExchangeDeviceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform: Platform | None = None
    app_version: str | None = None
    device_id: str | None = None


class AuthExchangeRequest(BaseModel):
    provider: Provider
    id_token: str
    device: ExchangeDeviceModel | None = None


class AuthExchangeResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    me: MeModel


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class UpdatePreferencesRequest(BaseModel):
    lang: Language
    sleep_window: SleepWindowModel
    topics: list[str] | None = None


class AcceptLegalRequest(BaseModel):
    terms_version: str
    privacy_version: str


class AcceptLegalResponse(BaseModel):
    accepted_terms: bool
    accepted_privacy: bool


class RegisterDeviceRequest(BaseModel):
    platform: Platform
    push_token: str
    device_id: str
    app_version: str | None = None


class RegisterDeviceResponse(BaseModel):
    ok: bool


class BriefingSourceModel(BaseModel):
    name: str
    url: str


class BriefingItemModel(BaseModel):
    story_id: str
    headline: str
    summary_bullets: list[str]
    score: float = Field(ge=0, le=1)
    sources: list[BriefingSourceModel]


class BriefingWindowModel(BaseModel):
    start: str
    end: str


class BriefingLimitsModel(BaseModel):
    max_items: int
    is_premium: bool


class BriefingResponse(BaseModel):
    date: str
    window: BriefingWindowModel
    lang: Language
    items: list[BriefingItemModel]
    limits: BriefingLimitsModel


class RevenueCatWebhookEvent(BaseModel):
    model_config = ConfigDict(extra="allow")


def entitlements_to_model(entitlements: EntitlementState) -> EntitlementsModel:
    """Map domain entitlements into API schema."""

    return EntitlementsModel(
        premium=entitlements.premium,
        expires_at=entitlements.expires_at,
        product_id=entitlements.product_id,
        store=entitlements.store,
    )


def me_to_model(user: UserProfile) -> MeModel:
    """Map a domain user profile into the OpenAPI Me response schema."""

    sleep_window = None
    if user.sleep_window is not None:
        sleep_window = SleepWindowModel(
            start=user.sleep_window.start,
            end=user.sleep_window.end,
            timezone=user.sleep_window.timezone,
        )
    return MeModel(
        id=user.user_id,
        email=user.email,
        name=user.name,
        lang=user.lang,
        sleep_window=sleep_window,
        topics=user.topics,
        onboarding_completed=user.onboarding_completed,
        accepted_terms=user.accepted_terms,
        accepted_privacy=user.accepted_privacy,
        entitlements=entitlements_to_model(user.entitlements),
    )


def briefing_to_model(record: BriefingRecord, *, max_items: int, is_premium: bool) -> BriefingResponse:
    """Map a domain briefing record into the OpenAPI response schema."""

    return BriefingResponse(
        date=record.date,
        window=BriefingWindowModel(start=record.window.start, end=record.window.end),
        lang=record.lang,
        items=[
            BriefingItemModel(
                story_id=item.story_id,
                headline=item.headline,
                summary_bullets=item.summary_bullets,
                score=item.score,
                sources=[BriefingSourceModel(name=src.name, url=src.url) for src in item.sources],
            )
            for item in record.items
        ],
        limits=BriefingLimitsModel(max_items=max_items, is_premium=is_premium),
    )
