"""Additional unit tests to raise summarizer_worker coverage."""

from __future__ import annotations

import json
import types
from typing import Any

import pytest

from while_i_slept_api.core.config import Settings
from while_i_slept_api.summarizer_worker import lambda_handler as lambda_module
from while_i_slept_api.summarizer_worker.errors import (
    SummaryJobNonRetryableError,
    SummaryJobRetryableError,
)
from while_i_slept_api.summarizer_worker.local_consumer import (
    _build_sqs_client,
    _parse_args,
    _process_article_job,
    _process_record,
    _resolve_queue_url,
    main,
    poll_once,
    run_forever,
    run_once,
)
from while_i_slept_api.summarizer_worker.logging import StructuredLogger
from while_i_slept_api.summarizer_worker.message_processing import process_sqs_record
from while_i_slept_api.summarizer_worker.retry import RetryPolicy, execute_with_retries


class _FakeUseCase:
    def __init__(self, *, mode: str = "ok") -> None:
        self.mode = mode
        self.calls = 0

    def process_summary_job(self, _job: Any) -> Any:
        self.calls += 1
        if self.mode == "retryable":
            raise SummaryJobRetryableError("retry")
        if self.mode == "non_retryable":
            raise SummaryJobNonRetryableError("no retry")
        if self.mode == "error":
            raise RuntimeError("boom")
        return types.SimpleNamespace(status="DONE")


class _FakeSqs:
    def __init__(self, messages: list[dict[str, Any]] | None = None) -> None:
        self.messages = messages or []
        self.deleted: list[dict[str, Any]] = []
        self.receive_calls: list[dict[str, Any]] = []
        self.queue_url_calls: list[dict[str, Any]] = []

    def receive_message(self, **kwargs: Any) -> dict[str, Any]:
        self.receive_calls.append(kwargs)
        return {"Messages": self.messages}

    def delete_message(self, **kwargs: Any) -> None:
        self.deleted.append(kwargs)

    def get_queue_url(self, **kwargs: Any) -> dict[str, str]:
        self.queue_url_calls.append(kwargs)
        return {"QueueUrl": "https://queue/url"}


def _legacy_payload() -> str:
    return json.dumps(
        {
            "version": "1.0",
            "job_id": "job",
            "user_id": "usr_1",
            "date": "2026-02-27",
            "lang": "en",
            "window_start": "2026-02-27T00:00:00Z",
            "window_end": "2026-02-27T06:00:00Z",
            "entries": [],
        }
    )


def _article_payload() -> dict[str, Any]:
    return {
        "version": 1,
        "job_id": "job1",
        "article_id": "a1",
        "content_hash": "a" * 64,
        "language": "en",
        "topic": "world",
        "summary_version": 1,
        "priority": "normal",
        "reprocess": False,
        "model_override": None,
        "created_at": "2026-02-27T00:00:00Z",
    }


def test_message_processing_invalid_and_non_retryable_paths() -> None:
    logger = StructuredLogger("tests.summary.additional")
    assert process_sqs_record(
        record_body="{bad",
        message_id="m1",
        receive_count=1,
        use_case=_FakeUseCase(),  # type: ignore[arg-type]
        logger=logger,
        retry_policy=RetryPolicy(max_attempts=1, base_backoff_seconds=0),
    ) is True
    assert process_sqs_record(
        record_body="[]",
        message_id="m2",
        receive_count=1,
        use_case=_FakeUseCase(),  # type: ignore[arg-type]
        logger=logger,
        retry_policy=RetryPolicy(max_attempts=1, base_backoff_seconds=0),
    ) is True
    assert process_sqs_record(
        record_body=json.dumps({"version": "1.0"}),
        message_id="m3",
        receive_count=1,
        use_case=_FakeUseCase(),  # type: ignore[arg-type]
        logger=logger,
        retry_policy=RetryPolicy(max_attempts=1, base_backoff_seconds=0),
    ) is True
    assert process_sqs_record(
        record_body=_legacy_payload(),
        message_id="m4",
        receive_count=1,
        use_case=_FakeUseCase(mode="non_retryable"),  # type: ignore[arg-type]
        logger=logger,
        retry_policy=RetryPolicy(max_attempts=1, base_backoff_seconds=0),
    ) is True


def test_retry_policy_error_branches() -> None:
    with pytest.raises(ValueError):
        execute_with_retries(lambda: "ok", policy=RetryPolicy(max_attempts=0, base_backoff_seconds=0))
    with pytest.raises(SummaryJobNonRetryableError):
        execute_with_retries(
            lambda: (_ for _ in ()).throw(SummaryJobNonRetryableError("x")),
            policy=RetryPolicy(max_attempts=2, base_backoff_seconds=0),
        )
    with pytest.raises(SummaryJobRetryableError):
        execute_with_retries(
            lambda: (_ for _ in ()).throw(SummaryJobRetryableError("x")),
            policy=RetryPolicy(max_attempts=1, base_backoff_seconds=0),
        )


def test_local_consumer_record_processing_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    logger = StructuredLogger("tests.local.consumer")
    policy = RetryPolicy(max_attempts=1, base_backoff_seconds=0)

    assert _process_record(
        record_body="{bad",
        message_id="m1",
        receive_count=1,
        use_case=_FakeUseCase(),
        logger=logger,
        retry_policy=policy,
    ) is True

    monkeypatch.setattr(
        "while_i_slept_api.summarizer_worker.local_consumer.process_sqs_record",
        lambda **_: False,
    )
    assert _process_record(
        record_body=_legacy_payload(),
        message_id="m2",
        receive_count=1,
        use_case=_FakeUseCase(),
        logger=logger,
        retry_policy=policy,
    ) is False

    assert _process_article_job(
        payload={"version": 1},
        message_id="m3",
        receive_count=1,
        use_case=_FakeUseCase(),
        logger=logger,
        retry_policy=policy,
    ) is True
    assert _process_article_job(
        payload=_article_payload(),
        message_id="m4",
        receive_count=1,
        use_case=_FakeUseCase(mode="error"),
        logger=logger,
        retry_policy=policy,
    ) is False
    assert _process_article_job(
        payload=_article_payload(),
        message_id="m5",
        receive_count=1,
        use_case=_FakeUseCase(mode="ok"),
        logger=logger,
        retry_policy=policy,
    ) is True


def test_local_consumer_poll_and_queue_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    sqs = _FakeSqs(messages=[])
    poll_once(
        sqs_client=sqs,
        queue_url="https://queue/url",
        logger=StructuredLogger("tests.local.poll"),
        use_case=_FakeUseCase(),
        retry_policy=RetryPolicy(max_attempts=1, base_backoff_seconds=0),
        wait_time_seconds=1,
        visibility_timeout_seconds=30,
        sleep_fn=lambda _: None,
    )
    assert len(sqs.receive_calls) == 1

    sqs2 = _FakeSqs(
        messages=[
            {
                "MessageId": "m1",
                "Body": _legacy_payload(),
                "ReceiptHandle": "r1",
                "Attributes": {"ApproximateReceiveCount": "bad"},
            }
        ]
    )
    monkeypatch.setattr(
        "while_i_slept_api.summarizer_worker.local_consumer._process_record",
        lambda **_: True,
    )
    poll_once(
        sqs_client=sqs2,
        queue_url="https://queue/url",
        logger=StructuredLogger("tests.local.poll2"),
        use_case=_FakeUseCase(),
        retry_policy=RetryPolicy(max_attempts=1, base_backoff_seconds=0),
        wait_time_seconds=1,
        visibility_timeout_seconds=30,
    )
    assert sqs2.deleted == [{"QueueUrl": "https://queue/url", "ReceiptHandle": "r1"}]


def test_local_consumer_resolve_queue_and_build_client(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        jwt_secret="x" * 32,
        summary_jobs_queue_url="https://from/settings",
    )
    sqs = _FakeSqs()
    assert _resolve_queue_url(settings, sqs) == "https://from/settings"

    settings_no_url = Settings(jwt_secret="x" * 32, summary_jobs_queue_url=None)
    monkeypatch.setenv("SQS_QUEUE_NAME", "summary-jobs")
    assert _resolve_queue_url(settings_no_url, sqs) == "https://queue/url"
    monkeypatch.delenv("SQS_QUEUE_NAME")
    with pytest.raises(ValueError):
        _resolve_queue_url(settings_no_url, sqs)

    calls: list[dict[str, Any]] = []
    fake_boto3 = types.SimpleNamespace(client=lambda service, **kwargs: calls.append({"service": service, **kwargs}) or "client")
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake_boto3)
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://endpoint")
    settings_client = Settings(jwt_secret="x" * 32, aws_region="us-east-1", sqs_endpoint_url=None, aws_endpoint_url=None)
    assert _build_sqs_client(settings_client) == "client"
    assert calls[0]["endpoint_url"] == "http://endpoint"


def test_local_consumer_run_forever_single_iteration(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(jwt_secret="x" * 32, summary_jobs_queue_url="https://queue")
    signal_handler: dict[str, Any] = {}
    poll_calls = {"count": 0}

    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer._build_sqs_client", lambda _: _FakeSqs())
    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer.build_process_summary_use_case", lambda: _FakeUseCase())
    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer._resolve_queue_url", lambda *_: "https://queue")

    def _fake_signal(_sig: Any, handler: Any) -> None:
        signal_handler["fn"] = handler

    def _fake_poll_once(**_: Any) -> None:
        poll_calls["count"] += 1
        signal_handler["fn"](2, None)

    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer.signal.signal", _fake_signal)
    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer.poll_once", _fake_poll_once)
    run_forever(settings)
    assert poll_calls["count"] == 1


def test_local_consumer_run_once_stops_after_empty_polls(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(jwt_secret="x" * 32, summary_jobs_queue_url="https://queue")
    poll_calls = {"count": 0}

    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer._build_sqs_client", lambda _: _FakeSqs())
    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer.build_process_summary_use_case", lambda: _FakeUseCase())
    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer._resolve_queue_url", lambda *_: "https://queue")
    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer.signal.signal", lambda *_: None)

    def _fake_poll_once(**_: Any) -> bool:
        poll_calls["count"] += 1
        return False

    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer.poll_once", _fake_poll_once)
    run_once(settings, max_empty_polls=2)

    assert poll_calls["count"] == 2


def test_local_consumer_cli_once_mode_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, Any] = {}

    def _fake_run_once(*, max_empty_polls: int, settings: Settings | None = None) -> None:
        called["run_once"] = {"max_empty_polls": max_empty_polls, "settings": settings}

    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer.run_once", _fake_run_once)
    monkeypatch.setattr("while_i_slept_api.summarizer_worker.local_consumer.run_forever", lambda *_: called.setdefault("run_forever", True))

    args = _parse_args(["--once", "--max-empty-polls", "3"])
    assert args.once is True
    assert args.max_empty_polls == 3

    main(["--once", "--max-empty-polls", "3"])
    assert called["run_once"]["max_empty_polls"] == 3
    assert "run_forever" not in called


def test_lambda_handler_extra_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    assert lambda_module.lambda_handler({"Records": "bad"}, None) == {"batchItemFailures": []}

    class _UseCase:
        def process_summary_job(self, _job: Any) -> Any:
            raise SummaryJobRetryableError("x")

    monkeypatch.setattr(lambda_module, "_get_use_case", lambda: _UseCase())
    monkeypatch.setattr(lambda_module, "_RETRY_POLICY", RetryPolicy(max_attempts=1, base_backoff_seconds=0))
    result = lambda_module.lambda_handler(
        {
            "Records": [
                "skip",
                {"messageId": "m1", "body": _legacy_payload(), "attributes": {"ApproximateReceiveCount": "oops"}},
            ]
        },
        None,
    )
    assert result == {"batchItemFailures": [{"itemIdentifier": "m1"}]}
