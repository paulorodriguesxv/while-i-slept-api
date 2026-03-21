"""Runtime wiring for article summary pipeline."""

from __future__ import annotations

import os

from while_i_slept_api.article_pipeline.infrastructure.aws_clients import AwsClientFactory
from while_i_slept_api.article_pipeline.infrastructure.dynamodb_single_table import DynamoArticleSummaryRepository
from while_i_slept_api.article_pipeline.infrastructure.sqs_queue import SqsArticleJobQueue, SqsSummaryJobQueue
from while_i_slept_api.article_pipeline.ports import ArticleJobQueue
from while_i_slept_api.article_pipeline.summarizers import NotImplementedSummarizer, SmartBrevitySummarizer
from while_i_slept_api.article_pipeline.use_cases import IngestArticleUseCase, ProcessSummaryJobUseCase
from while_i_slept_api.core.config import Settings, get_settings
from while_i_slept_api.core.logging import StructuredLogger


def _resolve_articles_table_name() -> str:
    return os.getenv("ARTICLES_TABLE_NAME") or os.getenv("DYNAMO_TABLE_NAME") or "articles"


def _resolve_queue_name() -> str:
    return os.getenv("SQS_QUEUE_NAME") or "summary-jobs"


def _resolve_queue_url() -> str | None:
    return os.getenv("SUMMARY_QUEUE_URL")


def _resolve_article_jobs_queue_name() -> str:
    return os.getenv("ARTICLE_JOBS_QUEUE_NAME") or "article-jobs"


def _resolve_article_jobs_queue_url() -> str | None:
    return os.getenv("ARTICLE_JOBS_QUEUE_URL")


def build_article_job_queue() -> ArticleJobQueue:
    """Build article-jobs queue adapter used by ingestion lambda."""

    factory = AwsClientFactory()
    queue_name = _resolve_article_jobs_queue_name()
    queue_url = _resolve_article_jobs_queue_url()
    if queue_url:
        return SqsArticleJobQueue(
            factory.sqs_client(),
            queue_name=queue_name,
            queue_url=queue_url,
        )
    return SqsArticleJobQueue(
        factory.sqs_client(),
        queue_name=queue_name,
    )


def build_ingestion_use_case() -> IngestArticleUseCase:
    """Build ingestion use case using AWS adapters."""

    factory = AwsClientFactory()
    repository = DynamoArticleSummaryRepository.from_resource(
        factory.dynamodb_resource(),
        table_name=_resolve_articles_table_name(),
    )
    queue_name = _resolve_queue_name()
    queue_url = _resolve_queue_url()
    if queue_url:
        queue = SqsSummaryJobQueue(
            factory.sqs_client(),
            queue_name=queue_name,
            queue_url=queue_url,
        )
    else:
        queue = SqsSummaryJobQueue(
            factory.sqs_client(),
            queue_name=queue_name,
        )
    return IngestArticleUseCase(
        repository=repository,
        queue=queue,
        logger=StructuredLogger("while_i_slept.ingestion"),
    )


def build_process_summary_use_case(settings: Settings | None = None) -> ProcessSummaryJobUseCase:
    """Build summary processing use case using AWS adapters."""

    factory = AwsClientFactory()
    cfg = settings or get_settings()
    repository = DynamoArticleSummaryRepository.from_resource(
        factory.dynamodb_resource(),
        table_name=_resolve_articles_table_name(),
    )

    logger = StructuredLogger("while_i_slept.summary_worker")

    summarizer_type = (cfg.summarizer_impl or "smart").lower()
    if summarizer_type == "smart":
        summarizer = SmartBrevitySummarizer(logger=logger)
    else:
        summarizer = NotImplementedSummarizer(logger=logger)

    return ProcessSummaryJobUseCase(
        repository=repository,
        summarizer=summarizer,
        logger=logger,
    )
