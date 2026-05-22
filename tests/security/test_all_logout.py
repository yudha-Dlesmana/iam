async def test_all_logout_kill_whole_family(user, redis, auth):
    res = await auth.login()
    r1 = res.cookies.get("refresh_token")
    res = await auth.refresh(r1)
    r2 = res.cookies.get("refresh_token")

    res = await auth.all_logout(r2)
    assert res.status_code == 204

    assert await redis.keys("sessions:*") == []
