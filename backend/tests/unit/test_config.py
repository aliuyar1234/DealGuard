"""Unit tests for application configuration.

Tests Settings validation and required fields.
"""

import os

import pytest


class TestAppSecretKeyValidation:
    """Test APP_SECRET_KEY is required."""

    def test_missing_app_secret_key_raises(self):
        """Test that missing APP_SECRET_KEY raises validation error."""
        from pydantic import ValidationError

        # Clear any existing env var
        env_backup = os.environ.get("APP_SECRET_KEY")
        if "APP_SECRET_KEY" in os.environ:
            del os.environ["APP_SECRET_KEY"]

        try:
            # Clear settings cache
            from dealguard.config import get_settings

            get_settings.cache_clear()

            # Import Settings fresh
            from dealguard.config import Settings

            with pytest.raises(ValidationError) as exc_info:
                Settings(
                    _env_file=None,
                    database_url="postgresql+asyncpg://test:test@localhost/test",
                    database_sync_url="postgresql://test:test@localhost/test",
                    # Missing app_secret_key
                )

            assert "app_secret_key" in str(exc_info.value).lower()
        finally:
            # Restore env var
            if env_backup:
                os.environ["APP_SECRET_KEY"] = env_backup

    def test_valid_app_secret_key_works(self):
        """Test that valid APP_SECRET_KEY works."""
        from dealguard.config import Settings

        settings = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_sync_url="postgresql://test:test@localhost/test",
            app_secret_key="valid-secret-key-for-testing-123",
        )

        assert settings.app_secret_key == "valid-secret-key-for-testing-123"


class TestSettingsDefaults:
    """Test Settings default values."""

    def test_default_ai_provider(self):
        """Test AI provider is set correctly."""
        from dealguard.config import Settings

        settings = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_sync_url="postgresql://test:test@localhost/test",
            app_secret_key="test-key-123",
            ai_provider="anthropic",  # Explicitly set to test
        )

        assert settings.ai_provider == "anthropic"

    def test_default_app_env(self):
        """Test default app environment is development."""
        from dealguard.config import Settings

        settings = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_sync_url="postgresql://test:test@localhost/test",
            app_secret_key="test-key-123",
        )

        assert settings.app_env == "development"

    def test_default_single_tenant_mode(self):
        """Test default single tenant mode is True."""
        from dealguard.config import Settings

        settings = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_sync_url="postgresql://test:test@localhost/test",
            app_secret_key="test-key-123",
        )

        assert settings.single_tenant_mode is True


class TestSettingsProperties:
    """Test Settings computed properties."""

    def test_is_development(self):
        """Test is_development property."""
        from dealguard.config import Settings

        settings = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_sync_url="postgresql://test:test@localhost/test",
            app_secret_key="test-key-123",
            app_env="development",
        )

        assert settings.is_development is True
        assert settings.is_production is False

    def test_is_production(self):
        """Test is_production property."""
        from dealguard.config import Settings

        settings = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_sync_url="postgresql://test:test@localhost/test",
            app_secret_key="00000000000000000000000000000000",
            app_env="production",
            app_debug=False,
            auth_provider="supabase",
            supabase_jwt_secret="00000000000000000000000000000000",
            redis_url="redis://:test-redis@localhost:6379/1",
            s3_access_key="test-access-key",
            s3_secret_key="test-secret-key",
            cors_origins="https://example.com",
        )

        assert settings.is_production is True
        assert settings.is_development is False


class TestDefaultIDs:
    """Test default organization and user IDs."""

    def test_default_organization_id(self):
        """Test default organization ID is defined."""
        from dealguard.config import DEFAULT_ORGANIZATION_ID

        assert DEFAULT_ORGANIZATION_ID is not None
        assert str(DEFAULT_ORGANIZATION_ID) == "00000000-0000-0000-0000-000000000001"

    def test_default_user_id(self):
        """Test default user ID is defined."""
        from dealguard.config import DEFAULT_USER_ID

        assert DEFAULT_USER_ID is not None
        assert str(DEFAULT_USER_ID) == "00000000-0000-0000-0000-000000000001"


class TestAIProviderSettings:
    """Test AI provider configuration."""

    def test_anthropic_settings(self):
        """Test Anthropic-specific settings."""
        from dealguard.config import Settings

        settings = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_sync_url="postgresql://test:test@localhost/test",
            app_secret_key="test-key-123",
            anthropic_api_key="sk-ant-test-key",
            anthropic_model="claude-3-opus",
            anthropic_max_tokens=8192,
        )

        assert settings.anthropic_api_key == "sk-ant-test-key"
        assert settings.anthropic_model == "claude-3-opus"
        assert settings.anthropic_max_tokens == 8192

    def test_deepseek_settings(self):
        """Test DeepSeek-specific settings."""
        from dealguard.config import Settings

        settings = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://test:test@localhost/test",
            database_sync_url="postgresql://test:test@localhost/test",
            app_secret_key="test-key-123",
            ai_provider="deepseek",
            deepseek_api_key="sk-deepseek-test",
            deepseek_model="deepseek-reasoner",
            deepseek_base_url="https://custom.deepseek.com",
        )

        assert settings.ai_provider == "deepseek"
        assert settings.deepseek_api_key == "sk-deepseek-test"
        assert settings.deepseek_model == "deepseek-reasoner"
        assert settings.deepseek_base_url == "https://custom.deepseek.com"
