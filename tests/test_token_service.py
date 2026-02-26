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


def test_hs256_signing_uses_configured_algorithm(token_service: TokenService) -> None:
    token = token_service.create_access_token("usr_alg")

    header = jwt.get_unverified_header(token)

    assert header["alg"] == "HS256"


def test_wrong_secret_fails_validation() -> None:
    token = TokenService(Settings(jwt_secret="a" * 32, jwt_algorithm="HS256")).create_access_token("usr_1")
    verifier = TokenService(Settings(jwt_secret="b" * 32, jwt_algorithm="HS256"))

    with pytest.raises(InvalidAccessTokenError):
        verifier.verify_access_token(token)


def test_expired_access_token_is_rejected() -> None:
    token_service = TokenService(Settings(jwt_secret="c" * 32, access_token_ttl_seconds=-5))
    token = token_service.create_access_token("usr_expired")

    with pytest.raises(ExpiredAccessTokenError):
        token_service.verify_access_token(token)


def test_invalid_refresh_token_is_rejected(token_service: TokenService) -> None:

    with pytest.raises(InvalidRefreshTokenError) as exc_info:
        token_service.verify_refresh_token("not-a-jwt")

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "INVALID_REFRESH_TOKEN"


def test_token_type_mismatch_fails(token_service: TokenService) -> None:
    refresh_token = token_service.create_refresh_token("usr_mismatch")
    access_token = token_service.create_access_token("usr_mismatch")

    with pytest.raises(InvalidTokenTypeError) as exc_info:
        token_service.verify_access_token(refresh_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "INVALID_TOKEN_TYPE"

    with pytest.raises(InvalidTokenTypeError):
        token_service.verify_refresh_token(access_token)


def test_token_payload_contains_correct_user_id(token_service: TokenService) -> None:
    token = token_service.create_access_token("usr_payload")

    claims = token_service.decode_access_token(token)

    assert claims.user_id == "usr_payload"
    assert claims.token_type == "access"


def test_missing_secret_raises_value_error() -> None:
    with pytest.raises(ValueError):
        TokenService(Settings(jwt_secret=None))


def test_alias_methods_delegate_to_new_api(token_service: TokenService) -> None:
    access_token = token_service.issue_access_token("usr_alias")
    refresh_token = token_service.issue_refresh_token("usr_alias")

    assert token_service.validate_access_token(access_token) == "usr_alias"
    assert token_service.validate_refresh_token(refresh_token) == "usr_alias"


def test_expired_refresh_token_is_rejected() -> None:
    service = TokenService(Settings(jwt_secret="d" * 32, refresh_token_ttl_seconds=-5))
    token = service.create_refresh_token("usr_expired_refresh")

    with pytest.raises(InvalidRefreshTokenError):
        service.verify_refresh_token(token)


def test_invalid_claim_shape_rejected_for_access_and_refresh() -> None:
    secret = "e" * 32
    settings = Settings(jwt_secret=secret)
    service = TokenService(settings)

    access_missing_type = jwt.encode(
        {"sub": "usr_x", "iat": 1, "exp": 9999999999, "jti": "j1"},
        secret,
        algorithm="HS256",
    )
    refresh_missing_type = jwt.encode(
        {"sub": "usr_y", "iat": 1, "exp": 9999999999, "jti": "j2"},
        secret,
        algorithm="HS256",
    )
    access_missing_sub = jwt.encode(
        {"type": "access", "iat": 1, "exp": 9999999999, "jti": "j3"},
        secret,
        algorithm="HS256",
    )
    refresh_missing_jti = jwt.encode(
        {"type": "refresh", "sub": "usr_z", "iat": 1, "exp": 9999999999},
        secret,
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        service.verify_access_token(access_missing_type)
    with pytest.raises(InvalidRefreshTokenError):
        service.verify_refresh_token(refresh_missing_type)
    with pytest.raises(InvalidAccessTokenError):
        service.verify_access_token(access_missing_sub)
    with pytest.raises(InvalidRefreshTokenError):
        service.verify_refresh_token(refresh_missing_jti)
