"""Unit and integration tests for the /api/v1/health endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_db
from app.main import app


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    session.execute.return_value = mock_result
    return session


def test_root_index():
    """Verify root endpoint returns metadata."""
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "The Lenny Growth Assistant API"
    assert data["health"] == "/api/v1/health"


def test_health_all_healthy(mock_db):
    """Verify 200 OK when both PostgreSQL and Ollama are reachable."""
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_ollama_response = MagicMock(status_code=200)

    with patch("httpx.AsyncClient.get", return_value=mock_ollama_response):
        client = TestClient(app)
        response = client.get("/api/v1/health")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["ollama"] == "reachable"
    assert data["provider"] == "ollama"


def test_health_ollama_unreachable(mock_db):
    """Verify 200 OK with degraded status when Ollama is unreachable."""
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
        client = TestClient(app)
        response = client.get("/api/v1/health")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "connected"
    assert data["ollama"] == "unreachable"


def test_health_db_disconnected():
    """Verify 503 Service Unavailable when database connection fails."""
    mock_failing_db = AsyncMock()
    mock_failing_db.execute.side_effect = Exception("DB Connection Timeout")

    app.dependency_overrides[get_db] = lambda: mock_failing_db

    mock_ollama_response = MagicMock(status_code=200)

    with patch("httpx.AsyncClient.get", return_value=mock_ollama_response):
        client = TestClient(app)
        response = client.get("/api/v1/health")

    app.dependency_overrides.clear()

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "disconnected"
