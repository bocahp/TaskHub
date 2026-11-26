from collections.abc import Mapping
from typing import cast
from uuid import UUID

from app.constants.messages import (
    TASK_ACCESS_FORBIDDEN,
    TASK_NOT_FOUND,
)
from app.core.exceptions import ForbiddenException, NotFoundException
from app.domain.enums import TaskPriority, TaskStatus, UserRole
from app.domain.task import TaskEntity
from app.repositories.task import TaskRepository


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self.repository = repository

    @staticmethod
    def _ensure_task_access(
        task: TaskEntity,
        *,
        current_user_id: UUID,
        current_user_role: UserRole,
    ) -> None:
        if current_user_role != UserRole.ADMIN and task.created_by != current_user_id:
            raise ForbiddenException(TASK_ACCESS_FORBIDDEN)

    async def create_task(
        self,
        *,
        created_by: UUID,
        title: str,
        description: str | None,
        status: TaskStatus,
        priority: TaskPriority,
    ) -> TaskEntity:
        return await self.repository.create(
            created_by=created_by,
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
        current_user_id: UUID,
        current_user_role: UserRole,
    ) -> list[TaskEntity]:
        if current_user_role == UserRole.ADMIN:
            tasks = await self.repository.list_all()
        else:
            tasks = await self.repository.list_by_creator(current_user_id)

        return tasks[skip : skip + limit]

    async def get_task(
        self,
        task_id: UUID,
        *,
        current_user_id: UUID,
        current_user_role: UserRole,
    ) -> TaskEntity:
        task = await self.repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)

        self._ensure_task_access(
            task,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

        return task

    async def update_task(
        self,
        task_id: UUID,
        changes: Mapping[str, object],
        *,
        current_user_id: UUID,
        current_user_role: UserRole,
    ) -> TaskEntity:
        task = await self.get_task(
            task_id,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

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

    async def delete_task(
        self,
        task_id: UUID,
        *,
        current_user_id: UUID,
        current_user_role: UserRole,
    ) -> None:
        task = await self.get_task(
            task_id,
            current_user_id=current_user_id,
            current_user_role=current_user_role,
        )

        await self.repository.delete(task.id)
