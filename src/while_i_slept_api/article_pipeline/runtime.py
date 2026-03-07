"""Runtime wiring for article summary pipeline."""

from __future__ import annotations

import os

from while_i_slept_api.article_pipeline.infrastructure.aws_clients import AwsClientFactory
from while_i_slept_api.article_pipeline.infrastructure.dynamodb_single_table import DynamoArticleSummaryRepository
from while_i_slept_api.article_pipeline.infrastructure.sqs_queue import SqsSummaryJobQueue
from while_i_slept_api.article_pipeline.summarizers import NotImplementedSummarizer, SmartBrevitySummarizer
from while_i_slept_api.article_pipeline.use_cases import IngestArticleUseCase, ProcessSummaryJobUseCase
from while_i_slept_api.core.config import Settings, get_settings
from while_i_slept_api.summarizer_worker.logging import StructuredLogger


def build_ingestion_use_case() -> IngestArticleUseCase:
    """Build ingestion use case using AWS adapters."""

    factory = AwsClientFactory()
    repository = DynamoArticleSummaryRepository.from_resource(
        factory.dynamodb_resource(),
        table_name=os.getenv("DYNAMO_TABLE_NAME", "articles"),
    )
    queue = SqsSummaryJobQueue(factory.sqs_client(), queue_name=os.getenv("SQS_QUEUE_NAME", "summary-jobs"))
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
        table_name=os.getenv("DYNAMO_TABLE_NAME", "articles"),
    )

    summarizer_type = (cfg.summarizer_impl or "smart").lower()
    if summarizer_type == "smart":
        summarizer = SmartBrevitySummarizer()
    else:
        summarizer = NotImplementedSummarizer()

    return ProcessSummaryJobUseCase(
        repository=repository,
        summarizer=summarizer,
        logger=StructuredLogger("while_i_slept.summary_worker"),
    )
