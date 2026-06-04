import pytest_asyncio
from sqlalchemy import select

from src.app import app
from src.core.audit_context import actor_id_var
from src.core.security import hash_password
from src.lib.deps import get_current_claims
from src.models import AuditLog, Role, User


def _claims_with(actor: str, perms: list[str]):
    async def _factory():
        actor_id_var.set(actor)
        return {"sub": actor, "role": "test", "permissions": perms}

    return _factory


@pytest_asyncio.fixture
async def actor(db):
    u = User(email="actor@x.com", password=hash_password("!Qwer123"))
    db.add(u)
    await db.commit()
    return u


@pytest_asyncio.fixture
async def actor_admin(client, actor):
    app.dependency_overrides[get_current_claims] = _claims_with(
        actor.id,
        [
            "iam.role.manage",
            "iam.role.read",
            "iam.service.manage",
            "iam.permission.manage",
            "iam.user.update",
            "iam.audit.read",
        ],
    )
    yield actor


@pytest_asyncio.fixture
async def reader_only(client, actor):
    app.dependency_overrides[get_current_claims] = _claims_with(
        actor.id, ["iam.user.read"]
    )
    yield actor


@pytest_asyncio.fixture
async def existing_role(db):
    r = Role(name="member")
    db.add(r)
    await db.commit()
    return r


async def _audit_count(db, **filters) -> int:
    stmt = select(AuditLog)
    for k, v in filters.items():
        stmt = stmt.where(getattr(AuditLog, k) == v)
    rows = (await db.scalars(stmt)).all()
    return len(rows)


async def test_role_create_records_audit(client, db, actor_admin):
    res = await client.post("/v1/roles", json={"name": "auditor"})
    assert res.status_code == 201
    role_id = res.json()["id"]

    rows = (
        await db.scalars(
            select(AuditLog).where(
                AuditLog.action == "role.create",
                AuditLog.target_id == str(role_id),
            )
        )
    ).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.actor_id == actor_admin.id
    assert row.target_type == "role"
    assert row.meta == {"name": "auditor"}


async def test_role_update_records_old_and_new_name(
    client, db, actor_admin, existing_role
):
    res = await client.patch(
        f"/v1/roles/{existing_role.id}", json={"name": "renamed"}
    )
    assert res.status_code == 200

    row = await db.scalar(
        select(AuditLog).where(AuditLog.action == "role.update")
    )
    assert row.meta == {"old_name": "member", "new_name": "renamed"}


async def test_role_delete_records_audit(client, db, actor_admin, existing_role):
    res = await client.delete(f"/v1/roles/{existing_role.id}")
    assert res.status_code == 204

    row = await db.scalar(
        select(AuditLog).where(AuditLog.action == "role.delete")
    )
    assert row is not None
    assert row.target_id == str(existing_role.id)


async def test_service_create_records_audit(client, db, actor_admin):
    res = await client.post("/v1/services", json={"name": "billing"})
    assert res.status_code == 201
    assert await _audit_count(db, action="service.create") == 1


async def test_failed_mutation_writes_no_audit(client, db, actor_admin, existing_role):
    res = await client.post("/v1/roles", json={"name": existing_role.name})
    assert res.status_code == 409
    await db.rollback()
    assert await _audit_count(db, action="role.create") == 0


async def test_audit_endpoint_lists_rows(client, db, actor_admin, existing_role):
    await client.patch(f"/v1/roles/{existing_role.id}", json={"name": "xy"})

    res = await client.get("/v1/audit-logs")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert body["items"][0]["action"] == "role.update"


async def test_audit_endpoint_filters_by_action(client, db, actor_admin):
    await client.post("/v1/roles", json={"name": "r1"})
    await client.post("/v1/services", json={"name": "s1"})

    res = await client.get("/v1/audit-logs", params={"action": "role.create"})
    assert res.status_code == 200
    actions = {item["action"] for item in res.json()["items"]}
    assert actions == {"role.create"}


async def test_audit_endpoint_requires_permission(client, reader_only):
    res = await client.get("/v1/audit-logs")
    assert res.status_code == 403


async def test_audit_endpoint_resolves_actor_email(client, db, actor_admin, existing_role):
    await client.patch(f"/v1/roles/{existing_role.id}", json={"name": "xy"})

    item = (await client.get("/v1/audit-logs")).json()["items"][0]
    assert item["actor_id"] == actor_admin.id
    assert item["actor_email"] == "actor@x.com"
    # role target is not a user → no email, raw id kept
    assert item["target_type"] == "role"
    assert item["target_email"] is None
    assert item["target_id"] == str(existing_role.id)


async def test_audit_endpoint_resolves_user_target_email(
    client, db, actor_admin, existing_role
):
    target = User(email="target@x.com", password=hash_password("!Qwer123"))
    db.add(target)
    await db.commit()

    res = await client.patch(
        f"/v1/users/{target.id}", json={"role_id": existing_role.id}
    )
    assert res.status_code == 200

    item = (
        await client.get("/v1/audit-logs", params={"action": "user.role_changed"})
    ).json()["items"][0]
    assert item["target_type"] == "user"
    assert item["target_id"] == target.id
    assert item["target_email"] == "target@x.com"
