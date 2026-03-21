"""Manual RSS fetch command for local development."""

from __future__ import annotations

import logging

from while_i_slept_api.article_pipeline.article_fetcher import enrich_article_content
from while_i_slept_api.article_pipeline.hashing import compute_content_hash
from while_i_slept_api.article_pipeline.models import RawArticle
from while_i_slept_api.article_pipeline.runtime import build_ingestion_use_case
from while_i_slept_api.content.registry import FeedRegistry
from while_i_slept_api.content.rss import RSSFetcher
from while_i_slept_api.core.config import Settings
from while_i_slept_api.services.utils import iso_now
from while_i_slept_api.core.logging import StructuredLogger

_INGESTION_LOGGER = logging.getLogger(__name__)
_LOGGER = StructuredLogger("while_i_slept.fetch_rss")


def main() -> None:
    settings = Settings()
    language = settings.feed_language
    topic = settings.feed_topic

    registry = FeedRegistry()
    feeds = registry.resolve(language=language, topic=topic)
    fetcher = RSSFetcher()
    ingestion_use_case = build_ingestion_use_case(settings)

    if not feeds:
        _LOGGER.info(f"No feeds configured for language={language}, topic={topic}")
        return

    total = 0
    inserted = 0
    duplicates = 0
    for feed in feeds:
        entries = fetcher.fetch_feed(language=language, topic=topic, feed=feed)
        total += len(entries)
        for entry in entries:
            source_url = entry.link or feed.url
            enriched = enrich_article_content(
                url=source_url,
                fallback_text=entry.summary or "",
                logger=_INGESTION_LOGGER,
            )
            content = enriched.content
            content_hash = compute_content_hash(title=entry.title, content=content)
            article = RawArticle(
                content_hash=content_hash,
                article_id=entry.entry_id,
                language=entry.language,
                topic=entry.topic,
                source=feed.source_name or "Unknown Source",
                source_url=source_url,
                title=entry.title,
                content=content,
                image_url=enriched.image_url,
                description=enriched.description,
                author=enriched.author,
                article_published_time=enriched.article_published_time,
                reading_time_minutes=enriched.reading_time_minutes,
                published_at=entry.published_at.isoformat(),
                ingested_at=iso_now(),
            )
            result = ingestion_use_case.ingest(article)
            if result.status == "CREATED":
                inserted += 1
            else:
                duplicates += 1
        _LOGGER.info(f"{feed.url}: {len(entries)} entries")
    _LOGGER.info(f"Total entries: {total} | inserted: {inserted} | duplicates: {duplicates}")


if __name__ == "__main__":
    main()
