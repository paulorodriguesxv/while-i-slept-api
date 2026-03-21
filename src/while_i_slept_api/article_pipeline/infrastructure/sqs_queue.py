"""SQS queue adapters for article pipeline jobs."""

from __future__ import annotations

import os
from typing import Any

from while_i_slept_api.article_pipeline.article_job_dto import ArticleJob
from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.ports import ArticleJobQueue, SummaryJobQueue


class SqsSummaryJobQueue(SummaryJobQueue):
    """Send summary jobs to SQS."""

    def __init__(self, client: Any, *, queue_name: str | None = None, queue_url: str | None = None) -> None:
        self._client = client
        self._queue_name = queue_name or os.getenv("SQS_QUEUE_NAME", "summary-jobs")
        self._queue_url: str | None = queue_url or os.getenv("SUMMARY_QUEUE_URL")

    def enqueue(self, job: SummaryJob) -> None:
        queue_url = self._get_queue_url()
        self._client.send_message(
            QueueUrl=queue_url,
            MessageBody=job.model_dump_json(),
        )

    def _get_queue_url(self) -> str:
        if self._queue_url is None:
            response = self._client.get_queue_url(QueueName=self._queue_name)
            self._queue_url = response["QueueUrl"]
        return self._queue_url


class SqsArticleJobQueue(ArticleJobQueue):
    """Send article jobs to SQS."""

    def __init__(self, client: Any, *, queue_name: str | None = None, queue_url: str | None = None) -> None:
        self._client = client
        self._queue_name = queue_name or os.getenv("ARTICLE_JOBS_QUEUE_NAME", "article-jobs")
        self._queue_url: str | None = queue_url or os.getenv("ARTICLE_JOBS_QUEUE_URL")

    def enqueue(self, job: ArticleJob) -> None:
        queue_url = self._get_queue_url()
        self._client.send_message(
            QueueUrl=queue_url,
            MessageBody=job.model_dump_json(),
        )

    def _get_queue_url(self) -> str:
        if self._queue_url is None:
            response = self._client.get_queue_url(QueueName=self._queue_name)
            self._queue_url = response["QueueUrl"]
        return self._queue_url
