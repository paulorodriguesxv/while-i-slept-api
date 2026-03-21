"""Unit tests for article-job processor Lambda adapters."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from types import SimpleNamespace

import pytest

import while_i_slept_api.article_pipeline.article_job_worker_processing as processing_module
from while_i_slept_api.article_pipeline.article_processor_handler import lambda_handler
from while_i_slept_api.article_pipeline.article_job_worker_processing import process_article_job_record
from while_i_slept_api.core.logging import StructuredLogger


def _valid_body() -> str:
    return json.dumps(
        {
            "version": 1,
            "entry_id": "entry_1",
            "language": "en",
            "topic": "world",
            "source": "Example",
            "source_feed_url": "https://example.com/feed",
            "article_url": "https://example.com/story",
            "title": "Story title",
            "summary": "Fallback summary",
            "published_at": "2026-02-27T10:00:00Z",
        }
    )


@dataclass
class _FakeIngestionResult:
    status: str
    content_hash: str
    enqueued: bool


@dataclass
class _FakeUseCase:
    status: str = "CREATED"
    raise_error: bool = False
    calls: int = 0

    def ingest(self, article):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.raise_error:
            raise RuntimeError("temporary")
        return _FakeIngestionResult(
            status=self.status,
            content_hash=article.content_hash,
            enqueued=self.status == "CREATED",
        )


def test_process_article_job_record_valid_payload_acknowledged(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = _FakeUseCase(status="CREATED")
    monkeypatch.setattr(
        processing_module,
        "enrich_article_content",
        lambda **_: SimpleNamespace(
            content="normalized content",
            image_url=None,
            description=None,
            author=None,
            article_published_time=None,
            reading_time_minutes=1,
        ),
    )
    monkeypatch.setattr(processing_module, "compute_content_hash", lambda **_: "a" * 64)
    monkeypatch.setattr(processing_module, "iso_now", lambda: "2026-02-27T10:01:00Z")

    should_ack = process_article_job_record(
        record_body=_valid_body(),
        message_id="m-1",
        receive_count=1,
        use_case=use_case,  # type: ignore[arg-type]
        logger=StructuredLogger("tests.article.processor"),
        article_logger=logging.getLogger("tests.article.processor.content"),
    )

    assert should_ack is True
    assert use_case.calls == 1


def test_process_article_job_record_duplicate_acknowledged(monkeypatch: pytest.MonkeyPatch) -> None:
    use_case = _FakeUseCase(status="DUPLICATE")
    monkeypatch.setattr(
        processing_module,
        "enrich_article_content",
        lambda **_: SimpleNamespace(
            content="normalized content",
            image_url=None,
            description=None,
            author=None,
            article_published_time=None,
            reading_time_minutes=1,
        ),
    )
    monkeypatch.setattr(processing_module, "compute_content_hash", lambda **_: "b" * 64)
    monkeypatch.setattr(processing_module, "iso_now", lambda: "2026-02-27T10:01:00Z")

    should_ack = process_article_job_record(
        record_body=_valid_body(),
        message_id="m-2",
        receive_count=1,
        use_case=use_case,  # type: ignore[arg-type]
        logger=StructuredLogger("tests.article.processor.duplicate"),
        article_logger=logging.getLogger("tests.article.processor.content.duplicate"),
    )

    assert should_ack is True
    assert use_case.calls == 1


def test_process_article_job_record_invalid_json_acknowledged() -> None:
    use_case = _FakeUseCase()
    should_ack = process_article_job_record(
        record_body="{not-json}",
        message_id="m-3",
        receive_count=1,
        use_case=use_case,  # type: ignore[arg-type]
        logger=StructuredLogger("tests.article.processor.invalid_json"),
        article_logger=logging.getLogger("tests.article.processor.content.invalid_json"),
    )

    assert should_ack is True
    assert use_case.calls == 0


def test_process_article_job_record_invalid_schema_acknowledged() -> None:
    use_case = _FakeUseCase()
    should_ack = process_article_job_record(
        record_body=json.dumps({"version": 1}),
        message_id="m-4",
        receive_count=1,
        use_case=use_case,  # type: ignore[arg-type]
        logger=StructuredLogger("tests.article.processor.invalid_schema"),
        article_logger=logging.getLogger("tests.article.processor.content.invalid_schema"),
    )

    assert should_ack is True
    assert use_case.calls == 0


def test_lambda_handler_returns_batch_failure_when_processing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import while_i_slept_api.article_pipeline.article_processor_handler as module

    use_case = _FakeUseCase()
    monkeypatch.setattr(module, "_get_use_case", lambda: use_case)
    monkeypatch.setattr(
        processing_module,
        "enrich_article_content",
        lambda **_: (_ for _ in ()).throw(RuntimeError("extract failed")),
    )

    result = lambda_handler(
        {
            "Records": [
                {
                    "messageId": "m-5",
                    "body": _valid_body(),
                    "attributes": {"ApproximateReceiveCount": "1"},
                }
            ]
        },
        None,
    )

    assert result == {"batchItemFailures": [{"itemIdentifier": "m-5"}]}
