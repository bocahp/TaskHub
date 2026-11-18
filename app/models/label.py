from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants.database import (
    LABEL_COLOR_MAX_LENGTH,
    LABEL_NAME_MAX_LENGTH,
)
from app.db.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task_label import TaskLabel


class Label(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "labels"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "name",
            name="uq_labels_project_id_name",
        ),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(LABEL_NAME_MAX_LENGTH),
        nullable=False,
    )

    color: Mapped[str] = mapped_column(
        String(LABEL_COLOR_MAX_LENGTH),
        nullable=False,
    )

    project: Mapped[Project] = relationship(
        back_populates="labels",
        lazy="raise",
    )

    task_labels: Mapped[list[TaskLabel]] = relationship(
        back_populates="label",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
