"""Auth endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from while_i_slept_api.api.models import (
    AuthExchangeRequest,
    AuthExchangeResponse,
    RefreshRequest,
    RefreshResponse,
    me_to_model,
)
from while_i_slept_api.dependencies.container import get_auth_service
from while_i_slept_api.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/oauth/exchange", response_model=AuthExchangeResponse)
def exchange_oauth(
    request: AuthExchangeRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthExchangeResponse:
    """Exchange provider id_token for backend JWT tokens."""

    access_token, refresh_token, expires_in, user = auth_service.exchange_oauth(
        provider=request.provider,
        id_token=request.id_token,
    )
    return AuthExchangeResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
        me=me_to_model(user),
    )


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    request: RefreshRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RefreshResponse:
    """Refresh an access token using a refresh token."""

    access_token, expires_in = auth_service.refresh_access(request.refresh_token)
    return RefreshResponse(access_token=access_token, token_type="bearer", expires_in=expires_in)
