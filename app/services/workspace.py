from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.messages import (
    DATABASE_CONFLICT,
    USER_NOT_FOUND,
    WORKSPACE_ACCESS_FORBIDDEN,
    WORKSPACE_MEMBER_ALREADY_EXISTS,
    WORKSPACE_MEMBER_INACTIVE,
    WORKSPACE_MEMBER_NOT_FOUND,
    WORKSPACE_NOT_FOUND,
    WORKSPACE_OWNER_PROTECTED,
    WORKSPACE_OWNER_REQUIRED,
)
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.domain.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository
from app.repositories.sqlalchemy_workspace import (
    SQLAlchemyWorkspaceRepository,
)

ResultT = TypeVar("ResultT")


class SQLAlchemyWorkspaceService:
    def __init__(
        self,
        workspace_repository: SQLAlchemyWorkspaceRepository,
        user_repository: SQLAlchemyUserRepository,
    ) -> None:
        self.workspace_repository = workspace_repository
        self.user_repository = user_repository
        self.session: AsyncSession = workspace_repository.session

    async def _write(
        self,
        operation: Callable[[], Awaitable[ResultT]],
        *,
        conflict_message: str = DATABASE_CONFLICT,
    ) -> ResultT:
        try:
            result = await operation()
            await self.session.commit()
            return result

        except IntegrityError as exc:
            await self.session.rollback()
            raise ConflictException(conflict_message) from exc

        except Exception:
            await self.session.rollback()
            raise

    async def _get_workspace(
        self,
        workspace_id: UUID,
        *,
        for_update: bool = False,
    ) -> Workspace:
        if for_update:
            workspace = await self.workspace_repository.get_by_id_for_update(
                workspace_id,
            )
        else:
            workspace = await self.workspace_repository.get_by_id(
                workspace_id,
            )

        if workspace is None:
            raise NotFoundException(WORKSPACE_NOT_FOUND)

        return workspace

    async def _require_membership(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> WorkspaceMember:
        membership = await self.workspace_repository.get_membership(
            workspace_id,
            user_id,
        )

        if membership is None:
            raise ForbiddenException(WORKSPACE_ACCESS_FORBIDDEN)

        return membership

    async def _require_owner(
        self,
        workspace: Workspace,
        user_id: UUID,
    ) -> WorkspaceMember:
        membership = await self._require_membership(
            workspace.id,
            user_id,
        )

        if workspace.owner_id != user_id or membership.role != WorkspaceRole.OWNER:
            raise ForbiddenException(WORKSPACE_OWNER_REQUIRED)

        return membership

    async def create_workspace(
        self,
        *,
        name: str,
        owner_id: UUID,
    ) -> Workspace:
        async def operation() -> Workspace:
            workspace = await self.workspace_repository.create_workspace(
                name=name,
                owner_id=owner_id,
            )

            await self.workspace_repository.create_membership(
                workspace_id=workspace.id,
                user_id=owner_id,
                role=WorkspaceRole.OWNER,
            )

            return workspace

        return await self._write(operation)

    async def list_workspaces(
        self,
        user_id: UUID,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Workspace]:
        return await self.workspace_repository.list_for_user(
            user_id,
            offset=offset,
            limit=limit,
        )

    async def get_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> Workspace:
        workspace = await self._get_workspace(workspace_id)

        await self._require_membership(
            workspace.id,
            user_id,
        )

        return workspace

    async def update_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
        *,
        name: str,
    ) -> Workspace:
        async def operation() -> Workspace:
            workspace = await self._get_workspace(
                workspace_id,
                for_update=True,
            )

            await self._require_owner(workspace, user_id)

            workspace.name = name

            return await self.workspace_repository.update(workspace)

        return await self._write(operation)

    async def delete_workspace(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> None:
        async def operation() -> None:
            workspace = await self._get_workspace(
                workspace_id,
                for_update=True,
            )

            await self._require_owner(workspace, user_id)

            await self.workspace_repository.delete(workspace)

        await self._write(operation)

    async def list_members(
        self,
        workspace_id: UUID,
        user_id: UUID,
    ) -> list[tuple[WorkspaceMember, User]]:
        workspace = await self._get_workspace(workspace_id)

        await self._require_membership(
            workspace.id,
            user_id,
        )

        return await self.workspace_repository.list_members(
            workspace.id,
        )

    async def add_member(
        self,
        workspace_id: UUID,
        current_user_id: UUID,
        *,
        email: str,
        role: WorkspaceRole,
    ) -> tuple[WorkspaceMember, User]:
        async def operation() -> tuple[WorkspaceMember, User]:
            workspace = await self._get_workspace(
                workspace_id,
                for_update=True,
            )

            await self._require_owner(
                workspace,
                current_user_id,
            )

            if role == WorkspaceRole.OWNER:
                raise ConflictException(WORKSPACE_OWNER_PROTECTED)

            user = await self.user_repository.get_by_email(
                email.strip().lower(),
            )

            if user is None:
                raise NotFoundException(USER_NOT_FOUND)

            if not user.is_active:
                raise ConflictException(WORKSPACE_MEMBER_INACTIVE)

            existing_membership = await self.workspace_repository.get_membership(
                workspace.id,
                user.id,
            )

            if existing_membership is not None:
                raise ConflictException(WORKSPACE_MEMBER_ALREADY_EXISTS)

            membership = await self.workspace_repository.create_membership(
                workspace_id=workspace.id,
                user_id=user.id,
                role=role,
            )

            return membership, user

        return await self._write(operation)

    async def update_member_role(
        self,
        workspace_id: UUID,
        current_user_id: UUID,
        target_user_id: UUID,
        *,
        role: WorkspaceRole,
    ) -> tuple[WorkspaceMember, User]:
        async def operation() -> tuple[WorkspaceMember, User]:
            workspace = await self._get_workspace(
                workspace_id,
                for_update=True,
            )

            await self._require_owner(
                workspace,
                current_user_id,
            )

            if role == WorkspaceRole.OWNER:
                raise ConflictException(WORKSPACE_OWNER_PROTECTED)

            if target_user_id == workspace.owner_id:
                raise ConflictException(WORKSPACE_OWNER_PROTECTED)

            membership = await self.workspace_repository.get_membership(
                workspace.id,
                target_user_id,
            )

            if membership is None:
                raise NotFoundException(WORKSPACE_MEMBER_NOT_FOUND)

            if membership.role == WorkspaceRole.OWNER:
                raise ConflictException(WORKSPACE_OWNER_PROTECTED)

            user = await self.user_repository.get_by_id(target_user_id)

            if user is None:
                raise NotFoundException(USER_NOT_FOUND)

            updated_membership = await self.workspace_repository.update_membership_role(
                membership,
                role,
            )

            return updated_membership, user

        return await self._write(operation)

    async def remove_member(
        self,
        workspace_id: UUID,
        current_user_id: UUID,
        target_user_id: UUID,
    ) -> None:
        async def operation() -> None:
            workspace = await self._get_workspace(
                workspace_id,
                for_update=True,
            )

            await self._require_owner(
                workspace,
                current_user_id,
            )

            if target_user_id == workspace.owner_id:
                raise ConflictException(WORKSPACE_OWNER_PROTECTED)

            membership = await self.workspace_repository.get_membership(
                workspace.id,
                target_user_id,
            )

            if membership is None:
                raise NotFoundException(WORKSPACE_MEMBER_NOT_FOUND)

            await self.workspace_repository.delete_membership(membership)

        await self._write(operation)
