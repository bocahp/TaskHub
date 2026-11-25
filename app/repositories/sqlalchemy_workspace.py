from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import WorkspaceRole
from app.domain.pagination import PaginatedResult, PaginationParams
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository


class SQLAlchemyWorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Workspace)

    async def create_workspace(
        self,
        *,
        name: str,
        owner_id: UUID,
    ) -> Workspace:
        return await self.create(
            {
                "name": name,
                "owner_id": owner_id,
            }
        )

    async def get_by_id_for_update(
        self,
        workspace_id: UUID,
    ) -> Workspace | None:
        statement = (
            select(Workspace)
            .where(Workspace.id == workspace_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        result = await self.session.scalars(statement)

        return result.one_or_none()

    async def paginate_for_user(
        self,
        user_id: UUID,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[Workspace]:
        filters = (
            Workspace.id.in_(
                select(WorkspaceMember.workspace_id).where(
                    WorkspaceMember.user_id == user_id,
                )
            ),
        )

        return await self.paginate(
            pagination=pagination,
            order_by=(
                Workspace.created_at.desc(),
                Workspace.id.asc(),
            ),
            filters=filters,
        )

    async def get_membership(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMember | None:
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )

        result = await self.session.scalars(statement)

        return result.one_or_none()

    async def paginate_members(
        self,
        workspace_id: UUID,
        *,
        pagination: PaginationParams,
    ) -> PaginatedResult[tuple[WorkspaceMember, User]]:
        count_statement = (
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )

        total = await self.session.scalar(count_statement)

        statement = (
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(User.full_name.asc(), User.id.asc())
            .offset(pagination.offset)
            .limit(pagination.limit)
        )

        result = await self.session.execute(statement)

        items = [(membership, user) for membership, user in result]

        return PaginatedResult(
            items=items,
            total=total or 0,
            page=pagination.page,
            limit=pagination.limit,
        )

    async def create_membership(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        role: WorkspaceRole = WorkspaceRole.VIEWER,
    ) -> WorkspaceMember:
        membership = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=user_id,
            role=role,
        )

        self.session.add(membership)

        await self.session.flush()
        await self.session.refresh(membership)

        return membership

    async def update_membership_role(
        self,
        membership: WorkspaceMember,
        role: WorkspaceRole,
    ) -> WorkspaceMember:
        membership.role = role

        await self.session.flush()
        await self.session.refresh(membership)

        return membership

    async def delete_membership(
        self,
        membership: WorkspaceMember,
    ) -> None:
        await self.session.delete(membership)
        await self.session.flush()
