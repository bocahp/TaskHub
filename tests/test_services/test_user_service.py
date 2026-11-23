
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants.messages import INVALID_CREDENTIALS
from app.core.exceptions import UnauthorizedException
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.sqlalchemy_refresh_token import (
    SQLAlchemyRefreshTokenRepository,
)
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository
from app.services.user import UserService


def create_user_service(
    session: AsyncSession,
) -> tuple[UserService, User]:
    user = User(
        email=f"{uuid4().hex}@example.test",
        full_name="Original Name",
        hashed_password=hash_password("OldPassword123!"),
    )

    session.add(user)

    user_repository = SQLAlchemyUserRepository(session)
    refresh_token_repository = SQLAlchemyRefreshTokenRepository(session)

    service = UserService(
        user_repository,
        refresh_token_repository,
    )

    return service, user


@pytest.mark.anyio
async def test_update_user_profile(
    db_session: AsyncSession,
) -> None:
    service, user = create_user_service(db_session)
    await db_session.flush()

    updated_user = await service.update_profile(
        user,
        full_name="Updated Name",
    )

    assert updated_user.full_name == "Updated Name"


@pytest.mark.anyio
async def test_change_password_rejects_incorrect_current_password(
    db_session: AsyncSession,
) -> None:
    service, user = create_user_service(db_session)
    await db_session.flush()

    with pytest.raises(UnauthorizedException) as exc_info:
        await service.change_password(
            user,
            current_password="WrongPassword123!",
            new_password="NewPassword123!",
        )

    assert exc_info.value.message == INVALID_CREDENTIALS
    assert verify_password("OldPassword123!", user.hashed_password)


@pytest.mark.anyio
async def test_change_password_revokes_all_refresh_tokens(
    db_session: AsyncSession,
) -> None:
    service, user = create_user_service(db_session)
    await db_session.flush()

    refresh_repository = SQLAlchemyRefreshTokenRepository(db_session)

    first_jti = uuid4()
    second_jti = uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=7)

    await refresh_repository.create_refresh_token(
        user_id=user.id,
        jti=first_jti,
        expires_at=expires_at,
    )

    await refresh_repository.create_refresh_token(
        user_id=user.id,
        jti=second_jti,
        expires_at=expires_at,
    )

    await service.change_password(
        user,
        current_password="OldPassword123!",
        new_password="NewPassword123!",
    )

    assert not verify_password("OldPassword123!", user.hashed_password)
    assert verify_password("NewPassword123!", user.hashed_password)

    first_token = await refresh_repository.get_by_jti(first_jti)
    second_token = await refresh_repository.get_by_jti(second_jti)

    assert first_token is not None
    assert first_token.revoked_at is not None

    assert second_token is not None
    assert second_token.revoked_at is not None
