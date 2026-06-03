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
    from src.models import Service

    svc = Service(name="iam")
    db.add(svc)
    await db.flush()
    items = [
        Permission(name="iam.user.read", service_id=svc.id),
        Permission(name="iam.user.create", service_id=svc.id),
    ]
    db.add_all(items)
    await db.commit()
    return items


@pytest.fixture
def can_manage(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "super_admin",
        "permissions": ["iam.role.read", "iam.role.manage"],
    }


@pytest.fixture
def read_only(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "viewer",
        "permissions": ["iam.role.read"],
    }


async def test_add_permissions_ok(client, can_manage, editor_role, two_perms):
    ids = [p.id for p in two_perms]
    res = await client.patch(
        URL.format(id=editor_role.id), json={"permission_ids": ids}
    )

    assert res.status_code == 200
    names = {p["name"] for p in res.json()["permissions"]}
    assert names == {"iam.user.read", "iam.user.create"}


async def test_add_permissions_forbidden(client, read_only, editor_role, two_perms):
    ids = [p.id for p in two_perms]
    res = await client.patch(
        URL.format(id=editor_role.id), json={"permission_ids": ids}
    )

    assert res.status_code == 403


async def test_add_permissions_unknown_id(client, can_manage, editor_role):
    res = await client.patch(
        URL.format(id=editor_role.id), json={"permission_ids": [999]}
    )

    assert res.status_code == 404


async def test_add_permissions_keeps_existing(
    client, can_manage, editor_role, two_perms, db
):
    # set 1 permission dulu
    p1, p2 = two_perms
    await client.patch(URL.format(id=editor_role.id), json={"permission_ids": [p1.id]})
    # PATCH p2 -> harus punya dua-duanya (bukan replace)
    res = await client.patch(
        URL.format(id=editor_role.id),
        json={"permission_ids": [p2.id]},
    )
    assert res.status_code == 200
    names = {p["name"] for p in res.json()["permissions"]}
    assert names == {"iam.user.read", "iam.user.create"}


async def test_add_permissions_idempotent(client, can_manage, editor_role, two_perms):
    p1, _ = two_perms
    await client.patch(
        URL.format(id=editor_role.id),
        json={"permission_ids": [p1.id]},
    )

    res = await client.patch(
        URL.format(id=editor_role.id),
        json={"permission_ids": [p1.id]},
    )
    assert res.status_code == 200
    ids = [p["id"] for p in res.json()["permissions"]]
    assert ids.count(p1.id) == 1


async def test_remove_permission_ok(client, can_manage, editor_role, two_perms):
    p1, p2 = two_perms
    await client.patch(
        URL.format(id=editor_role.id),
        json={"permission_ids": [p1.id, p2.id]},
    )

    res = await client.delete(f"{URL.format(id=editor_role.id)}/{p1.id}")
    assert res.status_code == 200
    names = {p["name"] for p in res.json()["permissions"]}
    assert names == {"iam.user.create"}
