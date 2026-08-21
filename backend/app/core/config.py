from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://localhost:5432/stockstack"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str
    admin_username: str = "admin"
    admin_password_hash: str
    access_token_expire_minutes: int = Field(default=15, ge=1)
    upload_root: str = "/tmp/stockstack-uploads"

    cache_ttl_seconds: int = Field(default=300, ge=1)
    cache_ttl_jitter_seconds: int = Field(default=30, ge=0)
    negative_cache_ttl_seconds: int = Field(default=30, ge=1)
    rate_limit_requests: int = Field(default=100, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    db_fallback_concurrency_limit: int = Field(default=10, ge=1)
    db_fallback_wait_ms: int = Field(default=100, ge=1)
    db_query_timeout_ms: int = Field(default=500, ge=1)
    cache_lock_ttl_ms: int = Field(default=3000, ge=100)
    cache_wait_budget_ms: int = Field(default=250, ge=0)
    redis_timeout_seconds: float = Field(default=0.2, gt=0)
    trust_proxy_headers: bool = False

    @model_validator(mode="after")
    def validate_timeouts(self) -> "Settings":
        if self.db_query_timeout_ms >= self.cache_lock_ttl_ms:
            raise ValueError("db_query_timeout_ms must be less than cache_lock_ttl_ms")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
