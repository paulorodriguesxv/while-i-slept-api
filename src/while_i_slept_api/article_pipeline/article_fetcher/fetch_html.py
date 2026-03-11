"""HTML fetch helper for article ingestion."""

from __future__ import annotations

import logging

try:
    import requests
except Exception:  # pragma: no cover - optional import safety
    requests = None  # type: ignore[assignment]

DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_USER_AGENT = "while-i-slept-api/1.0 (+https://local.dev)"


def fetch_html(
    url: str,
    *,
    logger: logging.Logger,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    user_agent: str = DEFAULT_USER_AGENT,
) -> str:
    """Fetch article HTML from source URL."""

    if not url:
        return ""
    if requests is None:
        logger.warning("Full article fetch unavailable", extra={"url": url, "error": "requests_missing"})
        return ""

    logger.info("Full article fetch started", extra={"url": url})
    try:
        response = requests.get(
            url,
            timeout=timeout_seconds,
            headers={"User-Agent": user_agent},
        )
        html = response.text or ""
    except Exception as exc:
        logger.warning(
            "Full article fetch failed",
            extra={"url": url, "error": exc.__class__.__name__},
        )
        return ""

    logger.info("Full article fetch succeeded", extra={"url": url, "html_length": len(html)})
    return html
