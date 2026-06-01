import pytest

from src.app import app
from src.lib.deps import get_current_claims
from src.lib.pagination import MAX_PAGE_LIMIT


PERMS = [
    "iam.user.read",
    "iam.role.read",
    "iam.permission.read",
    "iam.service.read",
]


@pytest.fixture
def reader(client):
    app.dependency_overrides[get_current_claims] = lambda: {
        "sub": "1",
        "role": "viewer",
        "permissions": PERMS,
    }


PAGINATED = [
    "/v1/users",
    "/v1/roles",
    "/v1/permissions",
    "/v1/services",
]


@pytest.mark.parametrize("path", PAGINATED)
async def test_limit_above_cap_rejected(client, reader, path):
    res = await client.get(path, params={"limit": MAX_PAGE_LIMIT + 1})
    assert res.status_code == 422


@pytest.mark.parametrize("path", PAGINATED)
async def test_limit_at_cap_allowed(client, reader, path):
    res = await client.get(path, params={"limit": MAX_PAGE_LIMIT})
    assert res.status_code == 200


@pytest.mark.parametrize("path", PAGINATED)
async def test_limit_zero_rejected(client, reader, path):
    res = await client.get(path, params={"limit": 0})
    assert res.status_code == 422


@pytest.mark.parametrize("path", PAGINATED)
async def test_negative_offset_rejected(client, reader, path):
    res = await client.get(path, params={"offset": -1})
    assert res.status_code == 422
