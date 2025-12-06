"""
Pytest configuration and fixtures for DealGuard backend tests.
"""
import asyncio
import os
import uuid
from collections.abc import AsyncGenerator, Generator
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from dealguard.config import Settings
from dealguard.infrastructure.database.models.base import Base
from dealguard.infrastructure.database.models.organization import Organization
from dealguard.infrastructure.database.models.user import User
from dealguard.main import create_app


# Use Docker PostgreSQL for integration tests
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://dealguard:dealguard@localhost:5432/dealguard_test"
)
TEST_DATABASE_SYNC_URL = os.getenv(
    "TEST_DATABASE_SYNC_URL",
    "postgresql://dealguard:dealguard@localhost:5432/dealguard_test"
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings using Docker PostgreSQL."""
    return Settings(
        database_url=TEST_DATABASE_URL,
        database_sync_url=TEST_DATABASE_SYNC_URL,
        redis_url="redis://localhost:6379/1",
        supabase_url="https://test.supabase.co",
        supabase_anon_key="test-anon-key",
        supabase_service_role_key="test-service-key",
        supabase_jwt_secret="test-jwt-secret-at-least-32-chars-long",
        anthropic_api_key="test-api-key",
        s3_bucket="test-bucket",
        s3_endpoint="http://localhost:9000",
        s3_access_key="minio",
        s3_secret_key="minio123",
        app_env="development",
        app_secret_key="test-secret-key-for-encryption-32chars",
    )


@pytest.fixture
async def async_engine(test_settings: Settings):
    """Create async test database engine."""
    engine = create_async_engine(
        str(test_settings.database_url),
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async test database session."""
    async_session_factory = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session


@pytest.fixture
def test_org_id() -> uuid.UUID:
    """Generate a test organization ID."""
    return uuid.uuid4()


@pytest.fixture
def test_user_id() -> uuid.UUID:
    """Generate a test user ID."""
    return uuid.uuid4()


@pytest.fixture
async def test_organization(async_session: AsyncSession, test_org_id: uuid.UUID) -> Organization:
    """Create a test organization."""
    org = Organization(
        id=test_org_id,
        name="Test Organization",
        slug="test-org",
        plan="business",
        monthly_contract_limit=100,
        monthly_partner_limit=50,
    )
    async_session.add(org)
    await async_session.commit()
    await async_session.refresh(org)
    return org


@pytest.fixture
async def test_user(
    async_session: AsyncSession,
    test_organization: Organization,
    test_user_id: uuid.UUID,
) -> User:
    """Create a test user."""
    user = User(
        id=test_user_id,
        organization_id=test_organization.id,
        email="test@example.com",
        full_name="Test User",
        role="admin",
        supabase_uid=str(uuid.uuid4()),
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
def mock_auth_user(test_user: User, test_organization: Organization) -> dict[str, Any]:
    """Create mock auth user data."""
    return {
        "id": str(test_user.id),
        "organization_id": str(test_organization.id),
        "email": test_user.email,
        "role": test_user.role,
    }


@pytest.fixture
def auth_headers(mock_auth_user: dict[str, Any]) -> dict[str, str]:
    """Create auth headers for API requests."""
    # In real tests, we'd create a proper JWT token
    # For unit tests, we'll mock the auth middleware
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Create test FastAPI application."""
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create sync test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# Mock fixtures for external services
@pytest.fixture
def mock_anthropic_client() -> MagicMock:
    """Create mock Anthropic client."""
    mock = MagicMock()
    mock.messages.create = AsyncMock(
        return_value=MagicMock(
            content=[MagicMock(text='{"summary": "Test analysis", "findings": []}')],
            usage=MagicMock(input_tokens=100, output_tokens=50),
        )
    )
    return mock


@pytest.fixture
def mock_s3_client() -> MagicMock:
    """Create mock S3 client."""
    mock = MagicMock()
    mock.upload_fileobj = MagicMock()
    mock.download_fileobj = MagicMock()
    mock.generate_presigned_url = MagicMock(return_value="https://test-url.com/file")
    return mock


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Create mock Redis client."""
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    return mock
