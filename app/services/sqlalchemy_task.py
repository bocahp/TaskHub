from collections.abc import Awaitable, Mapping
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.constants.messages import (
    DATABASE_CONFLICT,
    PROJECT_NOT_FOUND,
    TASK_NOT_FOUND,
    USER_NOT_FOUND,
)
from app.core.exceptions import ConflictException, NotFoundException
from app.domain.enums import TaskPriority, TaskStatus
from app.domain.pagination import PaginatedResult
from app.models.task import Task
from app.repositories.sqlalchemy_task import SQLAlchemyTaskRepository


class SQLAlchemyTaskService:
    def __init__(self, repository: SQLAlchemyTaskRepository) -> None:
        self.repository = repository

    async def _write[ResultT](
        self,
        operation: Awaitable[ResultT],
    ) -> ResultT:
        try:
            result = await operation
            await self.repository.session.commit()
            return result
        except IntegrityError as exc:
            await self.repository.session.rollback()
            raise ConflictException(DATABASE_CONFLICT) from exc
        except Exception:
            await self.repository.session.rollback()
            raise

    async def create_task(
        self,
        *,
        project_id: UUID,
        created_by: UUID,
        title: str,
        description: str | None = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: TaskPriority = TaskPriority.MEDIUM,
        assignee_id: UUID | None = None,
        due_date: datetime | None = None,
    ) -> Task:
        if not await self.repository.project_exists(project_id):
            raise NotFoundException(PROJECT_NOT_FOUND)

        if not await self.repository.user_exists(created_by):
            raise NotFoundException(USER_NOT_FOUND)

        if assignee_id is not None:
            if not await self.repository.user_exists(assignee_id):
                raise NotFoundException(USER_NOT_FOUND)

        return await self._write(
            self.repository.create_task(
                project_id=project_id,
                created_by=created_by,
                title=title,
                description=description,
                status=status,
                priority=priority,
                assignee_id=assignee_id,
                due_date=due_date,
            )
        )

    async def get_task(self, task_id: UUID) -> Task:
        task = await self.repository.get_by_id(task_id)

        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)

        return task

    async def list_tasks(
        self,
        project_id: UUID,
        *,
        page: int,
        limit: int,
    ) -> PaginatedResult[Task]:
        if not await self.repository.project_exists(project_id):
            raise NotFoundException(PROJECT_NOT_FOUND)

        return await self.repository.paginate_by_project(
            project_id,
            page=page,
            limit=limit,
        )

    async def update_task(
        self,
        task_id: UUID,
        changes: Mapping[str, object],
    ) -> Task:
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

        return await self._write(self.repository.update(task))

    async def delete_task(self, task_id: UUID) -> None:
        task = await self.get_task(task_id)

        await self._write(self.repository.delete(task))
