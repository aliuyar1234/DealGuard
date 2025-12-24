"""Unit tests for rate limiting functionality.

Tests rate limit configuration and key generation.
"""

import os
from unittest.mock import MagicMock, patch

# Set required env vars
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-encryption-32chars"


class TestRateLimitConfiguration:
    """Test rate limit configuration values."""

    def test_rate_limit_constants_defined(self):
        """Test that rate limit constants are defined correctly."""
        from dealguard.api.ratelimit import (
            RATE_LIMIT_AI,
            RATE_LIMIT_AUTH,
            RATE_LIMIT_DEFAULT,
            RATE_LIMIT_HEALTH,
            RATE_LIMIT_SEARCH,
            RATE_LIMIT_UPLOAD,
        )

        assert RATE_LIMIT_DEFAULT == "100/minute"
        assert RATE_LIMIT_AUTH == "5/minute"
        assert RATE_LIMIT_UPLOAD == "10/minute"
        assert RATE_LIMIT_AI == "20/minute"
        assert RATE_LIMIT_SEARCH == "30/minute"
        assert RATE_LIMIT_HEALTH == "60/minute"

    def test_limiter_exists(self):
        """Test that global limiter is created."""
        from dealguard.api.ratelimit import limiter

        assert limiter is not None


class TestRateLimitKeyGeneration:
    """Test rate limit key generation."""

    def test_get_rate_limit_key_with_user(self):
        """Test key generation for authenticated user."""
        from dealguard.api.ratelimit import _get_rate_limit_key

        mock_request = MagicMock()
        mock_request.state.user = MagicMock(id="user-123")
        mock_request.client.host = "192.168.1.1"

        key = _get_rate_limit_key(mock_request)

        assert key == "user:user-123"

    def test_get_rate_limit_key_without_user(self):
        """Test key generation for unauthenticated request (uses IP)."""
        from dealguard.api.ratelimit import _get_rate_limit_key

        mock_request = MagicMock()
        mock_request.state = MagicMock(spec=[])  # No user attribute
        mock_request.client.host = "192.168.1.1"

        key = _get_rate_limit_key(mock_request)

        assert key == "192.168.1.1"

    def test_get_rate_limit_key_user_is_none(self):
        """Test key generation when user is None."""
        from dealguard.api.ratelimit import _get_rate_limit_key

        mock_request = MagicMock()
        mock_request.state.user = None
        mock_request.client.host = "10.0.0.1"

        key = _get_rate_limit_key(mock_request)

        assert key == "10.0.0.1"


class TestRateLimitExceededHandler:
    """Test custom rate limit exceeded handler."""

    def _create_mock_limit(self, limit_str: str) -> MagicMock:
        """Create a mock limit object that slowapi expects."""
        mock_limit = MagicMock()
        mock_limit.error_message = None
        mock_limit.__str__ = MagicMock(return_value=limit_str)
        return mock_limit

    def test_handler_returns_429(self):
        """Test that handler returns 429 status code."""
        from slowapi.errors import RateLimitExceeded

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/chat"
        mock_request.method = "POST"
        mock_request.state.user = MagicMock(id="user-123")

        mock_limit = self._create_mock_limit("20/minute")
        exc = RateLimitExceeded(mock_limit)

        with patch("dealguard.api.ratelimit.logger"):
            from dealguard.api.ratelimit import rate_limit_exceeded_handler

            response = rate_limit_exceeded_handler(mock_request, exc)

        assert response.status_code == 429

    def test_handler_returns_json_body(self):
        """Test that handler returns proper JSON body."""
        import json

        from slowapi.errors import RateLimitExceeded

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/contracts"
        mock_request.method = "POST"
        mock_request.state.user = MagicMock(id="user-456")

        mock_limit = self._create_mock_limit("10/minute")
        exc = RateLimitExceeded(mock_limit)

        with patch("dealguard.api.ratelimit.logger"):
            from dealguard.api.ratelimit import rate_limit_exceeded_handler

            response = rate_limit_exceeded_handler(mock_request, exc)
            body = json.loads(response.body)

        assert body["error"] == "too_many_requests"
        assert "Zu viele Anfragen" in body["message"]

    def test_handler_includes_retry_after_header(self):
        """Test that handler includes Retry-After header."""
        from slowapi.errors import RateLimitExceeded

        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/auth/login"
        mock_request.method = "POST"
        mock_request.state.user = None
        mock_request.client.host = "1.2.3.4"

        mock_limit = self._create_mock_limit("5/minute")
        exc = RateLimitExceeded(mock_limit)
        exc.retry_after = 30

        with patch("dealguard.api.ratelimit.logger"):
            from dealguard.api.ratelimit import rate_limit_exceeded_handler

            response = rate_limit_exceeded_handler(mock_request, exc)

        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "30"


class TestGetRateLimitDecorator:
    """Test rate limit decorator factory."""

    def test_get_rate_limit_decorator_returns_callable(self):
        """Test that decorator factory returns a callable."""
        from dealguard.api.ratelimit import get_rate_limit_decorator

        decorator = get_rate_limit_decorator("50/minute")

        assert callable(decorator)

    def test_get_rate_limit_decorator_with_various_limits(self):
        """Test decorator factory with various limit strings."""
        from dealguard.api.ratelimit import get_rate_limit_decorator

        test_limits = [
            "1/second",
            "60/minute",
            "1000/hour",
            "10000/day",
        ]

        for limit in test_limits:
            decorator = get_rate_limit_decorator(limit)
            assert callable(decorator)
