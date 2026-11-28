from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.main import app


@pytest.fixture
async def auth_client(
    db_session: AsyncSession,
) -> AsyncIterator[AsyncClient]:
    previous_override = app.dependency_overrides.get(get_db)

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    try:
        transport = ASGITransport(app=app)

        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            yield client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override


async def register_and_login(
    client: AsyncClient,
    email: str,
    password: str,
) -> tuple[str, str]:
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "full_name": "Authentication Test User",
            "password": password,
        },
    )

    assert register_response.status_code == 201, register_response.text

    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token_data = login_response.json()

    return token_data["access_token"], token_data["refresh_token"]


@pytest.mark.anyio
async def test_auth_api_register_login_refresh_and_logout(
    auth_client: AsyncClient,
) -> None:
    email = f"{uuid4().hex}@example.com"
    password = "TestPassword123!"

    access_token, refresh_token = await register_and_login(
        auth_client,
        email,
        password,
    )

    assert access_token
    assert refresh_token

    refresh_response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refresh_response.status_code == 200

    rotated_refresh_token = refresh_response.json()["refresh_token"]

    assert rotated_refresh_token != refresh_token

    logout_response = await auth_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": rotated_refresh_token},
    )

    assert logout_response.status_code == 204

    refresh_after_logout = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": rotated_refresh_token},
    )

    assert refresh_after_logout.status_code == 401


@pytest.mark.anyio
async def test_user_api_profile_and_password_change(
    auth_client: AsyncClient,
) -> None:
    email = f"{uuid4().hex}@example.com"
    old_password = "OldPassword123!"
    new_password = "NewPassword123!"

    access_token, refresh_token = await register_and_login(
        auth_client,
        email,
        old_password,
    )

    old_headers = {
        "Authorization": f"Bearer {access_token}",
    }

    profile_response = await auth_client.get(
        "/api/v1/users/me",
        headers=old_headers,
    )

    assert profile_response.status_code == 200
    assert profile_response.json()["email"] == email

    update_response = await auth_client.patch(
        "/api/v1/users/me",
        headers=old_headers,
        json={"full_name": "Updated Authentication User"},
    )

    assert update_response.status_code == 200
    assert update_response.json()["full_name"] == "Updated Authentication User"

    change_password_response = await auth_client.post(
        "/api/v1/users/me/change-password",
        headers=old_headers,
        json={
            "current_password": old_password,
            "new_password": new_password,
        },
    )

    assert change_password_response.status_code == 204

    old_access_response = await auth_client.get(
        "/api/v1/users/me",
        headers=old_headers,
    )

    assert old_access_response.status_code == 401

    old_refresh_response = await auth_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert old_refresh_response.status_code == 401

    new_access_token, _ = await register_and_login_after_password_change(
        auth_client,
        email,
        new_password,
    )

    new_headers = {
        "Authorization": f"Bearer {new_access_token}",
    }

    new_profile_response = await auth_client.get(
        "/api/v1/users/me",
        headers=new_headers,
    )

    assert new_profile_response.status_code == 200
    assert new_profile_response.json()["email"] == email


async def register_and_login_after_password_change(
    client: AsyncClient,
    email: str,
    password: str,
) -> tuple[str, str]:
    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token_data = login_response.json()

    return token_data["access_token"], token_data["refresh_token"]


@pytest.mark.anyio
async def test_user_api_requires_authentication(
    auth_client: AsyncClient,
) -> None:
    profile_response = await auth_client.get(
        "/api/v1/users/me",
    )

    assert profile_response.status_code == 401

    update_response = await auth_client.patch(
        "/api/v1/users/me",
        json={"full_name": "Updated User"},
    )

    assert update_response.status_code == 401

    change_password_response = await auth_client.post(
        "/api/v1/users/me/change-password",
        json={
            "current_password": "OldPassword123!",
            "new_password": "NewPassword123!",
        },
    )

    assert change_password_response.status_code == 401
