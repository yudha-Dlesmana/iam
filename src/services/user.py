from redis.asyncio import Redis
from sqlalchemy.exc import IntegrityError

from src.models import User
from src.schemas.user import UserCreate, UserUpdate
from src.core.revocation import mark_revoked
from src.core.security import (
    hash_password,
    revoke_user as revoke_sessions,
    revoke_device,
    list_sessions,
)
from src.repositories.user import UserRepository
from src.exceptions.base import NotFoundError, ConflictError
from src.lib.audit import record as audit
from src.lib.db_errors import is_unique_violation, is_fk_violation


class UserService:
    def __init__(self, repo: UserRepository, redis: Redis):
        self.repo = repo
        self.redis = redis

    @staticmethod
    def _save_error(e: IntegrityError) -> Exception:
        if is_unique_violation(e):
            return ConflictError("email already exists")
        if is_fk_violation(e):
            return NotFoundError("role not found")
        return e

    async def get(self, id: str) -> User:
        user = await self.repo.get_by_id(id)
        if not user:
            raise NotFoundError("user not found")
        return user

    async def get_all_paginated(
        self, limit: int = 10, offset: int = 0, email_like: str | None = None
    ) -> tuple[list[User], int]:
        items = await self.repo.get_all(limit, offset, email_like)
        total = await self.repo.count(email_like)
        return items, total

    async def create(self, data: UserCreate) -> User:
        user = User(
            email=data.email,
            password=hash_password(data.password),
            role_id=data.role_id,
        )
        try:
            return await self.repo.save(user)
        except IntegrityError as e:
            raise self._save_error(e) from e

    async def update(self, id: str, data: UserUpdate) -> User:
        user = await self.get(id)
        old_role_id = user.role_id
        role_changed = (
            "role_id" in data.model_fields_set and data.role_id != old_role_id
        )
        if data.email:
            user.email = data.email
        if data.password:
            user.password = hash_password(data.password)
        if "role_id" in data.model_fields_set:
            user.role_id = data.role_id

        try:
            user = await self.repo.save(user)
        except IntegrityError as e:
            raise self._save_error(e) from e

        if role_changed:
            await audit(
                self.repo.session,
                "user.role_changed",
                "user",
                user.id,
                {"old_role_id": old_role_id, "new_role_id": user.role_id},
            )
        return user

    async def delete(self, id: str) -> None:
        user = await self.get(id)
        await mark_revoked(self.redis, user.id)
        await revoke_sessions(self.redis, user.id)
        await self.repo.delete(user)
        await audit(self.repo.session, "user.delete", "user", id, {"email": user.email})

    async def revoke_tokens(self, id: str) -> None:
        user = await self.get(id)
        await mark_revoked(self.redis, user.id)
        await revoke_sessions(self.redis, user.id)
        await audit(self.repo.session, "user.revoke_tokens", "user", user.id)

    async def sessions(self, id: str) -> list[dict]:
        user = await self.get(id)
        return await list_sessions(self.redis, user.id)

    async def revoke_session(self, id: str, device: str) -> None:
        user = await self.get(id)
        await revoke_device(self.redis, user.id, device)
        await audit(
            self.repo.session, "user.revoke_session", "user", user.id, {"device": device}
        )
