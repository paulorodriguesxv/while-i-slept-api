"""Summary job DTO contract (v1), runtime-agnostic."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from while_i_slept_api.article_pipeline.errors import SummaryJobValidationError


class SummaryJob(BaseModel):
    """Summary job contract v1."""

    model_config = ConfigDict(extra="forbid")

    version: Literal[1]
    job_id: str
    article_id: str
    content_hash: str
    language: Literal["en", "pt"]
    topic: Literal["world", "technology", "finance", "science", "sports"]
    summary_version: int
    priority: Literal["normal", "high"]
    reprocess: bool
    model_override: str | None
    created_at: datetime

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "SummaryJob":
        """Parse payload and raise typed error on failure."""

        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            raise SummaryJobValidationError("Invalid summary job payload.") from exc

