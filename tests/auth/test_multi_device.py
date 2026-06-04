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


async def test_current_session_returns_active_device(user, auth):
    ra = await auth.login()
    rb = await auth.login()
    a, ta = ra.cookies.get("refresh_token"), ra.json()["access_token"]
    b, tb = rb.cookies.get("refresh_token"), rb.json()["access_token"]

    res = await auth.current_session(b, tb)
    assert res.status_code == 200
    data = res.json()
    assert "device" in data and "ip" in data
    assert "jti" not in data

    # the current call identifies its own device, distinct from the other login
    other = await auth.current_session(a, ta)
    assert other.json()["device"] != data["device"]


async def test_current_session_missing_cookie(user, auth):
    access_token = (await auth.login()).json()["access_token"]
    res = await auth.current_session("", access_token)
    assert res.status_code == 401


async def test_current_session_after_logout(user, auth):
    r = await auth.login()
    a, token = r.cookies.get("refresh_token"), r.json()["access_token"]
    await auth.logout(a)
    res = await auth.current_session(a, token)
    assert res.status_code == 401
