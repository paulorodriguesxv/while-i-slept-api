"""Sleep-window feed endpoint."""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.article_pipeline.feed_query import (
    GetSleepWindowFeedUseCase,
    SleepWindowRequest,
    SleepWindowResponse,
)
from while_i_slept_api.article_pipeline.infrastructure.aws_clients import AwsClientFactory
from while_i_slept_api.article_pipeline.infrastructure.dynamodb_single_table import DynamoArticleSummaryRepository

router = APIRouter(tags=["Feed"])


@lru_cache(maxsize=1)
def build_sleep_window_use_case() -> GetSleepWindowFeedUseCase:
    """Build sleep-window feed use case with DynamoDB repository."""

    factory = AwsClientFactory()
    repository = DynamoArticleSummaryRepository.from_resource(
        factory.dynamodb_resource(),
        table_name=os.getenv("DYNAMO_TABLE_NAME", "articles"),
    )
    return GetSleepWindowFeedUseCase(repository=repository)


def get_sleep_window_use_case() -> GetSleepWindowFeedUseCase:
    """Dependency wrapper for sleep-window feed use case."""

    return build_sleep_window_use_case()


@router.get("/while-i-slept", response_model=SleepWindowResponse)
def get_sleep_window_feed(
    language: str,
    sleep_time: datetime,
    wake_time: datetime,
    use_case: Annotated[GetSleepWindowFeedUseCase, Depends(get_sleep_window_use_case)],
    limit: int = Query(default=50, ge=1, le=200),
) -> SleepWindowResponse:
    """Return feed items published during the provided sleep window."""

    if sleep_time >= wake_time:
        raise ApiError(
            status_code=400,
            code="INVALID_SLEEP_WINDOW",
            message="sleep_time must be earlier than wake_time.",
        )
    request = SleepWindowRequest(
        language=language,
        start_time=sleep_time,
        end_time=wake_time,
        limit=limit,
    )
    return use_case.execute(request)
