"""Article fetch/extraction helpers for ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from while_i_slept_api.article_pipeline.article_fetcher.cleaning import (
    calculate_reading_time_minutes,
    clean_article_text,
)
from while_i_slept_api.article_pipeline.article_fetcher.extract_metadata import extract_metadata
from while_i_slept_api.article_pipeline.article_fetcher.extract_text import extract_main_text
from while_i_slept_api.article_pipeline.article_fetcher.fetch_html import fetch_html

_MIN_EXTRACTED_CONTENT_LEN = 200


@dataclass(frozen=True, slots=True)
class EnrichedArticleContent:
    """Enriched content payload resolved from source page or RSS fallback."""

    content: str
    reading_time_minutes: int
    image_url: str | None = None
    description: str | None = None
    author: str | None = None
    article_published_time: str | None = None


def enrich_article_content(
    *,
    url: str,
    fallback_text: str,
    logger: logging.Logger,
) -> EnrichedArticleContent:
    """Fetch, extract, clean, and enrich article content with safe fallbacks."""

    fallback_clean = clean_article_text(str(fallback_text or ""))
    html = fetch_html(url, logger=logger)
    metadata = extract_metadata(html) if html else {}
    extracted = extract_main_text(html, logger=logger, url=url)
    cleaned_extracted = clean_article_text(extracted)

    logger.info(
        "Extracted content length",
        extra={"url": url, "content_length": len(cleaned_extracted)},
    )

    content = cleaned_extracted
    if len(cleaned_extracted) < _MIN_EXTRACTED_CONTENT_LEN:
        content = fallback_clean
        logger.info(
            "Extraction fallback used",
            extra={
                "url": url,
                "fallback_length": len(fallback_clean),
            },
        )

    reading_time_minutes = calculate_reading_time_minutes(content)
    logger.info(
        "Reading time calculated",
        extra={"url": url, "reading_time_minutes": reading_time_minutes},
    )

    return EnrichedArticleContent(
        content=content,
        reading_time_minutes=reading_time_minutes,
        image_url=metadata.get("image_url"),
        description=metadata.get("description"),
        author=metadata.get("author"),
        article_published_time=metadata.get("article_published_time"),
    )


__all__ = ["EnrichedArticleContent", "enrich_article_content"]
