from tests.conftest import LOGOUT


async def test_logout_revokes_and_cleans_family(user, redis, auth):
    res = await auth.login()
    r1 = res.cookies.get("refresh_token")

    res = await auth.logout(r1)
    assert res.status_code == 204

    assert await redis.keys("sessions:*") == []

    res = await auth.refresh(r1)
    assert res.status_code == 401


async def test_logout_without_cookie(client):
    client.cookies.clear()
    res = await client.post(LOGOUT)
    assert res.status_code == 204


async def test_logout_invalid_token(auth):
    res = await auth.logout("gerbage.invalid.token")
    assert res.status_code == 204
