from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.domain.enums import (
    ProjectStatus,
    TaskPriority,
    UserRole,
    WorkspaceRole,
)
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.repositories.sqlalchemy_task import SQLAlchemyTaskRepository
from app.services.sqlalchemy_task import SQLAlchemyTaskService


def create_task_service(
    session: AsyncSession,
) -> tuple[SQLAlchemyTaskService, SQLAlchemyTaskRepository]:
    repository = SQLAlchemyTaskRepository(session)
    service = SQLAlchemyTaskService(repository)

    return service, repository


async def create_user(
    session: AsyncSession,
    *,
    is_active: bool = True,
) -> User:
    user = User(
        email=f"{uuid4().hex}@example.com",
        full_name="Task Test User",
        hashed_password="test-password-hash",
        is_active=is_active,
    )

    session.add(user)
    await session.flush()

    return user


async def add_workspace_member(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    role: WorkspaceRole,
) -> WorkspaceMember:
    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
    )

    session.add(membership)
    await session.flush()

    return membership


@pytest.mark.anyio
async def test_service_create_and_get_task(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context
    due_date = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)

    service, _ = create_task_service(db_session)

    task = await service.create_task(
        project_id=project_id,
        current_user_id=user_id,
        current_user_role=UserRole.MEMBER,
        title="Task created by service",
        priority=TaskPriority.HIGH,
        due_date=due_date,
    )

    saved_task = await service.get_task(
        task.id,
        current_user_id=user_id,
        current_user_role=UserRole.MEMBER,
    )

    assert saved_task.id == task.id
    assert saved_task.title == "Task created by service"
    assert saved_task.priority == TaskPriority.HIGH
    assert saved_task.due_date == due_date
    assert saved_task.due_date is not None
    assert saved_task.due_date.tzinfo is not None
    assert saved_task.created_by == user_id


@pytest.mark.anyio
async def test_service_rejects_missing_project(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    _, user_id = task_context
    service, _ = create_task_service(db_session)

    with pytest.raises(NotFoundException):
        await service.create_task(
            project_id=uuid4(),
            current_user_id=user_id,
            current_user_role=UserRole.MEMBER,
            title="Invalid Project Task",
        )


@pytest.mark.anyio
async def test_service_update_and_delete_task(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context
    service, _ = create_task_service(db_session)

    task = await service.create_task(
        project_id=project_id,
        current_user_id=user_id,
        current_user_role=UserRole.MEMBER,
        title="Original Task",
    )

    task_id = task.id

    updated_task = await service.update_task(
        task_id,
        {
            "title": "Updated Task",
            "description": None,
        },
        current_user_id=user_id,
        current_user_role=UserRole.MEMBER,
    )

    assert updated_task.title == "Updated Task"
    assert updated_task.description is None

    await service.delete_task(
        task_id,
        current_user_id=user_id,
        current_user_role=UserRole.MEMBER,
    )

    with pytest.raises(NotFoundException):
        await service.get_task(
            task_id,
            current_user_id=user_id,
            current_user_role=UserRole.MEMBER,
        )


@pytest.mark.anyio
async def test_service_lists_tasks_with_offset_and_limit(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context
    service, _ = create_task_service(db_session)

    for index in range(3):
        await service.create_task(
            project_id=project_id,
            current_user_id=user_id,
            current_user_role=UserRole.MEMBER,
            title=f"Service Task {index + 1}",
        )

    result = await service.list_tasks(
        project_id,
        offset=1,
        limit=1,
        current_user_id=user_id,
        current_user_role=UserRole.MEMBER,
    )

    assert len(result) == 1
    assert result[0].project_id == project_id


@pytest.mark.anyio
async def test_editor_can_manage_workspace_tasks(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context
    service, _ = create_task_service(db_session)

    project = await db_session.get(Project, project_id)
    assert project is not None

    workspace_id = project.workspace_id

    editor = await create_user(db_session)
    editor_id = editor.id

    await add_workspace_member(
        db_session,
        workspace_id=workspace_id,
        user_id=editor_id,
        role=WorkspaceRole.EDITOR,
    )

    task = await service.create_task(
        project_id=project_id,
        current_user_id=editor_id,
        current_user_role=UserRole.MEMBER,
        title="Task created by editor",
    )

    task_id = task.id

    assert task.created_by == editor_id

    updated_task = await service.update_task(
        task_id,
        {"title": "Editor updated task"},
        current_user_id=editor_id,
        current_user_role=UserRole.MEMBER,
    )

    assert updated_task.title == "Editor updated task"

    await service.delete_task(
        task_id,
        current_user_id=editor_id,
        current_user_role=UserRole.MEMBER,
    )

    with pytest.raises(NotFoundException):
        await service.get_task(
            task_id,
            current_user_id=owner_id,
            current_user_role=UserRole.MEMBER,
        )


@pytest.mark.anyio
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_viewer_cannot_modify_workspace_tasks(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
    operation: str,
) -> None:
    project_id, owner_id = task_context
    service, _ = create_task_service(db_session)

    task = await service.create_task(
        project_id=project_id,
        current_user_id=owner_id,
        current_user_role=UserRole.MEMBER,
        title="Owner task",
    )

    task_id = task.id

    project = await db_session.get(Project, project_id)
    assert project is not None

    viewer = await create_user(db_session)
    viewer_id = viewer.id

    await add_workspace_member(
        db_session,
        workspace_id=project.workspace_id,
        user_id=viewer_id,
        role=WorkspaceRole.VIEWER,
    )

    visible_task = await service.get_task(
        task_id,
        current_user_id=viewer_id,
        current_user_role=UserRole.MEMBER,
    )

    visible_tasks = await service.list_tasks(
        project_id,
        current_user_id=viewer_id,
        current_user_role=UserRole.MEMBER,
    )

    assert visible_task.id == task_id
    assert len(visible_tasks) == 1

    with pytest.raises(ForbiddenException):
        if operation == "create":
            await service.create_task(
                project_id=project_id,
                current_user_id=viewer_id,
                current_user_role=UserRole.MEMBER,
                title="Viewer task",
            )
        elif operation == "update":
            await service.update_task(
                task_id,
                {"title": "Unauthorized update"},
                current_user_id=viewer_id,
                current_user_role=UserRole.MEMBER,
            )
        else:
            await service.delete_task(
                task_id,
                current_user_id=viewer_id,
                current_user_role=UserRole.MEMBER,
            )


@pytest.mark.anyio
async def test_non_member_cannot_access_project_tasks(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context
    service, _ = create_task_service(db_session)

    task = await service.create_task(
        project_id=project_id,
        current_user_id=owner_id,
        current_user_role=UserRole.MEMBER,
        title="Private workspace task",
    )

    task_id = task.id
    outsider = await create_user(db_session)
    outsider_id = outsider.id

    with pytest.raises(ForbiddenException):
        await service.get_task(
            task_id,
            current_user_id=outsider_id,
            current_user_role=UserRole.MEMBER,
        )

    with pytest.raises(ForbiddenException):
        await service.list_tasks(
            project_id,
            current_user_id=outsider_id,
            current_user_role=UserRole.MEMBER,
        )


@pytest.mark.anyio
async def test_admin_can_manage_tasks_without_workspace_membership(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, _ = task_context
    service, _ = create_task_service(db_session)

    admin = await create_user(db_session)
    admin_id = admin.id

    task = await service.create_task(
        project_id=project_id,
        current_user_id=admin_id,
        current_user_role=UserRole.ADMIN,
        title="Admin task",
    )

    task_id = task.id

    assert task.created_by == admin_id

    visible_tasks = await service.list_tasks(
        project_id,
        current_user_id=admin_id,
        current_user_role=UserRole.ADMIN,
    )

    assert len(visible_tasks) == 1

    updated_task = await service.update_task(
        task_id,
        {"title": "Admin updated task"},
        current_user_id=admin_id,
        current_user_role=UserRole.ADMIN,
    )

    assert updated_task.title == "Admin updated task"

    await service.delete_task(
        task_id,
        current_user_id=admin_id,
        current_user_role=UserRole.ADMIN,
    )


@pytest.mark.anyio
async def test_assignee_must_belong_to_project_workspace(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context
    service, _ = create_task_service(db_session)

    outsider = await create_user(db_session)
    outsider_id = outsider.id

    with pytest.raises(ConflictException):
        await service.create_task(
            project_id=project_id,
            current_user_id=owner_id,
            current_user_role=UserRole.MEMBER,
            title="Invalid assignment",
            assignee_id=outsider_id,
        )


@pytest.mark.anyio
async def test_task_can_be_assigned_to_active_workspace_member(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context
    service, _ = create_task_service(db_session)

    project = await db_session.get(Project, project_id)
    assert project is not None

    assignee = await create_user(db_session)
    assignee_id = assignee.id

    await add_workspace_member(
        db_session,
        workspace_id=project.workspace_id,
        user_id=assignee_id,
        role=WorkspaceRole.VIEWER,
    )

    task = await service.create_task(
        project_id=project_id,
        current_user_id=owner_id,
        current_user_role=UserRole.MEMBER,
        title="Assigned task",
        assignee_id=assignee_id,
    )

    assert task.assignee_id == assignee_id


@pytest.mark.anyio
async def test_inactive_assignee_is_rejected(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context
    service, _ = create_task_service(db_session)

    project = await db_session.get(Project, project_id)
    assert project is not None

    inactive_user = await create_user(
        db_session,
        is_active=False,
    )

    inactive_user_id = inactive_user.id

    await add_workspace_member(
        db_session,
        workspace_id=project.workspace_id,
        user_id=inactive_user_id,
        role=WorkspaceRole.VIEWER,
    )

    with pytest.raises(ConflictException):
        await service.create_task(
            project_id=project_id,
            current_user_id=owner_id,
            current_user_role=UserRole.MEMBER,
            title="Task with inactive assignee",
            assignee_id=inactive_user_id,
        )


@pytest.mark.anyio
@pytest.mark.parametrize("operation", ["create", "update", "delete"])
async def test_archived_project_rejects_task_modifications(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
    operation: str,
) -> None:
    project_id, owner_id = task_context
    service, _ = create_task_service(db_session)

    task = await service.create_task(
        project_id=project_id,
        current_user_id=owner_id,
        current_user_role=UserRole.MEMBER,
        title="Task before archive",
    )

    task_id = task.id

    project = await db_session.get(Project, project_id)
    assert project is not None

    project.status = ProjectStatus.ARCHIVED
    await db_session.flush()

    visible_task = await service.get_task(
        task_id,
        current_user_id=owner_id,
        current_user_role=UserRole.MEMBER,
    )

    visible_tasks = await service.list_tasks(
        project_id,
        current_user_id=owner_id,
        current_user_role=UserRole.MEMBER,
    )

    assert visible_task.id == task_id
    assert len(visible_tasks) == 1

    with pytest.raises(ConflictException):
        if operation == "create":
            await service.create_task(
                project_id=project_id,
                current_user_id=owner_id,
                current_user_role=UserRole.MEMBER,
                title="Task in archived project",
            )
        elif operation == "update":
            await service.update_task(
                task_id,
                {"title": "Archived task update"},
                current_user_id=owner_id,
                current_user_role=UserRole.MEMBER,
            )
        else:
            await service.delete_task(
                task_id,
                current_user_id=owner_id,
                current_user_role=UserRole.MEMBER,
            )


@pytest.mark.anyio
async def test_service_rolls_back_on_integrity_error(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_id, user_id = task_context
    service, repository = create_task_service(db_session)

    async def create_with_invalid_project(**values: object) -> Task:
        return await repository.create(
            {
                "project_id": uuid4(),
                "created_by": values["created_by"],
                "title": values["title"],
                "description": values["description"],
                "status": values["status"],
                "priority": values["priority"],
                "assignee_id": values["assignee_id"],
                "due_date": values["due_date"],
            }
        )

    monkeypatch.setattr(
        repository,
        "create_task",
        create_with_invalid_project,
    )

    with pytest.raises(ConflictException):
        await service.create_task(
            project_id=project_id,
            current_user_id=user_id,
            current_user_role=UserRole.MEMBER,
            title="Task with invalid foreign key",
        )

    result = await db_session.scalar(text("SELECT 1"))

    assert result == 1
