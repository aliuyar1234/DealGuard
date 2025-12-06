"""Unit tests for cryptographic utilities.

Tests encryption, decryption, and key validation.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# Set APP_SECRET_KEY before importing crypto module
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-encryption-32chars"


@pytest.fixture(autouse=True)
def mock_settings():
    """Mock get_settings for all crypto tests."""
    with patch("dealguard.shared.crypto.get_settings") as mock:
        mock.return_value = MagicMock(
            app_secret_key="test-secret-key-for-encryption-32chars"
        )
        from dealguard.shared.crypto import _get_fernet
        _get_fernet.cache_clear()
        yield mock
        _get_fernet.cache_clear()


class TestCryptoFunctions:
    """Test encryption and decryption functions."""

    def test_encrypt_secret_returns_encrypted_string(self):
        """Test that encrypt_secret returns a non-empty encrypted string."""
        from dealguard.shared.crypto import encrypt_secret, _get_fernet

        _get_fernet.cache_clear()

        plaintext = "my-secret-api-key-12345"
        encrypted = encrypt_secret(plaintext)

        assert encrypted is not None
        assert encrypted != plaintext
        assert len(encrypted) > 0
        # Fernet tokens start with 'gAAAAA'
        assert encrypted.startswith("gAAAAA")

    def test_decrypt_secret_returns_original(self):
        """Test that decrypt_secret returns the original plaintext."""
        from dealguard.shared.crypto import encrypt_secret, decrypt_secret, _get_fernet

        _get_fernet.cache_clear()

        plaintext = "my-secret-api-key-12345"
        encrypted = encrypt_secret(plaintext)
        decrypted = decrypt_secret(encrypted)

        assert decrypted == plaintext

    def test_encrypt_empty_string_returns_empty(self):
        """Test that encrypting empty string returns empty string."""
        from dealguard.shared.crypto import encrypt_secret

        assert encrypt_secret("") == ""
        assert encrypt_secret(None) == ""

    def test_decrypt_empty_string_returns_empty(self):
        """Test that decrypting empty string returns empty string."""
        from dealguard.shared.crypto import decrypt_secret

        assert decrypt_secret("") == ""
        assert decrypt_secret(None) == ""

    def test_is_encrypted_detects_encrypted_values(self):
        """Test that is_encrypted correctly identifies encrypted values."""
        from dealguard.shared.crypto import encrypt_secret, is_encrypted, _get_fernet

        _get_fernet.cache_clear()

        encrypted = encrypt_secret("test-value")

        assert is_encrypted(encrypted) is True
        assert is_encrypted("plain-text") is False
        assert is_encrypted("") is False
        assert is_encrypted(None) is False

    def test_encrypt_decrypt_roundtrip_various_inputs(self):
        """Test encryption/decryption with various input types."""
        from dealguard.shared.crypto import encrypt_secret, decrypt_secret, _get_fernet

        _get_fernet.cache_clear()

        test_cases = [
            "simple",
            "with spaces and special chars !@#$%",
            "unicode: äöü ß € 日本語",
            "a" * 1000,  # Long string
            "sk-ant-api03-very-long-api-key-1234567890abcdef",
        ]

        for plaintext in test_cases:
            encrypted = encrypt_secret(plaintext)
            decrypted = decrypt_secret(encrypted)
            assert decrypted == plaintext, f"Failed for: {plaintext[:50]}"

    def test_different_plaintexts_produce_different_ciphertexts(self):
        """Test that different inputs produce different outputs."""
        from dealguard.shared.crypto import encrypt_secret, _get_fernet

        _get_fernet.cache_clear()

        encrypted1 = encrypt_secret("secret1")
        encrypted2 = encrypt_secret("secret2")

        assert encrypted1 != encrypted2

    def test_same_plaintext_produces_different_ciphertexts(self):
        """Test that Fernet uses random IV (same input, different output)."""
        from dealguard.shared.crypto import encrypt_secret, _get_fernet

        _get_fernet.cache_clear()

        plaintext = "same-secret"
        encrypted1 = encrypt_secret(plaintext)
        encrypted2 = encrypt_secret(plaintext)

        # Fernet uses random IV, so same plaintext should produce different ciphertext
        assert encrypted1 != encrypted2


class TestKeyValidation:
    """Test APP_SECRET_KEY validation."""

    def test_insecure_default_key_raises_error(self):
        """Test that insecure default keys raise ValueError."""
        from dealguard.shared.crypto import _get_fernet, _INSECURE_DEFAULT_KEYS

        _get_fernet.cache_clear()

        # Test each insecure key
        for insecure_key in _INSECURE_DEFAULT_KEYS:
            with patch("dealguard.shared.crypto.get_settings") as mock_settings:
                mock_settings.return_value = MagicMock(app_secret_key=insecure_key)
                _get_fernet.cache_clear()

                with pytest.raises(ValueError) as exc_info:
                    _get_fernet()

                assert "APP_SECRET_KEY" in str(exc_info.value)

    def test_valid_key_works(self):
        """Test that a valid key works correctly."""
        from dealguard.shared.crypto import _get_fernet

        with patch("dealguard.shared.crypto.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(
                app_secret_key="valid-secret-key-for-testing-12345"
            )
            _get_fernet.cache_clear()

            fernet = _get_fernet()
            assert fernet is not None


class TestDecryptionErrors:
    """Test error handling during decryption."""

    def test_decrypt_invalid_token_raises_error(self):
        """Test that decrypting invalid token raises ValueError."""
        from dealguard.shared.crypto import decrypt_secret, _get_fernet

        _get_fernet.cache_clear()

        with pytest.raises(ValueError) as exc_info:
            decrypt_secret("gAAAAABinvalid-token-here")

        # Error message could be in German or English depending on environment
        error_msg = str(exc_info.value).lower()
        assert "entschlüsselung" in error_msg or "decrypt" in error_msg or "failed" in error_msg

    def test_decrypt_wrong_key_raises_error(self):
        """Test that decrypting with wrong key raises ValueError."""
        from dealguard.shared.crypto import encrypt_secret, decrypt_secret, _get_fernet

        # Encrypt with one key
        with patch("dealguard.shared.crypto.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(app_secret_key="key-one-for-testing-12345")
            _get_fernet.cache_clear()
            encrypted = encrypt_secret("secret")

        # Try to decrypt with different key
        with patch("dealguard.shared.crypto.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(app_secret_key="key-two-different-12345")
            _get_fernet.cache_clear()

            with pytest.raises(ValueError):
                decrypt_secret(encrypted)
