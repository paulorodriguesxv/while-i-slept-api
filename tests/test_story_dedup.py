"""Unit tests for story deduplication helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from while_i_slept_api.article_pipeline.feed_query.dto import SleepWindowItem
from while_i_slept_api.article_pipeline.story_dedup.cluster import cluster_articles, deduplicate_articles


def _item(*, content_hash: str, title: str, summary: str | None = None) -> SleepWindowItem:
    return SleepWindowItem(
        content_hash=content_hash,
        title=title,
        source="Example",
        source_url=f"https://example.com/{content_hash}",
        published_at=datetime(2026, 3, 10, 1, 0, tzinfo=UTC),
        summary=summary,
    )


def test_deduplicate_articles_identical_titles_returns_one_result() -> None:
    articles = [
        _item(content_hash="h1", title="Market Update: Inflation Falls", summary="Short."),
        _item(content_hash="h2", title="Market Update: Inflation Falls", summary="Longer summary text."),
    ]

    deduplicated = deduplicate_articles(articles)

    assert len(deduplicated) == 1
    assert deduplicated[0].content_hash == "h2"


def test_cluster_articles_groups_similar_titles() -> None:
    articles = [
        _item(content_hash="h1", title="Senate approves major climate bill in US"),
        _item(content_hash="h2", title="US senate approves major climate bill"),
    ]

    clusters = cluster_articles(articles)

    assert len(clusters) == 1
    assert [item.content_hash for item in clusters[0]] == ["h1", "h2"]


def test_cluster_articles_keeps_different_topics_separate() -> None:
    articles = [
        _item(content_hash="h1", title="Stock market closes higher after policy update"),
        _item(content_hash="h2", title="Football team wins championship after penalty shootout"),
    ]

    clusters = cluster_articles(articles)

    assert len(clusters) == 2
    assert [item.content_hash for item in deduplicate_articles(articles)] == ["h1", "h2"]


def test_deduplicate_articles_is_deterministic() -> None:
    articles = [
        _item(content_hash="a1", title="Court approves new tax package", summary="same-size"),
        _item(content_hash="a2", title="New tax package approved by court", summary="same-size"),
        _item(content_hash="b1", title="Space agency launches moon mission", summary="another"),
    ]

    result_one = deduplicate_articles(articles)
    result_two = deduplicate_articles(articles)

    assert [item.content_hash for item in result_one] == [item.content_hash for item in result_two]
    assert [item.content_hash for item in result_one] == ["a1", "b1"]
