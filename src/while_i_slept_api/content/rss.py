"""RSS fetch/parsing layer (infrastructure-only, no editorial logic)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import calendar
import time
import urllib.request
from typing import Any, Protocol, cast

from while_i_slept_api.content.models import FeedDefinition, NormalizedFeedEntry


class RSSFetcherError(RuntimeError):
    """Base error for RSS fetching/parsing."""


class RSSParserUnavailableError(RSSFetcherError):
    """Raised when the optional parser dependency is not installed."""


class ParsedFeedLike(Protocol):
    """Minimal parsed feed protocol used by the fetcher."""

    entries: Any


class RSSFetcher:
    """Fetches and normalizes RSS/Atom entries into internal models."""

    def __init__(
        self,
        *,
        http_get: Callable[[str], bytes] | None = None,
        parse_feed: Callable[[bytes], Any] | None = None,
    ) -> None:
        self._http_get = http_get or _default_http_get
        self._parse_feed = parse_feed or _default_parse_feed

    def fetch_feed(
        self,
        *,
        language: str,
        topic: str,
        feed: FeedDefinition,
    ) -> list[NormalizedFeedEntry]:
        """Fetch and normalize entries from a single feed."""

        raw = self._http_get(feed.url)
        parsed = self._parse_feed(raw)
        return self.normalize_parsed_feed(
            parsed=parsed,
            language=language,
            topic=topic,
            feed=feed,
        )

    def fetch_feeds(
        self,
        *,
        language: str,
        topic: str,
        feeds: Sequence[FeedDefinition],
    ) -> list[NormalizedFeedEntry]:
        """Fetch and concatenate entries from multiple feeds."""

        entries: list[NormalizedFeedEntry] = []
        for feed in feeds:
            entries.extend(self.fetch_feed(language=language, topic=topic, feed=feed))
        return entries

    def normalize_parsed_feed(
        self,
        *,
        parsed: Any,
        language: str,
        topic: str,
        feed: FeedDefinition,
    ) -> list[NormalizedFeedEntry]:
        """Normalize a parsed feed object into internal entries."""

        normalized_entries: list[NormalizedFeedEntry] = []
        for raw_entry in _extract_entries(parsed):
            published_at = _extract_published_at(raw_entry)
            if published_at is None:
                continue
            title = _lookup_text(raw_entry, "title") or ""
            link = _lookup_text(raw_entry, "link")
            summary = _lookup_text(raw_entry, "summary") or _lookup_text(raw_entry, "description")
            entry_id = _lookup_text(raw_entry, "id") or _lookup_text(raw_entry, "guid")
            normalized_entries.append(
                NormalizedFeedEntry(
                    language=language,
                    topic=topic,
                    feed_url=feed.url,
                    entry_id=entry_id,
                    title=title,
                    link=link,
                    summary=summary,
                    published_at=published_at,
                )
            )
        return normalized_entries


def _default_http_get(url: str) -> bytes:
    """Fetch raw feed bytes."""

    request = urllib.request.Request(url, headers={"User-Agent": "while-i-slept-api/0.1"})
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - internal infra utility
        return response.read()


def _default_parse_feed(raw_feed: bytes) -> Any:
    """Parse feed bytes using feedparser if available."""

    try:
        import feedparser  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - dependency optional for unit tests
        raise RSSParserUnavailableError("feedparser is not installed") from exc
    return feedparser.parse(raw_feed)


def _extract_entries(parsed: Any) -> list[Any]:
    """Extract parsed feed entries from object or mapping."""

    if isinstance(parsed, Mapping):
        entries = parsed.get("entries", [])
        return list(cast(Sequence[Any], entries))
    entries = getattr(parsed, "entries", [])
    return list(cast(Sequence[Any], entries))


def _lookup(raw: Any, key: str) -> Any:
    """Read a key/attribute from parser output entry objects."""

    if isinstance(raw, Mapping):
        return raw.get(key)
    return getattr(raw, key, None)


def _lookup_text(raw: Any, key: str) -> str | None:
    """Return a text field if present and non-empty."""

    value = _lookup(raw, key)
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _extract_published_at(raw_entry: Any) -> datetime | None:
    """Extract and normalize publication timestamp to aware UTC."""

    for field in ("published_parsed", "updated_parsed"):
        parsed_value = _lookup(raw_entry, field)
        dt = _coerce_datetime(parsed_value)
        if dt is not None:
            return dt

    for field in ("published", "updated", "pubDate", "date"):
        raw_value = _lookup(raw_entry, field)
        dt = _coerce_datetime(raw_value)
        if dt is not None:
            return dt

    return None


def _coerce_datetime(value: Any) -> datetime | None:
    """Convert parser date fields into timezone-aware UTC datetimes."""

    if value is None:
        return None

    if isinstance(value, datetime):
        return _to_utc(value)

    if isinstance(value, time.struct_time):
        timestamp = calendar.timegm(value)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    if isinstance(value, (tuple, list)) and len(value) >= 6:
        try:
            struct = time.struct_time(tuple(int(part) for part in value))
        except (TypeError, ValueError):
            return None
        timestamp = calendar.timegm(struct)
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    if isinstance(value, str):
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError, OverflowError):
            parsed = _parse_iso_datetime(value)
        if parsed is None:
            return None
        return _to_utc(parsed)

    return None


def _parse_iso_datetime(value: str) -> datetime | None:
    """Parse ISO-ish datetime strings as a fallback."""

    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _to_utc(value: datetime) -> datetime:
    """Ensure datetime is timezone-aware UTC."""

    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
