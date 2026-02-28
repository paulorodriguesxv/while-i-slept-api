"""Backend-controlled topic definitions for content ingestion."""

from __future__ import annotations


ALLOWED_TOPICS = frozenset(
    {
        "world",
        "technology",
        "business",
        "science",
        "sports",
        "finance",
    }
)


class TopicValidationError(ValueError):
    """Raised when a requested topic is not allowed by the backend."""


def list_allowed_topics() -> tuple[str, ...]:
    """Return allowed topics in stable sorted order."""

    return tuple(sorted(ALLOWED_TOPICS))


def is_allowed_topic(topic: str) -> bool:
    """Return whether the topic is allowed."""

    return topic in ALLOWED_TOPICS


def validate_topic(topic: str) -> str:
    """Validate and return the topic, raising if unsupported."""

    if not is_allowed_topic(topic):
        raise TopicValidationError(f"Unsupported topic: {topic}")
    return topic
