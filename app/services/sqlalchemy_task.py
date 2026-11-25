from collections.abc import Awaitable, Mapping, Sequence
from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.constants.messages import (
    ACCOUNT_INACTIVE,
    DATABASE_CONFLICT,
    PROJECT_ARCHIVED,
    PROJECT_NOT_FOUND,
    TASK_ASSIGNEE_NOT_MEMBER,
    TASK_MODIFICATION_FORBIDDEN,
    TASK_NOT_FOUND,
    USER_NOT_FOUND,
)
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
    UnprocessableEntityException,
)
from app.domain.enums import (
    ProjectStatus,
    TaskPriority,
    TaskStatus,
    UserRole,
    WorkspaceRole,
)
from app.domain.pagination import PaginatedResult, PaginationParams
from app.models.project import Project
from app.models.task import Task
from app.models.workspace_member import WorkspaceMember
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

    async def _require_active_user(self, user_id: UUID) -> None:
        user = await self.repository.get_user(user_id)

        if user is None:
            raise NotFoundException(USER_NOT_FOUND)

        if not user.is_active:
            raise ConflictException(ACCOUNT_INACTIVE)

    async def _get_project_access_context(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> tuple[Project, WorkspaceMember | None]:
        context = await self.repository.get_project_access_context(
            project_id,
            user_id,
        )

        if context is None:
            raise NotFoundException(PROJECT_NOT_FOUND)

        return context

    async def _get_task_access_context(
        self,
        task_id: UUID,
        user_id: UUID,
    ) -> tuple[Task, Project, WorkspaceMember | None]:
        context = await self.repository.get_task_access_context(
            task_id,
            user_id,
        )

        if context is None:
            raise NotFoundException(TASK_NOT_FOUND)

        return context

    @staticmethod
    def _authorize_project_access(
        project: Project,
        membership: WorkspaceMember | None,
        current_user_role: UserRole,
        *,
        write: bool = False,
        not_found_message: str = PROJECT_NOT_FOUND,
    ) -> None:
        if current_user_role != UserRole.ADMIN:
            if membership is None:
                raise NotFoundException(not_found_message)

            if write and membership.role not in (
                WorkspaceRole.OWNER,
                WorkspaceRole.EDITOR,
            ):
                raise ForbiddenException(TASK_MODIFICATION_FORBIDDEN)

        if write and project.status != ProjectStatus.ACTIVE:
            raise ConflictException(PROJECT_ARCHIVED)

    async def _validate_assignee(
        self,
        project_id: UUID,
        assignee_id: UUID,
    ) -> None:
        await self._require_active_user(assignee_id)

        membership = await self.repository.get_workspace_membership(
            project_id,
            assignee_id,
        )

        if membership is None:
            raise UnprocessableEntityException(TASK_ASSIGNEE_NOT_MEMBER)

    async def create_task(
        self,
        *,
        project_id: UUID,
        current_user_id: UUID,
        current_user_role: UserRole,
        title: str,
        description: str | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        assignee_id: UUID | None = None,
        due_date: datetime | None = None,
    ) -> Task:
        async def operation() -> Task:
            project, membership = await self._get_project_access_context(
                project_id,
                current_user_id,
            )

            self._authorize_project_access(
                project,
                membership,
                current_user_role,
                write=True,
            )

            if assignee_id is not None:
                await self._validate_assignee(project_id, assignee_id)

            if assignee_id is not None:
                await self._validate_assignee(project_id, assignee_id)

            return await self.repository.create_task(
                project_id=project_id,
                created_by=current_user_id,
                title=title,
                description=description,
                status=TaskStatus.TODO,
                priority=priority,
                assignee_id=assignee_id,
                due_date=due_date,
            )

        return await self._write(operation())

    async def get_task(
        self,
        task_id: UUID,
        *,
        current_user_id: UUID,
        current_user_role: UserRole,
    ) -> Task:
        task, project, membership = await self._get_task_access_context(
            task_id,
            current_user_id,
        )

        self._authorize_project_access(
            project,
            membership,
            current_user_role,
            not_found_message=TASK_NOT_FOUND,
        )

        return task

    async def list_tasks(
        self,
        project_id: UUID,
        *,
        pagination: PaginationParams,
        current_user_id: UUID,
        current_user_role: UserRole,
        statuses: Sequence[TaskStatus] | None = None,
        priorities: Sequence[TaskPriority] | None = None,
        assignee_ids: Sequence[UUID] | None = None,
    ) -> PaginatedResult[Task]:
        project, membership = await self._get_project_access_context(
            project_id,
            current_user_id,
        )

        self._authorize_project_access(
            project,
            membership,
            current_user_role,
        )

        return await self.repository.paginate_by_project(
            project_id,
            pagination=pagination,
            statuses=statuses,
            priorities=priorities,
            assignee_ids=assignee_ids,
        )

    async def update_task(
        self,
        task_id: UUID,
        changes: Mapping[str, object],
        *,
        current_user_id: UUID,
        current_user_role: UserRole,
    ) -> Task:
        async def operation() -> Task:
            task, project, membership = await self._get_task_access_context(
                task_id,
                current_user_id,
            )

            self._authorize_project_access(
                project,
                membership,
                current_user_role,
                write=True,
                not_found_message=TASK_NOT_FOUND,
            )

            if "assignee_id" in changes:
                assignee_id = cast(UUID | None, changes["assignee_id"])

                if assignee_id is not None:
                    await self._validate_assignee(
                        task.project_id,
                        assignee_id,
                    )

                task.assignee_id = assignee_id

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

            if "due_date" in changes:
                task.due_date = cast(
                    datetime | None,
                    changes["due_date"],
                )

            return await self.repository.update(task)

        return await self._write(operation())

    async def delete_task(
        self,
        task_id: UUID,
        *,
        current_user_id: UUID,
        current_user_role: UserRole,
    ) -> None:
        async def operation() -> None:
            task, project, membership = await self._get_task_access_context(
                task_id,
                current_user_id,
            )

            self._authorize_project_access(
                project,
                membership,
                current_user_role,
                write=True,
                not_found_message=TASK_NOT_FOUND,
            )

            await self.repository.delete(task)

        await self._write(operation())
