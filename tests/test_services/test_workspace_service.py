from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.domain.enums import WorkspaceRole
from app.domain.pagination import PaginationParams
from app.models.user import User
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository
from app.repositories.sqlalchemy_workspace import (
    SQLAlchemyWorkspaceRepository,
)
from app.services.workspace import SQLAlchemyWorkspaceService


def create_workspace_service(
    session: AsyncSession,
) -> tuple[
    SQLAlchemyWorkspaceService,
    SQLAlchemyWorkspaceRepository,
    SQLAlchemyUserRepository,
]:
    workspace_repository = SQLAlchemyWorkspaceRepository(session)
    user_repository = SQLAlchemyUserRepository(session)

    service = SQLAlchemyWorkspaceService(
        workspace_repository,
        user_repository,
    )

    return service, workspace_repository, user_repository


async def create_user(
    session: AsyncSession,
    *,
    is_active: bool = True,
) -> User:
    user = User(
        email=f"{uuid4().hex}@example.test",
        full_name="Test User",
        hashed_password="test-password-hash",
        is_active=is_active,
    )

    session.add(user)
    await session.flush()

    return user


@pytest.mark.anyio
async def test_create_workspace_creates_owner_membership(
    db_session: AsyncSession,
) -> None:
    service, repository, _ = create_workspace_service(db_session)
    owner = await create_user(db_session)

    owner_id = owner.id

    workspace = await service.create_workspace(
        name="Engineering",
        owner_id=owner_id,
    )

    workspace_id = workspace.id

    membership = await repository.get_membership(
        workspace_id,
        owner_id,
    )

    assert workspace.name == "Engineering"
    assert workspace.owner_id == owner_id

    assert membership is not None
    assert membership.role == WorkspaceRole.OWNER


@pytest.mark.anyio
async def test_list_workspaces_returns_only_user_memberships(
    db_session: AsyncSession,
) -> None:
    service, _, _ = create_workspace_service(db_session)

    first_user = await create_user(db_session)
    second_user = await create_user(db_session)

    first_user_id = first_user.id
    second_user_id = second_user.id

    first_workspace = await service.create_workspace(
        name="First Workspace",
        owner_id=first_user_id,
    )

    first_workspace_id = first_workspace.id

    await service.create_workspace(
        name="Second Workspace",
        owner_id=second_user_id,
    )

    pagination = PaginationParams(page=1, limit=20)

    workspaces = await service.list_workspaces(
        first_user_id,
        pagination=pagination,
    )

    assert len(workspaces.items) == 1
    assert workspaces.items[0].id == first_workspace_id
    assert workspaces.total == 1
    assert workspaces.page == 1
    assert workspaces.limit == 20

    empty_result = await service.list_workspaces(
        uuid4(),
        pagination=pagination,
    )

    assert empty_result.items == []
    assert empty_result.total == 0


@pytest.mark.anyio
async def test_workspace_access_requires_membership(
    db_session: AsyncSession,
) -> None:
    service, _, _ = create_workspace_service(db_session)

    owner = await create_user(db_session)
    member = await create_user(db_session)
    outsider = await create_user(db_session)

    owner_id = owner.id
    member_id = member.id
    outsider_id = outsider.id
    member_email = member.email

    workspace = await service.create_workspace(
        name="Shared Workspace",
        owner_id=owner_id,
    )

    workspace_id = workspace.id

    await service.add_member(
        workspace_id,
        owner_id,
        email=member_email,
        role=WorkspaceRole.VIEWER,
    )

    member_workspace = await service.get_workspace(
        workspace_id,
        member_id,
    )

    assert member_workspace.id == workspace_id

    with pytest.raises(NotFoundException) as outsider_error:
        await service.get_workspace(workspace_id, outsider_id)

    with pytest.raises(NotFoundException) as missing_error:
        await service.get_workspace(uuid4(), owner_id)

    assert outsider_error.value.message == missing_error.value.message


@pytest.mark.anyio
async def test_update_workspace_requires_owner(
    db_session: AsyncSession,
) -> None:
    service, _, _ = create_workspace_service(db_session)

    owner = await create_user(db_session)
    editor = await create_user(db_session)
    viewer = await create_user(db_session)

    owner_id = owner.id
    editor_id = editor.id
    viewer_id = viewer.id

    editor_email = editor.email
    viewer_email = viewer.email

    workspace = await service.create_workspace(
        name="Original Workspace",
        owner_id=owner_id,
    )

    workspace_id = workspace.id

    await service.add_member(
        workspace_id,
        owner_id,
        email=editor_email,
        role=WorkspaceRole.EDITOR,
    )

    await service.add_member(
        workspace_id,
        owner_id,
        email=viewer_email,
        role=WorkspaceRole.VIEWER,
    )

    with pytest.raises(ForbiddenException):
        await service.update_workspace(
            workspace_id,
            editor_id,
            name="Unauthorized Update",
        )

    with pytest.raises(ForbiddenException):
        await service.update_workspace(
            workspace_id,
            viewer_id,
            name="Unauthorized Update",
        )

    updated_workspace = await service.update_workspace(
        workspace_id,
        owner_id,
        name="Updated Workspace",
    )

    assert updated_workspace.name == "Updated Workspace"


@pytest.mark.anyio
async def test_add_member_requires_owner_and_rejects_duplicates(
    db_session: AsyncSession,
) -> None:
    service, repository, _ = create_workspace_service(db_session)

    owner = await create_user(db_session)
    editor = await create_user(db_session)
    new_member = await create_user(db_session)

    owner_id = owner.id
    editor_id = editor.id
    new_member_id = new_member.id

    editor_email = editor.email
    new_member_email = new_member.email

    workspace = await service.create_workspace(
        name="Member Management",
        owner_id=owner_id,
    )

    workspace_id = workspace.id

    await service.add_member(
        workspace_id,
        owner_id,
        email=editor_email,
        role=WorkspaceRole.EDITOR,
    )

    with pytest.raises(ForbiddenException):
        await service.add_member(
            workspace_id,
            editor_id,
            email=new_member_email,
            role=WorkspaceRole.VIEWER,
        )

    membership, user = await service.add_member(
        workspace_id,
        owner_id,
        email=new_member_email,
        role=WorkspaceRole.VIEWER,
    )

    assert user.id == new_member_id
    assert membership.role == WorkspaceRole.VIEWER

    with pytest.raises(ConflictException):
        await service.add_member(
            workspace_id,
            owner_id,
            email=new_member_email,
            role=WorkspaceRole.EDITOR,
        )

    saved_membership = await repository.get_membership(
        workspace_id,
        new_member_id,
    )

    assert saved_membership is not None


@pytest.mark.anyio
async def test_add_member_rejects_missing_and_inactive_users(
    db_session: AsyncSession,
) -> None:
    service, _, _ = create_workspace_service(db_session)

    owner = await create_user(db_session)
    inactive_user = await create_user(
        db_session,
        is_active=False,
    )

    owner_id = owner.id
    inactive_email = inactive_user.email

    workspace = await service.create_workspace(
        name="User Validation",
        owner_id=owner_id,
    )

    workspace_id = workspace.id

    with pytest.raises(NotFoundException):
        await service.add_member(
            workspace_id,
            owner_id,
            email="missing@example.test",
            role=WorkspaceRole.VIEWER,
        )

    with pytest.raises(ConflictException):
        await service.add_member(
            workspace_id,
            owner_id,
            email=inactive_email,
            role=WorkspaceRole.VIEWER,
        )


@pytest.mark.anyio
async def test_update_member_role_protects_owner(
    db_session: AsyncSession,
) -> None:
    service, repository, _ = create_workspace_service(db_session)

    owner = await create_user(db_session)
    editor = await create_user(db_session)
    viewer = await create_user(db_session)

    owner_id = owner.id
    editor_id = editor.id
    viewer_id = viewer.id

    editor_email = editor.email
    viewer_email = viewer.email

    workspace = await service.create_workspace(
        name="Role Management",
        owner_id=owner_id,
    )

    workspace_id = workspace.id

    await service.add_member(
        workspace_id,
        owner_id,
        email=editor_email,
        role=WorkspaceRole.EDITOR,
    )

    await service.add_member(
        workspace_id,
        owner_id,
        email=viewer_email,
        role=WorkspaceRole.VIEWER,
    )

    updated_membership, updated_user = await service.update_member_role(
        workspace_id,
        owner_id,
        viewer_id,
        role=WorkspaceRole.EDITOR,
    )

    assert updated_user.id == viewer_id
    assert updated_membership.role == WorkspaceRole.EDITOR

    with pytest.raises(ForbiddenException):
        await service.update_member_role(
            workspace_id,
            editor_id,
            viewer_id,
            role=WorkspaceRole.VIEWER,
        )

    with pytest.raises(ConflictException):
        await service.update_member_role(
            workspace_id,
            owner_id,
            owner_id,
            role=WorkspaceRole.VIEWER,
        )

    with pytest.raises(ConflictException):
        await service.update_member_role(
            workspace_id,
            owner_id,
            editor_id,
            role=WorkspaceRole.OWNER,
        )

    owner_membership = await repository.get_membership(
        workspace_id,
        owner_id,
    )

    assert owner_membership is not None
    assert owner_membership.role == WorkspaceRole.OWNER


@pytest.mark.anyio
async def test_remove_member_requires_owner_and_protects_owner(
    db_session: AsyncSession,
) -> None:
    service, repository, _ = create_workspace_service(db_session)

    owner = await create_user(db_session)
    editor = await create_user(db_session)
    viewer = await create_user(db_session)

    owner_id = owner.id
    editor_id = editor.id
    viewer_id = viewer.id

    editor_email = editor.email
    viewer_email = viewer.email

    workspace = await service.create_workspace(
        name="Member Removal",
        owner_id=owner_id,
    )

    workspace_id = workspace.id

    await service.add_member(
        workspace_id,
        owner_id,
        email=editor_email,
        role=WorkspaceRole.EDITOR,
    )

    await service.add_member(
        workspace_id,
        owner_id,
        email=viewer_email,
        role=WorkspaceRole.VIEWER,
    )

    with pytest.raises(ForbiddenException):
        await service.remove_member(
            workspace_id,
            editor_id,
            viewer_id,
        )

    with pytest.raises(ConflictException):
        await service.remove_member(
            workspace_id,
            owner_id,
            owner_id,
        )

    await service.remove_member(
        workspace_id,
        owner_id,
        viewer_id,
    )

    deleted_membership = await repository.get_membership(
        workspace_id,
        viewer_id,
    )

    owner_membership = await repository.get_membership(
        workspace_id,
        owner_id,
    )

    assert deleted_membership is None
    assert owner_membership is not None
    assert owner_membership.role == WorkspaceRole.OWNER


@pytest.mark.anyio
async def test_delete_workspace_requires_owner(
    db_session: AsyncSession,
) -> None:
    service, repository, _ = create_workspace_service(db_session)

    owner = await create_user(db_session)
    viewer = await create_user(db_session)

    owner_id = owner.id
    viewer_id = viewer.id
    viewer_email = viewer.email

    workspace = await service.create_workspace(
        name="Workspace Deletion",
        owner_id=owner_id,
    )

    workspace_id = workspace.id

    await service.add_member(
        workspace_id,
        owner_id,
        email=viewer_email,
        role=WorkspaceRole.VIEWER,
    )

    with pytest.raises(ForbiddenException):
        await service.delete_workspace(
            workspace_id,
            viewer_id,
        )

    await service.delete_workspace(
        workspace_id,
        owner_id,
    )

    deleted_workspace = await repository.get_by_id(workspace_id)
    deleted_owner_membership = await repository.get_membership(
        workspace_id,
        owner_id,
    )

    assert deleted_workspace is None
    assert deleted_owner_membership is None
