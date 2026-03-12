"""Modules responsible for content ingestion from RSS/Atom feeds.

This package is write-side only: it discovers configured sources, fetches raw
entries, and normalizes them for downstream ingestion in the article pipeline.
"""

from while_i_slept_api.content.models import FeedDefinition, NormalizedFeedEntry
from while_i_slept_api.content.registry import FeedRegistry
from while_i_slept_api.content.rss import RSSFetcher
from while_i_slept_api.content.topics import ALLOWED_TOPICS, TopicValidationError, validate_topic

__all__ = [
    "ALLOWED_TOPICS",
    "FeedDefinition",
    "FeedRegistry",
    "NormalizedFeedEntry",
    "RSSFetcher",
    "TopicValidationError",
    "validate_topic",
]
