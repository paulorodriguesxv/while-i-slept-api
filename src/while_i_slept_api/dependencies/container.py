"""FastAPI dependency container."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.core.config import Settings, get_settings
from while_i_slept_api.domain.models import UserProfile
from while_i_slept_api.repositories.base import RepositoryBundle
from while_i_slept_api.repositories.dynamodb import (
    DynamoBriefingRepository,
    DynamoDeviceRepository,
    DynamoTableFactory,
    DynamoUserRepository,
)
from while_i_slept_api.repositories.memory import (
    InMemoryBriefingRepository,
    InMemoryDeviceRepository,
    InMemoryUserRepository,
)
from while_i_slept_api.repositories.revenuecat_events import (
    DynamoRevenueCatEventRepository,
    InMemoryRevenueCatEventRepository,
    RevenueCatEventRepository,
)
from while_i_slept_api.services.auth import AuthService
from while_i_slept_api.services.briefings import BriefingService
from while_i_slept_api.services.entitlements import EntitlementService
from while_i_slept_api.services.oauth import OAuthVerifier
from while_i_slept_api.services.revenuecat import RevenueCatService
from while_i_slept_api.services.tokens import TokenService
from while_i_slept_api.services.users import UserService


bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def get_repository_bundle_cached() -> RepositoryBundle:
    """Build and cache the repository bundle."""

    settings = get_settings()
    repo_backend = (settings.storage_backend or "memory").lower()
    if repo_backend == "dynamodb":
        factory = DynamoTableFactory(settings)
        return RepositoryBundle(
            users=DynamoUserRepository(factory),
            devices=DynamoDeviceRepository(factory),
            briefings=DynamoBriefingRepository(factory),
        )
    return RepositoryBundle(
        users=InMemoryUserRepository(),
        devices=InMemoryDeviceRepository(),
        briefings=InMemoryBriefingRepository(),
    )


def get_repositories() -> RepositoryBundle:
    """Dependency wrapper for repository bundle."""

    return get_repository_bundle_cached()


@lru_cache(maxsize=1)
def get_token_service_cached() -> TokenService:
    """Build and cache token service."""

    return TokenService(get_settings())


def get_token_service() -> TokenService:
    """Dependency wrapper for token service."""

    return get_token_service_cached()


@lru_cache(maxsize=1)
def get_oauth_verifier_cached() -> OAuthVerifier:
    """Build and cache OAuth verifier."""

    return OAuthVerifier(get_settings())


def get_oauth_verifier() -> OAuthVerifier:
    """Dependency wrapper for OAuth verifier."""

    return get_oauth_verifier_cached()


@lru_cache(maxsize=1)
def get_entitlement_service_cached() -> EntitlementService:
    """Build and cache entitlement service."""

    return EntitlementService(get_settings())


def get_entitlement_service() -> EntitlementService:
    """Dependency wrapper for entitlement service."""

    return get_entitlement_service_cached()


def get_user_service(
    repos: Annotated[RepositoryBundle, Depends(get_repositories)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> UserService:
    """Build user service."""

    return UserService(repos.users, repos.devices, settings.timezone_default)


def get_auth_service(
    user_service: Annotated[UserService, Depends(get_user_service)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
    oauth_verifier: Annotated[OAuthVerifier, Depends(get_oauth_verifier)],
) -> AuthService:
    """Build auth service."""

    return AuthService(user_service, token_service, oauth_verifier)


def get_briefing_service(
    repos: Annotated[RepositoryBundle, Depends(get_repositories)],
    entitlements: Annotated[EntitlementService, Depends(get_entitlement_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> BriefingService:
    """Build briefing service."""

    return BriefingService(repos.briefings, entitlements, settings)


def get_revenuecat_service(
    repos: Annotated[RepositoryBundle, Depends(get_repositories)],
) -> RevenueCatService:
    """Build RevenueCat service."""

    return RevenueCatService(repos.users, get_revenuecat_event_repository_cached())


@lru_cache(maxsize=1)
def get_revenuecat_event_repository_cached() -> RevenueCatEventRepository:
    """Build and cache RevenueCat event idempotency repository."""

    settings = get_settings()
    repo_backend = (settings.storage_backend or "memory").lower()
    if repo_backend == "dynamodb":
        factory = DynamoTableFactory(settings)
        return DynamoRevenueCatEventRepository(factory.users())
    return InMemoryRevenueCatEventRepository()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    token_service: Annotated[TokenService, Depends(get_token_service)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> UserProfile:
    """Authenticate request and load current user."""

    if credentials is None or not credentials.credentials:
        raise ApiError(status_code=401, code="UNAUTHORIZED", message="Missing access token.")
    user_id = token_service.verify_access_token(credentials.credentials)
    return user_service.get_required(user_id, status_code=401)
