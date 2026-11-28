from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedException
from app.core.security import hash_password
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.sqlalchemy_refresh_token import (
    SQLAlchemyRefreshTokenRepository,
)
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository
from app.services.auth import AuthService
from app.services.user import UserService


@pytest.mark.anyio
async def test_password_change_revokes_access_and_refresh_tokens(
    db_session: AsyncSession,
) -> None:
    user = User(
        email=f"{uuid4().hex}@example.test",
        full_name="Authentication Test User",
        hashed_password=hash_password("OldPassword123!"),
    )

    db_session.add(user)
    await db_session.flush()

    user_repository = SQLAlchemyUserRepository(db_session)
    refresh_token_repository = SQLAlchemyRefreshTokenRepository(db_session)

    auth_service = AuthService(
        user_repository,
        refresh_token_repository,
    )

    user_service = UserService(
        user_repository,
        refresh_token_repository,
    )

    old_access_token, old_refresh_token = await auth_service.login(
        email=user.email,
        password="OldPassword123!",
    )

    authenticated_user = await get_current_user(
        token=old_access_token,
        session=db_session,
    )

    assert authenticated_user.id == user.id
    assert authenticated_user.token_version == 0

    await user_service.change_password(
        authenticated_user,
        current_password="OldPassword123!",
        new_password="NewPassword123!",
    )

    assert user.token_version == 1

    with pytest.raises(UnauthorizedException):
        await get_current_user(
            token=old_access_token,
            session=db_session,
        )

    with pytest.raises(UnauthorizedException):
        await auth_service.refresh(
            refresh_token=old_refresh_token,
        )

    new_access_token, _ = await auth_service.login(
        email=user.email,
        password="NewPassword123!",
    )

    new_authenticated_user = await get_current_user(
        token=new_access_token,
        session=db_session,
    )

    assert new_authenticated_user.id == user.id
    assert new_authenticated_user.token_version == 1
