"""Unit tests for content topic validation."""

from __future__ import annotations

import pytest

from while_i_slept_api.content.topics import TopicValidationError, is_allowed_topic, list_allowed_topics, validate_topic


def test_validate_topic_accepts_allowed_topic() -> None:
    assert validate_topic("technology") == "technology"
    assert is_allowed_topic("technology") is True


def test_validate_topic_rejects_unknown_topic() -> None:
    with pytest.raises(TopicValidationError):
        validate_topic("politics")

    assert is_allowed_topic("politics") is False


def test_list_allowed_topics_is_sorted_and_stable() -> None:
    topics = list_allowed_topics()

    assert topics == tuple(sorted(topics))
    assert "world" in topics
    assert "technology" in topics
