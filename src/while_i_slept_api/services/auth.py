"""Authentication and implicit signup flows."""

from __future__ import annotations

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.domain.models import EntitlementState, UserProfile
from while_i_slept_api.repositories.base import UserRepository
from while_i_slept_api.services.oauth import OAuthTokenValidator
from while_i_slept_api.services.tokens import TokenService
from while_i_slept_api.services.utils import iso_now, new_user_id


class AuthService:
    """Handles OAuth exchange and refresh-token flows."""

    def __init__(
        self,
        users: UserRepository,
        token_service: TokenService,
        oauth_validator: OAuthTokenValidator,
    ) -> None:
        self._users = users
        self._token_service = token_service
        self._oauth_validator = oauth_validator

    def exchange_oauth(self, *, provider: str, id_token: str) -> tuple[str, str, int, UserProfile]:
        """Validate provider token, create user if needed, and issue JWT tokens."""

        identity = self._oauth_validator.validate(provider=provider, id_token=id_token)  # type: ignore[arg-type]
        user = self._users.get_by_provider_identity(identity.provider, identity.provider_user_id)
        now = iso_now()
        if user is None:
            user = UserProfile(
                user_id=new_user_id(),
                provider=identity.provider,
                provider_user_id=identity.provider_user_id,
                email=identity.email,
                name=identity.name,
                entitlements=EntitlementState(),
                created_at=now,
                updated_at=now,
            )
        else:
            user.email = identity.email or user.email
            user.name = identity.name or user.name
            user.updated_at = now
        user = self._users.save(user)
        access_token = self._token_service.issue_access_token(user.user_id)
        refresh_token = self._token_service.issue_refresh_token(user.user_id)
        return access_token, refresh_token, self._token_service.access_ttl_seconds, user

    def refresh_access(self, refresh_token: str) -> tuple[str, int]:
        """Issue a new access token from a valid refresh token."""

        user_id = self._token_service.validate_refresh_token(refresh_token)
        user = self._users.get_by_id(user_id)
        if user is None:
            raise ApiError(status_code=401, code="UNAUTHORIZED", message="Invalid refresh token.")
        access_token = self._token_service.issue_access_token(user.user_id)
        return access_token, self._token_service.access_ttl_seconds
