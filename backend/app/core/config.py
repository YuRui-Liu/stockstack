from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://localhost:5432/stockstack"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str
    admin_username: str = "admin"
    admin_password_hash: str

    cache_ttl_seconds: int = Field(default=300, ge=1)
    cache_ttl_jitter_seconds: int = Field(default=30, ge=0)
    negative_cache_ttl_seconds: int = Field(default=30, ge=1)
    rate_limit_requests: int = Field(default=100, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    db_fallback_concurrency_limit: int = Field(default=10, ge=1)
