"""Integration tests for Settings API endpoints.

Tests the ORM-based settings endpoints.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Set required env vars
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-encryption-32chars"


@pytest.fixture(autouse=True)
def mock_crypto_settings():
    """Mock get_settings for all settings API tests."""
    with patch("dealguard.shared.crypto.get_settings") as mock:
        mock.return_value = MagicMock(
            app_secret_key="test-secret-key-for-encryption-32chars"
        )
        from dealguard.shared.crypto import _get_fernet
        _get_fernet.cache_clear()
        yield mock
        _get_fernet.cache_clear()


class TestGetUserSettings:
    """Test get_user_settings helper function."""

    @pytest.mark.asyncio
    async def test_get_settings_returns_empty_for_new_user(self):
        """Test that new user returns empty settings."""
        from dealguard.api.routes.settings import get_user_settings

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        settings = await get_user_settings(mock_session, str(uuid4()))

        assert settings == {}

    @pytest.mark.asyncio
    async def test_get_settings_decrypts_api_keys(self):
        """Test that API keys are decrypted."""
        from dealguard.api.routes.settings import get_user_settings
        from dealguard.shared.crypto import encrypt_secret, _get_fernet

        _get_fernet.cache_clear()

        # Encrypt a test key
        encrypted_key = encrypt_secret("sk-ant-test-key-12345")

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {
            "anthropic_api_key": encrypted_key,
            "ai_provider": "anthropic",
        }
        mock_session.execute.return_value = mock_result

        settings = await get_user_settings(mock_session, str(uuid4()))

        assert settings["anthropic_api_key"] == "sk-ant-test-key-12345"
        assert settings["ai_provider"] == "anthropic"

    @pytest.mark.asyncio
    async def test_get_settings_handles_unencrypted_legacy_keys(self):
        """Test backwards compatibility with unencrypted keys."""
        from dealguard.api.routes.settings import get_user_settings

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {
            "anthropic_api_key": "sk-ant-legacy-key",  # Not encrypted
            "ai_provider": "anthropic",
        }
        mock_session.execute.return_value = mock_result

        settings = await get_user_settings(mock_session, str(uuid4()))

        # Legacy unencrypted key should be returned as-is
        assert settings["anthropic_api_key"] == "sk-ant-legacy-key"

    @pytest.mark.asyncio
    async def test_get_settings_skip_decryption(self):
        """Test that decrypt_keys=False skips decryption."""
        from dealguard.api.routes.settings import get_user_settings
        from dealguard.shared.crypto import encrypt_secret, _get_fernet

        _get_fernet.cache_clear()

        encrypted_key = encrypt_secret("sk-ant-test-key")

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = {
            "anthropic_api_key": encrypted_key,
        }
        mock_session.execute.return_value = mock_result

        settings = await get_user_settings(mock_session, str(uuid4()), decrypt_keys=False)

        # Key should remain encrypted
        assert settings["anthropic_api_key"] == encrypted_key


class TestUpdateUserSettings:
    """Test update_user_settings helper function."""

    @pytest.mark.asyncio
    async def test_update_settings_commits(self):
        """Test that update commits the transaction."""
        from dealguard.api.routes.settings import update_user_settings

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        await update_user_settings(mock_session, str(uuid4()), {"ai_provider": "deepseek"})

        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()


class TestAPIKeysResponse:
    """Test APIKeysResponse model."""

    def test_api_keys_response_model(self):
        """Test APIKeysResponse creation."""
        from dealguard.api.routes.settings import APIKeysResponse

        response = APIKeysResponse(
            anthropic_configured=True,
            deepseek_configured=False,
            ai_provider="anthropic",
        )

        assert response.anthropic_configured is True
        assert response.deepseek_configured is False
        assert response.ai_provider == "anthropic"


class TestUpdateAPIKeysRequest:
    """Test UpdateAPIKeysRequest model."""

    def test_update_request_all_fields(self):
        """Test UpdateAPIKeysRequest with all fields."""
        from dealguard.api.routes.settings import UpdateAPIKeysRequest

        request = UpdateAPIKeysRequest(
            anthropic_api_key="sk-ant-new-key-123",
            deepseek_api_key="sk-deepseek-new",
            ai_provider="deepseek",
        )

        assert request.anthropic_api_key == "sk-ant-new-key-123"
        assert request.deepseek_api_key == "sk-deepseek-new"
        assert request.ai_provider == "deepseek"

    def test_update_request_partial(self):
        """Test UpdateAPIKeysRequest with partial fields."""
        from dealguard.api.routes.settings import UpdateAPIKeysRequest

        request = UpdateAPIKeysRequest(
            ai_provider="anthropic",
        )

        assert request.anthropic_api_key is None
        assert request.deepseek_api_key is None
        assert request.ai_provider == "anthropic"

    def test_update_request_key_min_length(self):
        """Test UpdateAPIKeysRequest key minimum length validation."""
        from pydantic import ValidationError
        from dealguard.api.routes.settings import UpdateAPIKeysRequest

        with pytest.raises(ValidationError):
            UpdateAPIKeysRequest(
                anthropic_api_key="short",  # Less than 10 chars
            )


class TestSettingsResponse:
    """Test SettingsResponse model."""

    def test_settings_response_model(self):
        """Test SettingsResponse creation."""
        from dealguard.api.routes.settings import SettingsResponse, APIKeysResponse

        response = SettingsResponse(
            api_keys=APIKeysResponse(
                anthropic_configured=True,
                deepseek_configured=True,
                ai_provider="anthropic",
            ),
            single_tenant_mode=True,
        )

        assert response.api_keys.anthropic_configured is True
        assert response.single_tenant_mode is True
        assert response.app_version == "2.0.0"


class TestEncryptionInUpdateFlow:
    """Test encryption is applied when updating API keys."""

    @pytest.mark.asyncio
    async def test_api_keys_encrypted_before_storage(self):
        """Test that API keys are encrypted before being stored."""
        from dealguard.shared.crypto import is_encrypted, _get_fernet

        _get_fernet.cache_clear()

        # We'll verify by checking what gets passed to update_user_settings
        stored_updates = {}

        async def capture_updates(db, user_id, updates):
            stored_updates.update(updates)

        with patch("dealguard.api.routes.settings.update_user_settings", side_effect=capture_updates):
            with patch("dealguard.api.routes.settings.get_user_settings") as mock_get:
                mock_get.return_value = {"ai_provider": "anthropic"}

                with patch("dealguard.api.routes.settings.get_settings") as mock_settings:
                    mock_settings.return_value = MagicMock(
                        anthropic_api_key="",
                        deepseek_api_key="",
                        ai_provider="anthropic",
                        single_tenant_mode=True,
                    )

                    from dealguard.api.routes.settings import update_api_keys, UpdateAPIKeysRequest
                    from dealguard.infrastructure.auth.provider import AuthUser

                    mock_db = AsyncMock()
                    mock_user = MagicMock(spec=AuthUser)
                    mock_user.id = str(uuid4())
                    mock_user.organization_id = str(uuid4())

                    request = UpdateAPIKeysRequest(
                        anthropic_api_key="sk-ant-test-key-12345",
                    )

                    await update_api_keys(request, mock_user, mock_db)

        # The stored key should be encrypted
        assert "anthropic_api_key" in stored_updates
        assert is_encrypted(stored_updates["anthropic_api_key"])
