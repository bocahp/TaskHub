from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TaskPriority, TaskStatus, WorkspaceRole
from app.domain.pagination import PaginationParams
from app.models.comment import Comment
from app.models.label import Label
from app.models.project import Project
from app.models.task import Task
from app.models.task_label import TaskLabel
from app.repositories.base import BaseRepository
from app.repositories.sqlalchemy_task import SQLAlchemyTaskRepository


@pytest.mark.anyio
async def test_create_and_get_task(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context

    repository = SQLAlchemyTaskRepository(db_session)

    user = await repository.get_user(user_id)

    assert user is not None
    assert user.id == user_id
    assert user.is_active

    task = await repository.create_task(
        project_id=project_id,
        created_by=user_id,
        title="Test PostgreSQL Task",
        description="Testing SQLAlchemy repository",
        priority=TaskPriority.HIGH,
    )

    assert task.id is not None
    assert task.created_at is not None
    assert task.title == "Test PostgreSQL Task"
    assert task.status == TaskStatus.TODO
    assert task.priority == TaskPriority.HIGH

    saved_task = await repository.get_by_id(task.id)

    assert saved_task is not None
    assert saved_task.id == task.id
    assert saved_task.project_id == project_id
    assert saved_task.created_by == user_id


@pytest.mark.anyio
async def test_update_and_delete_task(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context

    repository = SQLAlchemyTaskRepository(db_session)

    task = await repository.create_task(
        project_id=project_id,
        created_by=user_id,
        title="Original Task",
    )

    task.title = "Updated Task"

    updated_task = await repository.update(task)

    assert updated_task.title == "Updated Task"

    await repository.delete(updated_task)

    deleted_task = await repository.get_by_id(task.id)

    assert deleted_task is None


@pytest.mark.anyio
async def test_paginate_tasks(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context

    repository = SQLAlchemyTaskRepository(db_session)

    for index in range(5):
        await repository.create_task(
            project_id=project_id,
            created_by=user_id,
            title=f"Task {index + 1}",
        )

    result = await repository.paginate_by_project(
        project_id,
        pagination=PaginationParams(page=2, limit=2),
    )

    assert len(result.items) == 2
    assert all(isinstance(item, Task) for item in result.items)
    assert len(result.items) == 2
    assert result.total == 5
    assert result.page == 2
    assert result.limit == 2


@pytest.mark.anyio
async def test_base_repository_get_by_id(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context

    repository = BaseRepository(db_session, Task)

    task = await repository.create(
        {
            "project_id": project_id,
            "created_by": user_id,
            "title": "Test Generic Repository",
        }
    )

    saved_task = await repository.get_by_id(task.id)

    assert saved_task is not None
    assert saved_task.title == "Test Generic Repository"


@pytest.mark.anyio
async def test_get_project_and_workspace_membership(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context

    repository = SQLAlchemyTaskRepository(db_session)

    project = await repository.get_project(project_id)

    membership = await repository.get_workspace_membership(
        project_id,
        user_id,
    )

    outsider_membership = await repository.get_workspace_membership(
        project_id,
        UUID("00000000-0000-0000-0000-000000000001"),
    )

    assert project is not None
    assert project.id == project_id

    assert membership is not None
    assert membership.user_id == user_id
    assert membership.role == WorkspaceRole.OWNER

    assert outsider_membership is None

    assert await repository.project_exists(project_id)
    assert await repository.user_exists(user_id)

    assert (
        await repository.get_project(UUID("00000000-0000-0000-0000-000000000001"))
        is None
    )


@pytest.mark.anyio
async def test_paginate_tasks_with_filters(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context

    repository = SQLAlchemyTaskRepository(db_session)

    task_values = [
        (TaskStatus.TODO, TaskPriority.LOW, user_id),
        (TaskStatus.IN_PROGRESS, TaskPriority.HIGH, None),
        (TaskStatus.IN_PROGRESS, TaskPriority.HIGH, user_id),
        (TaskStatus.DONE, TaskPriority.HIGH, user_id),
    ]

    for index, (task_status, priority, assignee_id) in enumerate(task_values):
        await repository.create_task(
            project_id=project_id,
            created_by=user_id,
            title=f"Filtered task {index + 1}",
            status=task_status,
            priority=priority,
            assignee_id=assignee_id,
        )

    result = await repository.paginate_by_project(
        project_id,
        pagination=PaginationParams(page=1, limit=10),
        statuses=[TaskStatus.IN_PROGRESS, TaskStatus.DONE],
        priorities=[TaskPriority.HIGH],
        assignee_ids=[user_id],
    )

    assert len(result.items) == 2
    assert result.total == 2
    assert result.page == 1
    assert result.limit == 10

    assert all(
        task.status in [TaskStatus.IN_PROGRESS, TaskStatus.DONE]
        for task in result.items
    )
    assert all(task.priority == TaskPriority.HIGH for task in result.items)
    assert all(task.assignee_id == user_id for task in result.items)


@pytest.mark.anyio
async def test_delete_task_cascades_comments_and_task_labels(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context
    repository = SQLAlchemyTaskRepository(db_session)

    task = await repository.create_task(
        project_id=project_id,
        created_by=user_id,
        title="Task with related data",
    )

    label = Label(
        project_id=project_id,
        name="Cascade Label",
        color="#123456",
    )

    db_session.add(label)
    await db_session.flush()

    comment = Comment(
        task_id=task.id,
        author_id=user_id,
        content="Comment to be deleted",
    )

    task_label = TaskLabel(
        task_id=task.id,
        label_id=label.id,
    )

    db_session.add_all([comment, task_label])
    await db_session.flush()

    task_id = task.id
    label_id = label.id
    comment_id = comment.id

    await repository.delete(task)

    deleted_task = await db_session.scalar(select(Task.id).where(Task.id == task_id))

    deleted_comment = await db_session.scalar(
        select(Comment.id).where(Comment.id == comment_id)
    )

    deleted_task_label = await db_session.scalar(
        select(TaskLabel.task_id).where(
            TaskLabel.task_id == task_id,
            TaskLabel.label_id == label_id,
        )
    )

    existing_label = await db_session.scalar(
        select(Label.id).where(Label.id == label_id)
    )

    assert deleted_task is None
    assert deleted_comment is None
    assert deleted_task_label is None
    assert existing_label == label_id


@pytest.mark.anyio
async def test_delete_project_cascades_related_data(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context
    repository = SQLAlchemyTaskRepository(db_session)

    project = await db_session.get(Project, project_id)

    assert project is not None

    task = await repository.create_task(
        project_id=project_id,
        created_by=user_id,
        title="Task in project to delete",
    )

    label = Label(
        project_id=project_id,
        name="Project Label",
        color="#654321",
    )

    db_session.add(label)
    await db_session.flush()

    comment = Comment(
        task_id=task.id,
        author_id=user_id,
        content="Comment in project to delete",
    )

    task_label = TaskLabel(
        task_id=task.id,
        label_id=label.id,
    )

    db_session.add_all([comment, task_label])
    await db_session.flush()

    task_id = task.id
    label_id = label.id
    comment_id = comment.id

    await db_session.delete(project)
    await db_session.flush()

    deleted_project = await db_session.scalar(
        select(Project.id).where(Project.id == project_id)
    )

    deleted_task = await db_session.scalar(select(Task.id).where(Task.id == task_id))

    deleted_comment = await db_session.scalar(
        select(Comment.id).where(Comment.id == comment_id)
    )

    deleted_label = await db_session.scalar(
        select(Label.id).where(Label.id == label_id)
    )

    deleted_task_label = await db_session.scalar(
        select(TaskLabel.task_id).where(
            TaskLabel.task_id == task_id,
            TaskLabel.label_id == label_id,
        )
    )

    assert deleted_project is None
    assert deleted_task is None
    assert deleted_comment is None
    assert deleted_label is None
    assert deleted_task_label is None


@pytest.mark.anyio
async def test_get_project_access_context(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context
    repository = SQLAlchemyTaskRepository(db_session)

    result = await repository.get_project_access_context(
        project_id,
        owner_id,
    )

    assert result is not None

    project, membership = result

    assert project.id == project_id
    assert membership is not None
    assert membership.user_id == owner_id
    assert membership.role == WorkspaceRole.OWNER

    outsider_result = await repository.get_project_access_context(
        project_id,
        UUID(int=0),
    )

    assert outsider_result is not None

    outsider_project, outsider_membership = outsider_result

    assert outsider_project.id == project_id
    assert outsider_membership is None

    missing_result = await repository.get_project_access_context(
        UUID(int=0),
        owner_id,
    )

    assert missing_result is None


@pytest.mark.anyio
async def test_get_task_access_context(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context
    repository = SQLAlchemyTaskRepository(db_session)

    task = await repository.create_task(
        project_id=project_id,
        created_by=owner_id,
        title="Task access context",
    )

    result = await repository.get_task_access_context(
        task.id,
        owner_id,
    )

    assert result is not None

    loaded_task, project, membership = result

    assert loaded_task.id == task.id
    assert project.id == project_id
    assert membership is not None
    assert membership.user_id == owner_id
    assert membership.role == WorkspaceRole.OWNER

    outsider_result = await repository.get_task_access_context(
        task.id,
        UUID(int=0),
    )

    assert outsider_result is not None

    outsider_task, outsider_project, outsider_membership = outsider_result

    assert outsider_task.id == task.id
    assert outsider_project.id == project_id
    assert outsider_membership is None

    missing_result = await repository.get_task_access_context(
        UUID(int=0),
        owner_id,
    )

    assert missing_result is None
