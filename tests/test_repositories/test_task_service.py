from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.domain.enums import TaskPriority
from app.repositories.sqlalchemy_task import SQLAlchemyTaskRepository
from app.services.sqlalchemy_task import SQLAlchemyTaskService


@pytest.mark.anyio
async def test_service_create_and_get_task(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context
    due_date = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
    repository = SQLAlchemyTaskRepository(db_session)
    service = SQLAlchemyTaskService(repository)

    task = await service.create_task(
        project_id=project_id,
        created_by=user_id,
        title="Task created by service",
        priority=TaskPriority.HIGH,
        due_date=due_date,
    )

    saved_task = await service.get_task(task.id)

    assert saved_task.id == task.id
    assert saved_task.title == "Task created by service"
    assert saved_task.priority == TaskPriority.HIGH
    assert saved_task.due_date == due_date
    assert saved_task.due_date.tzinfo is not None


@pytest.mark.anyio
async def test_service_rejects_missing_project(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    _, user_id = task_context
    repository = SQLAlchemyTaskRepository(db_session)
    service = SQLAlchemyTaskService(repository)

    with pytest.raises(NotFoundException):
        await service.create_task(
            project_id=uuid4(),
            created_by=user_id,
            title="Invalid Project Task",
        )


@pytest.mark.anyio
async def test_service_update_and_delete_task(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context
    repository = SQLAlchemyTaskRepository(db_session)
    service = SQLAlchemyTaskService(repository)

    task = await service.create_task(
        project_id=project_id,
        created_by=user_id,
        title="Original Task",
    )

    updated_task = await service.update_task(
        task.id,
        {
            "title": "Updated Task",
            "description": None,
        },
    )

    assert updated_task.title == "Updated Task"
    assert updated_task.description is None

    await service.delete_task(task.id)

    with pytest.raises(NotFoundException):
        await service.get_task(task.id)


@pytest.mark.anyio
async def test_service_pagination(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, user_id = task_context
    repository = SQLAlchemyTaskRepository(db_session)
    service = SQLAlchemyTaskService(repository)

    for index in range(3):
        await service.create_task(
            project_id=project_id,
            created_by=user_id,
            title=f"Service Task {index + 1}",
        )

    result = await service.list_tasks(
        project_id,
        page=2,
        limit=2,
    )

    assert len(result.items) == 1
    assert result.total == 3
    assert result.page == 2
    assert result.limit == 2


@pytest.mark.anyio
async def test_service_rolls_back_on_integrity_error(
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = SQLAlchemyTaskRepository(db_session)
    service = SQLAlchemyTaskService(repository)

    async def always_exists(_: UUID) -> bool:
        return True

    monkeypatch.setattr(
        repository,
        "project_exists",
        always_exists,
    )

    monkeypatch.setattr(
        repository,
        "user_exists",
        always_exists,
    )

    with pytest.raises(ConflictException):
        await service.create_task(
            project_id=uuid4(),
            created_by=uuid4(),
            title="Task with invalid foreign key",
        )

    result = await db_session.scalar(text("SELECT 1"))

    assert result == 1
