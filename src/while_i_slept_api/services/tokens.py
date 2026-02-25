"""JWT token issuance and validation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from jwt import InvalidTokenError

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.core.config import Settings
from while_i_slept_api.services.utils import new_jti

TokenKind = Literal["access", "refresh"]


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

        return self._decode_subject(token=token, expected_kind="access")

    def validate_refresh_token(self, token: str) -> str:
        """Return the user id encoded in a valid refresh token."""

        return self._decode_subject(token=token, expected_kind="refresh")

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

    def _decode_subject(self, *, token: str, expected_kind: TokenKind) -> str:
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_algorithm],
            )
        except InvalidTokenError as exc:
            raise ApiError(status_code=401, code="UNAUTHORIZED", message="Invalid token.") from exc
        kind = payload.get("type")
        subject = payload.get("sub")
        if kind != expected_kind or not isinstance(subject, str) or not subject:
            raise ApiError(status_code=401, code="UNAUTHORIZED", message="Invalid token.")
        return subject
