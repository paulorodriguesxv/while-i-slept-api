"""AWS Lambda adapter logic for periodic RSS ingestion."""

from __future__ import annotations

import os
from typing import Any

from while_i_slept_api.article_pipeline.article_job_dto import ArticleJob
from while_i_slept_api.article_pipeline.runtime import build_article_job_queue
from while_i_slept_api.content.registry import FeedRegistry
from while_i_slept_api.content.rss import RSSFetcher
from while_i_slept_api.core.logging import StructuredLogger

_LOGGER = StructuredLogger("while_i_slept.lambda.ingestion")


def lambda_handler(event: dict[str, Any] | None, _context: Any) -> dict[str, Any]:
    """Fetch feeds and enqueue lightweight article jobs."""

    payload = event if isinstance(event, dict) else {}
    language = str(payload.get("language") or os.getenv("FEED_LANGUAGE", "pt"))
    topic = str(payload.get("topic") or os.getenv("FEED_TOPIC", "world"))

    registry = FeedRegistry()
    feeds = registry.resolve(language=language, topic=topic)
    fetcher = RSSFetcher()
    queue = build_article_job_queue()

    if not feeds:
        _LOGGER.info("ingestion_lambda.no_feeds", language=language, topic=topic)
        return {"language": language, "topic": topic, "total": 0, "enqueued": 0}

    total = 0
    enqueued = 0

    for feed in feeds:
        entries = fetcher.fetch_feed(language=language, topic=topic, feed=feed)
        total += len(entries)
        for entry in entries:
            source_url = entry.link or feed.url
            job = ArticleJob(
                version=1,
                entry_id=entry.entry_id,
                language=entry.language,  # type: ignore[arg-type]
                topic=entry.topic,  # type: ignore[arg-type]
                source=feed.source_name or "Unknown Source",
                source_feed_url=feed.url,
                article_url=source_url,
                title=entry.title,
                summary=entry.summary,
                published_at=entry.published_at,
            )
            queue.enqueue(job)
            enqueued += 1

    _LOGGER.info(
        "ingestion_lambda.completed",
        language=language,
        topic=topic,
        total=total,
        enqueued=enqueued,
    )
    return {
        "language": language,
        "topic": topic,
        "total": total,
        "enqueued": enqueued,
    }
