import pytest
import pytest_asyncio

from src.app import app
from src.lib.deps import get_current_claims
from src.models import Role, Permission

URL = "v1/roles/{id}/permissions"


@pytest_asyncio.fixture
async def editor_role(db):
    r = Role(name="editor")
    db.add(r)
    await db.commit()
    return r


@pytest_asyncio.fixture
async def two_perms(db):
    items = [Permission(name="user.read"), Permission(name="user.create")]
    db.add_all(items)
    await db.commit()
    return items


@pytest.fixture
def can_manage(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "super_admin",
        "permissions": ["role.read", "role.manage"],
    }


@pytest.fixture
def read_only(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "viewer",
        "permissions": ["role.read"],
    }


async def test_set_permissions_ok(client, can_manage, editor_role, two_perms):
    ids = [p.id for p in two_perms]
    res = await client.put(URL.format(id=editor_role.id), json={"permissions_ids": ids})

    assert res.status_code == 200
    names = {p["name"] for p in res.json()["permissions"]}
    assert names == {"user.read", "user.create"}


async def test_set_permissions_forbidden(client, read_only, editor_role, two_perms):
    ids = [p.id for p in two_perms]
    res = await client.put(URL.format(id=editor_role.id), json={"permissions_ids": ids})

    assert res.status_code == 403


async def test_set_permissions_unknown_id(client, can_manage, editor_role):
    res = await client.put(
        URL.format(id=editor_role.id), json={"permissions_ids": [999]}
    )

    assert res.status_code == 404
