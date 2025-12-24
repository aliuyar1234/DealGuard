"""Unit tests for Prometheus metrics endpoint."""

import os

from fastapi.testclient import TestClient


def test_metrics_endpoint_returns_text() -> None:
    os.environ["APP_SECRET_KEY"] = "test-secret-key-for-encryption-32chars"
    from dealguard.config import get_settings

    get_settings.cache_clear()
    from dealguard.main import create_app

    client = TestClient(create_app())
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
