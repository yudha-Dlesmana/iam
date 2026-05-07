from src.models.user import User

async def test_returns_admin_and_demo_when_both_exist(db_session, user_repo):
    db_session.add(User(email="user@starter.com", password="x"))
    db_session.add(User(email="super_admin@starter.com", password="x"))
    db_session.add(User(email="other@starter.com", password="x"))
    await db_session.flush()

    result = await user_repo.get_admin_and_demo_users()

    emails = {u.email for u in result}
    assert emails == {'super_admin@starter.com', 'user@starter.com'}

async def test_returns_admin_or_demo_when_one_exist(db_session, user_repo):
    db_session.add(User(email="user@starter.com", password="x"))
    db_session.add(User(email="other@starter.com", password="x"))
    await db_session.flush()

    result = await user_repo.get_admin_and_demo_users()

    emails = {u.email for u in result}
    assert emails == {"user@starter.com"}

async def test_return_none_when_not_exist(db_session, user_repo):
    db_session.add(User(email="other1@starter.com", password="x"))
    db_session.add(User(email="other2@starter.com", password="x"))
    await db_session.flush()

    result = await user_repo.get_admin_and_demo_users()

    emails = {u.email for u in result}
    assert len(result) == 0

async def test_return_none_when_data_is_not_exist(db_session, user_repo):
    result = await user_repo.get_admin_and_demo_users()

    emails = {u.email for u in result}
    assert len(result) == 0
