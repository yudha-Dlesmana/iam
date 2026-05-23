async def test_create_duplicate_role_conflict(role):
    assert (await role.post_role("admin")).status_code == 201
    assert (await role.post_role("admin")).status_code == 409
