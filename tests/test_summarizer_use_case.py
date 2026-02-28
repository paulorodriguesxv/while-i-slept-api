"""Unit tests for summary job use case."""

from __future__ import annotations

from while_i_slept_api.domain.models import (
    BriefingItem,
    BriefingRecord,
    BriefingSource,
    BriefingWindow,
)
from while_i_slept_api.repositories.memory import InMemoryBriefingRepository
from while_i_slept_api.summarizer_worker.dto import SummaryJob
from while_i_slept_api.summarizer_worker.logging import StructuredLogger
from while_i_slept_api.summarizer_worker.use_case import SummaryJobUseCase


def _job() -> SummaryJob:
    return SummaryJob.from_payload(
        {
            "version": "1.0",
            "job_id": "job_abc",
            "user_id": "usr_abc",
            "date": "2026-02-27",
            "lang": "en",
            "window_start": "2026-02-26T23:00:00-03:00",
            "window_end": "2026-02-27T07:00:00-03:00",
            "entries": [
                {
                    "entry_id": "entry_1",
                    "title": "Story title",
                    "summary": "Story summary",
                    "source_name": "Example",
                    "source_url": "https://example.com/story",
                    "published_at": "2026-02-27T06:00:00Z",
                }
            ],
        }
    )


def test_process_summary_job_saves_briefing_when_missing() -> None:
    repo = InMemoryBriefingRepository()
    use_case = SummaryJobUseCase(repo, StructuredLogger("tests.summary.use_case"))

    result = use_case.process_summary_job(_job())

    assert result.status == "processed"
    saved = repo.get_for_user_date("usr_abc", "2026-02-27")
    assert saved is not None
    assert len(saved.items) == 1
    assert saved.items[0].headline == "Story title"
    assert saved.items[0].summary_bullets == ["Story summary"]


def test_process_summary_job_is_idempotent() -> None:
    repo = InMemoryBriefingRepository()
    repo.save(
        BriefingRecord(
            user_id="usr_abc",
            date="2026-02-27",
            lang="en",
            window=BriefingWindow(start="2026-02-26T23:00:00-03:00", end="2026-02-27T07:00:00-03:00"),
            items=[
                BriefingItem(
                    story_id="sty_existing",
                    headline="Existing",
                    summary_bullets=["Existing summary"],
                    score=0.0,
                    sources=[BriefingSource(name="Example", url="https://example.com/existing")],
                )
            ],
            created_at="2026-02-27T07:30:00Z",
            updated_at="2026-02-27T07:30:00Z",
        )
    )
    use_case = SummaryJobUseCase(repo, StructuredLogger("tests.summary.idempotent"))

    result = use_case.process_summary_job(_job())

    assert result.status == "skipped_already_exists"
    assert result.items_count == 1
