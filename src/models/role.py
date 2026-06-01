from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, String, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.user import User
    from src.models.permission import Permission


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    __table_args__ = (
        CheckConstraint(
            "name NOT REGEXP '[[:space:]]'", name="role_name_no_whitespace"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    single_session: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="0"
    )

    users: Mapped[list[User]] = relationship(
        back_populates="role",
        passive_deletes="all",
    )
    permissions: Mapped[list[Permission]] = relationship(
        secondary="role_permissions", back_populates="roles"
    )

    @property
    def permission_name(self) -> list[str]:
        return [p.name for p in self.permissions]
