"""Additional unit tests for article pipeline local consumer helpers."""

from __future__ import annotations

import types
from typing import Any

import pytest

from while_i_slept_api.article_pipeline.local_consumer import (
    _build_sqs_client,
    _parse_args,
    _resolve_queue_url,
    main,
    run_once,
)
from while_i_slept_api.core.config import Settings


class _FakeSqs:
    def __init__(self) -> None:
        self.queue_url_calls: list[dict[str, Any]] = []

    def get_queue_url(self, **kwargs: Any) -> dict[str, str]:
        self.queue_url_calls.append(kwargs)
        return {"QueueUrl": "https://queue/url"}


def test_local_consumer_resolve_queue_url() -> None:
    sqs = _FakeSqs()

    settings_direct = Settings(jwt_secret="x" * 32, summary_jobs_queue_url="https://from/settings")
    assert _resolve_queue_url(settings_direct, sqs) == "https://from/settings"

    settings_by_name = Settings(jwt_secret="x" * 32, summary_jobs_queue_url=None, summary_jobs_queue_name="summary-jobs")
    assert _resolve_queue_url(settings_by_name, sqs) == "https://queue/url"

    with pytest.raises(ValueError):
        _resolve_queue_url(
            Settings(jwt_secret="x" * 32, summary_jobs_queue_url=None, summary_jobs_queue_name=""),
            sqs,
        )


def test_local_consumer_build_sqs_client(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []
    fake_boto3 = types.SimpleNamespace(client=lambda service, **kwargs: calls.append({"service": service, **kwargs}) or "client")
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake_boto3)

    settings_client = Settings(jwt_secret="x" * 32, aws_region="us-east-1")
    assert _build_sqs_client(settings_client) == "client"
    assert calls[0] == {"service": "sqs", "region_name": "us-east-1"}


def test_local_consumer_run_once_stops_after_empty_polls(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(jwt_secret="x" * 32, summary_jobs_queue_url="https://queue")
    poll_calls = {"count": 0}

    monkeypatch.setattr("while_i_slept_api.article_pipeline.local_consumer._build_sqs_client", lambda _: _FakeSqs())
    monkeypatch.setattr(
        "while_i_slept_api.article_pipeline.local_consumer.build_process_summary_use_case",
        lambda *_: object(),
    )
    monkeypatch.setattr("while_i_slept_api.article_pipeline.local_consumer._resolve_queue_url", lambda *_: "https://queue")
    monkeypatch.setattr("while_i_slept_api.article_pipeline.local_consumer.signal.signal", lambda *_: None)

    def _fake_poll_once(**_: Any) -> bool:
        poll_calls["count"] += 1
        return False

    monkeypatch.setattr("while_i_slept_api.article_pipeline.local_consumer.poll_once", _fake_poll_once)
    run_once(settings, max_empty_polls=2)

    assert poll_calls["count"] == 2


def test_local_consumer_cli_once_mode_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, Any] = {}

    def _fake_run_once(*, max_empty_polls: int, settings: Settings | None = None) -> None:
        called["run_once"] = {"max_empty_polls": max_empty_polls, "settings": settings}

    monkeypatch.setattr("while_i_slept_api.article_pipeline.local_consumer.run_once", _fake_run_once)
    monkeypatch.setattr(
        "while_i_slept_api.article_pipeline.local_consumer.run_forever",
        lambda *_: called.setdefault("run_forever", True),
    )

    args = _parse_args(["--once", "--max-empty-polls", "3"])
    assert args.once is True
    assert args.max_empty_polls == 3

    main(["--once", "--max-empty-polls", "3"])
    assert called["run_once"]["max_empty_polls"] == 3
    assert "run_forever" not in called
