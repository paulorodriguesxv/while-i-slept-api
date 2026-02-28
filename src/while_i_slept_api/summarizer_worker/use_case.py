"""Application use case for processing summary jobs."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

from while_i_slept_api.domain.models import BriefingItem, BriefingRecord, BriefingSource, BriefingWindow
from while_i_slept_api.repositories.base import BriefingRepository
from while_i_slept_api.services.utils import iso_now
from while_i_slept_api.summarizer_worker.dto import SummaryJob, SummaryJobEntry
from while_i_slept_api.summarizer_worker.errors import SummaryJobRetryableError
from while_i_slept_api.summarizer_worker.logging import StructuredLogger


@dataclass(frozen=True, slots=True)
class ProcessSummaryJobResult:
    """Result for a processed summary job."""

    status: str
    user_id: str
    date: str
    items_count: int


class SummaryJobUseCase:
    """Use case that processes a summary job into a briefing record."""

    def __init__(self, briefing_repo: BriefingRepository, logger: StructuredLogger) -> None:
        self._briefing_repo = briefing_repo
        self._logger = logger

    def process_summary_job(self, job: SummaryJob) -> ProcessSummaryJobResult:
        """Process a summary job with idempotent save behavior."""

        self._logger.info(
            "summary_job.start",
            job_id=job.job_id,
            user_id=job.user_id,
            date=job.date,
            entries_count=len(job.entries),
            version=job.version,
        )
        try:
            existing = self._briefing_repo.get_for_user_date(job.user_id, job.date)
            if existing is not None:
                self._logger.info(
                    "summary_job.idempotent_skip",
                    job_id=job.job_id,
                    user_id=job.user_id,
                    date=job.date,
                )
                return ProcessSummaryJobResult(
                    status="skipped_already_exists",
                    user_id=job.user_id,
                    date=job.date,
                    items_count=len(existing.items),
                )

            now = iso_now()
            record = BriefingRecord(
                user_id=job.user_id,
                date=job.date,
                lang=job.lang,
                window=BriefingWindow(start=job.window_start, end=job.window_end),
                items=[self._to_briefing_item(entry, index) for index, entry in enumerate(job.entries)],
                created_at=now,
                updated_at=now,
            )
            saved = self._briefing_repo.save(record)
            self._logger.info(
                "summary_job.processed",
                job_id=job.job_id,
                user_id=job.user_id,
                date=job.date,
                items_count=len(saved.items),
            )
            return ProcessSummaryJobResult(
                status="processed",
                user_id=saved.user_id,
                date=saved.date,
                items_count=len(saved.items),
            )
        except Exception as exc:  # pragma: no cover - guarded by tests via fake repository failures
            self._logger.exception(
                "summary_job.failed",
                job_id=job.job_id,
                user_id=job.user_id,
                date=job.date,
            )
            raise SummaryJobRetryableError("Transient failure processing summary job.") from exc

    def _to_briefing_item(self, entry: SummaryJobEntry, index: int) -> BriefingItem:
        story_id = entry.entry_id or _fallback_story_id(
            user_text=f"{entry.title}|{entry.published_at.isoformat()}|{index}"
        )
        bullets = [entry.summary] if entry.summary else [entry.title]
        sources: list[BriefingSource] = []
        if entry.source_url:
            sources.append(
                BriefingSource(
                    name=entry.source_name or "Unknown Source",
                    url=entry.source_url,
                )
            )
        return BriefingItem(
            story_id=story_id,
            headline=entry.title,
            summary_bullets=bullets,
            score=0.0,
            sources=sources,
        )


def _fallback_story_id(*, user_text: str) -> str:
    digest = sha1(user_text.encode("utf-8"), usedforsecurity=False).hexdigest()  # noqa: S324
    return f"sty_{digest[:20]}"
