LOGIN = "/v1/auth/login"
REFRESH = "/v1/auth/refresh"
CREDENTIALS = {"email": "test@starter.com", "password": "!Qwer123"}


async def _refresh(client, token):
    client.cookies.clear()
    client.cookies.set("refresh_token", token, path="/v1/auth")
    return await client.post(REFRESH)


async def test_old_refresh_reuse_revokes_family(client, user, redis):
    # login
    res = await client.post(LOGIN, json=CREDENTIALS)
    assert res.status_code == 200
    r1 = res.cookies.get("refresh_token")
    assert r1

    # refresh token
    res = await _refresh(client, r1)
    assert res.status_code == 200
    r2 = res.cookies.get("refresh_token")
    assert r2 and r2 != r1

    # attacker replay old r1
    res = await _refresh(client, r1)
    assert res.status_code == 401

    # reuse trigger revoke_family
    res = await _refresh(client, r2)
    assert res.status_code == 401

    assert await redis.keys("refresh:*") == []
    assert await redis.keys("fam:*") == []
