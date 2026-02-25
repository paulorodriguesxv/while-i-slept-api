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
        self._settings = settings

    @property
    def access_ttl_seconds(self) -> int:
        """Configured access token TTL."""

        return self._settings.access_token_ttl_seconds

    def issue_access_token(self, user_id: str) -> str:
        """Issue a signed access token."""

        return self._encode(user_id=user_id, kind="access", ttl_seconds=self._settings.access_token_ttl_seconds)

    def issue_refresh_token(self, user_id: str) -> str:
        """Issue a signed refresh token."""

        return self._encode(user_id=user_id, kind="refresh", ttl_seconds=self._settings.refresh_token_ttl_seconds)

    def validate_access_token(self, token: str) -> str:
        """Return the user id encoded in a valid access token."""

        return self.decode_access_token(token).user_id

    def validate_refresh_token(self, token: str) -> str:
        """Return the user id encoded in a valid refresh token."""

        return self.decode_refresh_token(token).user_id

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
        return jwt.encode(payload, self._settings.jwt_secret, algorithm=self._settings.jwt_algorithm)

    def _decode_claims(self, *, token: str, expected_kind: TokenKind) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
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
        if (
            kind != expected_kind
            or not isinstance(subject, str)
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
