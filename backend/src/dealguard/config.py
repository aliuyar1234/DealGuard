"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal
from uuid import UUID

from pydantic import Field, PostgresDsn, RedisDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Default IDs for single-tenant mode (self-hosted)
DEFAULT_ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000000001")
DEFAULT_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


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
        description="Secret key for encryption. Generate with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"",
    )

    # ----- Single-Tenant Mode -----
    # For self-hosted open-source deployment, multi-tenant is disabled
    single_tenant_mode: bool = True

    # ----- Database -----
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://dealguard:dealguard@localhost:5432/dealguard"
    )
    database_sync_url: PostgresDsn = Field(
        default="postgresql://dealguard:dealguard@localhost:5432/dealguard"
    )
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # ----- Redis -----
    redis_url: RedisDsn = Field(default="redis://localhost:6379")

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
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
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
            return json.loads(v)
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
            # Dev auth is not allowed in production
            if self.auth_provider == "dev":
                raise ValueError(
                    "AUTH_PROVIDER=dev is not allowed in production! "
                    "Use AUTH_PROVIDER=supabase with proper Supabase configuration."
                )
            # Ensure real auth is configured
            if self.auth_provider == "supabase" and not self.supabase_jwt_secret:
                raise ValueError(
                    "SUPABASE_JWT_SECRET must be set in production!"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
