from collections.abc import Mapping
from typing import cast
from uuid import UUID

from app.constants.messages import TASK_NOT_FOUND
from app.core.exceptions import NotFoundException
from app.domain.task import TaskEntity, TaskPriority, TaskStatus
from app.repositories.task import TaskRepository


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    async def create_task(
        self,
        *,
        title: str,
        description: str | None,
        status: TaskStatus,
        priority: TaskPriority,
    ) -> TaskEntity:
        return await self.repository.create(
            title=title,
            description=description,
            status=status,
            priority=priority,
        )

    async def list_tasks(
        self,
        *,
        skip: int,
        limit: int,
    ) -> list[TaskEntity]:
        tasks = await self.repository.list_all()

        return tasks[skip : skip + limit]

    async def get_task(self, task_id: UUID) -> TaskEntity:
        task = await self.repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)

        return task

    async def update_task(
        self,
        task_id: UUID,
        changes: Mapping[str, object],
    ) -> TaskEntity:
        task = await self.get_task(task_id)

        if "title" in changes:
            task.title = cast(str, changes["title"])

        if "description" in changes:
            task.description = cast(
                str | None,
                changes["description"],
            )

        if "status" in changes:
            task.status = cast(TaskStatus, changes["status"])

        if "priority" in changes:
            task.priority = cast(TaskPriority, changes["priority"])

        return await self.repository.update(task)

    async def delete_task(self, task_id: UUID) -> None:
        task = await self.get_task(task_id)

        await self.repository.delete(task.id)
