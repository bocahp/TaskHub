
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class SQLAlchemyUserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email)

        result = await self.session.scalars(statement)

        return result.one_or_none()

    async def create_user(
        self,
        *,
        email: str,
        full_name: str,
        hashed_password: str,
    ) -> User:
        return await self.create(
            {
                "email": email,
                "full_name": full_name,
                "hashed_password": hashed_password,
            }
        )
