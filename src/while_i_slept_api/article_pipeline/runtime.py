"""Runtime wiring for article summary pipeline."""

from __future__ import annotations

from while_i_slept_api.article_pipeline.infrastructure.aws_clients import AwsClientFactory
from while_i_slept_api.article_pipeline.infrastructure.dynamodb_single_table import DynamoArticleSummaryRepository
from while_i_slept_api.article_pipeline.infrastructure.sqs_queue import SqsArticleJobQueue, SqsSummaryJobQueue
from while_i_slept_api.article_pipeline.ports import ArticleJobQueue
from while_i_slept_api.article_pipeline.summarizers import NotImplementedSummarizer, SmartBrevitySummarizer
from while_i_slept_api.article_pipeline.use_cases import IngestArticleUseCase, ProcessSummaryJobUseCase
from while_i_slept_api.core.config import Settings
from while_i_slept_api.core.logging import StructuredLogger


def _resolve_articles_table_name(settings: Settings | None = None) -> str:
    return (settings or Settings()).articles_table


def _resolve_queue_name(settings: Settings | None = None) -> str:
    return (settings or Settings()).summary_jobs_queue_name


def _resolve_queue_url(settings: Settings | None = None) -> str | None:
    return (settings or Settings()).summary_jobs_queue_url


def _resolve_article_jobs_queue_name(settings: Settings | None = None) -> str:
    return (settings or Settings()).article_jobs_queue_name


def _resolve_article_jobs_queue_url(settings: Settings | None = None) -> str | None:
    return (settings or Settings()).article_jobs_queue_url


def build_article_job_queue(settings: Settings | None = None) -> ArticleJobQueue:
    """Build article-jobs queue adapter used by ingestion lambda."""

    cfg = settings or Settings()
    factory = AwsClientFactory(settings=cfg)
    queue_name = _resolve_article_jobs_queue_name(cfg)
    queue_url = _resolve_article_jobs_queue_url(cfg)
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


def build_ingestion_use_case(settings: Settings | None = None) -> IngestArticleUseCase:
    """Build ingestion use case using AWS adapters."""

    cfg = settings or Settings()
    factory = AwsClientFactory(settings=cfg)
    repository = DynamoArticleSummaryRepository.from_resource(
        factory.dynamodb_resource(),
        table_name=_resolve_articles_table_name(cfg),
    )
    queue_name = _resolve_queue_name(cfg)
    queue_url = _resolve_queue_url(cfg)
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

    cfg = settings or Settings()
    factory = AwsClientFactory(settings=cfg)
    repository = DynamoArticleSummaryRepository.from_resource(
        factory.dynamodb_resource(),
        table_name=_resolve_articles_table_name(cfg),
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
