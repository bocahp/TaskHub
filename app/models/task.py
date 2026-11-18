from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.task import (
    TASK_DESCRIPTION_MAX_LENGTH,
    TASK_TITLE_MAX_LENGTH,
)
from app.db.base import Base
from app.models.enums import TaskPriority, TaskStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.comment import Comment
    from app.models.project import Project
    from app.models.task_label import TaskLabel
    from app.models.user import User


class Task(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assignee_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(TASK_TITLE_MAX_LENGTH),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(TASK_DESCRIPTION_MAX_LENGTH),
        nullable=True,
    )

    status: Mapped[TaskStatus] = mapped_column(
        Enum(
            TaskStatus,
            name="task_status",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=TaskStatus.TODO,
        server_default=text("'TODO'"),
    )

    priority: Mapped[TaskPriority] = mapped_column(
        Enum(
            TaskPriority,
            name="task_priority",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=TaskPriority.MEDIUM,
        server_default=text("'MEDIUM'"),
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    project: Mapped[Project] = relationship(
        back_populates="tasks",
        lazy="raise",
    )

    assignee: Mapped[User | None] = relationship(
        back_populates="assigned_tasks",
        foreign_keys="[Task.assignee_id]",
        lazy="raise",
    )

    creator: Mapped[User] = relationship(
        back_populates="created_tasks",
        foreign_keys="[Task.created_by]",
        lazy="raise",
    )

    task_labels: Mapped[list[TaskLabel]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )

    comments: Mapped[list[Comment]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
