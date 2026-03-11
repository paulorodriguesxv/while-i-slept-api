"""Unit tests for article fetch/enrichment helpers used by RSS ingestion."""

from __future__ import annotations

import logging

from while_i_slept_api.article_pipeline import article_fetcher
from while_i_slept_api.article_pipeline.article_fetcher.cleaning import (
    calculate_reading_time_minutes,
    clean_article_text,
)
from while_i_slept_api.article_pipeline.article_fetcher.extract_metadata import extract_metadata


def test_enrich_article_content_uses_extracted_text_and_metadata(monkeypatch) -> None:
    extracted = "word " * 220
    html = "<html><head></head><body>ok</body></html>"
    metadata = {
        "image_url": "https://example.com/image.jpg",
        "description": "Short description",
        "author": "Reporter",
        "article_published_time": "2026-03-10T11:00:00Z",
    }

    monkeypatch.setattr(article_fetcher, "fetch_html", lambda *_args, **_kwargs: html)
    monkeypatch.setattr(article_fetcher, "extract_main_text", lambda *_args, **_kwargs: extracted)
    monkeypatch.setattr(article_fetcher, "extract_metadata", lambda *_args, **_kwargs: metadata)

    result = article_fetcher.enrich_article_content(
        url="https://example.com/story",
        fallback_text="RSS fallback",
        logger=logging.getLogger("tests.article_fetcher.success"),
    )

    assert result.content.strip() == extracted.strip()
    assert result.image_url == metadata["image_url"]
    assert result.description == metadata["description"]
    assert result.author == metadata["author"]
    assert result.article_published_time == metadata["article_published_time"]
    assert result.reading_time_minutes == 2


def test_enrich_article_content_falls_back_when_extraction_is_short(monkeypatch) -> None:
    monkeypatch.setattr(article_fetcher, "fetch_html", lambda *_args, **_kwargs: "<html></html>")
    monkeypatch.setattr(article_fetcher, "extract_main_text", lambda *_args, **_kwargs: "too short")
    monkeypatch.setattr(article_fetcher, "extract_metadata", lambda *_args, **_kwargs: {})

    result = article_fetcher.enrich_article_content(
        url="https://example.com/story",
        fallback_text="RSS summary text",
        logger=logging.getLogger("tests.article_fetcher.fallback"),
    )

    assert result.content == "RSS summary text"
    assert result.reading_time_minutes == 1


def test_extract_metadata_reads_open_graph_and_author_fields() -> None:
    html = """
    <html><head>
      <meta property="og:image" content="https://example.com/og.jpg"/>
      <meta property="og:description" content="OG description"/>
      <meta name="author" content="Author Name"/>
      <meta property="article:published_time" content="2026-03-10T08:00:00Z"/>
    </head><body></body></html>
    """

    metadata = extract_metadata(html)

    assert metadata["image_url"] == "https://example.com/og.jpg"
    assert metadata["description"] == "OG description"
    assert metadata["author"] == "Author Name"
    assert metadata["article_published_time"] == "2026-03-10T08:00:00Z"


def test_clean_article_text_removes_noise_and_repeated_blank_lines() -> None:
    raw_text = """
      First paragraph with useful text.

      Advertisement: buy now
      Subscribe to our newsletter
      Read more about this

      Second paragraph has real information.


      Third paragraph stays.
    """

    cleaned = clean_article_text(raw_text)

    assert "advertisement" not in cleaned.lower()
    assert "newsletter" not in cleaned.lower()
    assert "read more" not in cleaned.lower()
    assert "First paragraph with useful text." in cleaned
    assert "Second paragraph has real information." in cleaned
    assert "\n\n\n" not in cleaned


def test_calculate_reading_time_minutes_uses_200_wpm_with_minimum_one() -> None:
    assert calculate_reading_time_minutes("") == 1
    assert calculate_reading_time_minutes("word " * 1) == 1
    assert calculate_reading_time_minutes("word " * 200) == 1
    assert calculate_reading_time_minutes("word " * 201) == 2
