import pytest
import pytest_asyncio

from src.app import app
from src.lib.deps import get_current_claims
from src.models import Service, Permission

URL = "v1/permissions"


@pytest.fixture
def can_manage(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "super_admin",
        "permissions": ["iam.permission.read", "iam.permission.manage"],
    }


@pytest.fixture
def read_only(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "viewer",
        "permissions": ["iam.permission.read"],
    }


@pytest_asyncio.fixture
async def a_service(db):
    s = Service(name="iam")
    db.add(s)
    await db.commit()
    return s


async def test_create_permission_ok(client, can_manage, a_service):
    res = await client.post(
        URL, json={"name": "iam.report.read", "service_id": a_service.id}
    )
    assert res.status_code == 201
    assert res.json()["name"] == "iam.report.read"


async def test_create_permission_unknown_service(client, can_manage):
    # service_id gak ada -> FK violation -> 422 ValidationError
    res = await client.post(URL, json={"name": "x.y.z", "service_id": 999})
    assert res.status_code == 422


async def test_create_permission_duplicate_conflict(client, can_manage, a_service, db):
    db.add(Permission(name="iam.dup.read", service_id=a_service.id))
    await db.commit()
    res = await client.post(
        URL, json={"name": "iam.dup.read", "service_id": a_service.id}
    )
    assert res.status_code == 409


async def test_create_permission_forbidden(client, read_only, a_service):
    res = await client.post(
        URL, json={"name": "iam.x.read", "service_id": a_service.id}
    )
    assert res.status_code == 403


async def test_list_permissions_ok(client, can_manage, a_service, db):
    db.add(Permission(name="iam.foo.read", service_id=a_service.id))
    await db.commit()
    res = await client.get(URL)
    assert res.status_code == 200
    assert res.json()["total"] == 1
