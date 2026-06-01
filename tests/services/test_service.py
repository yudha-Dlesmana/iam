import pytest
import pytest_asyncio

from src.app import app
from src.lib.deps import get_current_claims
from src.models import Service, Permission

URL = "v1/services"


@pytest.fixture
def can_manage(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "super_admin",
        "permissions": ["iam.service.read", "iam.service.manage"],
    }


@pytest.fixture
def read_only(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "viewer",
        "permissions": ["iam.service.read"],
    }


@pytest_asyncio.fixture
async def a_service(db):
    s = Service(name="billing")
    db.add(s)
    await db.commit()
    return s


async def test_create_service_ok(client, can_manage):
    res = await client.post(URL, json={"name": "billing"})
    assert res.status_code == 201
    assert res.json()["name"] == "billing"


async def test_create_service_duplicate_conflict(client, can_manage, a_service):
    res = await client.post(URL, json={"name": "billing"})
    assert res.status_code == 409


async def test_create_service_forbidden(client, read_only):
    res = await client.post(URL, json={"name": "billing"})
    assert res.status_code == 403


async def test_list_services_ok(client, can_manage, a_service):
    res = await client.get(URL)
    assert res.status_code == 200
    assert res.json()["total"] == 1


async def test_delete_service_cascades_permissions(client, can_manage, a_service, db):
    # tambah permission ke service
    db.add(Permission(name="billing.invoice.read", service_id=a_service.id))
    await db.commit()

    res = await client.delete(f"{URL}/{a_service.id}")
    assert res.status_code == 204

    # permission ikut kehapus (CASCADE)
    from sqlalchemy import select, func

    left = await db.scalar(
        select(func.count())
        .select_from(Permission)
        .where(Permission.service_id == a_service.id)
    )
    assert left == 0
