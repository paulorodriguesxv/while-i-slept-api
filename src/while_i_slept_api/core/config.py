"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the API service."""

    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore")

    env: str = "dev"
    storage_backend: str = "memory"
    timezone_default: str = "America/Sao_Paulo"

    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_ttl_seconds: int = 3600
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30

    free_briefing_max_items: int = 5
    premium_briefing_max_items: int = 15

    revenuecat_webhook_secret: str = "change-me"
    allow_insecure_oauth_tokens: bool = False

    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = None
    sqs_endpoint_url: str | None = None
    dynamodb_endpoint_url: str | None = None
    users_table: str = "users"
    devices_table: str = "devices"
    briefings_table: str = "briefings"
    summary_jobs_queue_url: str | None = None
    summarizer_impl: str = "smart"
    summary_worker_visibility_timeout_seconds: int = 60
    summary_worker_wait_time_seconds: int = 20
    summary_worker_retry_attempts: int = 3
    summary_worker_retry_backoff_seconds: float = 0.2

    auth_bearer_scheme: str = Field(default="Bearer", frozen=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    return Settings()
