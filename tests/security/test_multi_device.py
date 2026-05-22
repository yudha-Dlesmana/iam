import json


async def test_logout_one_device_keeps_others(user, redis, auth):
    a = (await auth.login()).cookies.get("refresh_token")
    b = (await auth.login()).cookies.get("refresh_token")

    assert len(await redis.hkeys(f"sessions:{user.id}")) == 2

    await auth.logout(a)
    assert len(await redis.hkeys(f"sessions:{user.id}")) == 1
    assert (await auth.refresh(b)).status_code == 200
    assert (await auth.refresh(a)).status_code == 401


async def test_session_stores_metadata(user, redis, auth):
    await auth.login()
    raw = await redis.hvals(f"sessions:{user.id}")
    data = json.loads(raw[0])
    assert "ip" in data and "ua" in data and "jti" in data
