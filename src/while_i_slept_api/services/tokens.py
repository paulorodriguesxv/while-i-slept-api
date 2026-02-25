"""JWT token issuance and validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from dataclasses import dataclass
from typing import Any, Literal

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from while_i_slept_api.core.config import Settings
from while_i_slept_api.services.auth_errors import (
    ExpiredAccessTokenError,
    InvalidAccessTokenError,
    InvalidRefreshTokenError,
    InvalidTokenTypeError,
)
from while_i_slept_api.services.utils import new_jti

TokenKind = Literal["access", "refresh"]


@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Typed JWT claims used by the auth layer."""

    user_id: str
    token_type: TokenKind
    issued_at: int
    expires_at: int
    jwt_id: str


class TokenService:
    """Issues and validates JWT access and refresh tokens."""

    def __init__(self, settings: Settings) -> None:
        if not settings.jwt_secret:
            raise ValueError("APP_JWT_SECRET is required for JWT signing.")
        self._settings = settings
        self._secret = settings.jwt_secret
        self._algorithm = settings.jwt_algorithm

    @property
    def access_ttl_seconds(self) -> int:
        """Configured access token TTL."""

        return self._settings.access_token_ttl_seconds

    def create_access_token(self, user_id: str) -> str:
        """Create a signed access token."""

        return self._encode(user_id=user_id, kind="access", ttl_seconds=self._settings.access_token_ttl_seconds)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a signed refresh token."""

        return self._encode(user_id=user_id, kind="refresh", ttl_seconds=self._settings.refresh_token_ttl_seconds)

    def verify_access_token(self, token: str) -> str:
        """Verify an access token and return its user id."""

        return self.decode_access_token(token).user_id

    def verify_refresh_token(self, token: str) -> str:
        """Verify a refresh token and return its user id."""

        return self.decode_refresh_token(token).user_id

    # Backward-compatible aliases for existing callers while the codebase migrates.
    def issue_access_token(self, user_id: str) -> str:
        """Alias for create_access_token."""

        return self.create_access_token(user_id)

    def issue_refresh_token(self, user_id: str) -> str:
        """Alias for create_refresh_token."""

        return self.create_refresh_token(user_id)

    def validate_access_token(self, token: str) -> str:
        """Alias for verify_access_token."""

        return self.verify_access_token(token)

    def validate_refresh_token(self, token: str) -> str:
        """Alias for verify_refresh_token."""

        return self.verify_refresh_token(token)

    def decode_access_token(self, token: str) -> TokenClaims:
        """Decode and validate an access token, returning typed claims."""

        return self._decode_claims(token=token, expected_kind="access")

    def decode_refresh_token(self, token: str) -> TokenClaims:
        """Decode and validate a refresh token, returning typed claims."""

        return self._decode_claims(token=token, expected_kind="refresh")

    def _encode(self, *, user_id: str, kind: TokenKind, ttl_seconds: int) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            "sub": user_id,
            "type": kind,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
            "jti": new_jti(),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def _decode_claims(self, *, token: str, expected_kind: TokenKind) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
        except ExpiredSignatureError as exc:
            if expected_kind == "access":
                raise ExpiredAccessTokenError() from exc
            raise InvalidRefreshTokenError() from exc
        except InvalidTokenError as exc:
            if expected_kind == "access":
                raise InvalidAccessTokenError() from exc
            raise InvalidRefreshTokenError() from exc
        kind = payload.get("type")
        subject = payload.get("sub")
        issued_at = payload.get("iat")
        expires_at = payload.get("exp")
        jwt_id = payload.get("jti")
        if not isinstance(kind, str):
            if expected_kind == "access":
                raise InvalidAccessTokenError()
            raise InvalidRefreshTokenError()
        if kind != expected_kind:
            raise InvalidTokenTypeError(expected=expected_kind, actual=kind)
        if (
            not isinstance(subject, str)
            or not subject
            or not isinstance(issued_at, int)
            or not isinstance(expires_at, int)
            or not isinstance(jwt_id, str)
            or not jwt_id
        ):
            if expected_kind == "access":
                raise InvalidAccessTokenError()
            raise InvalidRefreshTokenError()
        return TokenClaims(
            user_id=subject,
            token_type=kind,
            issued_at=issued_at,
            expires_at=expires_at,
            jwt_id=jwt_id,
        )
