from src.core.config import settings

# Non-exempt endpoint; returns 401 unauthenticated, but the global rate-limit
# middleware runs before routing so it can still 429.
PROBE = "/v1/auth/current-user"
HEADERS = {"X-Forwarded-For": "9.9.9.9"}  # stable client IP for the limiter


async def test_global_rate_limit_blocks_after_threshold(client, monkeypatch):
    """A2: melebihi GLOBAL_RATE_LIMIT dari satu IP → 429 + Retry-After."""
    monkeypatch.setattr(settings, "GLOBAL_RATE_LIMIT", 3)

    for _ in range(3):
        res = await client.get(PROBE, headers=HEADERS)
        assert res.status_code != 429

    blocked = await client.get(PROBE, headers=HEADERS)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert int(blocked.headers["Retry-After"]) > 0


async def test_health_exempt_from_global_rate_limit(client, monkeypatch):
    """A2: /v1/health dikecualikan walau limit sudah terlampaui."""
    monkeypatch.setattr(settings, "GLOBAL_RATE_LIMIT", 1)

    await client.get(PROBE, headers=HEADERS)
    blocked = await client.get(PROBE, headers=HEADERS)
    assert blocked.status_code == 429

    health = await client.get("/v1/health", headers=HEADERS)
    assert health.status_code == 200
