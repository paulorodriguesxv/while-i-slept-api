"""Webhook endpoints."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.api.models import RevenueCatWebhookEvent
from while_i_slept_api.core.config import Settings, get_settings
from while_i_slept_api.dependencies.container import get_revenuecat_service
from while_i_slept_api.services.revenuecat import RevenueCatService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/revenuecat")
def revenuecat_webhook(
    payload: RevenueCatWebhookEvent,
    webhook_secret: Annotated[str, Header(alias="X-Webhook-Secret")],
    service: Annotated[RevenueCatService, Depends(get_revenuecat_service)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, bool]:
    """Receive RevenueCat webhook events to update entitlement state."""

    if webhook_secret != settings.revenuecat_webhook_secret:
        raise ApiError(status_code=401, code="UNAUTHORIZED", message="Invalid webhook secret.")
    service.process_webhook(payload.model_dump())
    return {"ok": True}
