from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.repositories.base import BaseRepository
from app.repositories.sqlalchemy_task import SQLAlchemyTaskRepository


@pytest.mark.anyio
async def test_create_and_get_task(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context

    repository = SQLAlchemyTaskRepository(db_session)

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
        page=2,
        limit=2,
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
