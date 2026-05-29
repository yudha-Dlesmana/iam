from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.role import Role


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    roles: Mapped[list[Role]] = relationship(
        secondary="role_permissions", back_populates="permissions"
    )
