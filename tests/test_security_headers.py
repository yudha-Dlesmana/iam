async def test_security_headers_present(client):
    res = await client.get("/v1/health")
    h = res.headers
    assert h.get("X-Content-Type-Options") == "nosniff"
    assert h.get("X-Frame-Options") == "DENY"
    assert h.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in h


async def test_hsts_not_set_in_development(client):
    res = await client.get("/v1/health")
    assert "Strict-Transport-Security" not in res.headers
