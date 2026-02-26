"""Unit tests for auth error classes to cover metadata branches."""

from __future__ import annotations

from while_i_slept_api.services.auth_errors import InvalidTokenTypeError, UserNotFoundError


def test_invalid_token_type_error_without_actual_has_expected_only() -> None:
    error = InvalidTokenTypeError(expected="access")

    assert error.code == "INVALID_TOKEN_TYPE"
    assert error.details == {"expected": "access"}


def test_user_not_found_error_defaults() -> None:
    error = UserNotFoundError()

    assert error.status_code == 404
    assert error.code == "USER_NOT_FOUND"
    assert error.message == "User not found."
