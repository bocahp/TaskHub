from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import WorkspaceRole
from app.domain.pagination import PaginationParams
from app.models.project import Project
from app.models.user import User
from app.repositories.sqlalchemy_workspace import (
    SQLAlchemyWorkspaceRepository,
)


@pytest.mark.anyio
async def test_create_workspace_and_owner_membership(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    _, user_id = task_context
    repository = SQLAlchemyWorkspaceRepository(db_session)

    workspace = await repository.create_workspace(
        name="New Workspace",
        owner_id=user_id,
    )

    membership = await repository.create_membership(
        workspace_id=workspace.id,
        user_id=user_id,
        role=WorkspaceRole.OWNER,
    )

    assert workspace.id is not None
    assert workspace.name == "New Workspace"
    assert workspace.owner_id == user_id

    assert membership.workspace_id == workspace.id
    assert membership.user_id == user_id
    assert membership.role == WorkspaceRole.OWNER


@pytest.mark.anyio
async def test_list_workspaces_for_user(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context
    repository = SQLAlchemyWorkspaceRepository(db_session)

    project = await db_session.get(Project, project_id)

    assert project is not None

    pagination = PaginationParams(page=1, limit=20)

    workspaces = await repository.paginate_for_user(
        user_id,
        pagination=pagination,
    )

    assert len(workspaces.items) == 1
    assert workspaces.items[0].id == project.workspace_id
    assert workspaces.total == 1
    assert workspaces.page == 1
    assert workspaces.limit == 20

    unrelated_workspaces = await repository.paginate_for_user(
        uuid4(),
        pagination=pagination,
    )

    assert unrelated_workspaces.items == []
    assert unrelated_workspaces.total == 0


@pytest.mark.anyio
async def test_get_workspace_and_list_members(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context
    repository = SQLAlchemyWorkspaceRepository(db_session)

    project = await db_session.get(Project, project_id)

    assert project is not None

    workspace = await repository.get_by_id_for_update(
        project.workspace_id,
    )

    assert workspace is not None
    assert workspace.owner_id == user_id

    membership = await repository.get_membership(
        workspace.id,
        user_id,
    )

    assert membership is not None
    assert membership.role == WorkspaceRole.OWNER

    members = await repository.paginate_members(
        workspace.id,
        pagination=PaginationParams(page=1, limit=20),
    )

    assert len(members.items) == 1
    assert members.total == 1
    assert members.page == 1
    assert members.limit == 20

    member, member_user = members.items[0]

    assert member.user_id == user_id
    assert member_user.id == user_id
    assert member_user.full_name == "Test User"


@pytest.mark.anyio
async def test_update_and_delete_membership(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context
    repository = SQLAlchemyWorkspaceRepository(db_session)

    project = await db_session.get(Project, project_id)

    assert project is not None

    second_user = User(
        email=f"{uuid4().hex}@example.test",
        full_name="Second User",
        hashed_password="test-password-hash",
    )

    db_session.add(second_user)
    await db_session.flush()

    membership = await repository.create_membership(
        workspace_id=project.workspace_id,
        user_id=second_user.id,
        role=WorkspaceRole.VIEWER,
    )

    assert membership.role == WorkspaceRole.VIEWER

    updated_membership = await repository.update_membership_role(
        membership,
        WorkspaceRole.EDITOR,
    )

    assert updated_membership.role == WorkspaceRole.EDITOR

    await repository.delete_membership(updated_membership)

    deleted_membership = await repository.get_membership(
        project.workspace_id,
        second_user.id,
    )

    owner_membership = await repository.get_membership(
        project.workspace_id,
        owner_id,
    )

    assert deleted_membership is None
    assert owner_membership is not None
    assert owner_membership.role == WorkspaceRole.OWNER
