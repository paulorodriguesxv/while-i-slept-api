"""Typed authentication-related API errors."""

from __future__ import annotations

from while_i_slept_api.api.errors import ApiError


class InvalidProviderTokenError(ApiError):
    """Raised when an Apple/Google provider token cannot be verified."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="INVALID_PROVIDER_TOKEN",
            message="Invalid provider token.",
        )


class InvalidAccessTokenError(ApiError):
    """Raised when an access token is malformed or otherwise invalid."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="UNAUTHORIZED",
            message="Invalid access token.",
        )


class ExpiredAccessTokenError(ApiError):
    """Raised when an access token is expired."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="UNAUTHORIZED",
            message="Access token expired.",
        )


class InvalidRefreshTokenError(ApiError):
    """Raised when a refresh token is malformed, expired, or invalid."""

    def __init__(self) -> None:
        super().__init__(
            status_code=401,
            code="INVALID_REFRESH_TOKEN",
            message="Invalid refresh token.",
        )


class UserNotFoundError(ApiError):
    """Raised when a referenced user record does not exist."""

    def __init__(self, *, status_code: int = 404, message: str = "User not found.") -> None:
        super().__init__(
            status_code=status_code,
            code="USER_NOT_FOUND",
            message=message,
        )
