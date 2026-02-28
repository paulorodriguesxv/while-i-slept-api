"""Runtime wiring for summarizer worker use case."""

from __future__ import annotations

import os

from while_i_slept_api.core.config import Settings, get_settings
from while_i_slept_api.repositories.dynamodb import DynamoBriefingRepository, DynamoTableFactory
from while_i_slept_api.repositories.memory import InMemoryBriefingRepository
from while_i_slept_api.summarizer_worker.logging import StructuredLogger
from while_i_slept_api.summarizer_worker.use_case import SummaryJobUseCase


def build_use_case(settings: Settings | None = None) -> SummaryJobUseCase:
    """Build the summarizer use case with env-selected repository backend."""

    cfg = settings or get_settings()
    repo_backend = (os.getenv("REPO_BACKEND") or cfg.storage_backend or "memory").lower()
    if repo_backend == "dynamodb":
        factory = DynamoTableFactory(cfg)
        repo = DynamoBriefingRepository(factory)
    else:
        repo = InMemoryBriefingRepository()
    return SummaryJobUseCase(briefing_repo=repo, logger=StructuredLogger("while_i_slept.summarizer"))
