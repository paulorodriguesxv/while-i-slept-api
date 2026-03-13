"""Unit tests for feed premium/free limit gating."""

from __future__ import annotations

from while_i_slept_api.api.routers.feed import (
    FREE_FEED_LIMIT,
    PREMIUM_MAX_FEED_LIMIT,
    resolve_effective_feed_limit,
    resolve_truncated_for_free_tier,
)


def test_free_user_limit_is_capped() -> None:
    assert resolve_effective_feed_limit(25, is_premium=False) == FREE_FEED_LIMIT


def test_premium_user_can_access_full_limit() -> None:
    assert resolve_effective_feed_limit(25, is_premium=True) == 25


def test_premium_user_is_capped_by_max_limit() -> None:
    assert resolve_effective_feed_limit(200, is_premium=True) == PREMIUM_MAX_FEED_LIMIT


def test_default_limit_still_respects_free_cap() -> None:
    assert resolve_effective_feed_limit(None, is_premium=False) == FREE_FEED_LIMIT


def test_default_limit_still_respects_premium_cap() -> None:
    assert resolve_effective_feed_limit(None, is_premium=True) == PREMIUM_MAX_FEED_LIMIT


def test_meta_indicates_free_user_truncation() -> None:
    applied_limit = resolve_effective_feed_limit(20, is_premium=False)

    assert resolve_truncated_for_free_tier(
        requested_limit=20,
        is_premium=False,
        applied_limit=applied_limit,
    ) is True


def test_meta_for_premium_user() -> None:
    applied_limit = resolve_effective_feed_limit(25, is_premium=True)

    assert resolve_truncated_for_free_tier(
        requested_limit=25,
        is_premium=True,
        applied_limit=applied_limit,
    ) is False


def test_meta_applied_limit_matches_gating() -> None:
    assert resolve_effective_feed_limit(20, is_premium=False) == FREE_FEED_LIMIT
