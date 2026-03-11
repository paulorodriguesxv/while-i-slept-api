"""Unit tests for single-table key builders."""

from __future__ import annotations

from while_i_slept_api.article_pipeline.keys import article_pk, feed_pk, feed_pk_for_date, feed_sk, raw_sk, summary_sk


def test_article_keys_format() -> None:
    assert article_pk("abc123") == "ARTICLE#abc123"
    assert raw_sk() == "RAW"
    assert summary_sk(1) == "SUMMARY#v1"


def test_feed_keys_format() -> None:
    assert feed_pk("en", "2026-03-11T02:10:00Z") == "FEED#en#2026-03-11"
    assert feed_pk("pt", "2026-03-11T02:10:00+00:00") == "FEED#pt#2026-03-11"
    assert feed_pk_for_date("en", "2026-03-11") == "FEED#en#2026-03-11"
    assert feed_sk("2026-02-27T12:00:00Z", "deadbeef") == "T#2026-02-27T12:00:00Z#H#deadbeef"
