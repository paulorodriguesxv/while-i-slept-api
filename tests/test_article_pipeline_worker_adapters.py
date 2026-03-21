"""Unit tests for article-pipeline worker adapters."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import pytest

from while_i_slept_api.article_pipeline.local_consumer import poll_once
from while_i_slept_api.article_pipeline.worker_handler import lambda_handler
from while_i_slept_api.article_pipeline.worker_processing import _execute_with_retries, process_sqs_record
from while_i_slept_api.core.logging import StructuredLogger


def _valid_body() -> str:
    return json.dumps(
        {
            "version": 1,
            "job_id": "job_1",
            "article_id": "article_1",
            "content_hash": "a" * 64,
            "language": "en",
            "topic": "world",
            "summary_version": 1,
            "priority": "normal",
            "reprocess": False,
            "model_override": None,
            "created_at": "2026-02-27T10:00:00Z",
        }
    )


@dataclass
class _FakeResult:
    status: str
    content_hash: str = "a" * 64
    summary_version: int = 1
    retry_count: int = 0


@dataclass
class _FakeUseCase:
    status: str = "DONE"
    raise_error: bool = False
    calls: int = 0

    def process_summary_job(self, _job: Any) -> _FakeResult:
        self.calls += 1
        if self.raise_error:
            raise RuntimeError("temporary")
        return _FakeResult(status=self.status)


class _FakeSQSClient:
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self._messages = messages
        self.deleted: list[dict[str, str]] = []
        self.receive_calls: list[dict[str, Any]] = []

    def receive_message(self, **kwargs: Any) -> dict[str, Any]:
        self.receive_calls.append(kwargs)
        return {"Messages": self._messages}

    def delete_message(self, **kwargs: Any) -> None:
        self.deleted.append(kwargs)


def test_process_sqs_record_returns_false_when_processing_failed() -> None:
    fake_use_case = _FakeUseCase(status="FAILED")
    should_ack = process_sqs_record(
        record_body=_valid_body(),
        message_id="m1",
        receive_count=1,
        use_case=fake_use_case,  # type: ignore[arg-type]
        logger=StructuredLogger("tests.summary.adapter"),
        max_attempts=1,
        base_backoff_seconds=0,
        sleep_fn=lambda _: None,
    )

    assert should_ack is False
    assert fake_use_case.calls == 1


def test_process_sqs_record_acks_invalid_json() -> None:
    fake_use_case = _FakeUseCase(status="DONE")
    should_ack = process_sqs_record(
        record_body="{invalid-json}",
        message_id="m-json",
        receive_count=1,
        use_case=fake_use_case,  # type: ignore[arg-type]
        logger=StructuredLogger("tests.summary.adapter.invalid_json"),
        max_attempts=1,
        base_backoff_seconds=0,
        sleep_fn=lambda _: None,
    )

    assert should_ack is True
    assert fake_use_case.calls == 0


def test_process_sqs_record_acks_invalid_payload_type() -> None:
    fake_use_case = _FakeUseCase(status="DONE")
    should_ack = process_sqs_record(
        record_body=json.dumps(["not-a-dict"]),
        message_id="m-type",
        receive_count=1,
        use_case=fake_use_case,  # type: ignore[arg-type]
        logger=StructuredLogger("tests.summary.adapter.invalid_type"),
        max_attempts=1,
        base_backoff_seconds=0,
        sleep_fn=lambda _: None,
    )

    assert should_ack is True
    assert fake_use_case.calls == 0


def test_process_sqs_record_acks_invalid_payload_schema() -> None:
    fake_use_case = _FakeUseCase(status="DONE")
    should_ack = process_sqs_record(
        record_body=json.dumps({"version": 1}),
        message_id="m-schema",
        receive_count=1,
        use_case=fake_use_case,  # type: ignore[arg-type]
        logger=StructuredLogger("tests.summary.adapter.invalid_schema"),
        max_attempts=1,
        base_backoff_seconds=0,
        sleep_fn=lambda _: None,
    )

    assert should_ack is True
    assert fake_use_case.calls == 0


def test_process_sqs_record_retries_and_returns_false_on_exception() -> None:
    fake_use_case = _FakeUseCase(raise_error=True)
    sleep_calls: list[float] = []
    should_ack = process_sqs_record(
        record_body=_valid_body(),
        message_id="m-retry",
        receive_count=2,
        use_case=fake_use_case,  # type: ignore[arg-type]
        logger=StructuredLogger("tests.summary.adapter.retry"),
        max_attempts=2,
        base_backoff_seconds=0.1,
        sleep_fn=lambda seconds: sleep_calls.append(seconds),
    )

    assert should_ack is False
    assert fake_use_case.calls == 2
    assert sleep_calls == [0.1]


def test_execute_with_retries_rejects_invalid_max_attempts() -> None:
    with pytest.raises(ValueError):
        _execute_with_retries(
            lambda: None,
            max_attempts=0,
            base_backoff_seconds=0,
            sleep_fn=lambda _: None,
        )


def test_lambda_handler_returns_batch_failure_for_failed_job(monkeypatch: pytest.MonkeyPatch) -> None:
    import while_i_slept_api.article_pipeline.worker_handler as module

    monkeypatch.setattr(module, "_get_use_case", lambda: _FakeUseCase(status="FAILED"))

    result = lambda_handler(
        {
            "Records": [
                {
                    "messageId": "m1",
                    "body": _valid_body(),
                    "attributes": {"ApproximateReceiveCount": "1"},
                }
            ]
        },
        None,
    )

    assert result == {"batchItemFailures": [{"itemIdentifier": "m1"}]}


def test_local_poll_once_deletes_message_on_success() -> None:
    sqs = _FakeSQSClient(
        messages=[
            {
                "MessageId": "m-1",
                "ReceiptHandle": "rh-1",
                "Body": _valid_body(),
                "Attributes": {"ApproximateReceiveCount": "1"},
            }
        ]
    )
    use_case = _FakeUseCase(status="DONE")

    poll_once(
        sqs_client=sqs,
        queue_url="https://example.com/queue",
        logger=StructuredLogger("tests.summary.local"),
        use_case=use_case,
        max_attempts=1,
        base_backoff_seconds=0,
        wait_time_seconds=2,
        visibility_timeout_seconds=45,
        sleep_fn=lambda _: None,
    )

    assert len(sqs.receive_calls) == 1
    assert sqs.receive_calls[0]["VisibilityTimeout"] == 45
    assert sqs.deleted == [{"QueueUrl": "https://example.com/queue", "ReceiptHandle": "rh-1"}]
    assert use_case.calls == 1
