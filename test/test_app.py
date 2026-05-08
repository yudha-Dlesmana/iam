from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.app import app


def test_app_is_fastapi_instance():
    assert isinstance(app, FastAPI)


def test_app_metadata():
    assert app.title == "FastAPI Starter"
    assert app.version == "0.0.1"
    assert app.swagger_ui_parameters == {"withCredentials": True}


def test_root_redirects_to_docs(client: TestClient):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_root_excluded_from_schema(client: TestClient):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/" not in paths


def test_docs_endpoint_available(client: TestClient):
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_openapi_schema_available(client: TestClient):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "FastAPI Starter"
    assert schema["info"]["version"] == "0.0.1"


def test_api_v1_prefix_mounted(client: TestClient):
    response = client.get("/openapi.json")

    paths = response.json()["paths"]
    assert any(path.startswith("/api/v1") for path in paths)
