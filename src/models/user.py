from __future__ import annotations
from typing import TYPE_CHECKING
from uuid import uuid4
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.role import Role
    from src.models.oauth_account import OauthAccount


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password: Mapped[str | None] = mapped_column(String(255))
    role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"))

    role: Mapped[Role | None] = relationship(back_populates="users")
    oauth_accounts: Mapped[list[OauthAccount]] = relationship(back_populates="user")

    @property
    def role_name(self) -> str | None:
        return self.role.name if self.role else None
