import json


async def test_list_sessions(user, auth):
    await auth.login()
    res = await auth.login()
    access_token = res.json()["access_token"]

    out = await auth.sessions(access_token)
    assert out.status_code == 200

    data = out.json()
    assert len(data) == 2
    assert "ip" in data[0]
    assert "jti" not in data[0]


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
