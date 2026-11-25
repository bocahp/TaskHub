from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.enums import TaskPriority, TaskStatus
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate


def test_task_create_normalizes_title_and_uses_defaults() -> None:
    payload = TaskCreate(title="  Learn FastAPI  ")

    assert payload.title == "Learn FastAPI"
    assert payload.description is None
    assert payload.status == TaskStatus.TODO
    assert payload.priority == TaskPriority.MEDIUM
    assert payload.assignee_id is None
    assert payload.due_date is None


def test_task_create_accepts_optional_fields() -> None:
    assignee_id = uuid4()
    due_date = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)

    payload = TaskCreate(
        title="Implement authentication",
        description="Add JWT authentication",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        assignee_id=assignee_id,
        due_date=due_date,
    )

    assert payload.assignee_id == assignee_id
    assert payload.due_date == due_date
    assert payload.status == TaskStatus.IN_PROGRESS
    assert payload.priority == TaskPriority.HIGH


def test_task_create_rejects_blank_title() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(title="   ")


def test_task_create_rejects_title_exceeding_max_length() -> None:
    from app.constants.task import TASK_TITLE_MAX_LENGTH

    with pytest.raises(ValidationError):
        TaskCreate(title="A" * (TASK_TITLE_MAX_LENGTH + 1))


def test_task_create_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(
            title="New task",
            created_by=str(uuid4()),
        )


def test_task_update_accepts_partial_fields() -> None:
    payload = TaskUpdate(
        title="Updated task",
        status=TaskStatus.IN_PROGRESS,
    )

    assert payload.title == "Updated task"
    assert payload.status == TaskStatus.IN_PROGRESS
    assert "title" in payload.model_fields_set
    assert "status" in payload.model_fields_set
    assert "description" not in payload.model_fields_set


def test_task_update_allows_null_description() -> None:
    payload = TaskUpdate(description=None)

    assert payload.description is None


def test_task_update_allows_null_assignee_and_due_date() -> None:
    payload = TaskUpdate(
        assignee_id=None,
        due_date=None,
    )

    assert payload.assignee_id is None
    assert payload.due_date is None


@pytest.mark.parametrize(
    "field",
    ["title", "status", "priority"],
)
def test_task_update_rejects_null_required_fields(
    field: str,
) -> None:
    with pytest.raises(ValidationError):
        TaskUpdate.model_validate({field: None})


def test_task_update_rejects_empty_body() -> None:
    with pytest.raises(ValidationError):
        TaskUpdate.model_validate({})


def test_task_update_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        TaskUpdate(
            title="Updated task",
            created_by=uuid4(),
        )


def test_task_response_validates_data() -> None:
    task_id = uuid4()
    project_id = uuid4()
    created_by = uuid4()
    assignee_id = uuid4()
    created_at = datetime(2026, 11, 25, 9, 0, tzinfo=UTC)
    due_date = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)

    payload = TaskResponse(
        id=task_id,
        project_id=project_id,
        created_by=created_by,
        assignee_id=assignee_id,
        title="Complete Day 5",
        description="Task management implementation",
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.HIGH,
        due_date=due_date,
        created_at=created_at,
    )

    assert payload.id == task_id
    assert payload.project_id == project_id
    assert payload.created_by == created_by
    assert payload.assignee_id == assignee_id
    assert payload.due_date == due_date
    assert payload.created_at == created_at


def test_task_response_allows_nullable_fields() -> None:
    payload = TaskResponse(
        id=uuid4(),
        project_id=uuid4(),
        created_by=uuid4(),
        assignee_id=None,
        title="Unassigned task",
        description=None,
        status=TaskStatus.TODO,
        priority=TaskPriority.MEDIUM,
        due_date=None,
        created_at=datetime.now(UTC),
    )

    assert payload.assignee_id is None
    assert payload.description is None
    assert payload.due_date is None


@pytest.mark.parametrize(
    "schema",
    [TaskCreate, TaskUpdate],
)
def test_task_schema_rejects_naive_due_date(
    schema: type[TaskCreate] | type[TaskUpdate],
) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate(
            {
                "title": "Task with naive datetime",
                "due_date": "2026-12-01T09:00:00",
            }
        )
