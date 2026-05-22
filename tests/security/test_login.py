from tests.conftest import LOGIN, CREDENTIALS


async def test_access_token_usable(user, auth):
    res = await auth.login()
    access = res.json()["access_token"]

    me = await auth.me(access)
    assert me.status_code == 200


async def test_login_wrong_password(client, user):
    res = await client.post(LOGIN, json={**CREDENTIALS, "password": "salah"})
    assert res.status_code == 401


async def test_login_unknown_email(client):
    res = await client.post(
        LOGIN, json={"email": "unkwnon@starter.com", "password": "!Qwer123"}
    )
    assert res.status_code == 401
