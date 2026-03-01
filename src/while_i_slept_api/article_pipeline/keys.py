"""Single-table DynamoDB key builders."""

from __future__ import annotations


def article_pk(content_hash: str) -> str:
    """Build article partition key."""

    return f"ARTICLE#{content_hash}"


def raw_sk() -> str:
    """Build raw article sort key."""

    return "RAW"


def summary_sk(summary_version: int) -> str:
    """Build summary sort key."""

    return f"SUMMARY#v{summary_version}"


def feed_pk(language: str, topic: str) -> str:
    """Build feed index partition key."""

    return f"FEED#{language}#{topic}"


def feed_sk(published_at: str, content_hash: str) -> str:
    """Build feed index sort key."""

    return f"T#{published_at}#H#{content_hash}"

