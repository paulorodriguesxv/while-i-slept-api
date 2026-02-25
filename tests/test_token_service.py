"""Unit tests for JWT token issuance and validation behavior."""

from __future__ import annotations

import pytest

from while_i_slept_api.core.config import Settings
from while_i_slept_api.services.auth_errors import ExpiredAccessTokenError, InvalidRefreshTokenError
from while_i_slept_api.services.tokens import TokenService


def test_expired_access_token_is_rejected() -> None:
    token_service = TokenService(Settings(jwt_secret="test-secret", access_token_ttl_seconds=-5))
    token = token_service.issue_access_token("usr_expired")

    with pytest.raises(ExpiredAccessTokenError):
        token_service.validate_access_token(token)


def test_invalid_refresh_token_is_rejected() -> None:
    token_service = TokenService(Settings(jwt_secret="test-secret"))

    with pytest.raises(InvalidRefreshTokenError) as exc_info:
        token_service.validate_refresh_token("not-a-jwt")

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "INVALID_REFRESH_TOKEN"


def test_token_payload_contains_correct_user_id() -> None:
    token_service = TokenService(Settings(jwt_secret="test-secret"))
    token = token_service.issue_access_token("usr_payload")

    claims = token_service.decode_access_token(token)

    assert claims.user_id == "usr_payload"
    assert claims.token_type == "access"
