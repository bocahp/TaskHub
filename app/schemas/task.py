from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.constants.task import (
    TASK_DESCRIPTION_MAX_LENGTH,
    TASK_TITLE_MAX_LENGTH,
    TASK_TITLE_MIN_LENGTH,
)
from app.domain.enums import TaskPriority, TaskStatus
from app.schemas.base import BaseSchema


class TaskCreate(BaseSchema):
    title: str = Field(
        min_length=TASK_TITLE_MIN_LENGTH,
        max_length=TASK_TITLE_MAX_LENGTH,
    )

    description: str | None = Field(
        default=None,
        max_length=TASK_DESCRIPTION_MAX_LENGTH,
    )

    status: TaskStatus = TaskStatus.TODO
    priority: TaskPriority = TaskPriority.MEDIUM

    assignee_id: UUID | None = None
    due_date: datetime | None = None

    @field_validator("due_date")
    @classmethod
    def validate_due_date_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("due_date must include a timezone")

        return value


class TaskUpdate(BaseSchema):
    title: str | None = Field(
        default=None,
        min_length=TASK_TITLE_MIN_LENGTH,
        max_length=TASK_TITLE_MAX_LENGTH,
    )

    description: str | None = Field(
        default=None,
        max_length=TASK_DESCRIPTION_MAX_LENGTH,
    )

    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: UUID | None = None
    due_date: datetime | None = None

    @field_validator("title", "status", "priority", mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, value: object) -> object:
        if value is None:
            raise ValueError("This field cannot be null")

        return value

    @model_validator(mode="after")
    def validate_not_empty(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        return self

    @field_validator("due_date")
    @classmethod
    def validate_due_date_timezone(
        cls,
        value: datetime | None,
    ) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("due_date must include a timezone")

        return value


class TaskResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    created_by: UUID
    assignee_id: UUID | None
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_at: datetime
