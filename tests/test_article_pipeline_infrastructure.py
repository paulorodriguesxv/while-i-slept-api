"""Unit tests for article_pipeline infrastructure adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from while_i_slept_api.article_pipeline.infrastructure import aws_clients
from while_i_slept_api.article_pipeline.article_job_dto import ArticleJob
from while_i_slept_api.article_pipeline.infrastructure.dynamodb_single_table import (
    DynamoArticleSummaryRepository,
    _normalize_number,
)
from while_i_slept_api.article_pipeline.infrastructure.sqs_queue import SqsArticleJobQueue, SqsSummaryJobQueue
from while_i_slept_api.article_pipeline.models import RawArticle
from while_i_slept_api.article_pipeline.dto import SummaryJob


class _ConditionalCheckFailed(Exception):
    pass


class _FakeTable:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict[str, Any]] = {}
        self.put_calls: list[dict[str, Any]] = []
        self.update_calls: list[dict[str, Any]] = []
        self.query_calls: list[dict[str, Any]] = []
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

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.query_calls.append(kwargs)
        values = kwargs.get("ExpressionAttributeValues", {})
        pk = values.get(":pk")
        start = values.get(":start")
        end = values.get(":end")
        limit = int(kwargs.get("Limit", 50))
        rows = [
            item
            for item in self.items.values()
            if item.get("pk") == pk and start <= item.get("sk", "") <= end
        ]
        rows.sort(key=lambda item: str(item.get("sk", "")))
        return {"Items": rows[:limit]}


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


def _sample_article_job() -> ArticleJob:
    return ArticleJob.from_payload(
        {
            "version": 1,
            "entry_id": "entry_1",
            "language": "en",
            "topic": "world",
            "source": "Example",
            "source_feed_url": "https://example.com/feed",
            "article_url": "https://example.com/story",
            "title": "Story",
            "summary": "Short summary",
            "published_at": "2026-02-27T10:00:00Z",
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
    monkeypatch.setenv("APP_ARTICLES_TABLE", "articles_env")

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

    monkeypatch.setenv("APP_SUMMARY_JOBS_QUEUE_NAME", "summary-jobs")
    monkeypatch.delenv("APP_SUMMARY_JOBS_QUEUE_URL", raising=False)
    queue = SqsSummaryJobQueue(_Client())
    job = _sample_job()
    queue.enqueue(job)
    queue.enqueue(job)

    assert len([call for call in calls if call["fn"] == "get_queue_url"]) == 1
    assert len([call for call in calls if call["fn"] == "send_message"]) == 2


def test_article_sqs_queue_enqueues_with_cached_url(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    class _Client:
        def get_queue_url(self, QueueName: str) -> dict[str, str]:  # noqa: N803
            calls.append({"fn": "get_queue_url", "QueueName": QueueName})
            return {"QueueUrl": "https://example/article-jobs"}

        def send_message(self, **kwargs: Any) -> None:
            calls.append({"fn": "send_message", **kwargs})

    monkeypatch.setenv("APP_ARTICLE_JOBS_QUEUE_NAME", "article-jobs")
    monkeypatch.delenv("APP_ARTICLE_JOBS_QUEUE_URL", raising=False)
    queue = SqsArticleJobQueue(_Client())
    job = _sample_article_job()
    queue.enqueue(job)
    queue.enqueue(job)

    assert len([call for call in calls if call["fn"] == "get_queue_url"]) == 1
    assert len([call for call in calls if call["fn"] == "send_message"]) == 2


def test_aws_client_factory_uses_resolved_env(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeBoto3(resource_calls=[], client_calls=[])
    monkeypatch.setattr(aws_clients, "boto3", fake)
    monkeypatch.setenv("APP_AWS_REGION", "us-east-2")
    monkeypatch.setenv("APP_AWS_ENDPOINT_URL", "http://localstack:4566")

    factory = aws_clients.AwsClientFactory()
    resource = factory.dynamodb_resource()
    client = factory.sqs_client()

    assert resource == "resource"
    assert client == "client"
    assert fake.resource_calls[0]["service_name"] == "dynamodb"
    assert fake.resource_calls[0]["region_name"] == "us-east-2"
    assert fake.resource_calls[0]["endpoint_url"] == "http://localstack:4566"
    assert fake.client_calls[0]["service_name"] == "sqs"

def test_dynamo_repo_query_feed_window_returns_rows_in_range_in_order() -> None:
    table = _FakeTable()
    repo = DynamoArticleSummaryRepository(table)
    table.items[("FEED#en#all", "T#2026-03-10T00:20:00+00:00#H#h0")] = {
        "pk": "FEED#en#all",
        "sk": "T#2026-03-10T00:20:00+00:00#H#h0",
        "content_hash": "h0",
        "title": "Old",
        "source": "S",
        "source_url": "https://s/0",
        "published_at": "2026-03-10T00:20:00+00:00",
        "summary_version_default": 1,
    }
    table.items[("FEED#en#all", "T#2026-03-10T01:20:00+00:00#H#h1")] = {
        "pk": "FEED#en#all",
        "sk": "T#2026-03-10T01:20:00+00:00#H#h1",
        "content_hash": "h1",
        "title": "One",
        "source": "S",
        "source_url": "https://s/1",
        "published_at": "2026-03-10T01:20:00+00:00",
        "summary_version_default": 1,
    }
    table.items[("FEED#en#all", "T#2026-03-10T02:20:00+00:00#H#h2")] = {
        "pk": "FEED#en#all",
        "sk": "T#2026-03-10T02:20:00+00:00#H#h2",
        "content_hash": "h2",
        "title": "Two",
        "source": "S",
        "source_url": "https://s/2",
        "published_at": "2026-03-10T02:20:00+00:00",
        "summary_version_default": 2,
    }
    table.items[("FEED#en#all", "T#2026-03-10T03:20:00+00:00#H#h3")] = {
        "pk": "FEED#en#all",
        "sk": "T#2026-03-10T03:20:00+00:00#H#h3",
        "content_hash": "h3",
        "title": "New",
        "source": "S",
        "source_url": "https://s/3",
        "published_at": "2026-03-10T03:20:00+00:00",
        "summary_version_default": 1,
    }

    rows = repo.query_feed_window(
        language="en",
        start_time=datetime(2026, 3, 10, 1, 0, tzinfo=UTC),
        end_time=datetime(2026, 3, 10, 3, 0, tzinfo=UTC),
        limit=10,
    )

    assert [row["content_hash"] for row in rows] == ["h1", "h2"]
    assert [row["published_at"] for row in rows] == [
        "2026-03-10T01:20:00+00:00",
        "2026-03-10T02:20:00+00:00",
    ]


def test_dynamo_repo_query_feed_window_empty_returns_empty_list() -> None:
    table = _FakeTable()
    repo = DynamoArticleSummaryRepository(table)

    rows = repo.query_feed_window(
        language="pt",
        start_time=datetime(2026, 3, 10, 1, 0, tzinfo=UTC),
        end_time=datetime(2026, 3, 10, 2, 0, tzinfo=UTC),
        limit=10,
    )

    assert rows == []


def test_dynamo_repo_get_summary_returns_only_done() -> None:
    table = _FakeTable()
    repo = DynamoArticleSummaryRepository(table)
    table.items[("ARTICLE#h1", "SUMMARY#v1")] = {
        "pk": "ARTICLE#h1",
        "sk": "SUMMARY#v1",
        "status": "DONE",
        "summary": "summary-1",
    }
    table.items[("ARTICLE#h2", "SUMMARY#v1")] = {
        "pk": "ARTICLE#h2",
        "sk": "SUMMARY#v1",
        "status": "PENDING",
        "summary": "summary-2",
    }

    assert repo.get_summary("h1", 1) == "summary-1"
    assert repo.get_summary("h2", 1) is None
    assert repo.get_summary("missing", 1) is None


def test_dynamo_repo_save_and_get_sleep_preferences() -> None:
    table = _FakeTable()
    repo = DynamoArticleSummaryRepository(table)

    repo.save_preferences(
        user_id="usr_1",
        sleep_time="23:00",
        wake_time="07:00",
        timezone="America/Sao_Paulo",
    )

    loaded = repo.get_preferences("usr_1")
    missing = repo.get_preferences("usr_missing")

    assert loaded == {
        "sleep_time": "23:00",
        "wake_time": "07:00",
        "timezone": "America/Sao_Paulo",
    }
    assert missing is None
