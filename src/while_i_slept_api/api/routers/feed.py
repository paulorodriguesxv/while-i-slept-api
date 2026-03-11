"""Sleep-window feed endpoint."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.article_pipeline.feed_query import GetSleepWindowFeedUseCase, SleepWindowRequest
from while_i_slept_api.article_pipeline.feed_query.dto import SleepWindowItem
from while_i_slept_api.article_pipeline.infrastructure.aws_clients import AwsClientFactory
from while_i_slept_api.article_pipeline.infrastructure.dynamodb_single_table import DynamoArticleSummaryRepository
from while_i_slept_api.dependencies.container import get_current_user
from while_i_slept_api.dependencies.container import get_user_service
from while_i_slept_api.domain.models import UserProfile
from while_i_slept_api.services.users import UserService
from while_i_slept_api.sleep_window.resolver import resolve_last_sleep_window

router = APIRouter(tags=["Feed"])


@lru_cache(maxsize=1)
def build_feed_repository() -> DynamoArticleSummaryRepository:
    """Build repository for feed and preferences queries."""

    factory = AwsClientFactory()
    return DynamoArticleSummaryRepository.from_resource(
        factory.dynamodb_resource(),
        table_name=os.getenv("DYNAMO_TABLE_NAME", "articles"),
    )


def get_sleep_window_use_case() -> GetSleepWindowFeedUseCase:
    """Dependency wrapper for sleep-window feed use case."""

    return GetSleepWindowFeedUseCase(repository=build_feed_repository())


class ResolvedSleepWindowResponse(BaseModel):
    """Serialized resolved sleep window for response payload."""

    start: datetime
    end: datetime


class WhileISleptResponse(BaseModel):
    """Feed payload for the last completed sleep window."""

    sleep_window: ResolvedSleepWindowResponse
    items: list[SleepWindowItem]


@router.get("/while-i-slept", response_model=WhileISleptResponse)
def get_sleep_window_feed(
    current_user: Annotated[UserProfile, Depends(get_current_user)],
    user_service: Annotated[UserService, Depends(get_user_service)],
    feed_use_case: Annotated[GetSleepWindowFeedUseCase, Depends(get_sleep_window_use_case)],
    limit: int = Query(default=50, ge=1, le=200),
) -> WhileISleptResponse:
    """Return feed items for the authenticated user's last completed sleep window."""

    profile = user_service.get_required(current_user.user_id)
    if profile.sleep_window is None:
        raise ApiError(status_code=404, code="PREFERENCES_NOT_FOUND", message="Sleep preferences not found.")
    resolved = resolve_last_sleep_window(profile.sleep_window)
    request = SleepWindowRequest(
        language=profile.lang or "pt",
        start_time=resolved.start,
        end_time=resolved.end,
        limit=limit,
    )
    result = feed_use_case.execute(request)
    return WhileISleptResponse(
        sleep_window=ResolvedSleepWindowResponse(start=resolved.start, end=resolved.end),
        items=result.items,
    )
