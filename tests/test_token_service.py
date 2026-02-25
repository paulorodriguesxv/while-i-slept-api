"""Unit tests for JWT token issuance and validation behavior."""

from __future__ import annotations

import jwt
import pytest

from while_i_slept_api.core.config import Settings
from while_i_slept_api.services.auth_errors import (
    ExpiredAccessTokenError,
    InvalidAccessTokenError,
    InvalidRefreshTokenError,
    InvalidTokenTypeError,
)
from while_i_slept_api.services.tokens import TokenService


def test_hs256_signing_uses_configured_algorithm() -> None:
    token_service = TokenService(Settings(jwt_secret="test-secret", jwt_algorithm="HS256"))
    token = token_service.create_access_token("usr_alg")

    header = jwt.get_unverified_header(token)

    assert header["alg"] == "HS256"


def test_wrong_secret_fails_validation() -> None:
    token = TokenService(Settings(jwt_secret="secret-a")).create_access_token("usr_1")
    verifier = TokenService(Settings(jwt_secret="secret-b"))

    with pytest.raises(InvalidAccessTokenError):
        verifier.verify_access_token(token)


def test_expired_access_token_is_rejected() -> None:
    token_service = TokenService(Settings(jwt_secret="test-secret", access_token_ttl_seconds=-5))
    token = token_service.create_access_token("usr_expired")

    with pytest.raises(ExpiredAccessTokenError):
        token_service.verify_access_token(token)


def test_invalid_refresh_token_is_rejected() -> None:
    token_service = TokenService(Settings(jwt_secret="test-secret"))

    with pytest.raises(InvalidRefreshTokenError) as exc_info:
        token_service.verify_refresh_token("not-a-jwt")

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "INVALID_REFRESH_TOKEN"


def test_token_type_mismatch_fails() -> None:
    token_service = TokenService(Settings(jwt_secret="test-secret"))
    refresh_token = token_service.create_refresh_token("usr_mismatch")
    access_token = token_service.create_access_token("usr_mismatch")

    with pytest.raises(InvalidTokenTypeError) as exc_info:
        token_service.verify_access_token(refresh_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "INVALID_TOKEN_TYPE"

    with pytest.raises(InvalidTokenTypeError):
        token_service.verify_refresh_token(access_token)


def test_token_payload_contains_correct_user_id() -> None:
    token_service = TokenService(Settings(jwt_secret="test-secret"))
    token = token_service.create_access_token("usr_payload")

    claims = token_service.decode_access_token(token)

    assert claims.user_id == "usr_payload"
    assert claims.token_type == "access"
