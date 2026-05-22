async def test_logout_revokes_and_cleans_family(user, redis, auth):
    res = await auth.login()
    r1 = res.cookies.get("refresh_token")

    res = await auth.logout(r1)
    assert res.status_code == 204

    assert await redis.keys("refresh:*") == []
    assert await redis.keys("fam::*") == []

    res = await auth.refresh(r1)
    assert res.status_code == 401
