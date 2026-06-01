import pytest_asyncio

from src.core.security import hash_password
from src.models import Role, User


@pytest_asyncio.fixture
async def single_session_user(db):
    role = Role(name="admin_singleton", single_session=True)
    db.add(role)
    await db.flush()
    u = User(
        email="single@starter.com",
        password=hash_password("!Qwer123"),
        role_id=role.id,
    )
    db.add(u)
    await db.commit()
    return u


@pytest_asyncio.fixture
async def multi_session_user(db):
    role = Role(name="member_multi", single_session=False)
    db.add(role)
    await db.flush()
    u = User(
        email="multi@starter.com",
        password=hash_password("!Qwer123"),
        role_id=role.id,
    )
    db.add(u)
    await db.commit()
    return u


CREDS_SINGLE = {"email": "single@starter.com", "password": "!Qwer123"}
CREDS_MULTI = {"email": "multi@starter.com", "password": "!Qwer123"}
LOGIN = "/v1/auth/login"


async def test_second_login_revokes_first_when_single_session(
    client, redis, single_session_user
):
    first = await client.post(LOGIN, json=CREDS_SINGLE)
    assert first.status_code == 200
    a = first.cookies.get("refresh_token")
    assert len(await redis.hkeys(f"sessions:{single_session_user.id}")) == 1

    client.cookies.clear()
    second = await client.post(LOGIN, json=CREDS_SINGLE)
    assert second.status_code == 200
    b = second.cookies.get("refresh_token")

    assert len(await redis.hkeys(f"sessions:{single_session_user.id}")) == 1

    client.cookies.clear()
    client.cookies.set("refresh_token", a, path="/v1/auth")
    refresh_old = await client.post("/v1/auth/refresh")
    assert refresh_old.status_code == 401

    client.cookies.clear()
    client.cookies.set("refresh_token", b, path="/v1/auth")
    refresh_new = await client.post("/v1/auth/refresh")
    assert refresh_new.status_code == 200


async def test_second_login_keeps_first_when_multi_session(
    client, redis, multi_session_user
):
    await client.post(LOGIN, json=CREDS_MULTI)
    client.cookies.clear()
    await client.post(LOGIN, json=CREDS_MULTI)

    assert len(await redis.hkeys(f"sessions:{multi_session_user.id}")) == 2


async def test_role_response_exposes_single_session(client, single_session_user):
    from src.app import app
    from src.lib.deps import get_current_claims

    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "super_admin",
        "permissions": ["iam.role.read"],
    }
    res = await client.get(f"/v1/roles/{single_session_user.role_id}")
    assert res.status_code == 200
    assert res.json()["single_session"] is True
