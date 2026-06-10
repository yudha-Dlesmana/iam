async def test_response_has_request_id(client):
    res = await client.get("/v1/health")
    assert "X-Request-ID" in res.headers
    assert res.headers["X-Request-ID"]
