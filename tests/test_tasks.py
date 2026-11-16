from uuid import uuid4

from fastapi.testclient import TestClient


def test_create_task(client: TestClient) -> None:
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


def test_list_tasks(client: TestClient) -> None:
    client.post(
        "/api/v1/tasks",
        json={"title": "Task 1"},
    )

    response = client.get("/api/v1/tasks")

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_task_not_found(client: TestClient) -> None:
    response = client.get(f"/api/v1/tasks/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_patch_rejects_null_title(client: TestClient) -> None:
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
    create_response = client.post(
        "/api/v1/tasks",
        json={"title": "Task to delete"},
    )

    task_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/tasks/{task_id}")

    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/tasks/{task_id}")

    assert get_response.status_code == 404
