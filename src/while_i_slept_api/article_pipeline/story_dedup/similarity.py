"""Title similarity helpers for story deduplication."""

from __future__ import annotations

import re

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "for",
    "from",
    "in",
    "is",
    "la",
    "na",
    "nas",
    "no",
    "nos",
    "of",
    "on",
    "or",
    "os",
    "para",
    "por",
    "the",
    "to",
    "um",
    "uma",
    "with",
}


def normalize_title(title: str) -> list[str]:
    """Normalize a title into meaningful tokens."""

    lowered = title.lower()
    normalized = re.sub(r"[^\w\s]", " ", lowered)
    tokens = normalized.split()
    return [token for token in tokens if token and token not in _STOPWORDS]


def jaccard_similarity(tokens_a: list[str], tokens_b: list[str]) -> float:
    """Return Jaccard similarity between two token lists."""

    set_a = set(tokens_a)
    set_b = set(tokens_b)
    union = set_a | set_b
    if not union:
        return 0.0
    intersection = set_a & set_b
    return len(intersection) / len(union)
