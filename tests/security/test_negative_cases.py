from tests.conftest import LOGIN, REFRESH, CREDENTIALS


async def test_login_wrong_password(client, user):
    res = await client.post(LOGIN, json={**CREDENTIALS, "password": "salah"})
    assert res.status_code == 401


async def test_login_unknown_email(client):
    res = await client.post(
        LOGIN, json={"email": "unkwnon@starter.com", "password": "!Qwer123"}
    )
    assert res.status_code == 401


async def test_refresh_without_cookie(client):
    client.cookies.clear()
    res = await client.post(REFRESH)
    assert res.status_code == 401


async def test_refresh_invalid_token(auth):
    res = await auth.refresh("gerbage.invalid.token")
    assert res.status_code == 401
