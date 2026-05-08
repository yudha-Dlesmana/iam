import uuid

import pytest
import pytest_asyncio
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.schemas.user_schema import UserCreateRequest, UserUpdateRequest


@pytest_asyncio.fixture(loop_scope="session")
async def user_repo(db_session: AsyncSession):
    return UserRepository(db_session)


# get_all_users

async def test_get_all_users_returns_empty_when_no_users(db_session, user_repo):
    result = await user_repo.get_all_users()

    assert result == []


async def test_get_all_users_returns_all_existing_users(db_session, user_repo):
    db_session.add(User(email="a@starter.com", password="x"))
    db_session.add(User(email="b@starter.com", password="x"))
    db_session.add(User(email="c@starter.com", password="x"))
    await db_session.flush()

    result = await user_repo.get_all_users()

    emails = {u.email for u in result}
    assert emails == {"a@starter.com", "b@starter.com", "c@starter.com"}


# get_admin_and_demo_users

async def test_returns_admin_and_demo_when_both_exist(db_session, user_repo):
    db_session.add(User(email="user@starter.com", password="x"))
    db_session.add(User(email="super_admin@starter.com", password="x"))
    db_session.add(User(email="other@starter.com", password="x"))
    await db_session.flush()

    result = await user_repo.get_admin_and_demo_users()

    emails = {u.email for u in result}
    assert emails == {"super_admin@starter.com", "user@starter.com"}


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

    assert len(result) == 0


async def test_return_none_when_data_is_not_exist(db_session, user_repo):
    result = await user_repo.get_admin_and_demo_users()

    assert len(result) == 0


# get_user_by_id

async def test_get_user_by_id_returns_user_when_exists(db_session, user_repo):
    user = User(email="found@starter.com", password="x")
    db_session.add(user)
    await db_session.flush()

    result = await user_repo.get_user_by_id(user.id)

    assert result is not None
    assert result.id == user.id
    assert result.email == "found@starter.com"


async def test_get_user_by_id_returns_none_when_not_exists(db_session, user_repo):
    result = await user_repo.get_user_by_id(str(uuid.uuid4()))

    assert result is None


# get_user_by_email

async def test_get_user_by_email_returns_user_when_exists(db_session, user_repo):
    user = User(email="search@starter.com", password="x")
    db_session.add(user)
    await db_session.flush()

    result = await user_repo.get_user_by_email("search@starter.com")

    assert result is not None
    assert result.email == "search@starter.com"


async def test_get_user_by_email_returns_none_when_not_exists(db_session, user_repo):
    result = await user_repo.get_user_by_email("missing@starter.com")

    assert result is None


# create_user

async def test_create_user_persists_and_returns_user(db_session, user_repo):
    request = UserCreateRequest(
        email="new@starter.com",
        password="Passw0rd!",
        role_id=None,
    )

    result = await user_repo.create_user(request)

    assert result.id is not None
    assert result.email == "new@starter.com"
    assert result.password == "Passw0rd!"
    assert result.role_id is None

    fetched = await user_repo.get_user_by_email("new@starter.com")
    assert fetched is not None
    assert fetched.id == result.id


async def test_create_user_with_role_id(db_session, user_repo):
    request = UserCreateRequest(
        email="role@starter.com",
        password="Passw0rd!",
        role_id=None,
    )

    result = await user_repo.create_user(request)

    assert result.email == "role@starter.com"
    assert result.id is not None


async def test_create_user_raises_when_email_already_exists(db_session, user_repo):
    db_session.add(User(email="dup@starter.com", password="x"))
    await db_session.flush()

    request = UserCreateRequest(
        email="dup@starter.com",
        password="Passw0rd!",
        role_id=None,
    )

    with pytest.raises(IntegrityError):
        await user_repo.create_user(request)


# update_user

async def test_update_user_changes_only_provided_fields(db_session, user_repo):
    user = User(email="upd@starter.com", password="oldpass", role_id=None)
    db_session.add(user)
    await db_session.flush()

    request = UserUpdateRequest(password="Newpass1!")
    result = await user_repo.update_user(user.id, request)

    assert result is not None
    assert result.password == "Newpass1!"
    assert result.email == "upd@starter.com"


async def test_update_user_excludes_none_fields(db_session, user_repo):
    user = User(email="excl@starter.com", password="origpass", role_id=None)
    db_session.add(user)
    await db_session.flush()

    request = UserUpdateRequest(password="Brandnew1!", role_id=None)
    result = await user_repo.update_user(user.id, request)

    assert result is not None
    assert result.password == "Brandnew1!"
    assert result.email == "excl@starter.com"


async def test_update_user_returns_none_when_user_not_exists(db_session, user_repo):
    request = UserUpdateRequest(password="Newpass1!")
    result = await user_repo.update_user(str(uuid.uuid4()), request)

    assert result is None


# delete_user

async def test_delete_user_returns_true_when_exists(db_session, user_repo):
    user = User(email="del@starter.com", password="x")
    db_session.add(user)
    await db_session.flush()

    result = await user_repo.delete_user(user.id)

    assert result is True
    fetched = await user_repo.get_user_by_id(user.id)
    assert fetched is None


async def test_delete_user_returns_false_when_not_exists(db_session, user_repo):
    result = await user_repo.delete_user(str(uuid.uuid4()))

    assert result is False
