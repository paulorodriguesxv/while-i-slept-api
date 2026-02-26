"""Unit tests for content feed registry resolution."""

from __future__ import annotations

import pytest

from while_i_slept_api.content.models import FeedDefinition
from while_i_slept_api.content.registry import FeedRegistry, UnsupportedLanguageError
from while_i_slept_api.content.topics import TopicValidationError


def test_feed_registry_resolves_by_language_and_topic() -> None:
    registry = FeedRegistry(
        {
            "en": {
                "technology": (
                    FeedDefinition(url="https://example.com/tech.xml", source_name="Example Tech"),
                )
            }
        }
    )

    feeds = registry.resolve("en", "technology")

    assert len(feeds) == 1
    assert feeds[0].url == "https://example.com/tech.xml"
    assert feeds[0].source_name == "Example Tech"


def test_feed_registry_returns_empty_tuple_when_topic_has_no_feeds() -> None:
    registry = FeedRegistry({"pt": {"science": ()}})

    feeds = registry.resolve("pt", "science")

    assert feeds == ()


def test_feed_registry_rejects_unknown_language() -> None:
    registry = FeedRegistry({"en": {"world": ()}})

    with pytest.raises(UnsupportedLanguageError):
        registry.resolve("pt", "world")


def test_feed_registry_rejects_unknown_topic() -> None:
    registry = FeedRegistry({"en": {"world": ()}})

    with pytest.raises(TopicValidationError):
        registry.resolve("en", "politics")
