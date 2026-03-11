"""DTOs for user sleep preferences."""

from __future__ import annotations

from pydantic import BaseModel


class SleepPreferencesRequest(BaseModel):
    """Request payload for sleep preferences."""

    sleep_time: str
    wake_time: str
    timezone: str


class SleepPreferencesResponse(BaseModel):
    """Response payload for sleep preferences."""

    sleep_time: str
    wake_time: str
    timezone: str
