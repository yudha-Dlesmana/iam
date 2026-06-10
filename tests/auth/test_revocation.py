import asyncio

import pytest_asyncio

from src.app import app
from src.core.context import actor_id_var
from src.lib.revocation import get_revoked_at, mark_revoked
from src.core.security import create_access_token, hash_password
from src.lib.deps import get_current_claims
from src.models import Role, User


def _claims_for(actor_id: str, perms: list[str]):
    async def _factory():
        actor_id_var.set(actor_id)
        return {"sub": actor_id, "role": "test", "permissions": perms, "iat": 0}

    return _factory


@pytest_asyncio.fixture
async def admin(db):
    role = Role(name="admin")
    role.permissions = []
    db.add(role)
    await db.flush()
    u = User(
        email="admin@x.com",
        password=hash_password("!Qwer123"),
        role_id=role.id,
        role=role,
    )
    db.add(u)
    await db.commit()
    return u


@pytest_asyncio.fixture
async def target(db):
    u = User(email="target@x.com", password=hash_password("!Qwer123"))
    db.add(u)
    await db.commit()
    return u


async def test_mark_revoked_writes_redis(redis):
    await mark_revoked(redis, "u-1")
    assert await get_revoked_at(redis, "u-1") is not None


async def test_old_access_token_rejected_after_revoke(client, redis, admin):
    token = create_access_token(admin)
    me = await client.get(
        "/v1/auth/current-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200

    await asyncio.sleep(1)
    await mark_revoked(redis, admin.id)

    me_after = await client.get(
        "/v1/auth/current-user",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_after.status_code == 401
    assert me_after.json()["message"] == "token revoked"


async def test_new_token_after_revoke_still_works(client, redis, admin):
    await mark_revoked(redis, admin.id)
    await asyncio.sleep(1)

    new_token = create_access_token(admin)
    res = await client.get(
        "/v1/auth/current-user",
        headers={"Authorization": f"Bearer {new_token}"},
    )
    assert res.status_code == 200


async def test_revoke_endpoint_marks_redis(client, redis, admin, target):
    app.dependency_overrides[get_current_claims] = _claims_for(
        admin.id, ["iam.user.update"]
    )
    res = await client.post(f"/v1/users/{target.id}/revoke-tokens")
    assert res.status_code == 204
    assert await get_revoked_at(redis, target.id) is not None


async def test_revoke_endpoint_requires_permission(client, admin, target):
    app.dependency_overrides[get_current_claims] = _claims_for(
        admin.id, ["iam.user.read"]
    )
    res = await client.post(f"/v1/users/{target.id}/revoke-tokens")
    assert res.status_code == 403


async def test_delete_user_marks_revoked(client, redis, admin, target):
    app.dependency_overrides[get_current_claims] = _claims_for(
        admin.id, ["iam.user.delete"]
    )
    res = await client.delete(f"/v1/users/{target.id}")
    assert res.status_code == 204
    assert await get_revoked_at(redis, target.id) is not None


async def test_revoke_also_drops_refresh_sessions(client, redis, admin, user, auth):
    await auth.login()
    assert await redis.hkeys(f"sessions:{user.id}") != []

    app.dependency_overrides[get_current_claims] = _claims_for(
        admin.id, ["iam.user.update"]
    )
    await client.post(f"/v1/users/{user.id}/revoke-tokens")
    assert await redis.hkeys(f"sessions:{user.id}") == []
