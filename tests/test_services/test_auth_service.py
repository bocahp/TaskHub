
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.messages import (
    EMAIL_ALREADY_REGISTERED,
    INVALID_CREDENTIALS,
    INVALID_REFRESH_TOKEN,
)
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.security import decode_token, verify_password
from app.domain.enums import UserRole
from app.repositories.sqlalchemy_refresh_token import (
    SQLAlchemyRefreshTokenRepository,
)
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository
from app.services.auth import AuthService


def create_auth_service(
    session: AsyncSession,
) -> tuple[
    AuthService,
    SQLAlchemyUserRepository,
    SQLAlchemyRefreshTokenRepository,
]:
    user_repository = SQLAlchemyUserRepository(session)
    refresh_token_repository = SQLAlchemyRefreshTokenRepository(session)

    service = AuthService(
        user_repository,
        refresh_token_repository,
    )

    return service, user_repository, refresh_token_repository


@pytest.mark.anyio
async def test_register_creates_user_with_hashed_password(
    db_session: AsyncSession,
) -> None:
    service, _, _ = create_auth_service(db_session)

    user = await service.register(
        email=" Test@Example.com ",
        full_name="Test User",
        password="TestPassword123!",
    )

    assert user.email == "test@example.com"
    assert user.full_name == "Test User"
    assert user.role == UserRole.MEMBER
    assert user.is_active is True

    assert user.hashed_password != "TestPassword123!"
    assert verify_password("TestPassword123!", user.hashed_password)


@pytest.mark.anyio
async def test_register_rejects_duplicate_email(
    db_session: AsyncSession,
) -> None:
    service, _, _ = create_auth_service(db_session)

    await service.register(
        email="duplicate@example.com",
        full_name="First User",
        password="TestPassword123!",
    )

    with pytest.raises(ConflictException) as exc_info:
        await service.register(
            email="DUPLICATE@example.com",
            full_name="Second User",
            password="TestPassword123!",
        )

    assert exc_info.value.message == EMAIL_ALREADY_REGISTERED


@pytest.mark.anyio
async def test_login_creates_access_and_refresh_tokens(
    db_session: AsyncSession,
) -> None:
    service, _, refresh_repository = create_auth_service(db_session)

    user = await service.register(
        email="login@example.com",
        full_name="Login User",
        password="TestPassword123!",
    )

    access_token, refresh_token = await service.login(
        email="LOGIN@example.com",
        password="TestPassword123!",
    )

    access_data = decode_token(access_token)
    refresh_data = decode_token(refresh_token)

    assert access_data["sub"] == str(user.id)
    assert access_data["type"] == "access"

    assert refresh_data["sub"] == str(user.id)
    assert refresh_data["type"] == "refresh"

    refresh_record = await refresh_repository.get_by_jti(
        UUID(refresh_data["jti"]),
    )

    assert refresh_record is not None
    assert refresh_record.user_id == user.id
    assert refresh_record.revoked_at is None


@pytest.mark.anyio
async def test_login_rejects_incorrect_password(
    db_session: AsyncSession,
) -> None:
    service, _, _ = create_auth_service(db_session)

    await service.register(
        email="wrong-password@example.com",
        full_name="Test User",
        password="TestPassword123!",
    )

    with pytest.raises(UnauthorizedException) as exc_info:
        await service.login(
            email="wrong-password@example.com",
            password="WrongPassword123!",
        )

    assert exc_info.value.message == INVALID_CREDENTIALS


@pytest.mark.anyio
async def test_login_rejects_inactive_account(
    db_session: AsyncSession,
) -> None:
    service, _, _ = create_auth_service(db_session)

    user = await service.register(
        email="inactive@example.com",
        full_name="Inactive User",
        password="TestPassword123!",
    )

    user.is_active = False
    await db_session.commit()

    with pytest.raises(UnauthorizedException):
        await service.login(
            email="inactive@example.com",
            password="TestPassword123!",
        )

@pytest.mark.anyio
async def test_refresh_rotates_token_and_rejects_old_token(
    db_session: AsyncSession,
) -> None:
    service, _, refresh_repository = create_auth_service(db_session)

    user = await service.register(
        email="rotation@example.com",
        full_name="Rotation User",
        password="TestPassword123!",
    )

    _, old_refresh_token = await service.login(
        email="rotation@example.com",
        password="TestPassword123!",
    )

    old_data = decode_token(old_refresh_token)

    new_access_token, new_refresh_token = await service.refresh(
        refresh_token=old_refresh_token,
    )

    new_access_data = decode_token(new_access_token)
    new_refresh_data = decode_token(new_refresh_token)

    assert new_access_data["sub"] == str(user.id)
    assert new_access_data["type"] == "access"
    assert new_refresh_data["sub"] == str(user.id)
    assert new_refresh_data["type"] == "refresh"

    old_record = await refresh_repository.get_by_jti(
        UUID(old_data["jti"]),
    )

    new_record = await refresh_repository.get_by_jti(
        UUID(new_refresh_data["jti"]),
    )

    assert old_record is not None
    assert old_record.revoked_at is not None

    assert new_record is not None
    assert new_record.revoked_at is None

    with pytest.raises(UnauthorizedException) as exc_info:
        await service.refresh(refresh_token=old_refresh_token)

    assert exc_info.value.message == INVALID_REFRESH_TOKEN


@pytest.mark.anyio
async def test_logout_revokes_refresh_token(
    db_session: AsyncSession,
) -> None:
    service, _, refresh_repository = create_auth_service(db_session)

    user = await service.register(
        email="logout@example.com",
        full_name="Logout User",
        password="TestPassword123!",
    )

    _, refresh_token = await service.login(
        email="logout@example.com",
        password="TestPassword123!",
    )

    token_data = decode_token(refresh_token)
    jti = UUID(token_data["jti"])

    await service.logout(refresh_token=refresh_token)

    saved_token = await refresh_repository.get_by_jti(jti)

    assert saved_token is not None
    assert saved_token.user_id == user.id
    assert saved_token.revoked_at is not None

    await service.logout(refresh_token=refresh_token)


@pytest.mark.anyio
async def test_refresh_rejects_access_token(
    db_session: AsyncSession,
) -> None:
    service, _, _ = create_auth_service(db_session)

    await service.register(
        email="wrong-token-type@example.com",
        full_name="Wrong Token Type",
        password="TestPassword123!",
    )

    access_token, _ = await service.login(
        email="wrong-token-type@example.com",
        password="TestPassword123!",
    )

    with pytest.raises(UnauthorizedException) as exc_info:
        await service.refresh(refresh_token=access_token)

    assert exc_info.value.message == INVALID_REFRESH_TOKEN
