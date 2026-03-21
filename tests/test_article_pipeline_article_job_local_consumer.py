"""Unit tests for article-job local consumer helpers."""

from __future__ import annotations

import logging
import types
from typing import Any

import pytest

from while_i_slept_api.article_pipeline.article_job_local_consumer import (
    _build_sqs_client,
    _parse_args,
    _resolve_queue_url,
    main,
    poll_once,
    run_once,
)
from while_i_slept_api.core.config import Settings
from while_i_slept_api.core.logging import StructuredLogger


class _FakeSqs:
    def __init__(self, messages: list[dict[str, Any]] | None = None) -> None:
        self._messages = messages or []
        self.queue_url_calls: list[dict[str, Any]] = []
        self.deleted: list[dict[str, Any]] = []
        self.receive_calls: list[dict[str, Any]] = []

    def get_queue_url(self, **kwargs: Any) -> dict[str, str]:
        self.queue_url_calls.append(kwargs)
        return {"QueueUrl": "https://example.com/article-jobs"}

    def receive_message(self, **kwargs: Any) -> dict[str, Any]:
        self.receive_calls.append(kwargs)
        return {"Messages": self._messages}

    def delete_message(self, **kwargs: Any) -> None:
        self.deleted.append(kwargs)


def test_article_job_consumer_resolve_queue_url() -> None:
    sqs = _FakeSqs()

    settings_url = Settings(jwt_secret="x" * 32, article_jobs_queue_url="https://from/env/url")
    assert _resolve_queue_url(settings_url, sqs) == "https://from/env/url"

    settings_name = Settings(jwt_secret="x" * 32, article_jobs_queue_name="article-jobs-custom")
    assert _resolve_queue_url(settings_name, sqs) == "https://example.com/article-jobs"
    assert sqs.queue_url_calls[-1] == {"QueueName": "article-jobs-custom"}


def test_article_job_consumer_build_sqs_client(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    fake_boto3 = types.SimpleNamespace(client=lambda service, **kwargs: calls.append({"service": service, **kwargs}) or "client")
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake_boto3)

    settings = Settings(jwt_secret="x" * 32, aws_region="us-east-1")
    assert _build_sqs_client(settings) == "client"
    assert calls[0] == {"service": "sqs", "region_name": "us-east-1"}


def test_article_job_poll_once_returns_false_for_empty_messages() -> None:
    sqs = _FakeSqs(messages=[])
    sleep_calls: list[float] = []

    has_messages = poll_once(
        sqs_client=sqs,
        queue_url="https://example.com/article-jobs",
        logger=StructuredLogger("tests.article_job.local"),
        article_logger=logging.getLogger("tests.article_job.local.content"),
        use_case=object(),
        wait_time_seconds=2,
        visibility_timeout_seconds=45,
        sleep_fn=lambda seconds: sleep_calls.append(seconds),
    )

    assert has_messages is False
    assert sleep_calls == [0.25]


def test_article_job_poll_once_deletes_message_on_ack(monkeypatch: pytest.MonkeyPatch) -> None:
    import while_i_slept_api.article_pipeline.article_job_local_consumer as module

    sqs = _FakeSqs(
        messages=[
            {
                "MessageId": "m-1",
                "ReceiptHandle": "rh-1",
                "Body": "{\"version\":1}",
                "Attributes": {"ApproximateReceiveCount": "1"},
            }
        ]
    )
    monkeypatch.setattr(module, "process_article_job_record", lambda **_: True)

    has_messages = poll_once(
        sqs_client=sqs,
        queue_url="https://example.com/article-jobs",
        logger=StructuredLogger("tests.article_job.local"),
        article_logger=logging.getLogger("tests.article_job.local.content"),
        use_case=object(),
        wait_time_seconds=2,
        visibility_timeout_seconds=45,
        sleep_fn=lambda _: None,
    )

    assert has_messages is True
    assert sqs.deleted == [{"QueueUrl": "https://example.com/article-jobs", "ReceiptHandle": "rh-1"}]


def test_article_job_run_once_stops_after_empty_polls(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(jwt_secret="x" * 32)
    poll_calls = {"count": 0}

    monkeypatch.setattr("while_i_slept_api.article_pipeline.article_job_local_consumer._build_sqs_client", lambda *_: _FakeSqs())
    monkeypatch.setattr("while_i_slept_api.article_pipeline.article_job_local_consumer._resolve_queue_url", lambda *_: "https://example.com/article-jobs")
    monkeypatch.setattr("while_i_slept_api.article_pipeline.article_job_local_consumer.build_ingestion_use_case", lambda *_: object())
    monkeypatch.setattr("while_i_slept_api.article_pipeline.article_job_local_consumer.signal.signal", lambda *_: None)

    def _fake_poll_once(**_: Any) -> bool:
        poll_calls["count"] += 1
        return False

    monkeypatch.setattr("while_i_slept_api.article_pipeline.article_job_local_consumer.poll_once", _fake_poll_once)
    run_once(settings, max_empty_polls=2)

    assert poll_calls["count"] == 2


def test_article_job_consumer_cli_dispatches_once_and_forever(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, Any] = {}

    def _fake_run_once(*, max_empty_polls: int, settings: Settings | None = None) -> None:
        called["run_once"] = {"max_empty_polls": max_empty_polls, "settings": settings}

    def _fake_run_forever(settings: Settings | None = None) -> None:
        called["run_forever"] = {"settings": settings}

    monkeypatch.setattr("while_i_slept_api.article_pipeline.article_job_local_consumer.run_once", _fake_run_once)
    monkeypatch.setattr("while_i_slept_api.article_pipeline.article_job_local_consumer.run_forever", _fake_run_forever)

    args = _parse_args(["--once", "--max-empty-polls", "3"])
    assert args.once is True
    assert args.max_empty_polls == 3
    main(["--once", "--max-empty-polls", "3"])
    assert called["run_once"]["max_empty_polls"] == 3

    main([])
    assert "run_forever" in called


def test_article_job_consumer_parse_args_rejects_invalid_empty_polls() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--once", "--max-empty-polls", "0"])
