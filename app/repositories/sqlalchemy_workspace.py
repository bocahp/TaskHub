from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import WorkspaceRole
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

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Workspace]:
        statement = (
            select(Workspace)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.desc(), Workspace.id)
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.scalars(statement)

        return list(result.all())

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

    async def list_members(
        self,
        workspace_id: UUID,
    ) -> list[tuple[WorkspaceMember, User]]:
        statement = (
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(User.full_name, User.id)
        )

        result = await self.session.execute(statement)

        return [(membership, user) for membership, user in result]

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
