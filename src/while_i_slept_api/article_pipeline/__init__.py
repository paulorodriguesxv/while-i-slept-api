"""Pipeline for fetching, extracting, and processing article content.

This package contains write-side ingestion and summary processing primitives
plus the read-side feed query submodule used by API endpoints.
"""

from while_i_slept_api.article_pipeline.constants import DEFAULT_SUMMARY_VERSION
from while_i_slept_api.article_pipeline.dto import SummaryJob

__all__ = ["DEFAULT_SUMMARY_VERSION", "SummaryJob"]
