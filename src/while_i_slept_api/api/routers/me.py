"""Current-user endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from while_i_slept_api.api.models import (
    AcceptLegalRequest,
    AcceptLegalResponse,
    MeModel,
    RegisterDeviceRequest,
    RegisterDeviceResponse,
    UpdatePreferencesRequest,
    me_to_model,
)
from while_i_slept_api.dependencies.container import get_current_user, get_user_service
from while_i_slept_api.domain.models import UserProfile
from while_i_slept_api.services.users import UserService

router = APIRouter(prefix="/me", tags=["Me"])


@router.get("", response_model=MeModel)
def get_me(
    current_user: Annotated[UserProfile, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> MeModel:
    """Get current user profile, flags, and entitlements."""

    return me_to_model(user_service.get_me(current_user))


@router.put("/preferences", response_model=MeModel)
def update_preferences(
    request: UpdatePreferencesRequest,
    current_user: Annotated[UserProfile, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> MeModel:
    """Update onboarding preferences."""

    updated = user_service.update_preferences(
        user=current_user,
        lang=request.lang,
        sleep_start=request.sleep_window.start,
        sleep_end=request.sleep_window.end,
        timezone=request.sleep_window.timezone,
        topics=request.topics,
    )
    return me_to_model(updated)


@router.post("/accept-legal", response_model=AcceptLegalResponse)
def accept_legal(
    request: AcceptLegalRequest,
    current_user: Annotated[UserProfile, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> AcceptLegalResponse:
    """Record acceptance of terms and privacy policy."""

    updated = user_service.accept_legal(
        user=current_user,
        terms_version=request.terms_version,
        privacy_version=request.privacy_version,
    )
    return AcceptLegalResponse(
        accepted_terms=updated.accepted_terms,
        accepted_privacy=updated.accepted_privacy,
    )


@router.post("/device", response_model=RegisterDeviceResponse)
def register_device(
    request: RegisterDeviceRequest,
    current_user: Annotated[UserProfile, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
) -> RegisterDeviceResponse:
    """Register or update a device push token."""

    user_service.register_device(
        user=current_user,
        device_id=request.device_id,
        platform=request.platform,
        push_token=request.push_token,
        app_version=request.app_version,
    )
    return RegisterDeviceResponse(ok=True)
