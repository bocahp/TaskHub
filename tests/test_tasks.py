from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.domain.enums import ProjectStatus, UserRole, WorkspaceRole
from app.main import app
from app.models.project import Project
from app.models.user import User
from app.models.workspace_member import WorkspaceMember


def authenticate_as(
    user_id: UUID,
    role: UserRole = UserRole.MEMBER,
) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=user_id,
        role=role,
    )


async def create_user(
    session: AsyncSession,
    *,
    full_name: str,
) -> User:
    user = User(
        email=f"{uuid4().hex}@example.com",
        full_name=full_name,
        hashed_password="test-password-hash",
        is_active=True,
    )

    session.add(user)
    await session.flush()

    return user


async def add_member(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID,
    role: WorkspaceRole,
) -> None:
    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
    )

    session.add(membership)
    await session.flush()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", f"/api/v1/projects/{uuid4()}/tasks", None),
        (
            "POST",
            f"/api/v1/projects/{uuid4()}/tasks",
            {"title": "Unauthenticated Task"},
        ),
        ("GET", f"/api/v1/tasks/{uuid4()}", None),
        ("PATCH", f"/api/v1/tasks/{uuid4()}", {"title": "Updated Task"}),
        ("DELETE", f"/api/v1/tasks/{uuid4()}", None),
    ],
)
async def test_task_endpoints_require_authentication(
    task_client: AsyncClient,
    method: str,
    path: str,
    payload: dict[str, str] | None,
) -> None:
    response = await task_client.request(
        method,
        path,
        json=payload,
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.anyio
async def test_owner_can_create_list_update_and_delete_task(
    task_client: AsyncClient,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context

    authenticate_as(owner_id)

    create_response = await task_client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "title": "Learn FastAPI",
            "description": "Practice SQLAlchemy CRUD",
            "priority": "HIGH",
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["status"] == "TODO"

    data = create_response.json()
    task_id = data["id"]

    assert data["title"] == "Learn FastAPI"
    assert data["project_id"] == str(project_id)
    assert data["created_by"] == str(owner_id)
    assert data["description"] == "Practice SQLAlchemy CRUD"
    assert data["priority"] == "HIGH"

    list_response = await task_client.get(
        f"/api/v1/projects/{project_id}/tasks",
    )

    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1
    assert list_response.json()["total"] == 1
    assert list_response.json()["page"] == 1
    assert list_response.json()["limit"] == 20

    get_response = await task_client.get(
        f"/api/v1/tasks/{task_id}",
    )

    assert get_response.status_code == 200

    update_response = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"description": None},
    )

    assert update_response.status_code == 200
    assert update_response.json()["description"] is None

    delete_response = await task_client.delete(
        f"/api/v1/tasks/{task_id}",
    )

    assert delete_response.status_code == 204

    deleted_response = await task_client.get(
        f"/api/v1/tasks/{task_id}",
    )

    assert deleted_response.status_code == 404


@pytest.mark.anyio
async def test_editor_can_manage_and_viewer_can_only_read_tasks(
    task_client: AsyncClient,
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context

    project = await db_session.get(Project, project_id)
    assert project is not None

    editor = await create_user(
        db_session,
        full_name="Workspace Editor",
    )
    viewer = await create_user(
        db_session,
        full_name="Workspace Viewer",
    )

    editor_id = editor.id
    viewer_id = viewer.id

    await add_member(
        db_session,
        workspace_id=project.workspace_id,
        user_id=editor_id,
        role=WorkspaceRole.EDITOR,
    )

    await add_member(
        db_session,
        workspace_id=project.workspace_id,
        user_id=viewer_id,
        role=WorkspaceRole.VIEWER,
    )

    authenticate_as(owner_id)

    create_response = await task_client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Owner task"},
    )

    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    authenticate_as(editor_id)

    editor_update = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated by editor"},
    )

    assert editor_update.status_code == 200
    assert editor_update.json()["title"] == "Updated by editor"

    authenticate_as(viewer_id)

    viewer_get = await task_client.get(
        f"/api/v1/tasks/{task_id}",
    )

    viewer_list = await task_client.get(
        f"/api/v1/projects/{project_id}/tasks",
    )

    assert viewer_get.status_code == 200
    assert viewer_list.status_code == 200

    viewer_create = await task_client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Unauthorized viewer task"},
    )

    viewer_update = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Unauthorized update"},
    )

    viewer_delete = await task_client.delete(
        f"/api/v1/tasks/{task_id}",
    )

    assert viewer_create.status_code == 403
    assert viewer_update.status_code == 403
    assert viewer_delete.status_code == 403


@pytest.mark.anyio
async def test_non_member_cannot_access_task(
    task_client: AsyncClient,
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context

    outsider = await create_user(
        db_session,
        full_name="Workspace Outsider",
    )

    authenticate_as(owner_id)

    create_response = await task_client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Private task"},
    )

    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    authenticate_as(outsider.id)

    get_response = await task_client.get(
        f"/api/v1/tasks/{task_id}",
    )

    list_response = await task_client.get(
        f"/api/v1/projects/{project_id}/tasks",
    )

    assert get_response.status_code == 404
    assert list_response.status_code == 404

    missing_task_response = await task_client.get(
        "/api/v1/tasks/00000000-0000-0000-0000-000000000000",
    )

    missing_project_response = await task_client.get(
        "/api/v1/projects/00000000-0000-0000-0000-000000000000/tasks",
    )

    assert get_response.status_code == missing_task_response.status_code == 404
    assert get_response.json() == missing_task_response.json()

    assert list_response.status_code == missing_project_response.status_code == 404
    assert list_response.json() == missing_project_response.json()


@pytest.mark.anyio
async def test_admin_can_manage_tasks_without_workspace_membership(
    task_client: AsyncClient,
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, _ = task_context

    admin = await create_user(
        db_session,
        full_name="System Admin",
    )

    authenticate_as(admin.id, UserRole.ADMIN)

    create_response = await task_client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Admin task"},
    )

    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    get_response = await task_client.get(
        f"/api/v1/tasks/{task_id}",
    )

    update_response = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Admin updated task"},
    )

    delete_response = await task_client.delete(
        f"/api/v1/tasks/{task_id}",
    )

    assert get_response.status_code == 200
    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Admin updated task"
    assert delete_response.status_code == 204


@pytest.mark.anyio
async def test_task_assignee_must_be_workspace_member(
    task_client: AsyncClient,
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context

    project = await db_session.get(Project, project_id)
    assert project is not None

    assignee = await create_user(
        db_session,
        full_name="Task Assignee",
    )

    await add_member(
        db_session,
        workspace_id=project.workspace_id,
        user_id=assignee.id,
        role=WorkspaceRole.VIEWER,
    )

    authenticate_as(owner_id)

    valid_response = await task_client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "title": "Assigned task",
            "assignee_id": str(assignee.id),
        },
    )

    assert valid_response.status_code == 201
    assert valid_response.json()["assignee_id"] == str(assignee.id)

    outsider = await create_user(
        db_session,
        full_name="External Assignee",
    )

    invalid_response = await task_client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "title": "Invalid assignment",
            "assignee_id": str(outsider.id),
        },
    )

    assert invalid_response.status_code == 422


@pytest.mark.anyio
async def test_task_api_can_update_assignee_and_due_date(
    task_client: AsyncClient,
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context

    project = await db_session.get(Project, project_id)
    assert project is not None

    first_assignee = await create_user(
        db_session,
        full_name="First Assignee",
    )
    second_assignee = await create_user(
        db_session,
        full_name="Second Assignee",
    )

    first_assignee_id = first_assignee.id
    second_assignee_id = second_assignee.id

    await add_member(
        db_session,
        workspace_id=project.workspace_id,
        user_id=first_assignee_id,
        role=WorkspaceRole.VIEWER,
    )

    await add_member(
        db_session,
        workspace_id=project.workspace_id,
        user_id=second_assignee_id,
        role=WorkspaceRole.EDITOR,
    )

    authenticate_as(owner_id)

    create_response = await task_client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "title": "Task with assignee",
            "assignee_id": str(first_assignee_id),
            "due_date": "2026-12-01T09:00:00Z",
        },
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["id"]

    assert create_response.json()["assignee_id"] == str(first_assignee_id)
    assert create_response.json()["due_date"].startswith("2026-12-01T09:00:00")

    update_response = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "assignee_id": str(second_assignee_id),
            "due_date": "2026-12-05T12:30:00Z",
        },
    )

    assert update_response.status_code == 200
    assert update_response.json()["assignee_id"] == str(second_assignee_id)
    assert update_response.json()["due_date"].startswith("2026-12-05T12:30:00")

    clear_response = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={
            "assignee_id": None,
            "due_date": None,
        },
    )

    assert clear_response.status_code == 200
    assert clear_response.json()["assignee_id"] is None
    assert clear_response.json()["due_date"] is None


@pytest.mark.anyio
async def test_archived_project_rejects_task_modifications(
    task_client: AsyncClient,
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context

    authenticate_as(owner_id)

    create_response = await task_client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task before archive"},
    )

    assert create_response.status_code == 201

    task_id = create_response.json()["id"]

    project = await db_session.get(Project, project_id)
    assert project is not None

    project.status = ProjectStatus.ARCHIVED
    await db_session.commit()

    get_response = await task_client.get(
        f"/api/v1/tasks/{task_id}",
    )

    list_response = await task_client.get(
        f"/api/v1/projects/{project_id}/tasks",
    )

    assert get_response.status_code == 200
    assert list_response.status_code == 200

    create_archived_response = await task_client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task in archived project"},
    )

    update_archived_response = await task_client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Unauthorized update"},
    )

    delete_archived_response = await task_client.delete(
        f"/api/v1/tasks/{task_id}",
    )

    assert create_archived_response.status_code == 409
    assert update_archived_response.status_code == 409
    assert delete_archived_response.status_code == 409


@pytest.mark.anyio
async def test_task_list_filters_and_paginates(
    task_client: AsyncClient,
    task_context: tuple[UUID, UUID],
) -> None:
    project_id, owner_id = task_context

    authenticate_as(owner_id)

    task_cases = [
        ("Matching IN_PROGRESS", "HIGH", owner_id, "IN_PROGRESS"),
        ("Matching DONE", "HIGH", owner_id, "DONE"),
        ("Wrong status", "HIGH", owner_id, "TODO"),
        ("Wrong priority", "LOW", owner_id, "DONE"),
        ("Unassigned task", "HIGH", None, "DONE"),
    ]

    for title, priority, assignee_id, task_status in task_cases:
        create_response = await task_client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={
                "title": title,
                "priority": priority,
                "assignee_id": str(assignee_id) if assignee_id else None,
            },
        )

        assert create_response.status_code == 201

        task_id = create_response.json()["id"]

        if task_status != "TODO":
            update_response = await task_client.patch(
                f"/api/v1/tasks/{task_id}",
                json={"status": task_status},
            )

            assert update_response.status_code == 200

    filters = [
        ("status", "IN_PROGRESS"),
        ("status", "DONE"),
        ("priority", "HIGH"),
        ("assignee_id", str(owner_id)),
    ]

    list_response = await task_client.get(
        f"/api/v1/projects/{project_id}/tasks",
        params=[*filters, ("page", "1"), ("limit", "1")],
    )

    assert list_response.status_code == 200

    data = list_response.json()

    assert len(data["items"]) == 1
    assert data["total"] == 2
    assert data["page"] == 1
    assert data["limit"] == 1

    assert {item["title"] for item in data["items"]} <= {
        "Matching IN_PROGRESS",
        "Matching DONE",
    }

    second_page_response = await task_client.get(
        f"/api/v1/projects/{project_id}/tasks",
        params=[*filters, ("page", "2"), ("limit", "1")],
    )

    assert second_page_response.status_code == 200

    second_page = second_page_response.json()

    assert len(second_page["items"]) == 1
    assert second_page["total"] == 2
    assert second_page["page"] == 2
    assert second_page["limit"] == 1

    assert data["items"][0]["id"] != second_page["items"][0]["id"]

    assert {
        data["items"][0]["title"],
        second_page["items"][0]["title"],
    } == {
        "Matching IN_PROGRESS",
        "Matching DONE",
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"limit": 0},
        {"limit": 101},
        {"status": "INVALID"},
        {"priority": "INVALID"},
        {"assignee_id": "not-a-uuid"},
    ],
)
async def test_task_list_rejects_invalid_query_parameters(
    task_client: AsyncClient,
    task_context: tuple[UUID, UUID],
    params: dict[str, str | int],
) -> None:
    project_id, owner_id = task_context

    authenticate_as(owner_id)

    response = await task_client.get(
        f"/api/v1/projects/{project_id}/tasks",
        params=params,
    )

    assert response.status_code == 422
