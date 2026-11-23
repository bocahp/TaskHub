
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.repositories.base import BaseRepository


class SQLAlchemyRefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshToken)

    async def create_refresh_token(
        self,
        *,
        user_id: UUID,
        jti: UUID,
        expires_at: datetime,
    ) -> RefreshToken:
        return await self.create(
            {
                "user_id": user_id,
                "jti": jti,
                "expires_at": expires_at,
            }
        )

    async def get_by_jti(self, jti: UUID) -> RefreshToken | None:
        statement = select(RefreshToken).where(RefreshToken.jti == jti)

        result = await self.session.scalars(statement)

        return result.one_or_none()

    async def get_by_jti_for_update(
        self,
        jti: UUID,
    ) -> RefreshToken | None:
        statement = (
            select(RefreshToken)
            .where(RefreshToken.jti == jti)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        result = await self.session.scalars(statement)

        return result.one_or_none()

    async def revoke(self, token: RefreshToken) -> RefreshToken:
        if token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)

        return await self.update(token)

    async def revoke_all_for_user(self, user_id: UUID) -> int:
        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
            .returning(RefreshToken.id)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.scalars(statement)

        return len(result.all())
