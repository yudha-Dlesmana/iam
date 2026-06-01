from src.services.auth import LOGIN_EMAIL_LIMIT
from tests.conftest import LOGIN, CREDENTIALS


async def test_login_blocked_after_threshold(client, user):
    wrong = {**CREDENTIALS, "password": "wrong"}
    for _ in range(LOGIN_EMAIL_LIMIT):
        res = await client.post(LOGIN, json=wrong)
        assert res.status_code == 401

    blocked = await client.post(LOGIN, json=wrong)
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    assert int(blocked.headers["Retry-After"]) > 0


async def test_login_blocked_blocks_correct_password(client, user):
    wrong = {**CREDENTIALS, "password": "wrong"}
    for _ in range(LOGIN_EMAIL_LIMIT):
        await client.post(LOGIN, json=wrong)

    res = await client.post(LOGIN, json=CREDENTIALS)
    assert res.status_code == 429


async def test_success_resets_email_counter(client, user):
    wrong = {**CREDENTIALS, "password": "wrong"}
    for _ in range(LOGIN_EMAIL_LIMIT - 1):
        res = await client.post(LOGIN, json=wrong)
        assert res.status_code == 401

    ok = await client.post(LOGIN, json=CREDENTIALS)
    assert ok.status_code == 200

    res = await client.post(LOGIN, json=wrong)
    assert res.status_code == 401
