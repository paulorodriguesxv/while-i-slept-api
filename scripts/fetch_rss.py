"""Manual RSS fetch command for local development."""

from __future__ import annotations

import logging
import os
from typing import Any

try:
    import requests
except Exception:  # pragma: no cover - fallback path for minimal environments
    requests = None  # type: ignore[assignment]

try:
    import trafilatura
except Exception:  # pragma: no cover - fallback path for minimal environments
    trafilatura = None  # type: ignore[assignment]

from while_i_slept_api.article_pipeline.hashing import compute_content_hash
from while_i_slept_api.article_pipeline.models import RawArticle
from while_i_slept_api.article_pipeline.runtime import build_ingestion_use_case
from while_i_slept_api.content.registry import FeedRegistry
from while_i_slept_api.content.rss import RSSFetcher
from while_i_slept_api.services.utils import iso_now

_LOGGER = logging.getLogger(__name__)
_MIN_EXTRACTED_CONTENT_LEN = 200


def _normalize_text(value: object) -> str:
    return str(value or "").strip()


def _extract_full_article_text(url: str) -> str:
    if not url:
        raise ValueError("URL is required to extract full article text.")
    
    if requests is None:
        raise ValueError("Requests library is required to fetch article page for full text extraction.")
    
    if trafilatura is None:
        raise ValueError("Trafilatura library is required to extract full article text.")

    try:
        html = requests.get(url, timeout=10).text
    except Exception as exc:
        _LOGGER.warning("Failed to fetch article page", extra={"url": url, "error": exc.__class__.__name__})
        return ""

    try:
        extracted = trafilatura.extract(html) or ""
    except Exception as exc:
        _LOGGER.warning("Failed to extract article content", extra={"url": url, "error": exc.__class__.__name__})
        return ""

    text = _normalize_text(extracted)
    _LOGGER.info(
        "Fetched full article",
        extra={
            "url": url,
            "content_length": len(text),
        },
    )
    return text


def _resolve_entry_content(entry: Any) -> str:
    fallback_summary = _normalize_text(getattr(entry, "summary", ""))
    url = _normalize_text(getattr(entry, "link", ""))
    extracted = _extract_full_article_text(url)
    if len(extracted) < _MIN_EXTRACTED_CONTENT_LEN:
        return fallback_summary
    return extracted


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
            content = _resolve_entry_content(entry)
            print(f"Processing entry {entry.entry_id} with content length {len(content)}")
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
