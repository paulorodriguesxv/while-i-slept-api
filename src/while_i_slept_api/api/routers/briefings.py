"""Briefing endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path

from while_i_slept_api.api.models import BriefingResponse, briefing_to_model
from while_i_slept_api.dependencies.container import get_briefing_service, get_current_user
from while_i_slept_api.domain.models import UserProfile
from while_i_slept_api.services.briefings import BriefingService

router = APIRouter(prefix="/briefings", tags=["Briefings"])


@router.get("/today", response_model=BriefingResponse)
def get_briefing_today(
    current_user: Annotated[UserProfile, Depends(get_current_user)],
    briefing_service: Annotated[BriefingService, Depends(get_briefing_service)],
) -> BriefingResponse:
    """Get today's precomputed briefing limited by free/premium access."""

    briefing, max_items, is_premium = briefing_service.get_today(current_user)
    return briefing_to_model(briefing, max_items=max_items, is_premium=is_premium)


@router.get("/{date}", response_model=BriefingResponse)
def get_briefing_by_date(
    date: Annotated[str, Path(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")],
    current_user: Annotated[UserProfile, Depends(get_current_user)],
    briefing_service: Annotated[BriefingService, Depends(get_briefing_service)],
) -> BriefingResponse:
    """Get a historical briefing (premium-only)."""

    briefing, max_items, is_premium = briefing_service.get_for_date(
        user=current_user,
        date_str=date,
        history=True,
    )
    return briefing_to_model(briefing, max_items=max_items, is_premium=is_premium)
