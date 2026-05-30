import pytest
from src.app import app
from src.lib.deps import get_current_claims

ROLES = "v1/roles"


@pytest.fixture
def role(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "super_admin",
        "permissions": ["iam.role.read", "iam.role.manage"],
    }

    class Role:
        async def post_role(self, role):
            return await client.post(ROLES, json={"name": role})

    return Role()


@pytest.fixture
def role_wrong(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "user",
        "permissions": ["iam.role.read"],
    }

    class Role:
        async def post_role(self, role):
            return await client.post(ROLES, json={"name": role})

    return Role()


@pytest.fixture
def role_no_auth(client):

    class Role:
        async def post_role(self, role):
            return await client.post(ROLES, json={"name": role})

    return Role()


async def test_create_role(role):
    assert (await role.post_role("admin")).status_code == 201


async def test_create_duplicate_role_conflict(role):
    assert (await role.post_role("admin")).status_code == 201
    assert (await role.post_role("admin")).status_code == 409


async def test_create_role_missing_permission_forbidden(role_wrong):
    assert (await role_wrong.post_role("admin")).status_code == 403


async def test_create_role_missing_token_unauthorized(role_no_auth):
    assert (await role_no_auth.post_role("admin")).status_code == 401
