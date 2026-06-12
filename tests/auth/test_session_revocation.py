from src.core.security import create_access_token, decode_access_token


async def test_logout_kills_access_token_immediately(client, user, auth):
    res = await auth.login()
    access = res.json()["access_token"]
    refresh = client.cookies.get("refresh_token")

    assert (await auth.me(access)).status_code == 200

    await auth.logout(refresh)

    assert (await auth.me(access)).status_code == 401


async def test_logout_one_device_keeps_other_access_alive(client, user, auth):
    res_a = await auth.login()
    access_a = res_a.json()["access_token"]
    refresh_a = client.cookies.get("refresh_token")

    res_b = await auth.login()
    access_b = res_b.json()["access_token"]

    await auth.logout(refresh_a)

    assert (await auth.me(access_a)).status_code == 401
    assert (await auth.me(access_b)).status_code == 200


async def test_logout_all_kills_all_access_token(client, user, auth):
    res_a = await auth.login()
    access_a = res_a.json()["access_token"]

    res_b = await auth.login()
    access_b = res_b.json()["access_token"]
    refresh_b = client.cookies.get("refresh_token")

    await auth.all_logout(refresh_b)
    assert (await auth.me(access_a)).status_code == 401
    assert (await auth.me(access_b)).status_code == 401


async def test_access_token_carries_sid(db, user):
    token = create_access_token(user, sid="device-xyz")
    claims = decode_access_token(token)
    assert claims["sid"] == "device-xyz"
