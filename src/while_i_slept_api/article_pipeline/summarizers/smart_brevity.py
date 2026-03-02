"""Deterministic Smart Brevity summarizer."""

from __future__ import annotations

import re
from typing import TypedDict

from while_i_slept_api.article_pipeline.dto import SummaryJob
from while_i_slept_api.article_pipeline.models import RawArticle, SummaryOutput


class _LanguageProfile(TypedDict):
    why_label: str
    bottom_label: str
    keywords: tuple[str, ...]
    fallback_why: str
    fallback_bullet: str
    fallback_bottom: str


_LANGUAGE_PROFILES: dict[str, _LanguageProfile] = {
    "en": {
        "why_label": "Why it matters",
        "bottom_label": "Bottom line",
        "keywords": (
            "impact",
            "increase",
            "decrease",
            "approve",
            "launch",
            "ban",
            "regulation",
            "court",
            "market",
            "economy",
        ),
        "fallback_why": "No clear context is available from the source text.",
        "fallback_bullet": "Details are limited in the source text.",
        "fallback_bottom": "Follow-up coverage is expected.",
    },
    "pt": {
        "why_label": "Por que importa",
        "bottom_label": "Em resumo",
        "keywords": (
            "impacto",
            "aumento",
            "queda",
            "aprov",
            "lan",
            "proib",
            "regula",
            "tribunal",
            "mercado",
            "economia",
        ),
        "fallback_why": "Ainda não há contexto suficiente no texto de origem.",
        "fallback_bullet": "Há poucos detalhes disponíveis no texto de origem.",
        "fallback_bottom": "Novas atualizações devem surgir em breve.",
    },
}


class SmartBrevitySummarizer:
    """Deterministic summarizer using Smart Brevity formatting rules."""

    def summarize(self, article: RawArticle, job: SummaryJob) -> SummaryOutput:
        language = _resolve_language(getattr(job, "language", "en"))
        profile = _LANGUAGE_PROFILES[language]
        try:
            headline = _truncate(_normalize_text(article.title) or "Untitled", 140)
            clean_content = _clean_content(getattr(article, "content", ""))
            sentences = _extract_sentences(clean_content)
            filtered = [sentence for sentence in sentences if len(sentence) >= 20]

            why_sentence = _pick_why_sentence(filtered, keywords=profile["keywords"], fallback=profile["fallback_why"])
            why_sentence = _truncate(why_sentence, 160)

            remaining = [sentence for sentence in filtered if sentence != why_sentence]
            bullet_sentences = _pick_bullets(remaining)
            if not bullet_sentences:
                bullet_sentences = [profile["fallback_bullet"]]
            bullet_lines = [f"• {_truncate(sentence, 200)}" for sentence in bullet_sentences]

            bottom_line_sentence = _pick_bottom_line(remaining, bullet_sentences, why_sentence)
            bottom_line_sentence = _truncate(bottom_line_sentence, 160)

            summary = "\n".join(
                [
                    f"📰 {headline}",
                    "",
                    f"{profile['why_label']}: {why_sentence}",
                    "",
                    *bullet_lines,
                    "",
                    f"{profile['bottom_label']}: {bottom_line_sentence}",
                ]
            )
            return SummaryOutput(summary=summary, model_used="smart_brevity_v1")
        except Exception:
            # Never raise for malformed content: emit deterministic fallback structure.
            fallback_headline = _truncate(_normalize_text(getattr(article, "title", "")) or "Untitled", 140)
            fallback = "\n".join(
                [
                    f"📰 {fallback_headline}",
                    "",
                    f"{profile['why_label']}: {profile['fallback_why']}",
                    "",
                    f"• {profile['fallback_bullet']}",
                    "",
                    f"{profile['bottom_label']}: {profile['fallback_bottom']}",
                ]
            )
            return SummaryOutput(summary=fallback, model_used="smart_brevity_v1")


def _clean_content(content: object) -> str:
    raw = "" if content is None else str(content)
    without_html = re.sub(r"<[^>]*>", " ", raw)
    return _normalize_text(without_html)


def _normalize_text(text: object) -> str:
    raw = "" if text is None else str(text)
    return re.sub(r"\s+", " ", raw).strip()


def _extract_sentences(content: str) -> list[str]:
    if not content:
        return []
    parts = re.split(r"(?<=[.!?])\s+", content)
    normalized = [_normalize_text(part) for part in parts]
    return [part for part in normalized if part]


def _contains_priority_signal(sentence: str, *, keywords: tuple[str, ...]) -> bool:
    lowered = sentence.lower()
    has_number = any(char.isdigit() for char in sentence)
    has_keyword = any(keyword in lowered for keyword in keywords)
    return has_number or has_keyword


def _pick_why_sentence(sentences: list[str], *, keywords: tuple[str, ...], fallback: str) -> str:
    for sentence in sentences:
        if _contains_priority_signal(sentence, keywords=keywords):
            return sentence
    if len(sentences) >= 2:
        return sentences[1]
    if sentences:
        return sentences[0]
    return fallback


def _pick_bullets(remaining_sentences: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for sentence in remaining_sentences:
        if sentence not in seen:
            seen.add(sentence)
            unique.append(sentence)

    with_numbers = [sentence for sentence in unique if any(char.isdigit() for char in sentence)]
    without_numbers = [sentence for sentence in unique if sentence not in with_numbers]
    return (with_numbers + without_numbers)[:3]


def _pick_bottom_line(remaining: list[str], bullets: list[str], why_sentence: str) -> str:
    remaining_not_used = [sentence for sentence in remaining if sentence not in bullets]
    if remaining_not_used:
        return remaining_not_used[-1]
    if bullets:
        return bullets[-1]
    return why_sentence


def _truncate(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    if max_len <= 3:
        return value[:max_len]
    return f"{value[: max_len - 3].rstrip()}..."


def _resolve_language(value: object) -> str:
    normalized = str(value or "en").strip().lower()
    if normalized in _LANGUAGE_PROFILES:
        return normalized
    return "en"
