"""Unit tests for auth exchange flow wiring and implicit signup."""

from __future__ import annotations

import pytest

from while_i_slept_api.services.auth import AuthService
from while_i_slept_api.services.auth_errors import InvalidTokenTypeError, UserNotFoundError
from while_i_slept_api.services.tokens import TokenService


def test_exchange_flow_with_stub_provider_creates_user_and_tokens(
    auth_service: AuthService,
    token_service: TokenService,
    user_repo,
) -> None:
    access_token, refresh_token, expires_in, user = auth_service.exchange_oauth(
        provider="google",
        id_token="stub:google-sub-1|user@example.com|Paulo",
    )

    assert user.user_id.startswith("usr_")
    assert user.provider == "google"
    assert user.provider_user_id == "google-sub-1"
    assert user.email == "user@example.com"
    assert user.name == "Paulo"
    assert expires_in == 3600
    assert token_service.verify_access_token(access_token) == user.user_id
    assert token_service.verify_refresh_token(refresh_token) == user.user_id
    assert user_repo.get_by_id(user.user_id) is not None


def test_refresh_flow_rejects_access_token(auth_service: AuthService, token_service: TokenService) -> None:
    access_token = token_service.create_access_token("usr_wrong_type")

    with pytest.raises(InvalidTokenTypeError):
        auth_service.refresh_access(access_token)


def test_refresh_flow_returns_new_access_token_for_existing_user(
    auth_service: AuthService,
    token_service: TokenService,
) -> None:
    _, refresh_token, _, user = auth_service.exchange_oauth(
        provider="google",
        id_token="stub:google-sub-refresh|refresh@example.com|Refresh User",
    )

    new_access_token, expires_in = auth_service.refresh_access(refresh_token)

    assert expires_in == token_service.access_ttl_seconds
    assert token_service.verify_access_token(new_access_token) == user.user_id


def test_refresh_flow_raises_user_not_found(auth_service: AuthService, token_service: TokenService) -> None:
    refresh_token = token_service.create_refresh_token("usr_missing")

    with pytest.raises(UserNotFoundError) as exc_info:
        auth_service.refresh_access(refresh_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "USER_NOT_FOUND"
