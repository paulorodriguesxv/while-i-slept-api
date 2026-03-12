"""Clustering helpers for story deduplication."""

from __future__ import annotations

from while_i_slept_api.article_pipeline.feed_query.dto import SleepWindowItem
from while_i_slept_api.article_pipeline.story_dedup.similarity import jaccard_similarity, normalize_title

_SIMILARITY_THRESHOLD = 0.6


def cluster_articles(articles: list[SleepWindowItem]) -> list[list[SleepWindowItem]]:
    """Group articles by title similarity."""

    if not articles:
        return []

    clusters: list[list[SleepWindowItem]] = []
    cluster_tokens: list[list[list[str]]] = []
    for article in articles:
        title_tokens = normalize_title(article.title)
        assigned = False
        for idx, token_group in enumerate(cluster_tokens):
            if any(jaccard_similarity(title_tokens, existing_tokens) > _SIMILARITY_THRESHOLD for existing_tokens in token_group):
                clusters[idx].append(article)
                token_group.append(title_tokens)
                assigned = True
                break
        if not assigned:
            clusters.append([article])
            cluster_tokens.append([title_tokens])
    return clusters


def deduplicate_articles(articles: list[SleepWindowItem]) -> list[SleepWindowItem]:
    """Keep one representative per story cluster."""

    deduplicated: list[SleepWindowItem] = []
    for cluster in cluster_articles(articles):
        representative = max(cluster, key=lambda item: len(item.summary or ""))
        deduplicated.append(representative)
    return deduplicated
