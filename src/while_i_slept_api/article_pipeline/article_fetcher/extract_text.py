"""Text extraction helper for article ingestion."""

from __future__ import annotations

import logging

try:
    import trafilatura
except Exception:  # pragma: no cover - optional import safety
    trafilatura = None  # type: ignore[assignment]


def extract_main_text(html: str, *, logger: logging.Logger, url: str) -> str:
    """Extract main article content from HTML."""

    if not html:
        return ""
    if trafilatura is None:
        logger.warning("Article extraction unavailable", extra={"url": url, "error": "trafilatura_missing"})
        return ""

    try:
        extracted = trafilatura.extract(html) or ""
    except Exception as exc:
        logger.warning(
            "Article extraction failed",
            extra={"url": url, "error": exc.__class__.__name__},
        )
        return ""

    text = extracted.strip()
    logger.info(
        "Fetched full article",
        extra={
            "url": url,
            "content_length": len(text),
        },
    )
    return text
