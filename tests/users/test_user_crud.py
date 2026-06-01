import pytest
import pytest_asyncio

from src.app import app
from src.lib.deps import get_current_claims
from src.models import Role

URL = "/v1/users"


@pytest.fixture
def can_manage(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "super_admin",
        "permissions": [
            "iam.user.read",
            "iam.user.create",
            "iam.user.update",
            "iam.user.delete",
        ],
    }


@pytest.fixture
def read_only(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "viewer",
        "permissions": ["iam.user.read"],
    }


@pytest_asyncio.fixture
async def a_role(db):
    r = Role(name="member")
    db.add(r)
    await db.commit()
    return r


async def test_create_user_ok(client, can_manage, a_role):
    res = await client.post(
        URL,
        json={"email": "new@x.com", "password": "!Qwer123", "role_id": a_role.id},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == "new@x.com"
    assert body["role_name"] == "member"


async def test_create_user_duplicate_email_conflict(client, can_manage, a_role, user):
    res = await client.post(
        URL,
        json={"email": user.email, "password": "!Qwer123", "role_id": a_role.id},
    )
    assert res.status_code == 409


async def test_create_user_unknown_role(client, can_manage):
    res = await client.post(
        URL, json={"email": "x@x.com", "password": "!Qwer123", "role_id": 999}
    )
    assert res.status_code == 404


async def test_create_user_weak_password_validation(client, can_manage, a_role):
    res = await client.post(
        URL, json={"email": "x@x.com", "password": "weak", "role_id": a_role.id}
    )
    assert res.status_code == 422


async def test_create_user_forbidden(client, read_only, a_role):
    res = await client.post(
        URL, json={"email": "x@x.com", "password": "!Qwer123", "role_id": a_role.id}
    )
    assert res.status_code == 403


async def test_get_user_ok(client, can_manage, user):
    res = await client.get(f"{URL}/{user.id}")
    assert res.status_code == 200
    assert res.json()["id"] == user.id


async def test_get_user_not_found(client, can_manage):
    res = await client.get(f"{URL}/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


async def test_list_users_ok(client, can_manage, user):
    res = await client.get(URL)
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert any(u["email"] == user.email for u in body["items"])


async def test_list_users_filter_email_like(client, can_manage, user):
    res = await client.get(URL, params={"email_like": "test"})
    assert res.status_code == 200
    assert res.json()["total"] == 1

    res = await client.get(URL, params={"email_like": "nomatch"})
    assert res.status_code == 200
    assert res.json()["total"] == 0


async def test_update_user_email(client, can_manage, user):
    res = await client.patch(f"{URL}/{user.id}", json={"email": "renamed@x.com"})
    assert res.status_code == 200
    assert res.json()["email"] == "renamed@x.com"


async def test_update_user_role(client, can_manage, user, a_role):
    res = await client.patch(f"{URL}/{user.id}", json={"role_id": a_role.id})
    assert res.status_code == 200
    assert res.json()["role_name"] == "member"


async def test_update_user_no_fields_validation(client, can_manage, user):
    res = await client.patch(f"{URL}/{user.id}", json={})
    assert res.status_code == 422


async def test_delete_user_ok(client, can_manage, user):
    res = await client.delete(f"{URL}/{user.id}")
    assert res.status_code == 204

    follow = await client.get(f"{URL}/{user.id}")
    assert follow.status_code == 404
