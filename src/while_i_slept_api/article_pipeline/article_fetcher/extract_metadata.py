"""Metadata extraction helper for article ingestion."""

from __future__ import annotations

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional import safety
    BeautifulSoup = None  # type: ignore[assignment]


def _meta_content(soup: object, *, key: str, attr_name: str) -> str | None:
    tag = soup.find("meta", attrs={attr_name: key})
    if tag is None:
        return None
    content = tag.get("content")
    if content is None:
        return None
    normalized = str(content).strip()
    return normalized or None


def extract_metadata(html: str) -> dict[str, str]:
    """Extract simple article metadata from HTML."""

    if not html or BeautifulSoup is None:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    image_url = _meta_content(soup, key="og:image", attr_name="property")
    description = _meta_content(soup, key="og:description", attr_name="property") or _meta_content(
        soup,
        key="description",
        attr_name="name",
    )
    author = (
        _meta_content(soup, key="author", attr_name="name")
        or _meta_content(soup, key="article:author", attr_name="property")
    )
    published_time = (
        _meta_content(soup, key="article:published_time", attr_name="property")
        or _meta_content(soup, key="article:published_time", attr_name="name")
    )

    metadata: dict[str, str] = {}
    if image_url:
        metadata["image_url"] = image_url
    if description:
        metadata["description"] = description
    if author:
        metadata["author"] = author
    if published_time:
        metadata["article_published_time"] = published_time
    return metadata
