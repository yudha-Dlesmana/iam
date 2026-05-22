from tests.conftest import REFRESH


async def test_refresh_without_cookie(client):
    client.cookies.clear()
    res = await client.post(REFRESH)
    assert res.status_code == 401


async def test_refresh_invalid_token(auth):
    res = await auth.refresh("gerbage.invalid.token")
    assert res.status_code == 401


async def test_old_refresh_reuse_revokes_family(user, redis, auth):
    # login
    res = await auth.login()
    assert res.status_code == 200
    r1 = res.cookies.get("refresh_token")
    assert r1

    # refresh token
    res = await auth.refresh(r1)
    assert res.status_code == 200
    r2 = res.cookies.get("refresh_token")
    assert r2 and r2 != r1

    # attacker replay old r1
    res = await auth.refresh(r1)
    assert res.status_code == 401

    # reuse trigger revoke_family
    res = await auth.refresh(r2)
    assert res.status_code == 401

    assert await redis.keys("refresh:*") == []
    assert await redis.keys("fam:*") == []
