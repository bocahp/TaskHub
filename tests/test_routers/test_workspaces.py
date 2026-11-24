from collections.abc import AsyncIterator
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.main import app
from app.models.user import User


@pytest.fixture
async def workspace_client(
    db_session: AsyncSession,
) -> AsyncIterator[AsyncClient]:
    previous_overrides = app.dependency_overrides.copy()

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)


def authenticate_as(user_id: UUID) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=user_id,
    )


async def create_user(
    db_session: AsyncSession,
    *,
    full_name: str,
) -> User:
    user = User(
        email=f"{uuid4().hex}@example.com",
        full_name=full_name,
        hashed_password="test-password-hash",
        is_active=True,
    )

    db_session.add(user)
    await db_session.flush()

    return user


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/api/v1/workspaces", None),
        ("POST", "/api/v1/workspaces", {"name": "New Workspace"}),
        ("GET", f"/api/v1/workspaces/{uuid4()}", None),
        (
            "PATCH",
            f"/api/v1/workspaces/{uuid4()}",
            {"name": "Updated Workspace"},
        ),
        ("DELETE", f"/api/v1/workspaces/{uuid4()}", None),
        ("GET", f"/api/v1/workspaces/{uuid4()}/members", None),
        (
            "POST",
            f"/api/v1/workspaces/{uuid4()}/members",
            {"email": "member@example.com"},
        ),
        (
            "PATCH",
            f"/api/v1/workspaces/{uuid4()}/members/{uuid4()}",
            {"role": "EDITOR"},
        ),
        (
            "DELETE",
            f"/api/v1/workspaces/{uuid4()}/members/{uuid4()}",
            None,
        ),
    ],
)
async def test_workspace_endpoints_require_authentication(
    workspace_client: AsyncClient,
    method: str,
    path: str,
    payload: dict[str, str] | None,
) -> None:
    response = await workspace_client.request(
        method,
        path,
        json=payload,
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.anyio
async def test_workspace_api_lifecycle_and_member_management(
    workspace_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner = await create_user(
        db_session,
        full_name="Workspace Owner",
    )
    member = await create_user(
        db_session,
        full_name="Workspace Member",
    )

    owner_id = owner.id
    member_id = member.id
    member_email = member.email

    authenticate_as(owner_id)

    create_response = await workspace_client.post(
        "/api/v1/workspaces",
        json={"name": "My Workspace"},
    )

    assert create_response.status_code == 201

    workspace_data = create_response.json()
    workspace_id = workspace_data["id"]

    assert workspace_data["name"] == "My Workspace"
    assert workspace_data["owner_id"] == str(owner_id)

    get_response = await workspace_client.get(f"/api/v1/workspaces/{workspace_id}")

    assert get_response.status_code == 200
    assert get_response.json()["name"] == "My Workspace"

    list_response = await workspace_client.get(
        "/api/v1/workspaces",
    )

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = await workspace_client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={"name": "Updated Workspace"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Workspace"

    add_member_response = await workspace_client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={
            "email": member_email,
            "role": "EDITOR",
        },
    )

    assert add_member_response.status_code == 201, add_member_response.json()
    assert add_member_response.json()["user_id"] == str(member_id)
    assert add_member_response.json()["role"] == "EDITOR"

    members_response = await workspace_client.get(
        f"/api/v1/workspaces/{workspace_id}/members",
    )

    assert members_response.status_code == 200
    assert len(members_response.json()) == 2

    update_member_response = await workspace_client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{member_id}",
        json={"role": "VIEWER"},
    )

    assert update_member_response.status_code == 200
    assert update_member_response.json()["role"] == "VIEWER"

    remove_member_response = await workspace_client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{member_id}",
    )

    assert remove_member_response.status_code == 204

    members_response = await workspace_client.get(
        f"/api/v1/workspaces/{workspace_id}/members",
    )

    assert members_response.status_code == 200
    assert len(members_response.json()) == 1

    delete_response = await workspace_client.delete(
        f"/api/v1/workspaces/{workspace_id}",
    )

    assert delete_response.status_code == 204

    get_deleted_response = await workspace_client.get(
        f"/api/v1/workspaces/{workspace_id}",
    )

    assert get_deleted_response.status_code == 404


@pytest.mark.anyio
async def test_workspace_viewer_cannot_manage_workspace(
    workspace_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    owner = await create_user(
        db_session,
        full_name="Workspace Owner",
    )
    viewer = await create_user(
        db_session,
        full_name="Workspace Viewer",
    )

    owner_id = owner.id
    viewer_id = viewer.id

    authenticate_as(owner_id)

    create_response = await workspace_client.post(
        "/api/v1/workspaces",
        json={"name": "Permission Test Workspace"},
    )

    assert create_response.status_code == 201

    workspace_id = create_response.json()["id"]

    add_member_response = await workspace_client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": viewer.email},
    )

    assert add_member_response.status_code == 201
    assert add_member_response.json()["role"] == "VIEWER"

    authenticate_as(viewer_id)

    get_response = await workspace_client.get(
        f"/api/v1/workspaces/{workspace_id}",
    )

    members_response = await workspace_client.get(
        f"/api/v1/workspaces/{workspace_id}/members",
    )

    assert get_response.status_code == 200
    assert members_response.status_code == 200

    update_workspace_response = await workspace_client.patch(
        f"/api/v1/workspaces/{workspace_id}",
        json={"name": "Unauthorized Update"},
    )

    delete_workspace_response = await workspace_client.delete(
        f"/api/v1/workspaces/{workspace_id}",
    )

    add_member_forbidden_response = await workspace_client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        json={"email": "another@example.com"},
    )

    update_member_forbidden_response = await workspace_client.patch(
        f"/api/v1/workspaces/{workspace_id}/members/{viewer_id}",
        json={"role": "EDITOR"},
    )

    remove_member_forbidden_response = await workspace_client.delete(
        f"/api/v1/workspaces/{workspace_id}/members/{viewer_id}",
    )

    assert update_workspace_response.status_code == 403
    assert delete_workspace_response.status_code == 403
    assert add_member_forbidden_response.status_code == 403
    assert update_member_forbidden_response.status_code == 403
    assert remove_member_forbidden_response.status_code == 403
