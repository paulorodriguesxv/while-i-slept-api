"""Small shared service-layer utilities."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def utc_now() -> datetime:
    """Return current UTC datetime."""

    return datetime.now(UTC)


def iso_now() -> str:
    """Return current UTC timestamp as ISO-8601 with Z suffix."""

    return utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_user_id() -> str:
    """Generate a stable user id format for the API."""

    return f"usr_{uuid4().hex}"


def new_jti() -> str:
    """Generate a unique JWT id."""

    return uuid4().hex
