"""Text cleaning helpers for article ingestion."""

from __future__ import annotations

import math
import re

_NOISE_TERMS = ("advertisement", "subscribe", "newsletter", "read more")


def clean_article_text(text: str) -> str:
    """Clean article text with deterministic, simple rules."""

    if not text:
        return ""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    cleaned_lines: list[str] = []
    last_was_blank = False

    for raw_line in lines:
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            if not last_was_blank:
                cleaned_lines.append("")
            last_was_blank = True
            continue

        lowered = line.lower()
        if any(term in lowered for term in _NOISE_TERMS):
            continue

        cleaned_lines.append(line)
        last_was_blank = False

    cleaned = "\n".join(cleaned_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def calculate_reading_time_minutes(text: str, *, words_per_minute: int = 200) -> int:
    """Estimate reading time in minutes."""

    if words_per_minute <= 0:
        return 1
    words = re.findall(r"\b[\w'-]+\b", text)
    if not words:
        return 1
    return max(1, math.ceil(len(words) / words_per_minute))
