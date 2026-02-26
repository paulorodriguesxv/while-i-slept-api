"""Unit tests for RSS fetcher normalization (offline/mocked)."""

from __future__ import annotations

from datetime import timezone
from types import SimpleNamespace

from while_i_slept_api.content.models import FeedDefinition
from while_i_slept_api.content.rss import RSSFetcher


def test_rss_fetcher_normalizes_entries_and_skips_missing_publication_date() -> None:
    feed = FeedDefinition(url="https://example.com/feed.xml", source_name="Example")
    seen_urls: list[str] = []
    seen_payloads: list[bytes] = []

    def fake_http_get(url: str) -> bytes:
        seen_urls.append(url)
        return b"<rss />"

    def fake_parse_feed(raw: bytes) -> object:
        seen_payloads.append(raw)
        return {
            "entries": [
                {
                    "id": "entry-1",
                    "title": "Story 1",
                    "link": "https://example.com/story-1",
                    "summary": "Summary 1",
                    "published": "Thu, 27 Feb 2026 01:30:00 -0300",
                },
                {
                    "id": "entry-no-date",
                    "title": "No date",
                    "link": "https://example.com/story-no-date",
                    "summary": "Should be skipped",
                },
                {
                    "guid": "entry-2",
                    "title": "Story 2",
                    "description": "Summary 2",
                    "published": "2026-02-27T05:00:00Z",
                },
            ]
        }

    fetcher = RSSFetcher(http_get=fake_http_get, parse_feed=fake_parse_feed)

    entries = fetcher.fetch_feed(language="en", topic="technology", feed=feed)

    assert seen_urls == ["https://example.com/feed.xml"]
    assert seen_payloads == [b"<rss />"]
    assert len(entries) == 2

    first = entries[0]
    assert first.language == "en"
    assert first.topic == "technology"
    assert first.feed_url == feed.url
    assert first.entry_id == "entry-1"
    assert first.title == "Story 1"
    assert first.link == "https://example.com/story-1"
    assert first.summary == "Summary 1"
    assert first.published_at.tzinfo is timezone.utc
    assert first.published_at.isoformat() == "2026-02-27T04:30:00+00:00"

    second = entries[1]
    assert second.entry_id == "entry-2"
    assert second.summary == "Summary 2"
    assert second.published_at.tzinfo is timezone.utc
    assert second.published_at.isoformat() == "2026-02-27T05:00:00+00:00"


def test_rss_fetcher_normalize_parsed_feed_accepts_object_entries() -> None:
    feed = FeedDefinition(url="https://example.com/feed.xml")
    parsed = SimpleNamespace(
        entries=[
            SimpleNamespace(
                id="obj-1",
                title="Object Entry",
                link="https://example.com/object-1",
                summary="Object summary",
                published="Fri, 27 Feb 2026 09:00:00 +0000",
            )
        ]
    )
    fetcher = RSSFetcher(http_get=lambda _: b"", parse_feed=lambda _: parsed)

    entries = fetcher.fetch_feed(language="pt", topic="world", feed=feed)

    assert len(entries) == 1
    assert entries[0].entry_id == "obj-1"
    assert entries[0].title == "Object Entry"
    assert entries[0].published_at.tzinfo is timezone.utc
