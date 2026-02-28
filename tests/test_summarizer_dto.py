"""Unit tests for summary job DTO parsing."""

from __future__ import annotations

from datetime import timedelta

import pytest

from while_i_slept_api.summarizer_worker.dto import SummaryJob
from while_i_slept_api.summarizer_worker.errors import SummaryJobPayloadError


def _payload() -> dict[str, object]:
    return {
        "version": "1.0",
        "job_id": "job_123",
        "user_id": "usr_123",
        "date": "2026-02-27",
        "lang": "en",
        "window_start": "2026-02-26T23:00:00-03:00",
        "window_end": "2026-02-27T07:00:00-03:00",
        "entries": [
            {
                "entry_id": "entry_1",
                "title": "Headline 1",
                "summary": "Summary 1",
                "source_name": "Example",
                "source_url": "https://example.com/1",
                "published_at": "2026-02-27T06:00:00Z",
            }
        ],
    }


def test_summary_job_from_payload_parses_versioned_dto() -> None:
    job = SummaryJob.from_payload(_payload())

    assert job.version == "1.0"
    assert job.job_id == "job_123"
    assert job.user_id == "usr_123"
    assert job.entries[0].published_at.utcoffset() == timedelta(0)


def test_summary_job_from_payload_rejects_invalid_version() -> None:
    payload = _payload()
    payload["version"] = "2.0"

    with pytest.raises(SummaryJobPayloadError):
        SummaryJob.from_payload(payload)
