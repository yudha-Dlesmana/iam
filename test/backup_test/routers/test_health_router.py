from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from src.app import app
from src.core.dependency import get_health_service
from src.schemas.base_schema import BaseResponse
from src.schemas.health_schema import HealthResponse
from src.services.health_services import HealthService


@pytest.fixture
def mock_service():
    return AsyncMock(spec=HealthService)


@pytest.fixture
def client(mock_service):
    app.dependency_overrides[get_health_service] = lambda: mock_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ═══════════════════════════════════
# GET /health
# ═══════════════════════════════════

def test_health_returns_200_with_status(client, mock_service):
    mock_service.get_health.return_value = BaseResponse[HealthResponse](
        message="Health checked",
        data=HealthResponse(
            status="running",
            database="connected to mysql",
            redis="connected",
            other_service="ok",
        ),
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Health checked"
    assert body["data"]["status"] == "running"
    assert body["data"]["database"] == "connected to mysql"
    assert body["data"]["redis"] == "connected"
    mock_service.get_health.assert_awaited_once()


def test_health_reports_partial_failure(client, mock_service):
    mock_service.get_health.return_value = BaseResponse[HealthResponse](
        message="Health checked",
        data=HealthResponse(
            status="running",
            database="mysql unavailable: connection error: refused",
            redis="connected",
            other_service="ok",
        ),
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert "unavailable" in body["data"]["database"]
    assert body["data"]["redis"] == "connected"
