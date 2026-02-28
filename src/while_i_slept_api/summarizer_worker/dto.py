"""Versioned DTOs for summarizer worker jobs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from while_i_slept_api.summarizer_worker.errors import SummaryJobPayloadError


class SummaryJobEntry(BaseModel):
    """Raw content entry provided to the summarizer worker."""

    model_config = ConfigDict(extra="forbid")

    entry_id: str | None = None
    title: str
    summary: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    published_at: datetime


class SummaryJob(BaseModel):
    """Versioned summary job payload."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    job_id: str
    user_id: str
    date: str
    lang: Literal["pt", "en"]
    window_start: str
    window_end: str
    entries: list[SummaryJobEntry] = Field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SummaryJob":
        """Parse and validate payload."""

        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            raise SummaryJobPayloadError("Invalid summary job payload.") from exc
