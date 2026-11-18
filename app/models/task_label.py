from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.label import Label
from app.models.task import Task


class TaskLabel(Base):
    __tablename__ = "task_labels"

    task_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )

    label_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("labels.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

    task: Mapped[Task] = relationship(
        back_populates="task_labels",
        lazy="raise",
    )

    label: Mapped[Label] = relationship(
        back_populates="task_labels",
        lazy="raise",
    )
