from fastapi.testclient import TestClient


def test_root_redirects_to_docs(client: TestClient):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_api_v1_prefix_mounted(client: TestClient):
    response = client.get("/openapi.json")

    paths = response.json()["paths"]
    assert any(path.startswith("/api/v1") for path in paths)
