async def test_create_role(role):
    assert (await role.post_role("admin")).status_code == 201


async def test_create_duplicate_role_conflict(role):
    assert (await role.post_role("admin")).status_code == 201
    assert (await role.post_role("admin")).status_code == 409
