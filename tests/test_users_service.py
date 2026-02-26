"""Unit tests for UserService onboarding and device behavior."""

from __future__ import annotations

from while_i_slept_api.domain.models import OAuthIdentity
from while_i_slept_api.services.auth_errors import UserNotFoundError
from while_i_slept_api.services.users import UserService


def test_get_me_returns_fallback_when_not_persisted(user_service: UserService, make_user) -> None:
    transient = make_user(user_id="usr_fallback")
    # Remove from repo to force fallback path.
    user_service._users._users.pop(transient.user_id)  # type: ignore[attr-defined]

    result = user_service.get_me(transient)

    assert result.user_id == transient.user_id


def test_get_by_id_and_get_required(user_service: UserService, make_user) -> None:
    user = make_user(user_id="usr_lookup")

    assert user_service.get_by_id(user.user_id) is not None
    assert user_service.get_by_id("usr_missing") is None
    assert user_service.get_required(user.user_id).user_id == user.user_id


def test_get_required_raises_user_not_found(user_service: UserService) -> None:
    try:
        user_service.get_required("usr_missing")
        raise AssertionError("Expected UserNotFoundError")
    except UserNotFoundError as exc:
        assert exc.status_code == 404
        assert exc.code == "USER_NOT_FOUND"


def test_get_or_create_from_oauth_identity_updates_existing_user(user_service: UserService) -> None:
    first = user_service.get_or_create_from_oauth_identity(
        OAuthIdentity(
            provider="google",
            provider_user_id="sub-123",
            email=None,
            name=None,
        )
    )
    updated = user_service.get_or_create_from_oauth_identity(
        OAuthIdentity(
            provider="google",
            provider_user_id="sub-123",
            email="user@example.com",
            name="Paulo",
        )
    )

    assert updated.user_id == first.user_id
    assert updated.email == "user@example.com"
    assert updated.name == "Paulo"


def test_onboarding_completed_transitions_after_preferences_and_legal(user_service: UserService, make_user) -> None:
    user = make_user(user_id="usr_onboarding_a")

    after_prefs = user_service.update_preferences(
        user=user,
        lang="pt",
        sleep_start="23:00",
        sleep_end="07:00",
        timezone=None,
        topics=["tech"],
    )
    assert after_prefs.onboarding_completed is False
    assert after_prefs.sleep_window is not None
    assert after_prefs.sleep_window.timezone == "America/Sao_Paulo"

    after_legal = user_service.accept_legal(
        user=after_prefs,
        terms_version="2026-02-25",
        privacy_version="2026-02-25",
    )
    assert after_legal.onboarding_completed is True
    assert after_legal.accepted_terms is True
    assert after_legal.accepted_privacy is True


def test_onboarding_completed_transitions_when_legal_first(user_service: UserService, make_user) -> None:
    user = make_user(user_id="usr_onboarding_b")

    after_legal = user_service.accept_legal(
        user=user,
        terms_version="v2",
        privacy_version="v2",
    )
    assert after_legal.onboarding_completed is False

    after_prefs = user_service.update_preferences(
        user=after_legal,
        lang="en",
        sleep_start="22:30",
        sleep_end="06:15",
        timezone="UTC",
        topics=None,
    )
    assert after_prefs.onboarding_completed is True


def test_register_device_upserts_device_record(user_service: UserService, make_user) -> None:
    user = make_user(user_id="usr_device")

    user_service.register_device(
        user=user,
        device_id="dev-1",
        platform="ios",
        push_token="push-token",
        app_version="1.0.0",
    )

    stored = user_service._devices._devices[(user.user_id, "dev-1")]  # type: ignore[attr-defined]
    assert stored.push_token == "push-token"
    assert stored.platform == "ios"
