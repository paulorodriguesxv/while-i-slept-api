"""Social provider id_token validation (stubbed for MVP/local dev)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.core.config import Settings
from while_i_slept_api.domain.models import OAuthIdentity, Provider


@dataclass(slots=True)
class StubTokenPayload:
    """Parsed payload for the local stub token format."""

    sub: str
    email: str | None
    name: str | None


class OAuthTokenValidator:
    """Validates provider id_tokens.

    Production signature validation is intentionally separated so the MVP can
    run locally with stub tokens while keeping the contract testable.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def validate(self, *, provider: Provider, id_token: str) -> OAuthIdentity:
        """Validate a provider token and return the provider identity."""

        if id_token.startswith("stub:"):
            payload = self._parse_stub_token(id_token)
            return OAuthIdentity(
                provider=provider,
                provider_user_id=payload.sub,
                email=payload.email,
                name=payload.name,
            )

        if self._settings.allow_insecure_oauth_tokens:
            digest = hashlib.sha256(f"{provider}:{id_token}".encode("utf-8")).hexdigest()
            return OAuthIdentity(
                provider=provider,
                provider_user_id=f"insecure_{digest[:24]}",
                email=None,
                name=None,
            )

        raise ApiError(
            status_code=401,
            code="UNAUTHORIZED",
            message="Invalid provider token.",
        )

    def _parse_stub_token(self, token: str) -> StubTokenPayload:
        """Parse `stub:<sub>|<email>|<name>` token format."""

        _, _, body = token.partition(":")
        if not body:
            raise ApiError(status_code=401, code="UNAUTHORIZED", message="Invalid provider token.")
        parts = body.split("|")
        if len(parts) < 1 or not parts[0]:
            raise ApiError(status_code=401, code="UNAUTHORIZED", message="Invalid provider token.")
        sub = parts[0]
        email = parts[1] if len(parts) > 1 and parts[1] else None
        name = parts[2] if len(parts) > 2 and parts[2] else None
        return StubTokenPayload(sub=sub, email=email, name=name)
