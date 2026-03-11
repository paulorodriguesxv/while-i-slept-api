"""Current-user sleep preferences endpoints."""

from __future__ import annotations

from functools import lru_cache
import os
from typing import Annotated

from fastapi import APIRouter, Depends

from while_i_slept_api.api.errors import ApiError
from while_i_slept_api.article_pipeline.infrastructure.aws_clients import AwsClientFactory
from while_i_slept_api.article_pipeline.infrastructure.dynamodb_single_table import DynamoArticleSummaryRepository
from while_i_slept_api.dependencies.container import get_current_user
from while_i_slept_api.domain.models import UserProfile
from while_i_slept_api.user_preferences.dto import SleepPreferencesRequest, SleepPreferencesResponse
from while_i_slept_api.user_preferences.use_cases import GetSleepPreferencesUseCase, SetSleepPreferencesUseCase

router = APIRouter(prefix="/users", tags=["Users"])


@lru_cache(maxsize=1)
def build_sleep_preferences_repository() -> DynamoArticleSummaryRepository:
    """Build repository for sleep preference storage."""

    factory = AwsClientFactory()
    return DynamoArticleSummaryRepository.from_resource(
        factory.dynamodb_resource(),
        table_name=os.getenv("DYNAMO_TABLE_NAME", "articles"),
    )


def build_set_sleep_preferences_use_case() -> SetSleepPreferencesUseCase:
    """Build set-preferences use case."""

    return SetSleepPreferencesUseCase(build_sleep_preferences_repository())


def build_get_sleep_preferences_use_case() -> GetSleepPreferencesUseCase:
    """Build get-preferences use case."""

    return GetSleepPreferencesUseCase(build_sleep_preferences_repository())


@router.post("/me/sleep-preferences", response_model=SleepPreferencesResponse)
def set_sleep_preferences(
    request: SleepPreferencesRequest,
    current_user: Annotated[UserProfile, Depends(get_current_user)],
    use_case: Annotated[SetSleepPreferencesUseCase, Depends(build_set_sleep_preferences_use_case)],
) -> SleepPreferencesResponse:
    """Store sleep preferences for authenticated user."""

    if request.sleep_time == request.wake_time:
        raise ApiError(
            status_code=400,
            code="INVALID_SLEEP_PREFERENCES",
            message="sleep_time and wake_time must be different.",
        )
    return use_case.execute(user_id=current_user.user_id, request=request)


@router.get("/me/sleep-preferences", response_model=SleepPreferencesResponse)
def get_sleep_preferences(
    current_user: Annotated[UserProfile, Depends(get_current_user)],
    use_case: Annotated[GetSleepPreferencesUseCase, Depends(build_get_sleep_preferences_use_case)],
) -> SleepPreferencesResponse:
    """Load sleep preferences for authenticated user."""

    response = use_case.execute(user_id=current_user.user_id)
    if response is None:
        raise ApiError(status_code=404, code="PREFERENCES_NOT_FOUND", message="Sleep preferences not found.")
    return response
