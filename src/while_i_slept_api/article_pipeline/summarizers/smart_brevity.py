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
    stopwords: tuple[str, ...]
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
        "stopwords": (
            "a",
            "about",
            "across",
            "after",
            "an",
            "and",
            "are",
            "as",
            "at",
            "be",
            "been",
            "being",
            "before",
            "but",
            "by",
            "can",
            "could",
            "did",
            "do",
            "does",
            "for",
            "from",
            "had",
            "has",
            "have",
            "he",
            "her",
            "his",
            "i",
            "if",
            "in",
            "into",
            "is",
            "it",
            "its",
            "may",
            "might",
            "new",
            "no",
            "not",
            "of",
            "on",
            "or",
            "our",
            "said",
            "she",
            "should",
            "than",
            "that",
            "the",
            "their",
            "them",
            "then",
            "these",
            "they",
            "this",
            "those",
            "through",
            "to",
            "under",
            "us",
            "was",
            "we",
            "were",
            "will",
            "with",
            "would",
            "you",
            "your",
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
        "stopwords": (
            "a",
            "ao",
            "aos",
            "as",
            "ate",
            "até",
            "com",
            "como",
            "da",
            "das",
            "de",
            "do",
            "dos",
            "e",
            "ela",
            "elas",
            "ele",
            "eles",
            "em",
            "entre",
            "eram",
            "estar",
            "foi",
            "isso",
            "isto",
            "ja",
            "já",
            "mais",
            "mas",
            "menos",
            "na",
            "nao",
            "nas",
            "não",
            "no",
            "nos",
            "o",
            "os",
            "ou",
            "para",
            "por",
            "que",
            "se",
            "sem",
            "ser",
            "seu",
            "seus",
            "sob",
            "sobre",
            "sua",
            "suas",
            "são",
            "tambem",
            "também",
            "um",
            "uma",
            "uns",
            "umas",
            "à",
            "às",
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
            meaningful = _dedupe_sentences([sentence for sentence in sentences if len(sentence) >= 20])
            scored_sentences = _score_sentences(
                meaningful,
                keywords=profile["keywords"],
                stopwords=profile["stopwords"],
            )

            why_sentence = _pick_why_sentence(scored_sentences, fallback=profile["fallback_why"])
            why_sentence = _truncate(why_sentence, 160)

            bullet_sentences = _pick_bullets(scored_sentences, why_sentence)
            if not bullet_sentences:
                bullet_sentences = [profile["fallback_bullet"]]
            bullet_lines = [f"• {_truncate(sentence, 200)}" for sentence in bullet_sentences]

            bottom_line_sentence = _pick_bottom_line(meaningful, fallback=profile["fallback_bottom"])
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


def _tokenize_words(text: str) -> list[str]:
    return re.findall(r"[a-zA-ZÀ-ÖØ-öø-ÿ0-9']+", text.lower())


def _build_word_frequency(sentences: list[str], *, stopwords: tuple[str, ...]) -> dict[str, float]:
    counts: dict[str, int] = {}
    stopword_set = set(stopwords)
    for sentence in sentences:
        for word in _tokenize_words(sentence):
            if len(word) <= 1 or word in stopword_set:
                continue
            counts[word] = counts.get(word, 0) + 1
    if not counts:
        return {}
    max_frequency = max(counts.values())
    if max_frequency <= 0:
        return {}
    return {word: count / max_frequency for word, count in counts.items()}


def _score_sentences(
    sentences: list[str],
    *,
    keywords: tuple[str, ...],
    stopwords: tuple[str, ...],
) -> list[tuple[str, float]]:
    if not sentences:
        return []
    frequencies = _build_word_frequency(sentences, stopwords=stopwords)
    scored: list[tuple[str, float, int]] = []
    last_index = len(sentences) - 1

    for index, sentence in enumerate(sentences):
        lowered = sentence.lower()
        words = _tokenize_words(sentence)
        base_score = sum(frequencies.get(word, 0.0) for word in words)
        number_bonus = 2.0 if any(char.isdigit() for char in sentence) else 0.0
        keyword_bonus = 2.0 if any(keyword in lowered for keyword in keywords) else 0.0
        position_bonus = 1.0 if index in (0, last_index) else 0.0
        score = base_score + number_bonus + keyword_bonus + position_bonus
        scored.append((sentence, score, index))

    scored.sort(key=lambda item: (-item[1], item[2]))
    return [(sentence, score) for sentence, score, _ in scored]


def _pick_why_sentence(scored_sentences: list[tuple[str, float]], *, fallback: str) -> str:
    if not scored_sentences:
        return fallback
    return scored_sentences[0][0]


def _pick_bullets(scored_sentences: list[tuple[str, float]], why_sentence: str) -> list[str]:
    bullets: list[str] = []
    for sentence, _score in scored_sentences:
        if sentence == why_sentence:
            continue
        bullets.append(sentence)
        if len(bullets) == 3:
            break
    return bullets


def _pick_bottom_line(sentences: list[str], *, fallback: str) -> str:
    if not sentences:
        return fallback
    return sentences[-1]


def _dedupe_sentences(sentences: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for sentence in sentences:
        if sentence in seen:
            continue
        seen.add(sentence)
        unique.append(sentence)
    return unique


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
