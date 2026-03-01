"""Hashing helpers for content deduplication."""

from __future__ import annotations

import hashlib


def compute_content_hash(*, title: str, content: str) -> str:
    """Compute deterministic content hash from normalized title+content."""

    normalized_title = " ".join(title.split()).strip()
    normalized_content = " ".join(content.split()).strip()
    payload = f"{normalized_title}\n{normalized_content}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

