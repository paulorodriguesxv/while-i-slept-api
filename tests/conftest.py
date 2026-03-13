"""Shared fixtures for unit tests."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from while_i_slept_api.core.config import Settings
from while_i_slept_api.domain.models import EntitlementState, SleepWindow, UserProfile
from while_i_slept_api.repositories.memory import (
    InMemoryBriefingRepository,
    InMemoryDeviceRepository,
    InMemoryUserRepository,
)
from while_i_slept_api.repositories.revenuecat_events import InMemoryRevenueCatEventRepository
from while_i_slept_api.services.auth import AuthService
from while_i_slept_api.services.briefings import BriefingService
from while_i_slept_api.services.entitlements import EntitlementService
from while_i_slept_api.services.oauth import OAuthVerifier
from while_i_slept_api.services.revenuecat import RevenueCatService
from while_i_slept_api.services.tokens import TokenService
from while_i_slept_api.services.users import UserService


@pytest.fixture
def settings() -> Settings:
    return Settings(
        jwt_secret="0123456789abcdef0123456789abcdef",
        jwt_algorithm="HS256",
        timezone_default="America/Sao_Paulo",
        free_briefing_max_items=5,
        premium_briefing_max_items=10,
        allow_insecure_oauth_tokens=False,
    )


@pytest.fixture
def user_repo() -> InMemoryUserRepository:
    return InMemoryUserRepository()


@pytest.fixture
def device_repo() -> InMemoryDeviceRepository:
    return InMemoryDeviceRepository()


@pytest.fixture
def briefing_repo() -> InMemoryBriefingRepository:
    return InMemoryBriefingRepository()


@pytest.fixture
def token_service(settings: Settings) -> TokenService:
    return TokenService(settings)


@pytest.fixture
def oauth_verifier(settings: Settings) -> OAuthVerifier:
    return OAuthVerifier(settings)


@pytest.fixture
def user_service(
    user_repo: InMemoryUserRepository,
    device_repo: InMemoryDeviceRepository,
    settings: Settings,
) -> UserService:
    return UserService(user_repo, device_repo, settings.timezone_default)


@pytest.fixture
def auth_service(
    user_service: UserService,
    token_service: TokenService,
    oauth_verifier: OAuthVerifier,
) -> AuthService:
    return AuthService(user_service=user_service, token_service=token_service, oauth_verifier=oauth_verifier)


@pytest.fixture
def entitlement_service(settings: Settings) -> EntitlementService:
    return EntitlementService(settings)


@pytest.fixture
def briefing_service(
    briefing_repo: InMemoryBriefingRepository,
    entitlement_service: EntitlementService,
    settings: Settings,
) -> BriefingService:
    return BriefingService(briefing_repo, entitlement_service, settings)


@pytest.fixture
def revenuecat_service(user_repo: InMemoryUserRepository) -> RevenueCatService:
    return RevenueCatService(user_repo, InMemoryRevenueCatEventRepository())


@pytest.fixture
def make_user(user_repo: InMemoryUserRepository) -> Callable[..., UserProfile]:
    def _make_user(
        *,
        user_id: str = "usr_test",
        provider: str = "google",
        provider_user_id: str = "provider_sub",
        premium: bool = False,
        expires_at: str | None = None,
        product_id: str | None = None,
        store: str | None = None,
        lang: str | None = None,
        sleep_window: SleepWindow | None = None,
        accepted_terms: bool = False,
        accepted_privacy: bool = False,
    ) -> UserProfile:
        user = UserProfile(
            user_id=user_id,
            provider=provider,  # type: ignore[arg-type]
            provider_user_id=provider_user_id,
            lang=lang,  # type: ignore[arg-type]
            sleep_window=sleep_window,
            entitlements=EntitlementState(
                premium=premium,
                expires_at=expires_at,
                product_id=product_id,
                store=store,  # type: ignore[arg-type]
            ),
            accepted_terms_version="v1" if accepted_terms else None,
            accepted_terms_at="2026-02-25T00:00:00Z" if accepted_terms else None,
            accepted_privacy_version="v1" if accepted_privacy else None,
            accepted_privacy_at="2026-02-25T00:00:00Z" if accepted_privacy else None,
            onboarding_completed=False,
            created_at="2026-02-25T00:00:00Z",
            updated_at="2026-02-25T00:00:00Z",
        )
        return user_repo.save(user)

    return _make_user
