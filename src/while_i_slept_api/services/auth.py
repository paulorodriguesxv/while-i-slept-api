"""Authentication and implicit signup flows."""

from __future__ import annotations

from typing import Protocol

from while_i_slept_api.domain.models import OAuthIdentity, UserProfile
from while_i_slept_api.services.oauth import OAuthVerifier
from while_i_slept_api.services.tokens import TokenService


class UserAccountService(Protocol):
    """Auth-facing user operations used by the authentication flow."""

    def get_or_create_from_oauth_identity(self, identity: OAuthIdentity) -> UserProfile:
        ...

    def get_required(self, user_id: str, *, status_code: int = 404) -> UserProfile:
        ...


class AuthService:
    """Handles OAuth exchange and refresh-token flows."""

    def __init__(
        self,
        user_service: UserAccountService,
        token_service: TokenService,
        oauth_verifier: OAuthVerifier,
    ) -> None:
        self._user_service = user_service
        self._token_service = token_service
        self._oauth_verifier = oauth_verifier

    def exchange_oauth(self, *, provider: str, id_token: str) -> tuple[str, str, int, UserProfile]:
        """Validate provider token, create user if needed, and issue JWT tokens."""

        identity = self._oauth_verifier.validate(provider=provider, id_token=id_token)  # type: ignore[arg-type]
        user = self._user_service.get_or_create_from_oauth_identity(identity)
        access_token = self._token_service.issue_access_token(user.user_id)
        refresh_token = self._token_service.issue_refresh_token(user.user_id)
        return access_token, refresh_token, self._token_service.access_ttl_seconds, user

    def refresh_access(self, refresh_token: str) -> tuple[str, int]:
        """Issue a new access token from a valid refresh token."""

        user_id = self._token_service.validate_refresh_token(refresh_token)
        user = self._user_service.get_required(
            user_id,
            status_code=401,
        )
        access_token = self._token_service.issue_access_token(user.user_id)
        return access_token, self._token_service.access_ttl_seconds
