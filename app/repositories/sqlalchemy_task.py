from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.domain.enums import TaskPriority, TaskStatus
from app.domain.pagination import PaginatedResult, PaginationParams
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository


class SQLAlchemyTaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Task)

    async def get_project(
        self,
        project_id: UUID,
    ) -> Project | None:
        return await self.session.get(Project, project_id)

    async def project_exists(self, project_id: UUID) -> bool:
        return await self.get_project(project_id) is not None

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def user_exists(self, user_id: UUID) -> bool:
        return await self.get_user(user_id) is not None

    async def get_workspace_membership(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMember | None:
        statement = (
            select(WorkspaceMember)
            .join(
                Project,
                Project.workspace_id == WorkspaceMember.workspace_id,
            )
            .where(
                Project.id == project_id,
                WorkspaceMember.user_id == user_id,
            )
        )

        result = await self.session.scalars(statement)

        return result.one_or_none()

    async def get_project_access_context(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> tuple[Project, WorkspaceMember | None] | None:
        statement = (
            select(Project, WorkspaceMember)
            .outerjoin(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == Project.workspace_id)
                & (WorkspaceMember.user_id == user_id),
            )
            .where(Project.id == project_id)
        )

        result = await self.session.execute(statement)
        row = result.one_or_none()

        if row is None:
            return None

        project, membership = row

        return project, membership

    async def get_task_access_context(
        self,
        task_id: UUID,
        user_id: UUID,
    ) -> tuple[Task, Project, WorkspaceMember | None] | None:
        statement = (
            select(Task, Project, WorkspaceMember)
            .join(
                Project,
                Project.id == Task.project_id,
            )
            .outerjoin(
                WorkspaceMember,
                (WorkspaceMember.workspace_id == Project.workspace_id)
                & (WorkspaceMember.user_id == user_id),
            )
            .where(Task.id == task_id)
        )

        result = await self.session.execute(statement)
        row = result.one_or_none()

        if row is None:
            return None

        task, project, membership = row

        return task, project, membership

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
        return await self.create(
            {
                "project_id": project_id,
                "created_by": created_by,
                "title": title,
                "description": description,
                "status": status,
                "priority": priority,
                "assignee_id": assignee_id,
                "due_date": due_date,
            }
        )

    async def paginate_by_project(
        self,
        project_id: UUID,
        *,
        pagination: PaginationParams,
        statuses: Sequence[TaskStatus] | None = None,
        priorities: Sequence[TaskPriority] | None = None,
        assignee_ids: Sequence[UUID] | None = None,
    ) -> PaginatedResult[Task]:
        filters: list[ColumnElement[bool]] = [
            Task.project_id == project_id,
        ]

        if statuses is not None:
            filters.append(Task.status.in_(statuses))

        if priorities is not None:
            filters.append(Task.priority.in_(priorities))

        if assignee_ids is not None:
            filters.append(Task.assignee_id.in_(assignee_ids))

        return await self.paginate(
            pagination=pagination,
            order_by=(
                Task.created_at.desc(),
                Task.id.asc(),
            ),
            filters=filters,
        )
