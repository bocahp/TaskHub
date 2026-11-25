from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.database import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from app.domain.enums import TaskPriority, TaskStatus
from app.domain.pagination import PaginatedResult
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

    async def list_by_project(
        self,
        project_id: UUID,
        *,
        offset: int = 0,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> list[Task]:
        statement = (
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.created_at.desc(), Task.id.asc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.scalars(statement)

        return list(result.all())

    async def paginate_by_project(
        self,
        project_id: UUID,
        *,
        page: int = DEFAULT_PAGE,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> PaginatedResult[Task]:
        count_statement = (
            select(func.count()).select_from(Task).where(Task.project_id == project_id)
        )

        total = await self.session.scalar(count_statement)

        items = await self.list_by_project(
            project_id,
            offset=(page - 1) * limit,
            limit=limit,
        )

        return PaginatedResult(
            items=items,
            total=total or 0,
            page=page,
            limit=limit,
        )
