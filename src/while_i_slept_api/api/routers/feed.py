"""Sleep-window feed endpoint."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.article_pipeline.feed_query import GetSleepWindowFeedUseCase, SleepWindowRequest
from while_i_slept_api.article_pipeline.feed_query.dto import SleepWindowItem
from while_i_slept_api.article_pipeline.infrastructure.aws_clients import AwsClientFactory
from while_i_slept_api.article_pipeline.infrastructure.dynamodb_single_table import DynamoArticleSummaryRepository
from while_i_slept_api.core.config import get_settings
from while_i_slept_api.dependencies.container import get_current_user
from while_i_slept_api.dependencies.container import get_user_service
from while_i_slept_api.domain.models import UserProfile
from while_i_slept_api.services.users import UserService
from while_i_slept_api.sleep_window.resolver import resolve_last_sleep_window

router = APIRouter(tags=["Feed"])

FREE_FEED_LIMIT = 3
PREMIUM_MAX_FEED_LIMIT = 25
DEFAULT_FEED_LIMIT = 50


def resolve_effective_feed_limit(requested_limit: int | None, *, is_premium: bool) -> int:
    """Resolve a safe feed query limit based on entitlement tier."""

    candidate = requested_limit if requested_limit is not None else DEFAULT_FEED_LIMIT
    if candidate < 1:
        candidate = 1
    cap = PREMIUM_MAX_FEED_LIMIT if is_premium else FREE_FEED_LIMIT
    return min(candidate, cap)


def resolve_truncated_for_free_tier(
    *,
    requested_limit: int | None,
    is_premium: bool,
    applied_limit: int,
) -> bool:
    """Whether response was truncated specifically by free-tier entitlement cap."""

    return (
        not is_premium
        and requested_limit is not None
        and requested_limit > FREE_FEED_LIMIT
        and applied_limit == FREE_FEED_LIMIT
    )


@lru_cache(maxsize=1)
def build_feed_repository() -> DynamoArticleSummaryRepository:
    """Build repository for feed and preferences queries."""

    factory = AwsClientFactory()
    table_name = get_settings().articles_table
    return DynamoArticleSummaryRepository.from_resource(
        factory.dynamodb_resource(),
        table_name=table_name,
    )


def get_sleep_window_use_case() -> GetSleepWindowFeedUseCase:
    """Dependency wrapper for sleep-window feed use case."""

    return GetSleepWindowFeedUseCase(repository=build_feed_repository())


class ResolvedSleepWindowResponse(BaseModel):
    """Serialized resolved sleep window for response payload."""

    start: datetime
    end: datetime


class WhileISleptMeta(BaseModel):
    """Metadata describing entitlement-based feed truncation behavior."""

    is_premium: bool
    applied_limit: int
    truncated_for_free_tier: bool


class WhileISleptResponse(BaseModel):
    """Feed payload for the last completed sleep window."""

    sleep_window: ResolvedSleepWindowResponse
    items: list[SleepWindowItem]
    meta: WhileISleptMeta


@router.get("/while-i-slept", response_model=WhileISleptResponse)
def get_sleep_window_feed(
    current_user: Annotated[UserProfile, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    feed_use_case: Annotated[GetSleepWindowFeedUseCase, Depends(get_sleep_window_use_case)],
    limit: int | None = Query(default=None, ge=1, le=200),
) -> WhileISleptResponse:
    """Return feed items for the authenticated user's last completed sleep window."""

    profile = user_service.get_required(current_user.user_id)
    if profile.sleep_window is None:
        raise ApiError(status_code=404, code="PREFERENCES_NOT_FOUND", message="Sleep preferences not found.")
    resolved = resolve_last_sleep_window(profile.sleep_window)
    is_premium = profile.entitlements.premium
    effective_limit = resolve_effective_feed_limit(limit, is_premium=is_premium)
    truncated_for_free_tier = resolve_truncated_for_free_tier(
        requested_limit=limit,
        is_premium=is_premium,
        applied_limit=effective_limit,
    )
    request = SleepWindowRequest(
        language=profile.lang or "pt",
        start_time=resolved.start,
        end_time=resolved.end,
        limit=effective_limit,
    )
    result = feed_use_case.execute(request)
    return WhileISleptResponse(
        sleep_window=ResolvedSleepWindowResponse(start=resolved.start, end=resolved.end),
        items=result.items,
        meta=WhileISleptMeta(
            is_premium=is_premium,
            applied_limit=effective_limit,
            truncated_for_free_tier=truncated_for_free_tier,
        ),
    )
