"""Manual RSS fetch command for local development."""

from __future__ import annotations

import os

from while_i_slept_api.content.registry import FeedRegistry
from while_i_slept_api.content.rss import RSSFetcher


def main() -> None:
    language = os.getenv("FEED_LANGUAGE", "en")
    topic = os.getenv("FEED_TOPIC", "world")

    registry = FeedRegistry()
    feeds = registry.resolve(language=language, topic=topic)
    fetcher = RSSFetcher()

    if not feeds:
        print(f"No feeds configured for language={language}, topic={topic}")
        return

    total = 0
    for feed in feeds:
        entries = fetcher.fetch_feed(language=language, topic=topic, feed=feed)
        total += len(entries)
        print(f"{feed.url}: {len(entries)} entries")
    print(f"Total entries: {total}")


if __name__ == "__main__":
    main()
