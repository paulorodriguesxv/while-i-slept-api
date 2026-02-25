"""Unit tests for stub OAuth token validation."""

from __future__ import annotations

import pytest

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.core.config import Settings
from while_i_slept_api.services.oauth import OAuthTokenValidator


def test_stub_token_parses_identity_fields() -> None:
    validator = OAuthTokenValidator(Settings())

    identity = validator.validate(
        provider="google",
        id_token="stub:google-sub-123|user@example.com|Paulo",
    )

    assert identity.provider == "google"
    assert identity.provider_user_id == "google-sub-123"
    assert identity.email == "user@example.com"
    assert identity.name == "Paulo"


def test_non_stub_token_is_rejected_when_insecure_mode_disabled() -> None:
    validator = OAuthTokenValidator(Settings(allow_insecure_oauth_tokens=False))

    with pytest.raises(ApiError) as exc_info:
        validator.validate(provider="apple", id_token="real-provider-token")

    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "INVALID_PROVIDER_TOKEN"
