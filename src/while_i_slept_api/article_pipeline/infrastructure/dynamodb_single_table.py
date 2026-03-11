"""DynamoDB single-table repository for article/summary pipeline."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import os
from typing import Any, cast

from while_i_slept_api.article_pipeline.keys import article_pk, feed_pk, feed_pk_for_date, feed_sk, raw_sk, summary_sk
from while_i_slept_api.article_pipeline.models import RawArticle, SummaryState
from while_i_slept_api.article_pipeline.ports import ArticleSummaryRepository
from while_i_slept_api.services.utils import iso_now


def _normalize_number(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, list):
        return [_normalize_number(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalize_number(item) for key, item in value.items()}
    return value


def _to_utc_iso(value: datetime) -> str:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0).isoformat()


def _to_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(microsecond=0)


def _date_range(start_date: date, end_date: date) -> list[str]:
    if end_date < start_date:
        return []
    buckets: list[str] = []
    current = start_date
    while current <= end_date:
        buckets.append(current.isoformat())
        current += timedelta(days=1)
    return buckets


class DynamoArticleSummaryRepository(ArticleSummaryRepository):
    """Single-table writes for RAW, FEED index, and SUMMARY items."""

    def __init__(self, table: Any) -> None:
        self._table = table

    @classmethod
    def from_resource(cls, resource: Any, table_name: str | None = None) -> "DynamoArticleSummaryRepository":
        resolved_table_name = table_name or os.getenv("DYNAMO_TABLE_NAME", "articles")
        return cls(resource.Table(resolved_table_name))

    def put_raw_article_if_absent(self, article: RawArticle) -> bool:
        item: dict[str, Any] = {
            "pk": article_pk(article.content_hash),
            "sk": raw_sk(),
            "content_hash": article.content_hash,
            "article_id": article.article_id,
            "language": article.language,
            "topic": article.topic,
            "source": article.source,
            "source_url": article.source_url,
            "title": article.title,
            "content": article.content,
            "published_at": article.published_at,
            "ingested_at": article.ingested_at,
            "reading_time_minutes": article.reading_time_minutes,
        }
        if article.image_url:
            item["image_url"] = article.image_url
        if article.description:
            item["description"] = article.description
        if article.author:
            item["author"] = article.author
        if article.article_published_time:
            item["article_published_time"] = article.article_published_time
        conditional_check_failed = self._table.meta.client.exceptions.ConditionalCheckFailedException
        try:
            self._table.put_item(Item=item, ConditionExpression="attribute_not_exists(pk)")
            return True
        except conditional_check_failed:
            return False

    def put_feed_index_item(self, article: RawArticle, *, topic: str) -> None:
        _ = topic  # kept for compatibility with existing use-case call shape
        item = {
            "pk": feed_pk(article.language, article.published_at),
            "sk": feed_sk(article.published_at, article.content_hash),
            "content_hash": article.content_hash,
            "published_at": article.published_at,
            "title": article.title,
            "source": article.source,
            "source_url": article.source_url,
            "ingested_at": article.ingested_at,
            "summary_version_default": 1,
        }
        self._table.put_item(Item=item)

    def put_summary_pending(self, *, content_hash: str, summary_version: int, created_at: str) -> None:
        item = {
            "pk": article_pk(content_hash),
            "sk": summary_sk(summary_version),
            "summary_version": summary_version,
            "status": "PENDING",
            "retry_count": 0,
            "created_at": created_at,
        }
        conditional_check_failed = self._table.meta.client.exceptions.ConditionalCheckFailedException
        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(pk)",
            )
        except conditional_check_failed:
            return

    def get_raw_article(self, content_hash: str) -> RawArticle | None:
        response = self._table.get_item(Key={"pk": article_pk(content_hash), "sk": raw_sk()})
        item = response.get("Item")
        if not item:
            return None
        normalized = cast(dict[str, Any], _normalize_number(item))
        return RawArticle(
            content_hash=normalized["content_hash"],
            article_id=normalized.get("article_id"),
            language=normalized["language"],
            topic=normalized["topic"],
            source=normalized["source"],
            source_url=normalized["source_url"],
            title=normalized["title"],
            content=normalized["content"],
            published_at=normalized["published_at"],
            ingested_at=normalized.get("ingested_at", ""),
            image_url=normalized.get("image_url"),
            description=normalized.get("description"),
            author=normalized.get("author"),
            article_published_time=normalized.get("article_published_time"),
            reading_time_minutes=int(normalized.get("reading_time_minutes", 1)),
        )

    def get_summary_state(self, *, content_hash: str, summary_version: int) -> SummaryState | None:
        response = self._table.get_item(Key={"pk": article_pk(content_hash), "sk": summary_sk(summary_version)})
        item = response.get("Item")
        if not item:
            return None
        normalized = cast(dict[str, Any], _normalize_number(item))
        return SummaryState(
            content_hash=content_hash,
            summary_version=summary_version,
            status=normalized.get("status", "PENDING"),
            retry_count=int(normalized.get("retry_count", 0)),
            summary=normalized.get("summary"),
        )

    def query_feed_window(
        self,
        language: str,
        start_time: datetime,
        end_time: datetime,
        limit: int,
    ) -> list[dict[str, Any]]:
        start_utc = _to_utc_datetime(start_time)
        end_utc = _to_utc_datetime(end_time)
        if end_utc < start_utc:
            return []

        start = f"T#{_to_utc_iso(start_utc)}"
        end = f"T#{_to_utc_iso(end_utc)}~"
        query_limit = max(1, int(limit))
        date_buckets = _date_range(start_utc.date(), end_utc.date())
        partition_keys = [feed_pk_for_date(language, bucket) for bucket in date_buckets]
        partition_keys.append(f"FEED#{language}#all")  # backward-compatible legacy partition

        merged_rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for pk in partition_keys:
            response = self._table.query(
                KeyConditionExpression="pk = :pk AND sk BETWEEN :start AND :end",
                ExpressionAttributeValues={
                    ":pk": pk,
                    ":start": start,
                    ":end": end,
                },
                Limit=query_limit,
            )
            rows = cast(list[dict[str, Any]], response.get("Items", []))
            for row in rows:
                normalized = cast(dict[str, Any], _normalize_number(row))
                content_hash = str(normalized.get("content_hash", ""))
                if not content_hash or content_hash in seen:
                    continue
                seen.add(content_hash)
                merged_rows.append(
                    {
                        "content_hash": content_hash,
                        "title": normalized.get("title", ""),
                        "source": normalized.get("source", ""),
                        "source_url": normalized.get("source_url", ""),
                        "published_at": normalized.get("published_at"),
                        "summary_version_default": int(normalized.get("summary_version_default", 1)),
                    }
                )

        merged_rows.sort(key=lambda row: str(row.get("published_at", "")))
        return merged_rows[:query_limit]

    def get_summary(self, content_hash: str, summary_version: int) -> str | None:
        response = self._table.get_item(
            Key={
                "pk": article_pk(content_hash),
                "sk": summary_sk(summary_version),
            }
        )
        item = cast(dict[str, Any] | None, response.get("Item"))
        if not item:
            return None
        normalized = cast(dict[str, Any], _normalize_number(item))
        if normalized.get("status") != "DONE":
            return None
        summary = normalized.get("summary")
        if summary is None:
            return None
        return str(summary)

    def mark_summary_done(
        self,
        *,
        content_hash: str,
        summary_version: int,
        summary: str,
        model_used: str,
        tokens_used: int | None,
        cost_estimate_usd: float | None,
        summarized_at: str,
    ) -> None:
        expression_names: dict[str, str] = {"#status": "status"}
        expression_values: dict[str, Any] = {
            ":summary_version": summary_version,
            ":status": "DONE",
            ":summary": summary,
            ":model_used": model_used,
            ":summarized_at": summarized_at,
            ":created_at": iso_now(),
            ":zero": 0,
        }
        set_clauses = [
            "summary_version = if_not_exists(summary_version, :summary_version)",
            "#status = :status",
            "summary = :summary",
            "model_used = :model_used",
            "summarized_at = :summarized_at",
            "created_at = if_not_exists(created_at, :created_at)",
            "retry_count = if_not_exists(retry_count, :zero)",
        ]
        if tokens_used is not None:
            expression_values[":tokens_used"] = tokens_used
            set_clauses.append("tokens_used = :tokens_used")
        if cost_estimate_usd is not None:
            expression_values[":cost_estimate_usd"] = Decimal(str(cost_estimate_usd))
            set_clauses.append("cost_estimate_usd = :cost_estimate_usd")

        self._table.update_item(
            Key={"pk": article_pk(content_hash), "sk": summary_sk(summary_version)},
            UpdateExpression=f"SET {', '.join(set_clauses)}",
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
        )

    def mark_summary_failed(
        self,
        *,
        content_hash: str,
        summary_version: int,
        error_code: str,
        error_message: str,
        retry_count: int,
        updated_at: str,
    ) -> None:
        self._table.update_item(
            Key={"pk": article_pk(content_hash), "sk": summary_sk(summary_version)},
            UpdateExpression=(
                "SET summary_version = if_not_exists(summary_version, :summary_version), "
                "#status = :status, "
                "error_code = :error_code, "
                "error_message = :error_message, "
                "retry_count = :retry_count, "
                "created_at = if_not_exists(created_at, :created_at), "
                "summarized_at = :updated_at"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":summary_version": summary_version,
                ":status": "FAILED",
                ":error_code": error_code,
                ":error_message": error_message,
                ":retry_count": retry_count,
                ":created_at": iso_now(),
                ":updated_at": updated_at,
            },
        )

    def _get_created_at(self, content_hash: str, summary_version: int) -> str:
        response = self._table.get_item(Key={"pk": article_pk(content_hash), "sk": summary_sk(summary_version)})
        item = cast(dict[str, Any] | None, response.get("Item"))
        if not item:
            return iso_now()
        return cast(str, _normalize_number(item).get("created_at") or iso_now())
