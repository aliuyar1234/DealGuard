"""Unit tests for Contract model with auto-encryption.

Tests the hybrid property for automatic encryption/decryption.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

# Set required env vars
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-encryption-32chars"


@pytest.fixture(autouse=True)
def mock_crypto_settings():
    """Mock get_settings for all contract model tests."""
    with patch("dealguard.shared.crypto.get_settings") as mock:
        mock.return_value = MagicMock(
            app_secret_key="test-secret-key-for-encryption-32chars"
        )
        from dealguard.shared.crypto import _get_fernet
        _get_fernet.cache_clear()
        yield mock
        _get_fernet.cache_clear()


class TestContractTextEncryption:
    """Test automatic encryption of contract text."""

    def test_contract_text_setter_encrypts(self):
        """Test that setting contract_text encrypts the value."""
        from dealguard.shared.crypto import _get_fernet, is_encrypted
        from dealguard.infrastructure.database.models.contract import Contract

        _get_fernet.cache_clear()

        contract = Contract(
            id=uuid4(),
            organization_id=uuid4(),
            created_by=uuid4(),
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

        plaintext = "Dies ist ein Testvertrag mit sensiblen Daten."
        contract.contract_text = plaintext

        # The internal storage should be encrypted
        assert contract._raw_text_encrypted is not None
        assert contract._raw_text_encrypted != plaintext
        assert is_encrypted(contract._raw_text_encrypted)

    def test_contract_text_getter_decrypts(self):
        """Test that getting contract_text decrypts the value."""
        from dealguard.shared.crypto import _get_fernet, encrypt_secret
        from dealguard.infrastructure.database.models.contract import Contract

        _get_fernet.cache_clear()

        plaintext = "Dies ist ein weiterer Testvertrag."
        encrypted = encrypt_secret(plaintext)

        contract = Contract(
            id=uuid4(),
            organization_id=uuid4(),
            created_by=uuid4(),
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )
        contract._raw_text_encrypted = encrypted

        assert contract.contract_text == plaintext

    def test_contract_text_roundtrip(self):
        """Test setting and getting contract_text preserves data."""
        from dealguard.shared.crypto import _get_fernet
        from dealguard.infrastructure.database.models.contract import Contract

        _get_fernet.cache_clear()

        contract = Contract(
            id=uuid4(),
            organization_id=uuid4(),
            created_by=uuid4(),
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

        original_text = """
        MIETVERTRAG

        zwischen Vermieter GmbH und Mieter AG

        § 1 Mietgegenstand
        Der Vermieter vermietet dem Mieter die Geschäftsräume...

        § 2 Mietzins
        Der monatliche Mietzins beträgt EUR 5.000,00...
        """

        contract.contract_text = original_text
        retrieved_text = contract.contract_text

        assert retrieved_text == original_text

    def test_contract_text_none_handling(self):
        """Test that None values are handled correctly."""
        from dealguard.infrastructure.database.models.contract import Contract

        contract = Contract(
            id=uuid4(),
            organization_id=uuid4(),
            created_by=uuid4(),
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

        contract.contract_text = None

        assert contract._raw_text_encrypted is None
        assert contract.contract_text is None

    def test_contract_text_empty_string(self):
        """Test that empty string is handled correctly."""
        from dealguard.infrastructure.database.models.contract import Contract

        contract = Contract(
            id=uuid4(),
            organization_id=uuid4(),
            created_by=uuid4(),
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

        contract.contract_text = ""

        assert contract._raw_text_encrypted is None
        assert contract.contract_text is None


class TestRawTextBackwardsCompatibility:
    """Test backwards compatibility with raw_text property."""

    def test_raw_text_getter_returns_decrypted(self):
        """Test that raw_text property returns decrypted text."""
        from dealguard.shared.crypto import _get_fernet
        from dealguard.infrastructure.database.models.contract import Contract

        _get_fernet.cache_clear()

        contract = Contract(
            id=uuid4(),
            organization_id=uuid4(),
            created_by=uuid4(),
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

        plaintext = "Legacy contract text"
        contract.contract_text = plaintext

        # raw_text should return the same as contract_text
        assert contract.raw_text == plaintext
        assert contract.raw_text == contract.contract_text

    def test_raw_text_setter_encrypts(self):
        """Test that raw_text setter encrypts the value."""
        from dealguard.shared.crypto import _get_fernet, is_encrypted
        from dealguard.infrastructure.database.models.contract import Contract

        _get_fernet.cache_clear()

        contract = Contract(
            id=uuid4(),
            organization_id=uuid4(),
            created_by=uuid4(),
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

        plaintext = "Legacy setter test"
        contract.raw_text = plaintext

        assert is_encrypted(contract._raw_text_encrypted)
        assert contract.raw_text == plaintext


class TestLegacyUnencryptedData:
    """Test handling of legacy unencrypted data."""

    def test_unencrypted_legacy_data_returned_as_is(self):
        """Test that unencrypted legacy data is returned without error."""
        from dealguard.infrastructure.database.models.contract import Contract

        contract = Contract(
            id=uuid4(),
            organization_id=uuid4(),
            created_by=uuid4(),
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

        # Simulate legacy unencrypted data
        legacy_text = "This is unencrypted legacy contract text"
        contract._raw_text_encrypted = legacy_text

        # Should return the unencrypted text as-is (backwards compatibility)
        assert contract.contract_text == legacy_text


class TestContractTextWithLongContent:
    """Test encryption with realistic contract content."""

    def test_long_contract_text(self):
        """Test encryption of long contract text."""
        from dealguard.shared.crypto import _get_fernet
        from dealguard.infrastructure.database.models.contract import Contract

        _get_fernet.cache_clear()

        contract = Contract(
            id=uuid4(),
            organization_id=uuid4(),
            created_by=uuid4(),
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

        # Simulate a long contract (100KB of text)
        long_text = "Vertragsklausel. " * 6000

        contract.contract_text = long_text
        retrieved = contract.contract_text

        assert retrieved == long_text
        assert len(retrieved) == len(long_text)

    def test_unicode_contract_text(self):
        """Test encryption of Unicode contract text."""
        from dealguard.shared.crypto import _get_fernet
        from dealguard.infrastructure.database.models.contract import Contract

        _get_fernet.cache_clear()

        contract = Contract(
            id=uuid4(),
            organization_id=uuid4(),
            created_by=uuid4(),
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size_bytes=1024,
            mime_type="application/pdf",
        )

        unicode_text = """
        VERTRAG gemäß § 1 ABGB

        Die Vertragsparteien (Käufer & Verkäufer) vereinbaren:

        1. Preis: € 50.000,00
        2. Währung: EUR (€)
        3. Besondere Zeichen: äöü ÄÖÜ ß
        4. 日本語テスト (Japanese test)
        5. Emoji: 📄 ✅ ⚠️
        """

        contract.contract_text = unicode_text
        retrieved = contract.contract_text

        assert retrieved == unicode_text
