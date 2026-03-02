"""Manual RSS fetch command for local development."""

from __future__ import annotations

import os

from while_i_slept_api.article_pipeline.hashing import compute_content_hash
from while_i_slept_api.article_pipeline.models import RawArticle
from while_i_slept_api.article_pipeline.runtime import build_ingestion_use_case
from while_i_slept_api.content.registry import FeedRegistry
from while_i_slept_api.content.rss import RSSFetcher
from while_i_slept_api.services.utils import iso_now


def main() -> None:
    language = os.getenv("FEED_LANGUAGE", "en")
    topic = os.getenv("FEED_TOPIC", "world")

    registry = FeedRegistry()
    feeds = registry.resolve(language=language, topic=topic)
    fetcher = RSSFetcher()
    ingestion_use_case = build_ingestion_use_case()

    if not feeds:
        print(f"No feeds configured for language={language}, topic={topic}")
        return

    total = 0
    inserted = 0
    duplicates = 0
    for feed in feeds:
        entries = fetcher.fetch_feed(language=language, topic=topic, feed=feed)
        total += len(entries)
        for entry in entries:
            content = entry.summary or ""
            content_hash = compute_content_hash(title=entry.title, content=content)
            article = RawArticle(
                content_hash=content_hash,
                article_id=entry.entry_id,
                language=entry.language,
                topic=entry.topic,
                source=feed.source_name or "Unknown Source",
                source_url=entry.link or feed.url,
                title=entry.title,
                content=content,
                published_at=entry.published_at.isoformat(),
                ingested_at=iso_now(),
            )
            result = ingestion_use_case.ingest(article)
            if result.status == "CREATED":
                inserted += 1
            else:
                duplicates += 1
        print(f"{feed.url}: {len(entries)} entries")
    print(f"Total entries: {total} | inserted: {inserted} | duplicates: {duplicates}")


if __name__ == "__main__":
    main()
