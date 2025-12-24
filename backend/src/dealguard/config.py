"""Application configuration using Pydantic Settings."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, cast
from uuid import UUID

from pydantic import Field, PostgresDsn, RedisDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default IDs for single-tenant mode (self-hosted)
DEFAULT_ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

DEFAULT_DATABASE_URL = "postgresql+asyncpg://dealguard:dealguard@localhost:5432/dealguard"
DEFAULT_DATABASE_SYNC_URL = "postgresql://dealguard:dealguard@localhost:5432/dealguard"
DEFAULT_REDIS_URL = "redis://localhost:6379"
DEFAULT_S3_ACCESS_KEY = "minio"
DEFAULT_S3_SECRET_KEY = "minio123"
INSECURE_APP_SECRETS = {
    "GENERATE_A_SECURE_KEY_HERE",
    "change-me-to-a-32-char-secret-key",
    "change-this-to-a-random-secret-key",
}
SECRET_FILE_ENV_VARS = (
    "APP_SECRET_KEY",
    "DATABASE_URL",
    "DATABASE_SYNC_URL",
    "REDIS_URL",
    "SUPABASE_JWT_SECRET",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_ANON_KEY",
    "ANTHROPIC_API_KEY",
    "DEEPSEEK_API_KEY",
    "S3_ACCESS_KEY",
    "S3_SECRET_KEY",
)


def _load_secret_file_env_vars() -> None:
    """Allow secrets to be sourced from *_FILE env vars (Docker secrets)."""
    for env_var in SECRET_FILE_ENV_VARS:
        file_var = f"{env_var}_FILE"
        file_path = os.getenv(file_var)
        if not file_path:
            continue
        try:
            value = Path(file_path).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Failed to read {file_var} at {file_path}") from exc
        if not value:
            raise ValueError(f"{file_var} is empty")
        os.environ[env_var] = value


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- Application -----
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_secret_key: str = Field(
        ...,  # Required - no default for security
        description='Secret key for encryption. Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"',
    )

    # ----- Single-Tenant Mode -----
    # For self-hosted open-source deployment, multi-tenant is disabled
    single_tenant_mode: bool = True

    # ----- Database -----
    database_url: PostgresDsn = Field(default=cast(PostgresDsn, DEFAULT_DATABASE_URL))
    database_sync_url: PostgresDsn = Field(default=cast(PostgresDsn, DEFAULT_DATABASE_SYNC_URL))
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # ----- Redis -----
    redis_url: RedisDsn = Field(default=cast(RedisDsn, DEFAULT_REDIS_URL))

    # ----- Auth -----
    auth_provider: Literal["supabase", "dev"] = "supabase"  # Use "dev" for local testing

    # ----- Supabase Auth -----
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    # ----- Anthropic AI -----
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096

    # ----- DeepSeek AI (cheaper alternative for testing) -----
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"  # cheapest: deepseek-chat, better: deepseek-reasoner
    deepseek_base_url: str = "https://api.deepseek.com"

    # ----- AI Provider Selection -----
    ai_provider: Literal["anthropic", "deepseek"] = "anthropic"

    # ----- S3 Storage -----
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = DEFAULT_S3_ACCESS_KEY
    s3_secret_key: str = DEFAULT_S3_SECRET_KEY
    s3_bucket: str = "dealguard-documents"
    s3_region: str = "eu-central-1"

    # ----- CORS -----
    # Can be set as JSON list or comma-separated string
    cors_origins_str: str = Field(default="http://localhost:3000", alias="cors_origins")

    @property
    def cors_origins(self) -> list[str]:
        """Parse cors_origins from comma-separated string or JSON list."""
        v = self.cors_origins_str
        if not v:
            return ["http://localhost:3000"]
        # Try JSON first
        if v.startswith("["):
            import json

            raw = json.loads(v)
            if not isinstance(raw, list) or not all(isinstance(origin, str) for origin in raw):
                raise ValueError("CORS_ORIGINS must be a JSON list of strings")
            return raw
        # Fall back to comma-separated
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Ensure secure settings in production environment."""
        if self.is_production:
            if self.app_debug:
                raise ValueError("APP_DEBUG must be false in production!")
            if len(self.app_secret_key) < 32 or self.app_secret_key in INSECURE_APP_SECRETS:
                raise ValueError(
                    "APP_SECRET_KEY must be at least 32 characters and not a placeholder!"
                )
            # Dev auth is not allowed in production
            if self.auth_provider == "dev":
                raise ValueError(
                    "AUTH_PROVIDER=dev is not allowed in production! "
                    "Use AUTH_PROVIDER=supabase with proper Supabase configuration."
                )
            # Ensure real auth is configured
            if self.auth_provider == "supabase" and not self.supabase_jwt_secret:
                raise ValueError("SUPABASE_JWT_SECRET must be set in production!")
            if str(self.database_url) == DEFAULT_DATABASE_URL:
                raise ValueError("DATABASE_URL must be set to a production database!")
            if str(self.database_sync_url) == DEFAULT_DATABASE_SYNC_URL:
                raise ValueError("DATABASE_SYNC_URL must be set to a production database!")
            if str(self.redis_url) == DEFAULT_REDIS_URL or "@" not in str(self.redis_url):
                raise ValueError(
                    "REDIS_URL must include credentials in production (redis://:password@host:port/db)."
                )
            if self.s3_access_key == DEFAULT_S3_ACCESS_KEY:
                raise ValueError("S3_ACCESS_KEY must be set to a non-default value!")
            if self.s3_secret_key == DEFAULT_S3_SECRET_KEY:
                raise ValueError("S3_SECRET_KEY must be set to a non-default value!")
            if any(origin in {"*", "http://localhost:3000"} for origin in self.cors_origins):
                raise ValueError("CORS_ORIGINS must be restricted in production!")
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    _load_secret_file_env_vars()
    return Settings()
