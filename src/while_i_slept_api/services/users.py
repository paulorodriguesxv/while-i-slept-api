"""User profile, onboarding, and device registration operations."""

from __future__ import annotations

from dataclasses import replace

from while_i_slept_api.domain.models import DeviceRegistration, SleepWindow, UserProfile
from while_i_slept_api.repositories.base import DeviceRepository, UserRepository
from while_i_slept_api.services.utils import iso_now


class UserService:
    """Encapsulates user profile and onboarding update logic."""

    def __init__(self, users: UserRepository, devices: DeviceRepository, default_timezone: str) -> None:
        self._users = users
        self._devices = devices
        self._default_timezone = default_timezone

    def get_me(self, user: UserProfile) -> UserProfile:
        """Return the latest user profile from storage."""

        return self._users.get_by_id(user.user_id) or user

    def update_preferences(
        self,
        *,
        user: UserProfile,
        lang: str,
        sleep_start: str,
        sleep_end: str,
        timezone: str | None,
        topics: list[str] | None,
    ) -> UserProfile:
        """Update onboarding preferences and recompute onboarding completion."""

        now = iso_now()
        updated = replace(
            user,
            lang=lang,  # type: ignore[arg-type]
            sleep_window=SleepWindow(
                start=sleep_start,
                end=sleep_end,
                timezone=timezone or self._default_timezone,
            ),
            topics=topics,
            updated_at=now,
        )
        updated.onboarding_completed = self._is_onboarding_complete(updated)
        return self._users.save(updated)

    def accept_legal(self, *, user: UserProfile, terms_version: str, privacy_version: str) -> UserProfile:
        """Record legal acceptance and recompute onboarding completion."""

        now = iso_now()
        updated = replace(
            user,
            accepted_terms_version=terms_version,
            accepted_terms_at=now,
            accepted_privacy_version=privacy_version,
            accepted_privacy_at=now,
            updated_at=now,
        )
        updated.onboarding_completed = self._is_onboarding_complete(updated)
        return self._users.save(updated)

    def register_device(
        self,
        *,
        user: UserProfile,
        device_id: str,
        platform: str,
        push_token: str,
        app_version: str | None,
    ) -> None:
        """Register or update a device push token."""

        existing_created_at = iso_now()
        self._devices.upsert(
            DeviceRegistration(
                user_id=user.user_id,
                device_id=device_id,
                platform=platform,  # type: ignore[arg-type]
                push_token=push_token,
                app_version=app_version,
                created_at=existing_created_at,
                updated_at=iso_now(),
            )
        )

    def _is_onboarding_complete(self, user: UserProfile) -> bool:
        return (
            user.lang is not None
            and user.sleep_window is not None
            and user.accepted_terms
            and user.accepted_privacy
        )
