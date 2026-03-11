"""Unit tests for article_pipeline infrastructure adapters."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import os
from types import SimpleNamespace
from typing import Any

import pytest

from while_i_slept_api.article_pipeline.infrastructure import aws_clients
from while_i_slept_api.article_pipeline.infrastructure.dynamodb_single_table import (
    DynamoArticleSummaryRepository,
    _normalize_number,
)
from while_i_slept_api.article_pipeline.infrastructure.sqs_queue import SqsSummaryJobQueue
from while_i_slept_api.article_pipeline.models import RawArticle
from while_i_slept_api.article_pipeline.dto import SummaryJob


class _ConditionalCheckFailed(Exception):
    pass


class _FakeTable:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict[str, Any]] = {}
        self.put_calls: list[dict[str, Any]] = []
        self.update_calls: list[dict[str, Any]] = []
        self.fail_put_condition = False
        self.meta = SimpleNamespace(
            client=SimpleNamespace(exceptions=SimpleNamespace(ConditionalCheckFailedException=_ConditionalCheckFailed))
        )

    def put_item(self, **kwargs: Any) -> None:
        self.put_calls.append(kwargs)
        if kwargs.get("ConditionExpression") and self.fail_put_condition:
            raise _ConditionalCheckFailed()
        item = kwargs["Item"]
        self.items[(item["pk"], item["sk"])] = dict(item)

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        key = kwargs["Key"]
        item = self.items.get((key["pk"], key["sk"]))
        return {"Item": item} if item is not None else {}

    def update_item(self, **kwargs: Any) -> None:
        self.update_calls.append(kwargs)


class _FakeResource:
    def __init__(self, table: _FakeTable) -> None:
        self._table = table
        self.requested_table_name: str | None = None

    def Table(self, name: str) -> _FakeTable:  # noqa: N802 - boto3 style
        self.requested_table_name = name
        return self._table


@dataclass
class _FakeBoto3:
    resource_calls: list[dict[str, Any]]
    client_calls: list[dict[str, Any]]

    def resource(self, service_name: str, **kwargs: Any) -> str:
        self.resource_calls.append({"service_name": service_name, **kwargs})
        return "resource"

    def client(self, service_name: str, **kwargs: Any) -> str:
        self.client_calls.append({"service_name": service_name, **kwargs})
        return "client"


def _sample_article() -> RawArticle:
    return RawArticle(
        content_hash="hash123",
        article_id="a1",
        language="en",
        topic="world",
        source="Example",
        source_url="https://example.com/story",
        title="Title",
        content="Content",
        published_at="2026-02-27T10:00:00Z",
        ingested_at="2026-02-27T10:01:00Z",
    )


def _sample_enriched_article() -> RawArticle:
    return RawArticle(
        content_hash="hash456",
        article_id="a2",
        language="en",
        topic="world",
        source="Example",
        source_url="https://example.com/story-2",
        title="Title 2",
        content="Long content",
        published_at="2026-02-27T11:00:00Z",
        ingested_at="2026-02-27T11:01:00Z",
        image_url="https://example.com/image.jpg",
        description="Description",
        author="Author",
        article_published_time="2026-02-27T10:58:00Z",
        reading_time_minutes=3,
    )


def _sample_job() -> SummaryJob:
    return SummaryJob.from_payload(
        {
            "version": 1,
            "job_id": "job1",
            "article_id": "a1",
            "content_hash": "hash123",
            "language": "en",
            "topic": "world",
            "summary_version": 1,
            "priority": "normal",
            "reprocess": False,
            "model_override": None,
            "created_at": "2026-02-27T10:02:00Z",
        }
    )


def test_normalize_number_handles_nested_decimals() -> None:
    value = {"a": Decimal("1"), "b": [Decimal("2.5"), {"c": Decimal("3")}]}
    assert _normalize_number(value) == {"a": 1, "b": [2.5, {"c": 3}]}


def test_dynamo_repo_put_get_and_update_paths() -> None:
    table = _FakeTable()
    repo = DynamoArticleSummaryRepository(table)
    article = _sample_article()

    assert repo.put_raw_article_if_absent(article) is True
    table.fail_put_condition = True
    assert repo.put_raw_article_if_absent(article) is False

    repo.put_feed_index_item(article, topic=article.topic)
    repo.put_summary_pending(content_hash=article.content_hash, summary_version=1, created_at=article.ingested_at)
    table.fail_put_condition = True
    repo.put_summary_pending(content_hash=article.content_hash, summary_version=1, created_at=article.ingested_at)

    fetched = repo.get_raw_article(article.content_hash)
    assert fetched is not None
    assert fetched.content_hash == article.content_hash
    assert repo.get_raw_article("missing") is None
    assert repo.get_summary_state(content_hash="missing", summary_version=1) is None

    table.items[("ARTICLE#hash123", "SUMMARY#v1")] = {
        "pk": "ARTICLE#hash123",
        "sk": "SUMMARY#v1",
        "status": "PENDING",
        "retry_count": Decimal("2"),
        "summary": "x",
    }
    state = repo.get_summary_state(content_hash="hash123", summary_version=1)
    assert state is not None and state.retry_count == 2

    repo.mark_summary_done(
        content_hash="hash123",
        summary_version=1,
        summary="done",
        model_used="m",
        tokens_used=10,
        cost_estimate_usd=0.01,
        summarized_at="2026-02-27T10:05:00Z",
    )
    repo.mark_summary_done(
        content_hash="hash123",
        summary_version=1,
        summary="done2",
        model_used="m2",
        tokens_used=None,
        cost_estimate_usd=None,
        summarized_at="2026-02-27T10:06:00Z",
    )
    repo.mark_summary_failed(
        content_hash="hash123",
        summary_version=1,
        error_code="E",
        error_message="msg",
        retry_count=3,
        updated_at="2026-02-27T10:07:00Z",
    )
    assert len(table.update_calls) == 3
    assert any("tokens_used" in call["UpdateExpression"] for call in table.update_calls)


def test_dynamo_repo_persists_optional_raw_metadata_fields() -> None:
    table = _FakeTable()
    repo = DynamoArticleSummaryRepository(table)
    article = _sample_enriched_article()

    assert repo.put_raw_article_if_absent(article) is True
    fetched = repo.get_raw_article(article.content_hash)

    assert fetched is not None
    assert fetched.image_url == article.image_url
    assert fetched.description == article.description
    assert fetched.author == article.author
    assert fetched.article_published_time == article.article_published_time
    assert fetched.reading_time_minutes == article.reading_time_minutes


def test_dynamo_repo_from_resource_uses_env_default(monkeypatch: pytest.MonkeyPatch) -> None:
    table = _FakeTable()
    resource = _FakeResource(table)
    monkeypatch.setenv("DYNAMO_TABLE_NAME", "articles_env")

    repo = DynamoArticleSummaryRepository.from_resource(resource)

    assert isinstance(repo, DynamoArticleSummaryRepository)
    assert resource.requested_table_name == "articles_env"


def test_sqs_queue_enqueues_with_cached_url(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    class _Client:
        def get_queue_url(self, QueueName: str) -> dict[str, str]:  # noqa: N803
            calls.append({"fn": "get_queue_url", "QueueName": QueueName})
            return {"QueueUrl": "https://example/queue"}

        def send_message(self, **kwargs: Any) -> None:
            calls.append({"fn": "send_message", **kwargs})

    monkeypatch.setenv("SQS_QUEUE_NAME", "summary-jobs")
    queue = SqsSummaryJobQueue(_Client())
    job = _sample_job()
    queue.enqueue(job)
    queue.enqueue(job)

    assert len([call for call in calls if call["fn"] == "get_queue_url"]) == 1
    assert len([call for call in calls if call["fn"] == "send_message"]) == 2


def test_aws_client_factory_uses_resolved_env(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeBoto3(resource_calls=[], client_calls=[])
    monkeypatch.setattr(aws_clients, "boto3", fake)
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://localstack:4566")

    factory = aws_clients.AwsClientFactory()
    resource = factory.dynamodb_resource()
    client = factory.sqs_client()

    assert resource == "resource"
    assert client == "client"
    assert fake.resource_calls[0]["service_name"] == "dynamodb"
    assert fake.resource_calls[0]["region_name"] == "us-east-2"
    assert fake.resource_calls[0]["endpoint_url"] == "http://localstack:4566"
    assert fake.client_calls[0]["service_name"] == "sqs"
