"""Unit tests for article_pipeline runtime wiring and hashing."""

from __future__ import annotations

from typing import Any

import pytest

from while_i_slept_api.article_pipeline.hashing import compute_content_hash
from while_i_slept_api.article_pipeline import runtime
from while_i_slept_api.article_pipeline.summarizer import NotImplementedSummarizer, SmartBrevitySummarizer
from while_i_slept_api.article_pipeline.models import RawArticle
from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.use_cases import IngestArticleUseCase, ProcessSummaryJobUseCase


def test_compute_content_hash_normalizes_whitespace() -> None:
    hash_one = compute_content_hash(title="Title  A", content="Line  one")
    hash_two = compute_content_hash(title="Title A", content="Line one")
    hash_three = compute_content_hash(title="Title B", content="Line one")

    assert hash_one == hash_two
    assert hash_one != hash_three
    assert len(hash_one) == 64


def test_runtime_build_ingestion_use_case(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Factory:
        def dynamodb_resource(self) -> str:
            return "dynamo-resource"

        def sqs_client(self) -> str:
            return "sqs-client"

    class _Repo:
        @classmethod
        def from_resource(cls, resource: Any, table_name: str | None = None) -> str:
            assert resource == "dynamo-resource"
            assert table_name == "articles-test"
            return "repo"

    class _Queue:
        def __init__(self, client: Any, *, queue_name: str | None = None) -> None:
            assert client == "sqs-client"
            assert queue_name == "queue-test"

    monkeypatch.setattr(runtime, "AwsClientFactory", _Factory)
    monkeypatch.setattr(runtime, "DynamoArticleSummaryRepository", _Repo)
    monkeypatch.setattr(runtime, "SqsSummaryJobQueue", _Queue)
    monkeypatch.setenv("DYNAMO_TABLE_NAME", "articles-test")
    monkeypatch.setenv("SQS_QUEUE_NAME", "queue-test")

    use_case = runtime.build_ingestion_use_case()

    assert isinstance(use_case, IngestArticleUseCase)


def test_runtime_build_article_job_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Factory:
        def sqs_client(self) -> str:
            return "sqs-client"

    class _Queue:
        def __init__(self, client: Any, *, queue_name: str | None = None, queue_url: str | None = None) -> None:
            assert client == "sqs-client"
            assert queue_name == "article-jobs-test"
            assert queue_url == "https://example.com/article-jobs"

    monkeypatch.setattr(runtime, "AwsClientFactory", _Factory)
    monkeypatch.setattr(runtime, "SqsArticleJobQueue", _Queue)
    monkeypatch.setenv("ARTICLE_JOBS_QUEUE_NAME", "article-jobs-test")
    monkeypatch.setenv("ARTICLE_JOBS_QUEUE_URL", "https://example.com/article-jobs")

    queue = runtime.build_article_job_queue()

    assert isinstance(queue, _Queue)


def test_runtime_build_process_summary_use_case(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Factory:
        def dynamodb_resource(self) -> str:
            return "dynamo-resource"

    class _Repo:
        @classmethod
        def from_resource(cls, resource: Any, table_name: str | None = None) -> str:
            assert resource == "dynamo-resource"
            assert table_name == "articles-test"
            return "repo"

    monkeypatch.setattr(runtime, "AwsClientFactory", _Factory)
    monkeypatch.setattr(runtime, "DynamoArticleSummaryRepository", _Repo)
    monkeypatch.setenv("DYNAMO_TABLE_NAME", "articles-test")

    use_case = runtime.build_process_summary_use_case()

    assert isinstance(use_case, ProcessSummaryJobUseCase)


def test_compat_summarizer_exports() -> None:
    assert SmartBrevitySummarizer is not None
    assert NotImplementedSummarizer is not None


def test_not_implemented_summarizer_raises() -> None:
    summarizer = NotImplementedSummarizer()
    article = RawArticle(
        content_hash="hash",
        article_id="a1",
        language="en",
        topic="world",
        source="Example",
        source_url="https://example.com",
        title="Title",
        content="Content",
        published_at="2026-02-27T00:00:00Z",
        ingested_at="2026-02-27T00:01:00Z",
    )
    job = SummaryJob.from_payload(
        {
            "version": 1,
            "job_id": "job",
            "article_id": "a1",
            "content_hash": "hash",
            "language": "en",
            "topic": "world",
            "summary_version": 1,
            "priority": "normal",
            "reprocess": False,
            "model_override": None,
            "created_at": "2026-02-27T00:02:00Z",
        }
    )
    with pytest.raises(NotImplementedError):
        summarizer.summarize(article, job)
