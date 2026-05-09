from fastapi.testclient import TestClient

from src.app import app


# ═══════════════════════════════════
# APP METADATA
# ═══════════════════════════════════

def test_swagger_ui_with_credentials_enabled():
    """Cookies harus dikirim dari Swagger UI saat test endpoint."""
    assert app.swagger_ui_parameters == {"withCredentials": True}


# ═══════════════════════════════════
# DEFAULT ROUTE
# ═══════════════════════════════════

def test_root_redirects_to_docs(client: TestClient):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_root_excluded_from_openapi_schema(client: TestClient):
    response = client.get("/openapi.json")
    paths = response.json()["paths"]

    assert "/" not in paths


# ═══════════════════════════════════
# ROUTER MOUNTING
# ═══════════════════════════════════

def test_api_v1_prefix_mounted(client: TestClient):
    response = client.get("/openapi.json")
    paths = response.json()["paths"]

    assert any(path.startswith("/api/v1") for path in paths)


def test_api_routes_not_at_root(client: TestClient):
    response = client.get("/openapi.json")
    paths = response.json()["paths"]

    api_routes = [p for p in paths if "/user" in p or "/health" in p]
    for route in api_routes:
        assert route.startswith("/api/v1"), f"Route bocor di luar prefix: {route}"


# ═══════════════════════════════════
# CORS — preflight check
# ═══════════════════════════════════

def test_cors_preflight_responds(client: TestClient):
    """OPTIONS request harus dapat CORS headers."""
    response = client.options(
        "/api/v1/user",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" in {h.lower() for h in response.headers.keys()}


# ═══════════════════════════════════
# DOCS ENDPOINTS
# ═══════════════════════════════════

def test_docs_endpoint_available(client: TestClient):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_json_available(client: TestClient):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "FastAPI Starter"
