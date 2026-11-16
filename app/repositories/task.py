from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from app.domain.task import TaskEntity, TaskPriority, TaskStatus


class TaskRepository(Protocol):
    async def create(
        self,
        *,
        title: str,
        description: str | None,
        status: TaskStatus,
        priority: TaskPriority,
    ) -> TaskEntity: ...

    async def get_by_id(self, task_id: UUID) -> TaskEntity | None: ...

    async def list_all(self) -> list[TaskEntity]: ...

    async def update(self, task: TaskEntity) -> TaskEntity: ...

    async def delete(self, task_id: UUID) -> None: ...


class InMemoryTaskRepository:
    def __init__(self) -> None:
        self._tasks: dict[UUID, TaskEntity] = {}

    async def create(
        self,
        *,
        title: str,
        description: str | None,
        status: TaskStatus,
        priority: TaskPriority,
    ) -> TaskEntity:
        task = TaskEntity(
            id=uuid4(),
            title=title,
            description=description,
            status=status,
            priority=priority,
            created_at=datetime.now(UTC),
        )

        self._tasks[task.id] = task

        return task

    async def get_by_id(self, task_id: UUID) -> TaskEntity | None:
        return self._tasks.get(task_id)

    async def list_all(self) -> list[TaskEntity]:
        return list(self._tasks.values())

    async def update(self, task: TaskEntity) -> TaskEntity:
        self._tasks[task.id] = task

        return task

    async def delete(self, task_id: UUID) -> None:
        self._tasks.pop(task_id, None)
