from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.database import COMMENT_CONTENT_MAX_LENGTH
from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


class Comment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "comments"

    task_id: Mapped[UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(
        String(COMMENT_CONTENT_MAX_LENGTH),
        nullable=False,
    )

    task: Mapped[Task] = relationship(
        back_populates="comments",
        lazy="raise",
    )

    author: Mapped[User] = relationship(
        back_populates="authored_comments",
        lazy="raise",
    )
