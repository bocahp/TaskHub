from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.enums import TaskPriority, TaskStatus


@dataclass(slots=True)
class TaskEntity:
    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    created_at: datetime
