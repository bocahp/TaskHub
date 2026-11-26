
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.sqlalchemy_refresh_token import (
    SQLAlchemyRefreshTokenRepository,
)
from app.repositories.sqlalchemy_user import SQLAlchemyUserRepository


@pytest.mark.anyio
async def test_create_and_get_user_by_email(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyUserRepository(db_session)
    email = f"{uuid4().hex}@example.test"

    user = await repository.create_user(
        email=email,
        full_name="Authentication Test User",
        hashed_password="test-password-hash",
    )

    assert user.id is not None
    assert user.email == email
    assert user.full_name == "Authentication Test User"

    saved_user = await repository.get_by_email(email)

    assert saved_user is not None
    assert saved_user.id == user.id
    assert saved_user.hashed_password == "test-password-hash"


@pytest.mark.anyio
async def test_create_get_and_revoke_refresh_token(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    _, user_id = task_context
    repository = SQLAlchemyRefreshTokenRepository(db_session)

    jti = uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=7)

    token = await repository.create_refresh_token(
        user_id=user_id,
        jti=jti,
        expires_at=expires_at,
    )

    assert token.id is not None
    assert token.user_id == user_id
    assert token.jti == jti
    assert token.revoked_at is None

    saved_token = await repository.get_by_jti(jti)

    assert saved_token is not None
    assert saved_token.id == token.id
    assert saved_token.expires_at == expires_at

    revoked_token = await repository.revoke(saved_token)

    assert revoked_token.revoked_at is not None

    saved_revoked_token = await repository.get_by_jti(jti)

    assert saved_revoked_token is not None
    assert saved_revoked_token.revoked_at is not None


@pytest.mark.anyio
async def test_revoke_all_refresh_tokens_for_user(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    _, user_id = task_context
    repository = SQLAlchemyRefreshTokenRepository(db_session)

    first_jti = uuid4()
    second_jti = uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=7)

    await repository.create_refresh_token(
        user_id=user_id,
        jti=first_jti,
        expires_at=expires_at,
    )

    await repository.create_refresh_token(
        user_id=user_id,
        jti=second_jti,
        expires_at=expires_at,
    )

    revoked_count = await repository.revoke_all_for_user(user_id)

    assert revoked_count == 2

    first_token = await repository.get_by_jti(first_jti)
    second_token = await repository.get_by_jti(second_jti)

    assert first_token is not None
    assert first_token.revoked_at is not None

    assert second_token is not None
    assert second_token.revoked_at is not None

@pytest.mark.anyio
async def test_get_by_jti_for_update(
    db_session: AsyncSession,
    task_context: tuple[UUID, UUID],
) -> None:
    _, user_id = task_context
    repository = SQLAlchemyRefreshTokenRepository(db_session)

    jti = uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=7)

    token = await repository.create_refresh_token(
        user_id=user_id,
        jti=jti,
        expires_at=expires_at,
    )

    locked_token = await repository.get_by_jti_for_update(jti)

    assert locked_token is not None
    assert locked_token.id == token.id
    assert locked_token.jti == jti
    assert locked_token.revoked_at is None
