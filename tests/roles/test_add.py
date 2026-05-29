async def test_create_role(role):
    assert (await role.post_role("admin")).status_code == 201


async def test_create_duplicate_role_conflict(role):
    assert (await role.post_role("admin")).status_code == 201
    assert (await role.post_role("admin")).status_code == 409


async def test_create_role_wrong_role_forbidden(role_wrong):
    assert (await role_wrong.post_role("admin")).status_code == 403


async def test_create_role_missing_token_unauthorized(role_no_auth):
    assert (await role_no_auth.post_role("admin")).status_code == 401
