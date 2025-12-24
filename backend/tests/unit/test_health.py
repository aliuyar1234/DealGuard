"""Unit tests for health check endpoints.

Tests database, Redis, and storage health checks.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Set required env vars
os.environ["APP_SECRET_KEY"] = "test-secret-key-for-encryption-32chars"


class TestHealthEndpoint:
    """Test basic health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_healthy(self):
        """Test that /health returns healthy status."""
        from dealguard.api.routes.health import health_check

        response = await health_check()

        assert response.status == "healthy"
        assert response.database == "not_checked"
        assert response.redis == "not_checked"

    @pytest.mark.asyncio
    async def test_health_includes_version(self):
        """Test that /health includes version."""
        from dealguard.api.routes.health import health_check

        response = await health_check()

        assert response.version is not None
        assert len(response.version) > 0


class TestReadinessEndpoint:
    """Test readiness check endpoint."""

    @pytest.mark.asyncio
    async def test_ready_all_services_up(self):
        """Test /ready when all services are available."""
        from dealguard.api.routes.health import readiness_check

        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        # Mock Redis and S3
        with patch("redis.asyncio.from_url") as mock_redis_from_url, patch(
            "boto3.client"
        ) as mock_boto_client:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis.close = AsyncMock()
            mock_redis_from_url.return_value = mock_redis
            mock_boto_client.return_value = MagicMock()

            response = await readiness_check(session=mock_session)

        assert response.ready is True
        assert response.checks["database"] is True
        assert response.checks["redis"] is True
        assert response.checks["storage"] is True

    @pytest.mark.asyncio
    async def test_ready_database_down(self):
        """Test /ready when database is unavailable."""
        from dealguard.api.routes.health import readiness_check

        # Mock database session that fails
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("Connection refused"))

        # Mock Redis and S3 working
        with patch("redis.asyncio.from_url") as mock_redis_from_url, patch(
            "boto3.client"
        ) as mock_boto_client:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock()
            mock_redis.close = AsyncMock()
            mock_redis_from_url.return_value = mock_redis
            mock_boto_client.return_value = MagicMock()

            response = await readiness_check(session=mock_session)

        assert response.ready is False
        assert response.checks["database"] is False
        assert response.checks["redis"] is True
        assert response.checks["storage"] is True

    @pytest.mark.asyncio
    async def test_ready_redis_down(self):
        """Test /ready when Redis is unavailable."""
        from dealguard.api.routes.health import readiness_check

        # Mock database session working
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        # Mock Redis failing, S3 working
        with patch("redis.asyncio.from_url") as mock_redis_from_url, patch(
            "boto3.client"
        ) as mock_boto_client:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=Exception("Connection refused"))
            mock_redis_from_url.return_value = mock_redis
            mock_boto_client.return_value = MagicMock()

            response = await readiness_check(session=mock_session)

        assert response.ready is False
        assert response.checks["database"] is True
        assert response.checks["redis"] is False
        assert response.checks["storage"] is True

    @pytest.mark.asyncio
    async def test_ready_all_services_down(self):
        """Test /ready when all services are unavailable."""
        from dealguard.api.routes.health import readiness_check

        # Mock database session that fails
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB down"))

        # Mock Redis and S3 failing
        with patch("redis.asyncio.from_url") as mock_redis_from_url, patch(
            "boto3.client"
        ) as mock_boto_client:
            mock_redis = AsyncMock()
            mock_redis.ping = AsyncMock(side_effect=Exception("Redis down"))
            mock_redis_from_url.return_value = mock_redis
            mock_boto_client.return_value = MagicMock(
                list_objects_v2=MagicMock(side_effect=Exception("S3 down"))
            )

            response = await readiness_check(session=mock_session)

        assert response.ready is False
        assert response.checks["database"] is False
        assert response.checks["redis"] is False
        assert response.checks["storage"] is False


class TestHealthResponseModels:
    """Test response model validation."""

    def test_health_response_model(self):
        """Test HealthResponse model."""
        from dealguard.api.routes.health import HealthResponse

        response = HealthResponse(
            status="healthy",
            version="1.0.0",
            database="connected",
            redis="connected",
        )

        assert response.status == "healthy"
        assert response.version == "1.0.0"

    def test_ready_response_model(self):
        """Test ReadyResponse model."""
        from dealguard.api.routes.health import ReadyResponse

        response = ReadyResponse(
            ready=True,
            checks={"database": True, "redis": True},
        )

        assert response.ready is True
        assert response.checks["database"] is True
        assert response.checks["redis"] is True

    def test_ready_response_with_extra_checks(self):
        """Test ReadyResponse with additional checks."""
        from dealguard.api.routes.health import ReadyResponse

        response = ReadyResponse(
            ready=True,
            checks={
                "database": True,
                "redis": True,
                "s3": True,
                "ai_provider": True,
            },
        )

        assert len(response.checks) == 4
