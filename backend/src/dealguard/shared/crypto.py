"""Cryptographic utilities for sensitive data encryption.

Uses Fernet symmetric encryption with the APP_SECRET_KEY.
Keys are derived using PBKDF2 to ensure proper key length.
"""

import base64
import hashlib
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from dealguard.config import get_settings

logger = logging.getLogger(__name__)


# Known default/placeholder values that should never be used in production
_INSECURE_DEFAULT_KEYS = {
    "change-this-to-a-random-secret-key",
    "change-me-in-production",
    "",
}


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    """Get Fernet instance with derived key from APP_SECRET_KEY.

    Fernet requires a 32-byte base64-encoded key.
    We derive it from APP_SECRET_KEY using SHA256.
    """
    settings = get_settings()
    secret = settings.app_secret_key

    if not secret or secret in _INSECURE_DEFAULT_KEYS:
        raise ValueError(
            "APP_SECRET_KEY muss für Verschlüsselung konfiguriert sein. "
            "Generiere einen sicheren Key mit: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )

    # Derive a 32-byte key using SHA256
    derived_key = hashlib.sha256(secret.encode()).digest()
    # Fernet needs base64-encoded key
    fernet_key = base64.urlsafe_b64encode(derived_key)

    return Fernet(fernet_key)


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a secret string (e.g., API key).

    Args:
        plaintext: The secret to encrypt

    Returns:
        Base64-encoded encrypted string (safe for JSON storage)
    """
    if not plaintext:
        return ""

    fernet = _get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return encrypted.decode()  # Fernet output is already base64


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt an encrypted secret.

    Args:
        ciphertext: The encrypted string from encrypt_secret

    Returns:
        The original plaintext

    Raises:
        ValueError: If decryption fails (wrong key, corrupted data)
    """
    if not ciphertext:
        return ""

    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(ciphertext.encode())
        return decrypted.decode()
    except InvalidToken as e:
        logger.error("Failed to decrypt secret - invalid token or wrong key")
        raise ValueError("Entschlüsselung fehlgeschlagen - möglicherweise falscher Key") from e


def is_encrypted(value: str) -> bool:
    """Check if a value looks like it's already encrypted.

    Fernet tokens start with 'gAAAAA' (base64 of version byte + timestamp).
    """
    if not value:
        return False
    return value.startswith("gAAAAA")
