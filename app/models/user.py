from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.database import (
    EMAIL_MAX_LENGTH,
    FULL_NAME_MAX_LENGTH,
    PASSWORD_HASH_MAX_LENGTH,
)
from app.db.base import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.task import Task
    from app.models.workspace import Workspace
    from app.models.workspace_member import WorkspaceMember


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(EMAIL_MAX_LENGTH),
        unique=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(FULL_NAME_MAX_LENGTH),
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(PASSWORD_HASH_MAX_LENGTH),
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=UserRole.MEMBER,
        server_default=text("'MEMBER'"),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    token_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    owned_workspaces: Mapped[list[Workspace]] = relationship(
        back_populates="owner",
        passive_deletes="all",
        lazy="raise",
    )

    workspace_memberships: Mapped[list[WorkspaceMember]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )

    assigned_tasks: Mapped[list[Task]] = relationship(
        back_populates="assignee",
        foreign_keys="[Task.assignee_id]",
        passive_deletes="all",
        lazy="raise",
    )

    created_tasks: Mapped[list[Task]] = relationship(
        back_populates="creator",
        foreign_keys="[Task.created_by]",
        passive_deletes="all",
        lazy="raise",
    )

    authored_comments: Mapped[list[Comment]] = relationship(
        back_populates="author",
        passive_deletes="all",
        lazy="raise",
    )
