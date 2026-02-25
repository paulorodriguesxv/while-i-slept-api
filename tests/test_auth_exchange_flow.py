"""Unit tests for auth exchange flow wiring and implicit signup."""

from __future__ import annotations

from while_i_slept_api.core.config import Settings
from while_i_slept_api.repositories.memory import InMemoryDeviceRepository, InMemoryUserRepository
from while_i_slept_api.services.auth import AuthService
from while_i_slept_api.services.oauth import OAuthVerifier
from while_i_slept_api.services.tokens import TokenService
from while_i_slept_api.services.users import UserService


def test_exchange_flow_with_stub_provider_creates_user_and_tokens() -> None:
    user_repo = InMemoryUserRepository()
    user_service = UserService(user_repo, InMemoryDeviceRepository(), "America/Sao_Paulo")
    token_service = TokenService(Settings(jwt_secret="test-secret"))
    auth_service = AuthService(
        user_service=user_service,
        token_service=token_service,
        oauth_verifier=OAuthVerifier(Settings()),
    )

    access_token, refresh_token, expires_in, user = auth_service.exchange_oauth(
        provider="google",
        id_token="stub:google-sub-1|user@example.com|Paulo",
    )

    assert user.user_id.startswith("usr_")
    assert user.provider == "google"
    assert user.provider_user_id == "google-sub-1"
    assert user.email == "user@example.com"
    assert user.name == "Paulo"
    assert expires_in == 3600
    assert token_service.verify_access_token(access_token) == user.user_id
    assert token_service.verify_refresh_token(refresh_token) == user.user_id
    assert user_repo.get_by_id(user.user_id) is not None
