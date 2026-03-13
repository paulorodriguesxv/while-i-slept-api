"""Domain models used by repositories and services."""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass, field
from typing import Literal

Provider = Literal["apple", "google"]
Platform = Literal["ios", "android"]
Language = Literal["pt", "en"]
Store = Literal["apple", "google"] | None


@dataclass(slots=True)
class SleepWindow:
    """User sleep window preference."""

    start: str
    end: str
    timezone: str


@dataclass(slots=True)
class EntitlementState:
    """Snapshot of subscription entitlements stored on the user."""

    premium: bool = False
    expires_at: str | None = None
    product_id: str | None = None
    store: Store = None
    last_event_id: str | None = None
    last_event_type: str | None = None
    last_event_at: datetime | None = None
    environment: str | None = None


@dataclass(slots=True)
class UserProfile:
    """User profile and onboarding state."""

    user_id: str
    provider: Provider
    provider_user_id: str
    email: str | None = None
    name: str | None = None
    lang: Language | None = None
    sleep_window: SleepWindow | None = None
    topics: list[str] | None = None
    accepted_terms_version: str | None = None
    accepted_terms_at: str | None = None
    accepted_privacy_version: str | None = None
    accepted_privacy_at: str | None = None
    onboarding_completed: bool = False
    entitlements: EntitlementState = field(default_factory=EntitlementState)
    created_at: str = ""
    updated_at: str = ""

    @property
    def accepted_terms(self) -> bool:
        """Whether terms were accepted."""

        return self.accepted_terms_version is not None

    @property
    def accepted_privacy(self) -> bool:
        """Whether privacy policy was accepted."""

        return self.accepted_privacy_version is not None


@dataclass(slots=True)
class DeviceRegistration:
    """Device registration data for push notifications."""

    user_id: str
    device_id: str
    platform: Platform
    push_token: str
    app_version: str | None
    created_at: str
    updated_at: str


@dataclass(slots=True)
class BriefingSource:
    """Source link for a story."""

    name: str
    url: str


@dataclass(slots=True)
class BriefingItem:
    """Precomputed story item."""

    story_id: str
    headline: str
    summary_bullets: list[str]
    score: float
    sources: list[BriefingSource]


@dataclass(slots=True)
class BriefingWindow:
    """Time window covered by a briefing."""

    start: str
    end: str


@dataclass(slots=True)
class BriefingRecord:
    """Stored briefing for a user and date."""

    user_id: str
    date: str
    lang: Language
    window: BriefingWindow
    items: list[BriefingItem]
    created_at: str
    updated_at: str


@dataclass(slots=True)
class OAuthIdentity:
    """Validated provider identity extracted from a social login token."""

    provider: Provider
    provider_user_id: str
    email: str | None
    name: str | None
