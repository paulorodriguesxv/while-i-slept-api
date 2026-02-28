"""Unit tests for summary worker adapters and retries."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import pytest

from while_i_slept_api.summarizer_worker.errors import SummaryJobRetryableError
from while_i_slept_api.summarizer_worker.lambda_handler import lambda_handler
from while_i_slept_api.summarizer_worker.local_consumer import poll_once
from while_i_slept_api.summarizer_worker.logging import StructuredLogger
from while_i_slept_api.summarizer_worker.message_processing import process_sqs_record
from while_i_slept_api.summarizer_worker.retry import RetryPolicy, execute_with_retries


def _valid_body() -> str:
    return json.dumps(
        {
            "version": "1.0",
            "job_id": "job_1",
            "user_id": "usr_1",
            "date": "2026-02-27",
            "lang": "en",
            "window_start": "2026-02-26T23:00:00-03:00",
            "window_end": "2026-02-27T07:00:00-03:00",
            "entries": [],
        }
    )


@dataclass
class _FakeUseCase:
    calls: int = 0
    should_fail_retryable: bool = False

    def process_summary_job(self, _job: Any) -> Any:
        self.calls += 1
        if self.should_fail_retryable:
            raise SummaryJobRetryableError("temporary")
        return object()


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


def test_execute_with_retries_retries_and_succeeds() -> None:
    attempts = {"count": 0}

    def _fn() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise SummaryJobRetryableError("retry")
        return "ok"

    result = execute_with_retries(_fn, policy=RetryPolicy(max_attempts=3, base_backoff_seconds=0), sleep_fn=lambda _: None)

    assert result == "ok"
    assert attempts["count"] == 3


def test_process_sqs_record_returns_false_for_retryable_failure() -> None:
    fake_use_case = _FakeUseCase(should_fail_retryable=True)
    should_ack = process_sqs_record(
        record_body=_valid_body(),
        message_id="m1",
        receive_count=1,
        use_case=fake_use_case,  # type: ignore[arg-type]
        logger=StructuredLogger("tests.summary.adapter"),
        retry_policy=RetryPolicy(max_attempts=1, base_backoff_seconds=0),
    )

    assert should_ack is False
    assert fake_use_case.calls == 1


def test_lambda_handler_returns_batch_failure_for_retryable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import while_i_slept_api.summarizer_worker.lambda_handler as module

    monkeypatch.setattr(module, "_get_use_case", lambda: _FakeUseCase(should_fail_retryable=True))
    monkeypatch.setattr(module, "_RETRY_POLICY", RetryPolicy(max_attempts=1, base_backoff_seconds=0))

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
    use_case = _FakeUseCase()

    poll_once(
        sqs_client=sqs,
        queue_url="https://example.com/queue",
        logger=StructuredLogger("tests.summary.local"),
        use_case=use_case,
        retry_policy=RetryPolicy(max_attempts=1, base_backoff_seconds=0),
        wait_time_seconds=2,
        visibility_timeout_seconds=45,
        sleep_fn=lambda _: None,
    )

    assert len(sqs.receive_calls) == 1
    assert sqs.receive_calls[0]["VisibilityTimeout"] == 45
    assert sqs.deleted == [{"QueueUrl": "https://example.com/queue", "ReceiptHandle": "rh-1"}]
    assert use_case.calls == 1
