"""Unit tests for SummaryJob DTO contract."""

from __future__ import annotations

from datetime import timedelta

import pytest

from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.errors import SummaryJobValidationError


def _payload() -> dict[str, object]:
    return {
        "version": 1,
        "job_id": "job_123",
        "article_id": "art_123",
        "content_hash": "a" * 64,
        "language": "en",
        "topic": "technology",
        "summary_version": 1,
        "priority": "normal",
        "reprocess": False,
        "model_override": None,
        "created_at": "2026-02-27T10:00:00Z",
    }


def test_summary_job_contract_deserialization() -> None:
    job = SummaryJob.from_payload(_payload())

    assert job.version == 1
    assert job.summary_version == 1
    assert job.priority == "normal"
    assert job.created_at.utcoffset() == timedelta(0)


def test_summary_job_contract_rejects_invalid_version() -> None:
    payload = _payload()
    payload["version"] = 2

    with pytest.raises(SummaryJobValidationError):
        SummaryJob.from_payload(payload)

