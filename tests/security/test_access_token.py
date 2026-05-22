async def test_access_token_usable(user, auth):
    res = await auth.login()
    access = res.json()["access_token"]

    me = await auth.me(access)
    assert me.status_code == 200
