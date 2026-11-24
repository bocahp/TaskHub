from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import get_current_user
from app.domain.enums import UserRole
from app.main import app


def authenticate_as(
    user_id: UUID,
    role: UserRole = UserRole.MEMBER,
) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=user_id,
        role=role,
    )


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/api/v1/tasks", None),
        ("POST", "/api/v1/tasks", {"title": "Unauthenticated Task"}),
        ("GET", f"/api/v1/tasks/{uuid4()}", None),
        ("PATCH", f"/api/v1/tasks/{uuid4()}", {"title": "Updated Task"}),
        ("DELETE", f"/api/v1/tasks/{uuid4()}", None),
    ],
)
def test_task_endpoints_require_authentication(
    client: TestClient,
    method: str,
    path: str,
    payload: dict[str, str] | None,
) -> None:
    response = client.request(method, path, json=payload)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_create_task(client: TestClient) -> None:
    authenticate_as(uuid4())

    response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Learn FastAPI",
            "description": "Practice CRUD",
            "status": "TODO",
            "priority": "HIGH",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["title"] == "Learn FastAPI"
    assert data["description"] == "Practice CRUD"
    assert data["status"] == "TODO"
    assert data["priority"] == "HIGH"
    assert "id" in data


def test_member_only_sees_own_tasks(client: TestClient) -> None:
    first_user_id = uuid4()
    second_user_id = uuid4()

    authenticate_as(first_user_id)

    first_task = client.post(
        "/api/v1/tasks",
        json={"title": "First User Task"},
    )

    authenticate_as(second_user_id)

    second_task = client.post(
        "/api/v1/tasks",
        json={"title": "Second User Task"},
    )

    assert first_task.status_code == 201
    assert second_task.status_code == 201

    authenticate_as(first_user_id)

    response = client.get("/api/v1/tasks")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "First User Task"


def test_get_task_not_found(client: TestClient) -> None:
    authenticate_as(uuid4())

    response = client.get(f"/api/v1/tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_member_cannot_access_another_users_task(
    client: TestClient,
) -> None:
    owner_id = uuid4()
    other_user_id = uuid4()

    authenticate_as(owner_id)

    create_response = client.post(
        "/api/v1/tasks",
        json={"title": "Private Task"},
    )

    task_id = create_response.json()["id"]

    authenticate_as(other_user_id)

    get_response = client.get(f"/api/v1/tasks/{task_id}")
    update_response = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Unauthorized Update"},
    )
    delete_response = client.delete(f"/api/v1/tasks/{task_id}")

    assert get_response.status_code == 403
    assert update_response.status_code == 403
    assert delete_response.status_code == 403

    assert (
        get_response.json()["detail"]
        == "You do not have permission to access this task"
    )

    authenticate_as(owner_id)

    owner_response = client.get(f"/api/v1/tasks/{task_id}")

    assert owner_response.status_code == 200
    assert owner_response.json()["title"] == "Private Task"


def test_admin_can_access_all_user_tasks(client: TestClient) -> None:
    first_user_id = uuid4()
    second_user_id = uuid4()
    admin_id = uuid4()

    authenticate_as(first_user_id)

    first_task = client.post(
        "/api/v1/tasks",
        json={"title": "First User Task"},
    )

    authenticate_as(second_user_id)

    second_task = client.post(
        "/api/v1/tasks",
        json={"title": "Second User Task"},
    )

    first_task_id = first_task.json()["id"]
    second_task_id = second_task.json()["id"]

    authenticate_as(admin_id, UserRole.ADMIN)

    list_response = client.get("/api/v1/tasks")
    get_response = client.get(f"/api/v1/tasks/{first_task_id}")
    update_response = client.patch(
        f"/api/v1/tasks/{first_task_id}",
        json={"title": "Admin Updated Task"},
    )
    delete_response = client.delete(f"/api/v1/tasks/{second_task_id}")

    assert list_response.status_code == 200
    assert len(list_response.json()) == 2

    assert get_response.status_code == 200

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Admin Updated Task"

    assert delete_response.status_code == 204


def test_patch_rejects_null_title(client: TestClient) -> None:
    authenticate_as(uuid4())

    create_response = client.post(
        "/api/v1/tasks",
        json={"title": "Original title"},
    )

    task_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"title": None},
    )

    assert response.status_code == 422


def test_patch_allows_null_description(client: TestClient) -> None:
    authenticate_as(uuid4())

    create_response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Learn FastAPI",
            "description": "Old description",
        },
    )

    task_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"description": None},
    )

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_patch_rejects_empty_body(client: TestClient) -> None:
    authenticate_as(uuid4())

    create_response = client.post(
        "/api/v1/tasks",
        json={"title": "Learn FastAPI"},
    )

    task_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={},
    )

    assert response.status_code == 422


def test_delete_task(client: TestClient) -> None:
    authenticate_as(uuid4())

    create_response = client.post(
        "/api/v1/tasks",
        json={"title": "Task to delete"},
    )

    task_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/tasks/{task_id}")

    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/tasks/{task_id}")

    assert get_response.status_code == 404
