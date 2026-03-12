"""Single-table DynamoDB key builders."""

from __future__ import annotations

from datetime import UTC, datetime


def article_pk(content_hash: str) -> str:
    """Build article partition key."""

    return f"ARTICLE#{content_hash}"


def raw_sk() -> str:
    """Build raw article sort key."""

    return "RAW"


def summary_sk(summary_version: int) -> str:
    """Build summary sort key."""

    return f"SUMMARY#v{summary_version}"


def _date_bucket_from_published_at(published_at: str) -> str:
    raw = str(published_at or "").strip()
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return str(published_at)[:10]
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).date().isoformat()


def feed_pk(language: str, published_at: str) -> str:
    """Build feed index partition key bucketed by UTC date."""

    return f"FEED#{language}#{_date_bucket_from_published_at(published_at)}"


def feed_pk_for_date(language: str, date_bucket: str) -> str:
    """Build feed index partition key from explicit date bucket."""

    return f"FEED#{language}#{date_bucket}"


def feed_sk(published_at: str, content_hash: str) -> str:
    """Build feed index sort key."""

    return f"T#{published_at}#H#{content_hash}"
