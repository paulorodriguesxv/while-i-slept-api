# Ingestion Split: Minimal-Change Flow

## Old flow

1. `ingestion` Lambda fetched RSS entries.
2. For each entry, it enriched article content inline, computed `content_hash`, built `RawArticle`, and called `IngestArticleUseCase`.
3. `IngestArticleUseCase` persisted raw/feed/pending summary state and enqueued `SummaryJob` to the summary queue.

## New flow

1. `ingestion` Lambda fetches RSS entries and enqueues lightweight `ArticleJob` messages to `article-jobs` SQS.
2. New `article-processor` Lambda consumes `article-jobs` records.
3. For each record, it performs the exact per-article enrichment/hash/`RawArticle` creation logic that ingestion previously did.
4. It then calls the existing `IngestArticleUseCase`, which keeps persisting state and enqueueing `SummaryJob` to the existing summary queue.

## Why this is minimal change

- Existing `IngestArticleUseCase` is reused as-is.
- Existing summary worker and `SummaryJob` schema are untouched.
- Changes are additive: one DTO, one queue adapter, one runtime builder, and one new Lambda processing path.
- Handler behavior stays narrow and testable with record-level partial batch failure semantics.

## Unchanged contracts

- `SummaryJob` payload contract
- Summary worker queue and processing behavior
- Repository write logic for raw/feed/summary items
