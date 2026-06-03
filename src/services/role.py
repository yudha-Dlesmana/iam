from sqlalchemy.exc import IntegrityError
from src.models import Role
from src.schemas.role import RoleRequest
from src.repositories.role import RoleRepository
from src.repositories.permission import PermissionRepository
from src.exceptions.base import NotFoundError, ConflictError, ValidationError
from src.lib.audit import record as audit
from src.lib.db_errors import is_check_violation, is_unique_violation


class RoleService:
    def __init__(self, repo: RoleRepository, permission_repo: PermissionRepository):
        self.repo = repo
        self.perm_repo = permission_repo

    @staticmethod
    def _save_error(e: IntegrityError) -> Exception:
        if is_unique_violation(e):
            return ConflictError("role already exists")
        if is_check_violation(e, "role_name_no_whitespace"):
            return ValidationError("role must not contain whitespace")
        return e

    async def get(self, id: int) -> Role:
        role = await self.repo.get_by_id(id)
        if not role:
            raise NotFoundError("role not found")
        return role

    async def get_with_permissions(self, id: int) -> Role:
        role = await self.repo.get_by_id_with_permission(id)
        if not role:
            raise NotFoundError("role not found")
        return role

    async def get_all_paginated(
        self, limit: int = 10, offset: int = 0, name_like: str | None = None
    ) -> tuple[list[Role], int]:
        items = await self.repo.get_all(limit, offset, name_like)
        total = await self.repo.count(name_like)
        return items, total

    async def create(self, data: RoleRequest) -> Role:
        try:
            role = await self.repo.save(Role(name=data.name))
        except IntegrityError as e:
            raise self._save_error(e) from e
        await audit(self.repo.session, "role.create", "role", role.id, {"name": role.name})
        return role

    async def update(self, id: int, data: RoleRequest) -> Role:
        role = await self.get(id)
        old_name = role.name
        role.name = data.name

        try:
            role = await self.repo.save(role)
        except IntegrityError as e:
            raise self._save_error(e) from e
        await audit(
            self.repo.session,
            "role.update",
            "role",
            role.id,
            {"old_name": old_name, "new_name": role.name},
        )
        return role

    async def delete(self, id: int) -> None:
        role = await self.get(id)
        snapshot = {"name": role.name}

        try:
            await self.repo.delete(role)
        except IntegrityError:
            raise ConflictError("role still referenced by users")
        await audit(self.repo.session, "role.delete", "role", id, snapshot)

    async def add_permissions(self, role_id: int, permission_ids: list[int]) -> Role:
        role = await self.repo.get_by_id_with_permission(role_id)
        if not role:
            raise NotFoundError("role not found")

        perms = await self.perm_repo.get_by_ids(permission_ids)
        found = {p.id for p in perms}
        missing = set(permission_ids) - found
        if missing:
            raise NotFoundError(f"permission not found: {sorted(missing)}")
        existing = {p.id for p in role.permissions}
        for p in perms:
            if p.id not in existing:
                role.permissions.append(p)

        await self.repo.save(role)
        await audit(
            self.repo.session,
            "role.add_permissions",
            "role",
            role_id,
            {"permission_ids": sorted(permission_ids)},
        )
        return await self.repo.get_by_id_with_permission(role_id)

    async def remove_permission(self, role_id: int, permission_id: int) -> Role:
        role = await self.repo.get_by_id_with_permission(role_id)
        if not role:
            raise NotFoundError("role not found")

        role.permissions = [p for p in role.permissions if p.id != permission_id]
        await self.repo.save(role)
        await audit(
            self.repo.session,
            "role.remove_permission",
            "role",
            role_id,
            {"permission_id": permission_id},
        )
        return await self.repo.get_by_id_with_permission(role_id)
