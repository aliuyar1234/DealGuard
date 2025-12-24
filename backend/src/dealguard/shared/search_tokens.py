"""Search tokenization and hashing utilities.

DealGuard stores contract texts encrypted at rest. To enable scalable keyword
search without decrypting entire datasets, we maintain a separate search index
based on HMAC-hashed tokens.

Security properties:
- Tokens are HMAC'd using a key derived from APP_SECRET_KEY.
- Without APP_SECRET_KEY, token hashes are not reversible in practice.

Limitations:
- This is a term-based index (no linguistic stemming like PostgreSQL FTS).
"""

from __future__ import annotations

import hashlib
import hmac
import re
from functools import lru_cache

from dealguard.config import get_settings

# Unicode-aware "word" tokens, excluding underscores.
_WORD_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)

# Common German stop words to ignore for indexing and queries.
_STOP_WORDS = {
    "der",
    "die",
    "das",
    "den",
    "dem",
    "des",
    "ein",
    "eine",
    "einer",
    "einem",
    "einen",
    "und",
    "oder",
    "aber",
    "wenn",
    "weil",
    "ist",
    "sind",
    "war",
    "waren",
    "wird",
    "werden",
    "hat",
    "haben",
    "hatte",
    "hatten",
    "ich",
    "du",
    "er",
    "sie",
    "es",
    "wir",
    "ihr",
    "mein",
    "meine",
    "dein",
    "deine",
    "sein",
    "seine",
    "was",
    "wer",
    "wie",
    "wo",
    "wann",
    "warum",
    "zu",
    "von",
    "mit",
    "bei",
    "für",
    "auf",
    "an",
    "in",
    "nicht",
    "kein",
    "keine",
    "auch",
    "noch",
    "nur",
    "schon",
}


@lru_cache(maxsize=1)
def _get_hmac_key() -> bytes:
    secret = get_settings().app_secret_key
    # Domain-separated key derivation.
    return hashlib.sha256(f"dealguard:search-index:{secret}".encode()).digest()


def _normalize_token(token: str) -> str | None:
    t = token.casefold()
    if len(t) < 3:
        return None
    if t in _STOP_WORDS:
        return None
    if len(t) > 128:
        t = t[:128]
    return t


def _expand_token(token: str) -> set[str]:
    tokens = {token}
    # Add a prefix token to improve recall for compound words.
    if len(token) >= 8:
        tokens.add(token[:6])
    return tokens


def token_hash(token: str) -> bytes:
    """Compute a stable HMAC-SHA256 hash for a single token."""
    key = _get_hmac_key()
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).digest()


def token_hashes_from_text(
    text: str,
    *,
    max_unique_tokens: int = 20_000,
) -> list[bytes]:
    """Extract unique token hashes for indexing a document."""
    hashes: set[bytes] = set()

    for raw in _WORD_RE.findall(text):
        normalized = _normalize_token(raw)
        if normalized is None:
            continue
        for expanded in _expand_token(normalized):
            hashes.add(token_hash(expanded))
            if len(hashes) >= max_unique_tokens:
                break
        if len(hashes) >= max_unique_tokens:
            break

    return sorted(hashes)


def token_hashes_from_query(
    query: str,
    *,
    max_unique_tokens: int = 32,
) -> list[bytes]:
    """Extract token hashes for a user query."""
    hashes: set[bytes] = set()

    for raw in _WORD_RE.findall(query):
        normalized = _normalize_token(raw)
        if normalized is None:
            continue
        for expanded in _expand_token(normalized):
            hashes.add(token_hash(expanded))
            if len(hashes) >= max_unique_tokens:
                break
        if len(hashes) >= max_unique_tokens:
            break

    return sorted(hashes)
